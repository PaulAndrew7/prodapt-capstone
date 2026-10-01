/*
  The companion's expressions. A mode from the controller maps to one expression; the
  assessing stage picks a finer one per workflow stage. Each expression is a full look:
  face parts, a hand pose, one emote, a head pose and a movement style. Nothing here
  reads the user's state; expressions follow real run events only.
*/
import type { AgentRole } from "@/lib/api/types";
import type { RunPhase } from "@/lib/events/runStore";
import type { AvatarMode } from "./controller";

export type Eyes = "open" | "happy" | "sleep" | "sparkle" | "wide" | "squint" | "shine";
export type Mouth = "cat" | "smile" | "open" | "pout" | "o" | "grin" | "wavy" | "flat";
export type Brows = "neutral" | "raised" | "focused" | "worried" | "determined";
export type Hands = "none" | "chin" | "pray" | "fists" | "magnifier" | "point" | "paper";
export type Emote = "none" | "dots" | "question" | "exclaim" | "sparkles" | "heart" | "zz" | "sweat" | "thought" | "bulb" | "check";
/* Movement layered on the head pose by the frame loop. */
export type Move = "still" | "sway" | "bounce" | "hop" | "tremble" | "nod" | "scan";

export type Look = {
  eyes: Eyes;
  mouth: Mouth;
  brows: Brows;
  hands: Hands;
  emote: Emote;
  move: Move;
  /* Head tilt (deg), lean (down, px), turn (sideways, px) and gaze offset. */
  tilt: number;
  lean: number;
  turn: number;
  gx: number;
  gy: number;
};

export type Expression =
  | "idle"
  | "listening"
  | "cheerful"
  | "working"
  | "eager"
  | "searching"
  | "thinking"
  | "worried"
  | "scrutinizing"
  | "inspired"
  | "pleading"
  | "proud"
  | "reading"
  | "sleepy";

const base = { move: "still", tilt: 0, lean: 0, turn: 0, gx: 0, gy: 0, hands: "none", emote: "none" } as const;

export const LOOKS: Record<Expression, Look> = {
  idle: { ...base, eyes: "open", mouth: "cat", brows: "neutral", move: "sway" },
  listening: { ...base, eyes: "open", mouth: "smile", brows: "raised", tilt: 3, lean: 2.5, gx: -0.5, gy: 2.8 },
  cheerful: { ...base, eyes: "happy", mouth: "open", brows: "raised", emote: "heart", move: "bounce", tilt: -2 },
  working: { ...base, eyes: "open", mouth: "pout", brows: "focused", emote: "dots", move: "scan", lean: 2, gy: 2 },
  eager: { ...base, eyes: "sparkle", mouth: "grin", brows: "raised", hands: "fists", emote: "exclaim", move: "hop", tilt: -3 },
  searching: { ...base, eyes: "wide", mouth: "o", brows: "focused", hands: "magnifier", move: "scan", tilt: 4, turn: 2 },
  thinking: { ...base, eyes: "open", mouth: "pout", brows: "raised", hands: "chin", emote: "thought", move: "sway", tilt: -7, gx: -2.5, gy: -3.2 },
  worried: { ...base, eyes: "wide", mouth: "wavy", brows: "worried", hands: "pray", emote: "sweat", move: "tremble", tilt: 3, lean: 1.5 },
  scrutinizing: { ...base, eyes: "squint", mouth: "flat", brows: "determined", hands: "paper", emote: "check", move: "nod", lean: 2, gy: 3.2 },
  inspired: { ...base, eyes: "sparkle", mouth: "grin", brows: "raised", hands: "point", emote: "bulb", move: "bounce", tilt: 5, lean: -1 },
  pleading: { ...base, eyes: "shine", mouth: "o", brows: "worried", hands: "pray", emote: "question", move: "sway", tilt: -9, turn: -1.5, gx: -3.2, gy: -1 },
  proud: { ...base, eyes: "happy", mouth: "grin", brows: "raised", hands: "fists", emote: "sparkles", move: "hop", tilt: 5, lean: -1 },
  reading: { ...base, eyes: "open", mouth: "smile", brows: "neutral", tilt: 4, lean: 0.5, turn: 3, gx: 4, gy: 0.5 },
  sleepy: { ...base, eyes: "sleep", mouth: "pout", brows: "neutral", emote: "zz", tilt: -6, lean: 4 },
};

export const MODE_EXPRESSION: Record<AvatarMode, Expression> = {
  resting: "idle",
  attending: "listening",
  acknowledging: "cheerful",
  working: "working",
  waiting_for_user: "pleading",
  presenting: "proud",
  evidence_focus: "reading",
  unavailable: "sleepy",
};

/*
  The assessing stage: one expression per workflow stage, from the same events as the stage
  track. `finishing` is the moment after the last stage completes and before the result lands.
*/
export function stageExpression(phase: RunPhase, active: AgentRole | null, finishing = false): Expression {
  if (phase === "waiting_for_user") return "pleading";
  if (phase === "completed" || (phase === "running" && finishing)) return "proud";
  if (phase === "queued" || !active) return "eager";
  switch (active) {
    case "retrieval":
      return "searching";
    case "analysis":
      return "thinking";
    case "risk":
      return "worried";
    case "validation":
      return "scrutinizing";
    case "recommendation":
      return "inspired";
  }
}
