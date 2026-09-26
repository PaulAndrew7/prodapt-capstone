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
  CaseSummary,
  LookupAnswer,
  Policy,
  PolicyVersion,
  RunEvent,
} from "./types";

const BASE = "/api/v1";

async function request<T>(path: string, init?: RequestInit & { idempotencyKey?: string }): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set("Accept", "application/json");
  if (init?.body) headers.set("Content-Type", "application/json");
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
  "run.completed",
  "run.failed",
  "run.canceled",
];

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
  subscribeRun(runId: string, onEvent: (e: RunEvent) => void) {
    const source = new EventSource(`${BASE}/runs/${encodeURIComponent(runId)}/events`, {
      withCredentials: true,
    });
    const handler = (msg: MessageEvent<string>) => {
      try {
        onEvent(JSON.parse(msg.data) as RunEvent);
      } catch {
        /* Malformed event: ignore; status reconciliation happens via getCase. */
      }
    };
    EVENT_TYPES.forEach((t) => source.addEventListener(t, handler as EventListener));
    return () => source.close();
  }
  answerClarification(runId: string, answers: Record<string, string | null>) {
    return request<void>(`/runs/${encodeURIComponent(runId)}/resume`, {
      method: "POST",
      body: JSON.stringify({ answers }),
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
  lookup(question: string) {
    /* Evidence search is POST /search; the cited answer is POST /lookup (F06). */
    return request<LookupAnswer>("/lookup", {
      method: "POST",
      body: JSON.stringify({ question }),
    });
  }
}
