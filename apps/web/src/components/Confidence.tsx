import { useId, useState } from "react";
import { CaretDown } from "@phosphor-icons/react";
import clsx from "clsx";
import type { Confidence } from "@/lib/api/types";

const bandLabel: Record<Confidence["band"], string> = { high: "High", medium: "Medium", low: "Low" };

/* Scores come from the API's recorded checks (app/workflow/confidence.py), never from the model. */
export const CONFIDENCE_NOTE =
  "Evidence score from the checks this run recorded. It ranks how well the verdict is backed; it is not a probability that it is right.";

export function ConfidenceMeter({ confidence, className }: { confidence: Confidence; className?: string }) {
  const low = confidence.band === "low";
  return (
    <span
      className={clsx("inline-flex items-center gap-2 text-sm", className)}
      aria-label={`Evidence score ${confidence.score} of 100, ${bandLabel[confidence.band]}`}
    >
      <span aria-hidden className="relative h-1.5 w-12 bg-rule">
        <span className={clsx("absolute inset-y-0 left-0", low ? "bg-unknown" : "bg-ink")} style={{ width: `${confidence.score}%` }} />
      </span>
      <span aria-hidden className="tnum font-semibold">
        {confidence.score}
      </span>
      <span aria-hidden className={clsx(low ? "font-semibold text-unknown" : "text-ink-2")}>{bandLabel[confidence.band]}</span>
    </span>
  );
}

export function ConfidenceFactors({ confidence }: { confidence: Confidence }) {
  return (
    <div className="text-sm">
      <p className="font-semibold">
        Evidence score <span className="tnum">{confidence.score}</span>/100 · {bandLabel[confidence.band]}
      </p>
      <p className="text-ink-2">{confidence.basis}</p>
      <ul className="mt-2 space-y-1">
        {confidence.factors.map((f) => (
          <li key={f.label} className="grid grid-cols-[minmax(0,1fr)_auto] gap-3">
            <span className={clsx(f.points === 0 && "text-ink-2")}>{f.label}</span>
            <span className="tnum text-ink-2">
              {f.points}/{f.max_points}
            </span>
          </li>
        ))}
      </ul>
      <p className="mt-2 text-ink-2">{CONFIDENCE_NOTE}</p>
    </div>
  );
}

/* One line under a result or answer, with the breakdown behind a disclosure. */
export function ConfidenceSummary({ confidence, subject }: { confidence: Confidence; subject: string }) {
  const [open, setOpen] = useState(false);
  const panelId = useId();
  return (
    <div className="mt-4">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
        <span className="text-sm font-semibold">Evidence checks for this {subject}</span>
        <ConfidenceMeter confidence={confidence} />
        <button
          type="button"
          aria-expanded={open}
          aria-controls={panelId}
          onClick={() => setOpen((o) => !o)}
          className="inline-flex items-center gap-1 text-sm font-semibold underline decoration-1 underline-offset-4"
        >
          How it was scored
          <CaretDown size={14} aria-hidden className={clsx("transition-transform duration-200 motion-reduce:transition-none", open && "rotate-180")} />
        </button>
      </div>
      {open && (
        <div id={panelId} className="mt-3 max-w-[52ch] bg-sheet p-4">
          <ConfidenceFactors confidence={confidence} />
        </div>
      )}
    </div>
  );
}
