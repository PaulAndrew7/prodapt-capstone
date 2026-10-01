import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { AgentRole, CaseDetail, RunEvent } from "@/lib/api/types";
import {
  derivePhase,
  deriveStages,
  STAGES,
  useRunStore,
  type RunPhase,
  type StageStatus,
} from "@/lib/events/runStore";

const EMPTY: RunEvent[] = [];
const REFRESH = new Set<RunEvent["type"]>([
  "clarification.required",
  "run.completed",
  "run.failed",
  "run.canceled",
  "run.resumed",
  "run.fallback",
]);

function fill(status: StageStatus) {
  return Object.fromEntries(STAGES.map((s) => [s.role, status])) as Record<AgentRole, StageStatus>;
}

function phaseFromState(state: CaseDetail["run_state"] | undefined): RunPhase {
  if (!state) return "idle";
  return state;
}

/*
  Subscribes to the case's latest run, feeds the shared run store, and refreshes the
  case record on events that change it. Historical completed runs are not re-streamed.
*/
export function useCaseRun(detail: CaseDetail | undefined) {
  const qc = useQueryClient();
  const runId = detail?.latest_run_id ?? null;
  const events = useRunStore((s) => (runId ? s.runs[runId]?.events : undefined)) ?? EMPTY;
  const ingest = useRunStore((s) => s.ingest);
  const caseId = detail?.id;
  const historical = detail?.run_state === "completed" && events.length === 0;

  useEffect(() => {
    if (!runId || !caseId || historical) return;
    const after = useRunStore.getState().runs[runId]?.lastSequence ?? 0;
    return api.subscribeRun(
      runId,
      (e) => {
        if (ingest(e) && REFRESH.has(e.type)) {
          void qc.invalidateQueries({ queryKey: ["case", caseId] });
          void qc.invalidateQueries({ queryKey: ["cases"] });
        }
      },
      after,
    );
  }, [runId, caseId, historical, ingest, qc]);

  const phase = events.length ? derivePhase(events) : phaseFromState(detail?.run_state);
  const stages = events.length
    ? deriveStages(events)
    : phase === "completed"
      ? fill("done")
      : fill("pending");

  return { runId, events, phase, stages };
}
