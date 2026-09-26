import { useEffect, useLayoutEffect, useRef, useState, type ReactNode, type RefObject } from "react";
import { useInView, useReducedMotion } from "motion/react";
import { ArrowCounterClockwise } from "@phosphor-icons/react";
import clsx from "clsx";

/*
  A product exhibit: real app components rendered at a fixed logical size and scaled to
  fit, like a screenshot. Internals are inert, so keyboard and screen-reader users are not
  pulled into illustrative controls; the figure label describes what it shows.
*/
export function Exhibit({
  label,
  width = 1280,
  height = 800,
  children,
  className,
  caption,
  onReplay,
  interactive = false,
  frameRef,
}: {
  label: string;
  width?: number;
  height?: number;
  children: ReactNode;
  className?: string;
  caption?: ReactNode;
  onReplay?: () => void;
  interactive?: boolean;
  frameRef?: RefObject<HTMLDivElement | null>;
}) {
  const box = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(1);
  useLayoutEffect(() => {
    const el = box.current;
    if (!el) return;
    const measure = () => setScale(el.clientWidth / width);
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, [width]);

  return (
    <figure aria-label={label} className={clsx("relative", className)}>
      <div
        ref={(el) => {
          box.current = el;
          if (frameRef) frameRef.current = el;
        }}
        className="relative overflow-hidden border-[1.5px] border-ink bg-paper"
        style={{ height: Math.round(height * scale) }}
      >
        <div
          inert={!interactive}
          aria-hidden={!interactive}
          className="absolute left-0 top-0 origin-top-left"
          style={{ width, height, transform: `scale(${scale})` }}
        >
          {children}
        </div>
      </div>
      {(caption || onReplay) && (
        <figcaption className="mt-3 flex items-baseline justify-between gap-4 text-sm text-ink-2">
          <span>{caption}</span>
          {onReplay && (
            <button
              type="button"
              onClick={onReplay}
              className="inline-flex shrink-0 items-center gap-1.5 font-semibold text-ink underline decoration-1 underline-offset-4"
            >
              <ArrowCounterClockwise size={14} aria-hidden /> Replay
            </button>
          )}
        </figcaption>
      )}
    </figure>
  );
}

/*
  Steps an exhibit through its states while it is at least 40% in view.
  Pauses offscreen; under reduced motion it shows the final state at once.
*/
export function useExhibitScript(ref: RefObject<Element | null>, timeline: number[]) {
  const reduce = useReducedMotion();
  const inView = useInView(ref, { amount: 0.4 });
  const [step, setStep] = useState(0);
  const [run, setRun] = useState(0);
  const last = timeline.length;

  useEffect(() => {
    if (reduce) {
      setStep(last);
      return;
    }
    if (!inView || step >= last) return;
    const t = window.setTimeout(() => setStep((s) => s + 1), timeline[step]);
    return () => window.clearTimeout(t);
  }, [inView, step, reduce, run, last, timeline]);

  return {
    step: reduce ? last : step,
    done: reduce || step >= last,
    replay: () => {
      setStep(0);
      setRun((r) => r + 1);
    },
  };
}
