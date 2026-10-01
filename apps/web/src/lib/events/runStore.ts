/*
  Single deduplicating store for run events (IMPLEMENTATION_PLAN.md section 5.5).
  The workspace, the stage track and the avatar controller all read from here;
  nothing subscribes to the network stream directly.
*/
import { create } from "zustand";
import type { AgentRole, RunEvent } from "@/lib/api/types";

export const STAGES: { role: AgentRole; label: string; done: RunEvent["type"] }[] = [
  { role: "retrieval", label: "Retrieve", done: "retrieval.completed" },
  { role: "analysis", label: "Analyze", done: "analysis.completed" },
  { role: "risk", label: "Assess risk", done: "risk.completed" },
  { role: "validation", label: "Validate", done: "validation.completed" },
  { role: "recommendation", label: "Recommend", done: "recommendation.completed" },
];

export type StageStatus = "pending" | "active" | "done" | "skipped";

export type RunPhase =
  | "idle"
  | "queued"
  | "running"
  | "waiting_for_user"
  | "completed"
  | "failed"
  | "canceled";

type RunView = {
  events: RunEvent[];
  lastSequence: number;
  seen: Set<string>;
};

type RunStore = {
  runs: Record<string, RunView>;
  ingest: (event: RunEvent) => boolean;
  reset: (runId: string) => void;
};

export const useRunStore = create<RunStore>((set, get) => ({
  runs: {},
  ingest: (event) => {
    if (!Number.isSafeInteger(event.sequence) || event.sequence < 1) return false;
    const current = get().runs[event.run_id] ?? { events: [], lastSequence: 0, seen: new Set<string>() };
    if (current.seen.has(event.event_id) || current.events.some((e) => e.sequence === event.sequence)) return false;
    const seen = new Set(current.seen);
    seen.add(event.event_id);
    const events = [...current.events, event].sort((a, b) => a.sequence - b.sequence);
    set((s) => ({
      runs: {
        ...s.runs,
        [event.run_id]: { events, seen, lastSequence: Math.max(current.lastSequence, event.sequence) },
      },
    }));
    return true;
  },
  reset: (runId) =>
    set((s) => {
      const next = { ...s.runs };
      delete next[runId];
      return { runs: next };
    }),
}));

export function derivePhase(events: RunEvent[]): RunPhase {
  const last = events[events.length - 1];
  if (!last) return "idle";
  switch (last.type) {
    case "run.queued":
      return "queued";
    case "clarification.required":
      return "waiting_for_user";
    case "run.completed":
      return "completed";
    case "run.failed":
      return "failed";
    case "run.canceled":
      return "canceled";
    default:
      return "running";
  }
}

/* Stage status from actual completion events. Clarification restarts every stage. */
export function deriveStages(events: RunEvent[]): Record<AgentRole, StageStatus> {
  const status = Object.fromEntries(STAGES.map((s) => [s.role, "pending"])) as Record<AgentRole, StageStatus>;
  let cursor = -1;
  for (const e of events) {
    if (e.type === "run.started" || e.type === "run.resumed") {
      STAGES.forEach((s) => { status[s.role] = "pending"; });
      cursor = 0;
    }
    if (e.type === "run.fallback") {
      STAGES.forEach((s) => { status[s.role] = s.role === "retrieval" ? "done" : "pending"; });
      cursor = 1;
    }
    const idx = STAGES.findIndex((s) => s.done === e.type);
    if (idx >= 0) {
      status[STAGES[idx].role] = "done";
      cursor = idx + 1;
    }
    if (e.type === "clarification.required") cursor = -1;
    if (e.type === "run.completed" || e.type === "run.failed" || e.type === "run.canceled") {
      STAGES.forEach((s) => {
        if (status[s.role] !== "done") status[s.role] = "skipped";
      });
      cursor = -1;
    }
  }
  if (cursor >= 0 && cursor < STAGES.length) status[STAGES[cursor].role] = "active";
  return status;
}
