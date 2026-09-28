import { useEffect, useReducer } from "react";
import type { RunPhase } from "@/lib/events/runStore";
import { avatarReducer, initialAvatarState, modeCaption, type AvatarMode } from "./controller";
import { useAvatarPref } from "./avatarPref";
import AvatarFigure from "./AvatarFigure";

export function AvatarView({ mode, size }: { mode: AvatarMode; size: number }) {
  return (
    <div className="shrink-0" style={{ width: size, height: size }}>
      <AvatarFigure mode={mode} />
    </div>
  );
}

/*
  The workspace companion. Inputs are the same deduplicated run phase and UI focus the
  rest of the workspace uses; stale events cannot animate a newer conversation.
*/
export function AvatarPanel({
  phase,
  composerFocused,
  evidenceOpen,
  ackKey,
  stageLabel,
}: {
  phase: RunPhase;
  composerFocused: boolean;
  evidenceOpen: boolean;
  ackKey: number;
  stageLabel: string | null;
}) {
  const { enabled, setEnabled } = useAvatarPref();
  const [state, dispatch] = useReducer(avatarReducer, { ...initialAvatarState, phase });

  useEffect(() => dispatch({ type: "run_phase", phase, at: performance.now() }), [phase]);
  useEffect(() => {
    const t = window.setTimeout(() => dispatch({ type: composerFocused ? "composer_focus" : "composer_blur" }), 180);
    return () => window.clearTimeout(t);
  }, [composerFocused]);
  useEffect(() => dispatch({ type: evidenceOpen ? "evidence_open" : "evidence_close" }), [evidenceOpen]);
  useEffect(() => {
    if (ackKey > 0) dispatch({ type: "message_accepted", at: performance.now() });
  }, [ackKey]);
  useEffect(() => {
    if (state.mode !== "acknowledging" && state.mode !== "presenting") return;
    const t = window.setTimeout(() => dispatch({ type: "animation_done", at: performance.now() }), state.mode === "presenting" ? 2200 : 1100);
    return () => window.clearTimeout(t);
  }, [state.mode]);

  if (!enabled) {
    return (
      <div className="flex items-center justify-between border-t-2 border-ink px-4 py-2 md:px-8">
        <span className="text-sm text-ink-2">Figure hidden</span>
        <button type="button" onClick={() => setEnabled(true)} className="text-sm font-semibold underline decoration-1 underline-offset-4">
          Show figure
        </button>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-4 border-t-2 border-ink px-4 py-2 md:px-8">
      <AvatarView mode={state.mode} size={88} />
      <div className="min-w-0 flex-1">
        <p className="font-semibold" aria-live="polite">
          {modeCaption[state.mode]}
        </p>
        {state.mode === "working" && stageLabel && <p className="text-sm text-ink-2">{stageLabel}</p>}
      </div>
      <button type="button" onClick={() => setEnabled(false)} className="shrink-0 text-sm font-semibold text-ink-2 underline decoration-1 underline-offset-4 hover:text-ink">
        Hide
      </button>
    </div>
  );
}
