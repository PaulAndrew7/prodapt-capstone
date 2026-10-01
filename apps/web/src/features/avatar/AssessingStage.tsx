/*
  The assessing screen's companion stage: while a run is in progress she takes over the
  assessment pane, acting out the stage the run is actually in (from the same events as
  the stage track) and saying what that stage does in a speech bubble. The stage track
  keeps the live progress announcement; the bubble is read once, not announced as it types.
*/
import { useEffect, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import clsx from "clsx";
import type { AgentRole } from "@/lib/api/types";
import { STAGES, type RunPhase, type StageStatus } from "@/lib/events/runStore";
import { formatDate } from "@/lib/format";
import { AvatarView } from "./AvatarPanel";
import { useAvatarPref } from "./avatarPref";
import { stageExpression } from "./expressions";

type Line = { headline: string; says: string };

const COUNT = ["No", "One", "Two", "Three", "Four", "Five"];

function lineFor(phase: RunPhase, active: AgentRole | null, finishing: boolean, asOf: string, questions: number): Line {
  if (phase === "running" && finishing) {
    return { headline: "Wrapping up.", says: "Almost there! Putting your result together…" };
  }
  if (phase === "waiting_for_user") {
    const facts = questions === 1 ? "One fact decides" : `${COUNT[questions] ?? questions} facts decide`;
    return {
      headline: "Waiting for your answers.",
      says: `${facts} this case. Can you answer in the conversation? “I don’t know” is fine too!`,
    };
  }
  switch (phase === "queued" ? null : active) {
    case "retrieval":
      return { headline: "Finding the clauses.", says: `Looking for every clause that applied on ${formatDate(asOf)}.` };
    case "analysis":
      return { headline: "Comparing your plan.", says: "Hmm… let me hold your plan up against each requirement." };
    case "risk":
      return { headline: "Weighing the risks.", says: "How serious could each gap be? Careful, careful…" };
    case "validation":
      return { headline: "Checking the sources.", says: "Every quote has to match the policy word for word. Checking!" };
    case "recommendation":
      return { headline: "Writing next steps.", says: "Got it! Here’s what to do next…" };
    default:
      return { headline: "Getting started.", says: "Okay! Opening the policy library." };
  }
}

/* Types a line out while keeping its full layout, so wrapping never jumps. */
function useTyped(text: string, animate: boolean) {
  const [state, setState] = useState({ text, count: animate ? 0 : text.length });
  // A new line starts empty on its first render, not at the old line's count.
  const count = state.text === text ? state.count : animate ? 0 : text.length;
  useEffect(() => {
    if (!animate) {
      setState({ text, count: text.length });
      return;
    }
    setState({ text, count: 0 });
    let n = 0;
    const id = window.setInterval(() => {
      n += 1;
      setState({ text, count: n });
      if (n >= text.length) window.clearInterval(id);
    }, 28);
    return () => window.clearInterval(id);
  }, [text, animate]);
  return { typed: text.slice(0, count), rest: text.slice(count), typing: count < text.length };
}

function HideFigure({ onHide, className }: { onHide: () => void; className: string }) {
  return (
    <button
      type="button"
      onClick={onHide}
      className={clsx("text-sm font-semibold text-ink-2 underline decoration-1 underline-offset-4 hover:text-ink", className)}
    >
      Hide figure
    </button>
  );
}

export function AssessingStage({
  phase,
  stages,
  asOf,
  questionCount,
}: {
  phase: RunPhase;
  stages: Record<AgentRole, StageStatus>;
  asOf: string;
  questionCount: number;
}) {
  const reduce = useReducedMotion();
  const { setEnabled } = useAvatarPref();
  const active = STAGES.find((s) => stages[s.role] === "active")?.role ?? null;
  const finishing = !active && stages.recommendation === "done";
  const expression = stageExpression(phase, active, finishing);
  const line = lineFor(phase, active, finishing, asOf, questionCount);
  const { typed, rest, typing } = useTyped(line.says, !reduce);

  return (
    <div className="@container relative flex min-h-[20rem] flex-1 flex-col">
      {/* The stage bleeds into the pane's right padding; the text column keeps clear of it. */}
      <div className="relative z-10 flex max-w-full flex-col items-start pr-4 md:pr-10 @xl:max-w-[46%] @xl:pr-0">
        <AnimatePresence mode="wait" initial={false}>
          <motion.p
            key={line.headline}
            className="font-display text-[clamp(2rem,3.2vw,3rem)] font-bold leading-[1.05]"
            initial={reduce ? false : { opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            exit={reduce ? undefined : { opacity: 0, y: -10 }}
            transition={{ duration: 0.26, ease: [0.2, 0.8, 0.2, 1] }}
          >
            {line.headline}
          </motion.p>
        </AnimatePresence>
        <motion.div
          key={line.says}
          className="relative mt-6 w-full max-w-[26rem] border-2 border-ink bg-sheet px-5 py-4"
          initial={reduce ? false : { opacity: 0, scale: 0.94, x: -8 }}
          animate={{ opacity: 1, scale: 1, x: 0 }}
          transition={{ type: "spring", stiffness: 520, damping: 26 }}
          style={{ transformOrigin: "100% 60%" }}
        >
          <p className="text-lg font-semibold leading-snug">
            <span className="sr-only">{line.says}</span>
            <span aria-hidden>
              {typed}
              <span className="invisible">{rest}</span>
            </span>
          </p>
          {/* The tail points at her: sideways when she stands beside the bubble, down when she stands below it. */}
          <svg aria-hidden width="34" height="30" viewBox="0 0 34 30" className="absolute -bottom-[28px] left-10 overflow-visible @xl:hidden">
            <path d="M0 0 L14 28 L26 0" fill="var(--sheet)" stroke="var(--ink)" strokeWidth={2} strokeLinejoin="miter" />
            <rect x={1.5} y={-3} width={23} height={4} fill="var(--sheet)" />
          </svg>
          <svg aria-hidden width="34" height="30" viewBox="0 0 34 30" className="absolute -right-[32px] top-7 hidden overflow-visible @xl:block">
            <path d="M0 0 L32 20 L0 24" fill="var(--sheet)" stroke="var(--ink)" strokeWidth={2} strokeLinejoin="miter" />
            <rect x={-3} y={1.5} width={4} height={21} fill="var(--sheet)" />
          </svg>
        </motion.div>
        <HideFigure onHide={() => setEnabled(false)} className="absolute top-full mt-6 hidden @xl:block" />
      </div>

      {/* She stands at the bottom right and bleeds off the pane's edges, like a sprite on a stage. */}
      <div className="pointer-events-none relative mt-auto flex justify-center self-stretch @xl:absolute @xl:inset-y-0 @xl:right-0 @xl:mt-0 @xl:w-[62%] @xl:justify-end">
        <div className="relative aspect-square w-[min(100%,24rem)] text-ink @xl:h-full @xl:max-h-[44rem] @xl:w-auto @xl:self-end">
          {/* Screentone behind her head: flat halftone dots, no glow. */}
          <div
            aria-hidden
            className="absolute left-1/2 top-[42%] aspect-square w-[88%] -translate-x-1/2 -translate-y-1/2 rounded-full opacity-[0.16]"
            style={{ backgroundImage: "radial-gradient(var(--ink) 1.3px, transparent 1.6px)", backgroundSize: "13px 13px" }}
          />
          <AvatarView mode="working" expression={expression} size="100%" talking={typing} />
        </div>
      </div>
      {/* Stacked, the bubble's tail points down at her, so the control moves below her. */}
      <HideFigure onHide={() => setEnabled(false)} className="mb-8 mt-4 self-center @xl:hidden" />
    </div>
  );
}
