import type {
  Assessment,
  CaseDetail,
  Clause,
  CaseSummary,
  LookupAnswer,
  Policy,
  PolicyVersion,
  RunEvent,
  UploadPolicyInput, DraftReview, DraftReviewInput, Publication,
} from "./types";

export interface NewCaseInput {
  text: string;
  business_area: string;
  as_of: string;
}

export interface ReviewInput {
  disposition: "accepted" | "challenged" | "information_requested";
  rationale: string;
}

export interface HypotheticalChange {
  fact_key: string;
  value: string;
}

/* One seam for fixture and live backends. Components never call fetch directly. */
export interface ComplianceApi {
  readonly mode: "fixture" | "http";
  listCases(): Promise<CaseSummary[]>;
  getCase(caseId: string): Promise<CaseDetail>;
  createCase(input: NewCaseInput): Promise<CaseDetail>;
  addMessage(caseId: string, text: string): Promise<void>;
  startRun(caseId: string): Promise<{ run_id: string }>;
  /* Streams events; returns an unsubscribe. afterSequence replays only newer events. */
  subscribeRun(
    runId: string,
    onEvent: (event: RunEvent) => void,
    afterSequence?: number,
  ): () => void;
  /** Up to three answers, each at most 4,000 characters; null means unknown. */
  answerClarification(runId: string, answers: Record<string, string | null>, finishLocalReview?: boolean): Promise<void>;
  cancelRun(runId: string): Promise<void>;
  createBranch(caseId: string, changes: HypotheticalChange[]): Promise<Assessment>;
  submitReview(caseId: string, runId: string, input: ReviewInput): Promise<void>;
  listPolicies(): Promise<Policy[]>;
  getPolicyVersion(versionId: string): Promise<PolicyVersion>;
  getClause(clauseId: string): Promise<Clause>;
  lookup(question: string): Promise<LookupAnswer>;
  uploadPolicy(file: File, metadata: UploadPolicyInput): Promise<DraftReview>;
  getDraftReview(versionId: string): Promise<DraftReview>;
  saveDraftReview(versionId: string, input: DraftReviewInput): Promise<DraftReview>;
  publishPolicy(versionId: string, expectedRevision: number): Promise<Publication>;
}
