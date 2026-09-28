import { afterEach, expect, it, vi } from "vitest";
import { HttpApi } from "./httpApi";
import type { RunEvent } from "./types";

class FakeSource {
  static latest: FakeSource;
  listeners = new Map<string, EventListener>();
  close = vi.fn();
  constructor(public url: string) { FakeSource.latest = this; }
  addEventListener(type: string, listener: EventListener) { this.listeners.set(type, listener); }
  emit(type: string, data: string) { this.listeners.get(type)?.(new MessageEvent(type, { data })); }
}

const event: RunEvent = { schema_version: "1.0", event_id: "event-1", run_id: "run-1", sequence: 1,
  type: "retrieval.completed", occurred_at: "2026-09-27T00:00:00Z", payload: {} };

afterEach(() => vi.unstubAllGlobals());

it("ignores malformed, wrong-run and mismatched event payloads", () => {
  vi.stubGlobal("EventSource", FakeSource);
  const received = vi.fn();
  new HttpApi().subscribeRun("run-1", received);
  const source = FakeSource.latest;
  for (const bad of [null, [], {}, { ...event, run_id: "another-run" },
    { ...event, sequence: 0 }, { ...event, sequence: 1.5 }, { ...event, sequence: "1" },
    { ...event, payload: [] }, { ...event, payload: null },
    { ...event, occurred_at: "not-a-date" }, { ...event, type: "run.completed" },
    { ...event, event_id: "" }, { ...event, schema_version: "2.0" }, { ...event, schema_version: undefined }]) {
    source.emit(event.type, JSON.stringify(bad));
  }
  source.emit(event.type, "{bad json");
  expect(received).not.toHaveBeenCalled();
  expect(source.close).not.toHaveBeenCalled();
  source.emit(event.type, JSON.stringify(event));
  expect(received).toHaveBeenCalledExactlyOnceWith(event);
});

it("passes reconnect cursor and closes on valid terminal events and cleanup", () => {
  vi.stubGlobal("EventSource", FakeSource);
  const received = vi.fn();
  const stop = new HttpApi().subscribeRun("run-1", received, 7);
  const source = FakeSource.latest;
  expect(source.url).toContain("?after=7");
  source.emit("run.completed", JSON.stringify({ ...event, type: "run.completed", sequence: 8 }));
  expect(received).toHaveBeenCalledTimes(1);
  expect(source.close).toHaveBeenCalledTimes(1);
  stop();
  expect(source.close).toHaveBeenCalledTimes(2);
});
