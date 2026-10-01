/*
  FixtureApi: plays authored scenarios with realistic timing so the UI can be built
  before the backend exists. Every screen shows a "Fixture data" tag in this mode.
*/
import type { ComplianceApi, NewCaseInput, ReviewInput } from "./client";
import type { Assessment, CaseDetail, CaseSummary, RunEvent, UploadPolicyInput, DraftReview, DraftReviewInput, Publication, PolicyGraph, GraphInput } from "./types";
import { caseDetails, caseSummaries } from "@/fixtures/cases";
import { clauseById, policies, policyVersions, SNAPSHOT_ID } from "@/fixtures/policies";
import { lookupAnswer } from "@/fixtures/lookup";
import {
  vendorAgentMessages,
  vendorAssessment,
  vendorFactsFinal,
  vendorFactsInitial,
  vendorHypothetical,
  vendorQuestions,
  vendorScriptAfterClarification,
  vendorScriptBeforeClarification,
  type ScriptStep,
} from "@/fixtures/vendorCase";

const delay = (ms: number) => new Promise((r) => setTimeout(r, ms));

type RunRecord = {
  runId: string;
  caseId: string;
  kind: "vendor" | "out_of_scope";
  events: RunEvent[];
  listeners: Set<(e: RunEvent) => void>;
  timers: number[];
  state: "running" | "paused" | "done" | "canceled";
};

function isVendorLike(text: string) {
  return /vendor|shar|customer (data|records)|third party|analytics/i.test(text);
}

function outOfScopeAssessment(runId: string, asOf: string): Assessment {
  return {
    schema_version: "1.0",
    run_id: runId,
    case_revision_id: `${runId}_rev`,
    policy_snapshot_id: SNAPSHOT_ID,
    as_of: asOf,
    status: "out_of_scope",
    scope: "Kestrel Mutual demo policy corpus",
    summary: "No policy in the demo corpus sets requirements for this activity. This is not a compliant result.",
    findings: [],
    citations: [],
    risks: [],
    recommendations: [],
    limitations: ["Retrieval found no applicable clause in snapshot_demo_v1. Ask the policy owner which policy applies."],
    review_state: "unreviewed",
  };
}

export class FixtureApi implements ComplianceApi {
  readonly mode = "fixture" as const;
  private cases = new Map<string, CaseDetail>(Object.entries(structuredClone(caseDetails)));
  private summaries: CaseSummary[] = structuredClone(caseSummaries);
  private runs = new Map<string, RunRecord>();

  async listCases() {
    await delay(220);
    return this.summaries
      .map((s) => {
        const live = this.cases.get(s.id);
        return live
          ? { ...s, status: live.status, run_state: live.run_state, unresolved_facts: live.unresolved_facts, updated_at: live.updated_at }
          : s;
      })
      .sort((a, b) => b.updated_at.localeCompare(a.updated_at));
  }

  async getCase(caseId: string) {
    await delay(180);
    const c = this.cases.get(caseId);
    if (!c) throw Object.assign(new Error("Case not found"), { code: "not_found", retryable: false });
    return structuredClone(c);
  }

  async createCase(input: NewCaseInput) {
    await delay(260);
    const id = `case_${Date.now().toString(36)}`;
    const vendor = isVendorLike(input.text);
    const detail: CaseDetail = {
      id,
      title: vendor ? "Share customer records with a new analytics vendor" : input.text.slice(0, 64),
      owner: "You",
      business_area: input.business_area,
      status: null,
      run_state: null,
      unresolved_facts: vendor ? 2 : 0,
      review_state: "unreviewed",
      updated_at: new Date().toISOString(),
      as_of: input.as_of,
      scope: vendor ? "Data sharing and vendor policies" : "Full demo corpus",
      scenario_text: input.text,
      policy_snapshot_id: SNAPSHOT_ID,
      messages: [{ id: `${id}_m1`, role: "user", text: input.text, created_at: new Date().toISOString() }],
      facts: vendor ? structuredClone(vendorFactsInitial) : [],
      latest_run_id: null,
      assessment: null,
      pending_questions: [],
      agent_messages: [],
    };
    this.cases.set(id, detail);
    this.summaries.unshift({
      id,
      title: detail.title,
      owner: detail.owner,
      business_area: detail.business_area,
      status: null,
      run_state: null,
      unresolved_facts: detail.unresolved_facts,
      review_state: "unreviewed",
      updated_at: detail.updated_at,
    });
    return structuredClone(detail);
  }

  async addMessage(caseId: string, text: string) {
    await delay(120);
    const c = this.cases.get(caseId);
    if (!c) throw new Error("Case not found");
    c.messages.push({ id: `${c.id}_m${c.messages.length + 1}`, role: "user", text, created_at: new Date().toISOString() });
  }

  async startRun(caseId: string) {
    await delay(140);
    const c = this.cases.get(caseId);
    if (!c) throw new Error("Case not found");
    const runId = `run_${Date.now().toString(36)}`;
    const kind = isVendorLike(c.scenario_text) ? "vendor" : "out_of_scope";
    const rec: RunRecord = { runId, caseId, kind, events: [], listeners: new Set(), timers: [], state: "running" };
    this.runs.set(runId, rec);
    c.latest_run_id = runId;
    c.run_state = "queued";
    c.assessment = null;
    const script: ScriptStep[] =
      kind === "vendor"
        ? vendorScriptBeforeClarification
        : [
            { after_ms: 0, type: "run.queued" },
            { after_ms: 350, type: "run.started" },
            { after_ms: 1300, type: "retrieval.completed", payload: { clauses: 0, policies: 0 } },
            { after_ms: 500, type: "run.completed", payload: { status: "out_of_scope" } },
          ];
    this.play(rec, script);
    return { run_id: runId };
  }

  subscribeRun(runId: string, onEvent: (e: RunEvent) => void, afterSequence = 0) {
    const rec = this.runs.get(runId);
    if (!rec) return () => {};
    rec.events.filter((e) => e.sequence > afterSequence).forEach((e) => onEvent(e));
    rec.listeners.add(onEvent);
    return () => rec.listeners.delete(onEvent);
  }

  async answerClarification(runId: string, answers: Record<string, string | null>) {
    await delay(200);
    const rec = this.runs.get(runId);
    if (!rec || rec.state !== "paused") throw new Error("Run is not waiting for answers");
    const c = this.cases.get(rec.caseId)!;
    const reply = Object.values(answers)
      .map((a) => a ?? "I don’t know.")
      .join(" ");
    c.messages.push({ id: `${c.id}_m${c.messages.length + 1}`, role: "user", text: reply, created_at: new Date().toISOString() });
    c.pending_questions = [];
    c.facts = structuredClone(vendorFactsFinal);
    if (answers.q_vendor_review) {
      const f = c.facts.find((f) => f.key === "vendor_review_status")!;
      f.value = answers.q_vendor_review.startsWith("Yes") ? "Approved" : "Not approved";
      f.origin = "provided";
    }
    if (answers.q_fields === null) {
      const f = c.facts.find((f) => f.key === "fields_shared")!;
      f.value = null;
      f.origin = "unknown";
    }
    rec.state = "running";
    this.play(rec, vendorScriptAfterClarification);
  }

  async cancelRun(runId: string) {
    const rec = this.runs.get(runId);
    if (!rec || rec.state === "done") return;
    rec.timers.forEach((t) => clearTimeout(t));
    rec.state = "canceled";
    const c = this.cases.get(rec.caseId)!;
    c.run_state = "canceled";
    c.pending_questions = [];
    this.emit(rec, "run.canceled", {});
  }

  async createBranch(_caseId: string) {
    await delay(2400);
    return structuredClone(vendorHypothetical);
  }

  async submitReview(caseId: string, _runId: string, input: ReviewInput) {
    await delay(350);
    const c = this.cases.get(caseId);
    if (!c) throw new Error("Case not found");
    if (!input.rationale.trim()) throw Object.assign(new Error("A rationale is required"), { code: "validation", retryable: false });
    c.review_state = input.disposition;
    if (c.assessment) c.assessment.review_state = input.disposition;
    const s = this.summaries.find((x) => x.id === caseId);
    if (s) s.review_state = input.disposition;
  }

  async listPolicies() {
    await delay(200);
    return structuredClone(policies);
  }

  async getPolicyVersion(versionId: string) {
    await delay(160);
    const v = policyVersions[versionId];
    if (v) return structuredClone(v);
    const p = policies.find((p) => p.versions.some((x) => x.id === versionId));
    const summary = p?.versions.find((x) => x.id === versionId);
    if (!p || !summary) throw Object.assign(new Error("Policy version not found"), { code: "not_found", retryable: false });
    // Listed in the demo corpus, but its clause text is not authored yet.
    return { ...structuredClone(summary), policy_id: p.id, policy_title: p.title, clauses: [], extraction_warnings: [] };
  }

  async getClause(clauseId: string) {
    await delay(80);
    const c = clauseById(clauseId);
    if (!c) throw Object.assign(new Error("Clause not found"), { code: "not_found", retryable: false });
    return structuredClone(c);
  }

  async lookup(question: string) {
    await delay(1600);
    // Fixture mode answers every question with the authored data-sharing lookup.
    return { ...structuredClone(lookupAnswer), question };
  }

  async uploadPolicy(_file: File, _metadata: UploadPolicyInput): Promise<DraftReview> { throw new Error("Policy upload requires the live API."); }
  async getDraftReview(_versionId: string): Promise<DraftReview> { throw new Error("Policy review requires the live API."); }
  async saveDraftReview(_versionId: string, _input: DraftReviewInput): Promise<DraftReview> { throw new Error("Policy review requires the live API."); }
  async publishPolicy(_versionId: string, _revision: number): Promise<Publication> { throw new Error("Policy publication requires the live API."); }
  async getPolicyGraph(_input: GraphInput): Promise<PolicyGraph> { throw new Error("The stored knowledge graph requires the live API."); }

  private play(rec: RunRecord, script: ScriptStep[]) {
    let at = 0;
    for (const step of script) {
      at += step.after_ms;
      const t = window.setTimeout(() => this.emit(rec, step.type, step.payload ?? {}), at);
      rec.timers.push(t);
    }
  }

  private emit(rec: RunRecord, type: RunEvent["type"], payload: Record<string, unknown>) {
    const c = this.cases.get(rec.caseId)!;
    const event: RunEvent = {
      event_id: `evt_${rec.runId}_${rec.events.length + 1}`,
      run_id: rec.runId,
      sequence: rec.events.length + 1,
      occurred_at: new Date().toISOString(),
      schema_version: "1.0",
      type,
      payload,
    };
    switch (type) {
      case "run.started":
      case "run.resumed":
        c.run_state = "running";
        break;
      case "clarification.required":
        rec.state = "paused";
        c.run_state = "waiting_for_user";
        c.pending_questions = structuredClone(vendorQuestions);
        c.messages.push({
          id: `${c.id}_m${c.messages.length + 1}`,
          role: "assistant",
          text: "Two facts decide this case. I have two questions before I finish the assessment.",
          created_at: new Date().toISOString(),
        });
        break;
      case "run.completed": {
        rec.state = "done";
        c.run_state = "completed";
        if (rec.kind === "vendor") {
          const a = structuredClone(vendorAssessment);
          a.run_id = rec.runId;
          a.as_of = c.as_of;
          c.assessment = a;
          c.agent_messages = structuredClone(vendorAgentMessages);
          c.unresolved_facts = c.facts.filter((f) => f.origin === "unknown").length;
        } else {
          c.assessment = outOfScopeAssessment(rec.runId, c.as_of);
          c.unresolved_facts = 0;
        }
        c.status = c.assessment.status;
        break;
      }
    }
    c.updated_at = event.occurred_at;
    rec.events.push(event);
    rec.listeners.forEach((l) => l(event));
  }
}
