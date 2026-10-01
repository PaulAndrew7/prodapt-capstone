import { beforeEach, expect, it } from "vitest";
import type { RunEvent } from "@/lib/api/types";
import { deriveStages, useRunStore } from "./runStore";

const event = (sequence: number, type: RunEvent["type"], id = `event-${sequence}`): RunEvent => ({
  schema_version: "1.0", event_id: id, run_id: "run", sequence, type, occurred_at: "2026-09-27T00:00:00Z", payload: {},
});
beforeEach(() => useRunStore.setState({ runs: {} }));

it("deduplicates event IDs and sequence numbers while retaining late missing events", () => {
  const { ingest } = useRunStore.getState();
  expect(ingest(event(2, "analysis.completed"))).toBe(true);
  expect(ingest(event(2, "analysis.completed"))).toBe(false);
  expect(ingest(event(2, "run.failed", "different-id"))).toBe(false);
  expect(ingest(event(1, "retrieval.completed"))).toBe(true);
  expect(ingest(event(0, "run.failed"))).toBe(false);
  const run = useRunStore.getState().runs.run;
  expect(run.events.map((e) => e.sequence)).toEqual([1, 2]);
  expect(run.lastSequence).toBe(2);
});

it("never invents earlier completion when a later stage arrives", () => {
  const stages = deriveStages([event(1, "validation.completed"), event(2, "run.completed")]);
  expect(stages.validation).toBe("done");
  expect(stages.retrieval).toBe("skipped");
  expect(stages.analysis).toBe("skipped");
  expect(stages.risk).toBe("skipped");
  expect(stages.recommendation).toBe("skipped");
});

it("resets completed stages and starts retrieval again after clarification", () => {
  const history = [event(1, "run.started"), event(2, "retrieval.completed"),
    event(3, "analysis.completed"), event(4, "clarification.required")];
  expect(deriveStages(history).analysis).toBe("done");
  const resumed = [...history, event(5, "run.resumed")];
  expect(deriveStages(resumed)).toEqual({ retrieval: "active", analysis: "pending", risk: "pending", validation: "pending", recommendation: "pending" });
  expect(deriveStages([...resumed, event(6, "retrieval.completed")]).analysis).toBe("active");
});

it("preserves retrieved evidence and resets model stages after fallback", () => {
  const events = [event(1, "run.started"), event(2, "retrieval.completed"),
    event(3, "analysis.completed"), event(4, "validation.completed"), event(5, "run.fallback")];
  expect(deriveStages(events)).toEqual({ retrieval: "done", analysis: "active", risk: "pending", validation: "pending", recommendation: "pending" });
});
