import type { AssessmentStatus, FactOrigin, RequirementStatus } from "@/lib/api/types";

/* Verdict copy. No dashes, no percentages, sentence case with a full stop. */
export const verdictCopy: Record<AssessmentStatus, string> = {
  non_compliant: "Non-compliant.",
  compliant_within_scope: "Compliant within scope.",
  insufficient_information: "Not enough to decide.",
  conflicting_policy: "Policies conflict.",
  out_of_scope: "Outside the policy corpus.",
};

export const statusLabel: Record<AssessmentStatus, string> = {
  non_compliant: "Non-compliant",
  compliant_within_scope: "Compliant within scope",
  insufficient_information: "Not enough information",
  conflicting_policy: "Policies conflict",
  out_of_scope: "Out of scope",
};

export type Tone = "violated" | "unknown" | "met" | "muted" | "conflict";

export const assessmentTone: Record<AssessmentStatus, Tone> = {
  non_compliant: "violated",
  compliant_within_scope: "met",
  insufficient_information: "unknown",
  conflicting_policy: "conflict",
  out_of_scope: "muted",
};

export const requirementLabel: Record<RequirementStatus, string> = {
  met: "Met",
  violated: "Violated",
  unknown: "Unknown",
  not_applicable: "Not applicable",
  conflict: "Conflict",
};

export const requirementTone: Record<RequirementStatus, Tone> = {
  met: "met",
  violated: "violated",
  unknown: "unknown",
  not_applicable: "muted",
  conflict: "conflict",
};

export const factOriginLabel: Record<FactOrigin, string> = {
  provided: "Provided",
  inferred: "Inferred",
  unknown: "Unknown",
};

export const toneText: Record<Tone, string> = {
  violated: "text-violated",
  unknown: "text-unknown",
  met: "text-met",
  muted: "text-muted",
  conflict: "text-ink",
};
