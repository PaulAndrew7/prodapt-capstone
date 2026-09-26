import { describe, expect, it } from "vitest";
import { ACK_COOLDOWN_MS, avatarReducer, initialAvatarState, type AvatarEvent, type AvatarState } from "./controller";

const run = (events: AvatarEvent[], from: AvatarState = initialAvatarState) => events.reduce(avatarReducer, from);

describe("avatarReducer", () => {
  it("attends while the composer has focus and rests when it leaves", () => {
    expect(run([{ type: "composer_focus" }]).mode).toBe("attending");
    expect(run([{ type: "composer_focus" }, { type: "composer_blur" }]).mode).toBe("resting");
  });

  it("acknowledges an accepted message, then works once the run starts", () => {
    const s = run([
      { type: "message_accepted", at: 1000 },
      { type: "run_phase", phase: "queued", at: 1100 },
    ]);
    expect(s.mode).toBe("acknowledging");
    expect(avatarReducer(s, { type: "animation_done", at: 2200 }).mode).toBe("working");
  });

  it("rate-limits repeated acknowledgments", () => {
    const s = run([
      { type: "message_accepted", at: 1000 },
      { type: "animation_done", at: 2000 },
      { type: "message_accepted", at: 1000 + ACK_COOLDOWN_MS - 1 },
    ]);
    expect(s.mode).toBe("resting");
  });

  it("waits for the user only on a real clarification", () => {
    const s = run([
      { type: "run_phase", phase: "running", at: 1 },
      { type: "run_phase", phase: "waiting_for_user", at: 2 },
    ]);
    expect(s.mode).toBe("waiting_for_user");
  });

  it("presents once when a live run completes, not when a finished case is opened", () => {
    const live = run([
      { type: "run_phase", phase: "running", at: 1 },
      { type: "run_phase", phase: "completed", at: 2 },
    ]);
    expect(live.mode).toBe("presenting");
    expect(avatarReducer(live, { type: "animation_done", at: 3 }).mode).toBe("resting");
    expect(run([{ type: "run_phase", phase: "completed", at: 1 }]).mode).toBe("resting");
  });

  it("focuses evidence while the drawer is open and returns afterwards", () => {
    const s = run([
      { type: "run_phase", phase: "running", at: 1 },
      { type: "evidence_open" },
    ]);
    expect(s.mode).toBe("evidence_focus");
    expect(avatarReducer(s, { type: "evidence_close" }).mode).toBe("working");
  });

  it("stays unavailable after a render failure", () => {
    const s = run([{ type: "render_failed" }, { type: "composer_focus" }, { type: "evidence_open" }]);
    expect(s.mode).toBe("unavailable");
  });
});
