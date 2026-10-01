/*
  HttpApi: the live backend (IMPLEMENTATION_PLAN.md section 5.4). Same-origin cookies,
  no tokens in URLs. EventSource reconnects on its own and sends Last-Event-ID;
  the run store deduplicates whatever is replayed.
*/
import type { ComplianceApi, HypotheticalChange, NewCaseInput, ReviewInput } from "./client";
import type {
  ApiError,
  Assessment,
  CaseDetail,
  Clause,
  CaseSummary,
  LookupAnswer,
  Policy,
  PolicyVersion,
  RunEvent,
  UploadPolicyInput, DraftReview, DraftReviewInput, Publication, PolicyGraph, GraphInput,
} from "./types";

const BASE = "/api/v1";

async function request<T>(path: string, init?: RequestInit & { idempotencyKey?: string }): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set("Accept", "application/json");
  if (init?.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  if (init?.idempotencyKey) headers.set("Idempotency-Key", init.idempotencyKey);
  const res = await fetch(`${BASE}${path}`, { ...init, headers, credentials: "same-origin" });
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as ApiError | null;
    throw Object.assign(new Error(body?.message ?? `Request failed (${res.status})`), {
      code: body?.code ?? String(res.status),
      retryable: body?.retryable ?? res.status >= 500,
      request_id: body?.request_id,
    });
  }
  return (await res.json()) as T;
}

const TERMINAL = new Set<RunEvent["type"]>(["run.completed", "run.failed", "run.canceled"]);

const EVENT_TYPES: RunEvent["type"][] = [
  "run.queued",
  "run.started",
  "retrieval.completed",
  "analysis.completed",
  "risk.completed",
  "validation.completed",
  "recommendation.completed",
  "clarification.required",
  "run.resumed",
  "run.fallback",
  "run.completed",
  "run.failed",
  "run.canceled",
];

function isRunEvent(value: unknown, runId: string): value is RunEvent {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const event = value as Partial<RunEvent>;
  return event.schema_version === "1.0" && event.run_id === runId
    && typeof event.event_id === "string" && event.event_id.trim().length > 0
    && Number.isSafeInteger(event.sequence) && event.sequence! > 0
    && typeof event.occurred_at === "string" && Number.isFinite(Date.parse(event.occurred_at))
    && EVENT_TYPES.includes(event.type!)
    && event.payload !== null && typeof event.payload === "object" && !Array.isArray(event.payload);
}

export class HttpApi implements ComplianceApi {
  readonly mode = "http" as const;

  listCases() {
    return request<{ items: CaseSummary[] }>("/cases").then((r) => r.items);
  }
  getCase(caseId: string) {
    return request<CaseDetail>(`/cases/${encodeURIComponent(caseId)}`);
  }
  createCase(input: NewCaseInput) {
    return request<CaseDetail>("/cases", { method: "POST", body: JSON.stringify(input) });
  }
  addMessage(caseId: string, text: string) {
    return request<void>(`/cases/${encodeURIComponent(caseId)}/messages`, {
      method: "POST",
      body: JSON.stringify({ text }),
    });
  }
  startRun(caseId: string) {
    return request<{ run_id: string }>(`/cases/${encodeURIComponent(caseId)}/runs`, {
      method: "POST",
      idempotencyKey: crypto.randomUUID(),
      body: JSON.stringify({}),
    });
  }
  subscribeRun(runId: string, onEvent: (e: RunEvent) => void, afterSequence = 0) {
    const source = new EventSource(
      `${BASE}/runs/${encodeURIComponent(runId)}/events?after=${afterSequence}`,
      { withCredentials: true },
    );
    const handler = (msg: MessageEvent<string>) => {
      let event: unknown;
      try {
        event = JSON.parse(msg.data);
      } catch {
        return; /* Malformed event: do not corrupt the progress store. */
      }
      if (!isRunEvent(event, runId) || event.type !== msg.type) return;
      onEvent(event);
      /* A finished run sends nothing more; closing stops the browser reconnecting. */
      if (TERMINAL.has(event.type)) source.close();
    };
    EVENT_TYPES.forEach((t) => source.addEventListener(t, handler as EventListener));
    return () => source.close();
  }
  answerClarification(runId: string, answers: Record<string, string | null>, finishLocalReview = false) {
    return request<void>(`/runs/${encodeURIComponent(runId)}/resume`, {
      method: "POST",
      body: JSON.stringify({ answers, ...(finishLocalReview && { finish_local_review: true }) }),
    });
  }
  cancelRun(runId: string) {
    return request<void>(`/runs/${encodeURIComponent(runId)}/cancel`, { method: "POST" });
  }
  createBranch(caseId: string, changes: HypotheticalChange[]) {
    return request<Assessment>(`/cases/${encodeURIComponent(caseId)}/branches`, {
      method: "POST",
      body: JSON.stringify({ changes }),
    });
  }
  submitReview(_caseId: string, runId: string, input: ReviewInput) {
    return request<void>(`/runs/${encodeURIComponent(runId)}/reviews`, {
      method: "POST",
      body: JSON.stringify(input),
    });
  }
  listPolicies() {
    return request<{ items: Policy[] }>("/policies").then((r) => r.items);
  }
  getPolicyVersion(versionId: string) {
    return request<PolicyVersion>(`/policy-versions/${encodeURIComponent(versionId)}`);
  }
  getClause(clauseId: string) {
    return request<Clause>(`/clauses/${encodeURIComponent(clauseId)}`);
  }
  lookup(question: string) {
    /* Evidence search is POST /search; the cited answer is POST /lookup (F06). */
    return request<LookupAnswer>("/lookup", {
      method: "POST",
      body: JSON.stringify({ question }),
    });
  }
  uploadPolicy(file: File, metadata: UploadPolicyInput) {
    const body = new FormData();
    body.append("file", file);
    body.append("metadata", JSON.stringify(metadata));
    return request<DraftReview>("/admin/policies/upload", { method: "POST", body });
  }
  getDraftReview(versionId: string) {
    return request<DraftReview>(`/admin/policy-versions/${encodeURIComponent(versionId)}/review`);
  }
  saveDraftReview(versionId: string, input: DraftReviewInput) {
    return request<DraftReview>(`/admin/policy-versions/${encodeURIComponent(versionId)}/review`, { method: "POST", body: JSON.stringify(input) });
  }
  publishPolicy(versionId: string, expectedRevision: number) {
    return request<Publication>(`/admin/policy-versions/${encodeURIComponent(versionId)}/publish`, { method: "POST", body: JSON.stringify({ expected_revision: expectedRevision }) });
  }
  getPolicyGraph(input: GraphInput) {
    const params = new URLSearchParams(Object.entries(input).filter(([, value]) => Boolean(value)) as [string, string][]);
    return request<PolicyGraph>(`/policy-graph?${params}`);
  }
}
