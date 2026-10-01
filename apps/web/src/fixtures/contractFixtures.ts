/*
  The shared contract fixtures in packages/contracts/fixtures/ are generated from these
  web fixtures, so the backend tests and the UI read the same JSON. Regenerate with
  `corepack pnpm --dir apps/web contracts:fixtures`; contracts.test.ts fails on drift.
*/
import type { Assessment, RunEvent } from "@/lib/api/types";
import { coverageGapAssessment } from "./coverageCase";
import { localReviewAssessment } from "./localReviewCase";
import {
  VENDOR_RUN_ID,
  vendorAssessment,
  vendorScriptAfterClarification,
  vendorScriptBeforeClarification,
} from "./vendorCase";

const RUN_START = Date.parse("2026-09-25T09:12:04Z");

export function vendorAssessmentFixture(): Assessment {
  return vendorAssessment;
}

/* The worked run as a gap-free event log with deterministic timestamps. */
export function vendorRunEventsFixture(): RunEvent[] {
  let at = RUN_START;
  return [...vendorScriptBeforeClarification, ...vendorScriptAfterClarification].map((step, i) => {
    at += step.after_ms;
    return {
      event_id: `evt_${VENDOR_RUN_ID}_${i + 1}`,
      run_id: VENDOR_RUN_ID,
      sequence: i + 1,
      occurred_at: new Date(at).toISOString(),
      schema_version: "1.0",
      type: step.type,
      payload: step.payload ?? {},
    };
  });
}

export const CONTRACT_FIXTURES = {
  "assessment.local-review.json": () => localReviewAssessment,
  "assessment.coverage-gap.json": () => coverageGapAssessment,
  "assessment.vendor-sharing.json": vendorAssessmentFixture,
  "run-events.vendor-sharing.json": vendorRunEventsFixture,
} as const;
