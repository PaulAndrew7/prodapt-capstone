import { useRef } from "react";
import { AvatarView } from "@/features/avatar/AvatarPanel";
import { modeCaption, type AvatarMode } from "@/features/avatar/controller";
import { useExhibitScript } from "./Exhibit";

/* The same figure the workspace uses, stepping through the states a real run produces. */
const SEQUENCE: AvatarMode[] = ["resting", "attending", "working", "waiting_for_user", "working", "presenting", "resting"];
const TIMELINE = [900, 1600, 2200, 1800, 2000, 2400];

export function AvatarExhibit() {
  const ref = useRef<HTMLDivElement>(null);
  const { step, replay, done } = useExhibitScript(ref, TIMELINE);
  const mode = SEQUENCE[Math.min(step, SEQUENCE.length - 1)];
  return (
    <div ref={ref} className="flex items-center gap-5">
      <AvatarView mode={mode} size={140} />
      <div>
        <p className="font-semibold" aria-live="off">
          {modeCaption[mode]}
        </p>
        {done && (
          <button type="button" onClick={replay} className="mt-2 text-sm font-semibold underline decoration-1 underline-offset-4">
            Replay
          </button>
        )}
      </div>
    </div>
  );
}
