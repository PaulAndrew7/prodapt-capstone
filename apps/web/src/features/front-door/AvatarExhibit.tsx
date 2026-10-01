import { useRef } from "react";
import { AvatarView } from "@/features/avatar/AvatarPanel";
import type { Expression } from "@/features/avatar/expressions";
import { useExhibitScript } from "./Exhibit";

/* The same figure the workspace uses, stepping through the expressions a real run produces. */
const SEQUENCE: { expression: Expression; caption: string }[] = [
  { expression: "idle", caption: "Ready" },
  { expression: "listening", caption: "Listening to what you type" },
  { expression: "searching", caption: "Finding the clauses" },
  { expression: "thinking", caption: "Comparing your plan" },
  { expression: "pleading", caption: "Waiting for your answers" },
  { expression: "scrutinizing", caption: "Checking the sources" },
  { expression: "inspired", caption: "Writing next steps" },
  { expression: "proud", caption: "Result ready" },
];
const TIMELINE = [900, 1500, 1900, 1900, 2000, 1900, 1900];

export function AvatarExhibit() {
  const ref = useRef<HTMLDivElement>(null);
  const { step, replay, done } = useExhibitScript(ref, TIMELINE);
  const { expression, caption } = SEQUENCE[Math.min(step, SEQUENCE.length - 1)];
  return (
    <div ref={ref} className="flex items-center gap-5">
      <AvatarView mode="resting" expression={expression} size={168} />
      <div>
        <p className="font-semibold" aria-live="off">
          {caption}
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
