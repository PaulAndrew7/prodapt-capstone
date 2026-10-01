import { describe, expect, it } from "vitest";
import type { AvatarMode } from "./controller";
import { LOOKS, MODE_EXPRESSION, stageExpression } from "./expressions";

describe("stageExpression", () => {
  it("acts out the stage the run is actually in", () => {
    expect(stageExpression("queued", null)).toBe("eager");
    expect(stageExpression("running", "retrieval")).toBe("searching");
    expect(stageExpression("running", "analysis")).toBe("thinking");
    expect(stageExpression("running", "risk")).toBe("worried");
    expect(stageExpression("running", "validation")).toBe("scrutinizing");
    expect(stageExpression("running", "recommendation")).toBe("inspired");
  });

  it("asks for answers while waiting, and celebrates only once every stage is done", () => {
    expect(stageExpression("waiting_for_user", null)).toBe("pleading");
    expect(stageExpression("running", null, true)).toBe("proud");
    expect(stageExpression("running", null, false)).toBe("eager");
    expect(stageExpression("completed", null)).toBe("proud");
  });
});

describe("MODE_EXPRESSION", () => {
  it("gives every controller mode a defined look", () => {
    const modes: AvatarMode[] = ["resting", "attending", "acknowledging", "working", "waiting_for_user", "presenting", "evidence_focus", "unavailable"];
    for (const m of modes) expect(LOOKS[MODE_EXPRESSION[m]]).toBeDefined();
  });
});
