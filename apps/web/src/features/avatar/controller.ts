/*
  AvatarController (IMPLEMENTATION_PLAN.md section 11.2). A pure reducer over a typed
  projection of app events. It never calls a model, never infers the user's emotions,
  and reacts only to deliberate input and real workflow state.
*/
import type { RunPhase } from "@/lib/events/runStore";

export type AvatarMode =
  | "resting"
  | "attending"
  | "acknowledging"
  | "working"
  | "waiting_for_user"
  | "presenting"
  | "evidence_focus"
  | "unavailable";

export type AvatarEvent =
  | { type: "composer_focus" }
  | { type: "composer_blur" }
  | { type: "message_accepted"; at: number }
  | { type: "run_phase"; phase: RunPhase; at: number }
  | { type: "evidence_open" }
  | { type: "evidence_close" }
  | { type: "animation_done"; at: number }
  | { type: "render_failed" };

export type AvatarState = {
  mode: AvatarMode;
  phase: RunPhase;
  composerFocused: boolean;
  evidenceOpen: boolean;
  lastAckAt: number;
};

export const initialAvatarState: AvatarState = {
  mode: "resting",
  phase: "idle",
  composerFocused: false,
  evidenceOpen: false,
  lastAckAt: -Infinity,
};

/* Acknowledgments closer together than this are not repeated. */
export const ACK_COOLDOWN_MS = 4000;

function settle(s: AvatarState): AvatarMode {
  if (s.evidenceOpen) return "evidence_focus";
  if (s.phase === "queued" || s.phase === "running") return "working";
  if (s.phase === "waiting_for_user") return "waiting_for_user";
  if (s.composerFocused) return "attending";
  return "resting";
}

export function avatarReducer(s: AvatarState, e: AvatarEvent): AvatarState {
  if (s.mode === "unavailable") return s;
  switch (e.type) {
    case "render_failed":
      return { ...s, mode: "unavailable" };
    case "composer_focus": {
      const n = { ...s, composerFocused: true };
      return transient(s) ? n : { ...n, mode: settle(n) };
    }
    case "composer_blur": {
      const n = { ...s, composerFocused: false };
      return transient(s) ? n : { ...n, mode: settle(n) };
    }
    case "message_accepted":
      if (e.at - s.lastAckAt < ACK_COOLDOWN_MS) return s;
      return { ...s, mode: "acknowledging", lastAckAt: e.at };
    case "run_phase": {
      const n = { ...s, phase: e.phase };
      if (e.phase === "completed" && s.phase !== "completed" && s.phase !== "idle") return { ...n, mode: "presenting" };
      if (s.mode === "acknowledging" && (e.phase === "queued" || e.phase === "running")) return n;
      return { ...n, mode: settle(n) };
    }
    case "evidence_open":
      return { ...s, evidenceOpen: true, mode: "evidence_focus" };
    case "evidence_close": {
      const n = { ...s, evidenceOpen: false };
      return { ...n, mode: settle(n) };
    }
    case "animation_done":
      return transient(s) ? { ...s, mode: settle(s) } : s;
  }
}

function transient(s: AvatarState) {
  return s.mode === "acknowledging" || s.mode === "presenting";
}

export const modeCaption: Record<AvatarMode, string> = {
  resting: "Ready",
  attending: "Listening to what you type",
  acknowledging: "Got it",
  working: "Working through the stages",
  waiting_for_user: "Waiting for your answers",
  presenting: "Result ready",
  evidence_focus: "Looking at the evidence",
  unavailable: "Figure unavailable",
};
