import { lazy, memo, Suspense, useCallback, useEffect, useRef, useState, type ReactNode, type Ref } from "react";
import { Link } from "react-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactLenis, useLenis } from "lenis/react";
import "lenis/dist/lenis.css";
import {
  AnimatePresence,
  motion,
  useInView,
  useMotionValueEvent,
  useReducedMotion,
  useScroll,
  useTransform,
} from "motion/react";
import clsx from "clsx";
import { Wordmark } from "@/components/Wordmark";
import { Button, ButtonLink } from "@/components/Button";
import { HighlightMark } from "@/components/HighlightMark";
import { StageTrack } from "@/components/StageTrack";
import { RunTimeline } from "@/features/cases/Assessment";
import { STAGES, type StageStatus } from "@/lib/events/runStore";
import type { AgentRole } from "@/lib/api/types";
import { policyVersions } from "@/fixtures/policies";
import { vendorAgentMessages } from "@/fixtures/vendorCase";
import {
  AssessExhibit,
  ClarificationExhibit,
  EvidenceExhibit,
  ExportExcerpt,
  HypotheticalExhibit,
  LookupExhibit,
  ReviewExhibit,
  VersionExhibit,
  WorkspaceExhibit,
} from "./exhibits";
import { Exhibit } from "./Exhibit";
import { Skeleton } from "@/components/Feedback";
import { AvatarExhibit } from "./AvatarExhibit";
import { IntroLoader } from "./IntroLoader";

const PolicyStack = lazy(() => import("./PolicyStack"));

/* Exhibits always show fixture data, even when the app runs against a live backend. */
const exhibitClient = new QueryClient({ defaultOptions: { queries: { staleTime: Infinity, retry: false } } });
Object.values(policyVersions).forEach((v) => exhibitClient.setQueryData(["policy-version", v.id], v));

function useScrollTo() {
  const lenis = useLenis();
  return (id: string) => {
    const el = document.getElementById(id);
    if (!el) return;
    if (lenis) lenis.scrollTo(el, { offset: -72 });
    else el.scrollIntoView({ behavior: "auto", block: "start" });
  };
}

function can3D() {
  if (typeof window === "undefined") return false;
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return false;
  if (!window.matchMedia("(min-width: 768px)").matches) return false;
  const nav = navigator as Navigator & { connection?: { saveData?: boolean } };
  if (nav.connection?.saveData) return false;
  if ((navigator.hardwareConcurrency ?? 8) <= 4) return false;
  try {
    const c = document.createElement("canvas");
    return Boolean(c.getContext("webgl2") || c.getContext("webgl"));
  } catch {
    return false;
  }
}

function H2({ children, className, id }: { children: ReactNode; className?: string; id?: string }) {
  return (
    <h2
      id={id}
      className={clsx(
        "font-display text-[clamp(2.25rem,4.6vw,4.5rem)] font-bold leading-[1.03] tracking-[-0.01em]",
        className,
      )}
    >
      {children}
    </h2>
  );
}

function Lead({ children, className }: { children: ReactNode; className?: string }) {
  return <p className={clsx("mt-5 max-w-[50ch] text-lg leading-relaxed text-ink-2 md:text-xl", className)}>{children}</p>;
}

function FrontNav({ markRef, markHidden }: { markRef: Ref<HTMLSpanElement>; markHidden: boolean }) {
  const scrollTo = useScrollTo();
  const links = [
    ["product", "Product"],
    ["how", "How it works"],
    ["review", "Review"],
  ] as const;
  return (
    <header className="sticky top-0 z-10 border-b-2 border-ink bg-paper">
      <div className="mx-auto flex h-[72px] max-w-[1400px] items-center gap-8 px-4 md:px-8">
        <Link to="/" aria-label="Clause home">
          {/* The intro's wordmark lands on this one; it shows the moment the intro leaves. */}
          <Wordmark ref={markRef} className={clsx(markHidden && "opacity-0")} />
        </Link>
        <nav aria-label="Sections" className="hidden items-center gap-7 md:flex">
          {links.map(([id, label]) => (
            <a
              key={id}
              href={`#${id}`}
              onClick={(e) => {
                e.preventDefault();
                scrollTo(id);
              }}
              className="font-semibold text-ink-2 transition-colors hover:text-ink"
            >
              {label}
            </a>
          ))}
        </nav>
        <ButtonLink to="/app" variant="mark" className="ml-auto">
          Enter demo
        </ButtonLink>
      </div>
    </header>
  );
}

const EASE_OUT_EXPO: [number, number, number, number] = [0.16, 1, 0.3, 1];

function Hero({ revealed, onReady }: { revealed: boolean; onReady: () => void }) {
  const ref = useRef<HTMLElement>(null);
  const reduce = useReducedMotion();
  const scrollTo = useScrollTo();
  // Rise in behind the intro's lifting curtain; when there is no intro, just be there.
  const [entrance] = useState(() => !revealed && !reduce);
  const rise = (delay: number) =>
    entrance
      ? {
          initial: { opacity: 0, y: 56 },
          animate: revealed ? { opacity: 1, y: 0 } : undefined,
          transition: { duration: 1, delay, ease: EASE_OUT_EXPO },
        }
      : {};
  // Decided once, before first paint, so the pinned layout never changes height after mount.
  const [pinned] = useState(() => can3D());
  const [mount3d, setMount3d] = useState(false);
  const visible = useInView(ref, { amount: 0.02, initial: true });
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start start", "end end"] });
  // Function-form transforms: Motion would otherwise hand scroll-linked opacity to a native
  // ViewTimeline whose range does not match this pinned section, making the fade non-monotonic.
  const textOpacity = useTransform(() => 1 - Math.min(1, Math.max(0, (scrollYProgress.get() - 0.02) / 0.13)));
  const textY = useTransform(scrollYProgress, [0, 0.16], [0, -70]);
  const ctaPointer = useTransform(() => (textOpacity.get() > 0.5 ? "auto" : "none"));
  // 0 until the pin releases, then 1 once the section's bottom reaches the top of the viewport.
  const { scrollYProgress: exitProgress } = useScroll({ target: ref, offset: ["end end", "end start"] });

  useEffect(() => {
    if (!pinned) return;
    // Load the 3D scene after first paint so the headline stays the largest contentful paint.
    const t = window.setTimeout(() => setMount3d(true), 300);
    return () => window.clearTimeout(t);
  }, [pinned]);
  useEffect(() => {
    // Without 3D the hero is ready once its still has loaded, which the image reports itself.
    if (pinned) return;
    const still = ref.current?.querySelector("img");
    if (!still || still.complete) onReady();
  }, [pinned, onReady]);

  return (
    <section
      ref={ref}
      aria-labelledby="hero-h"
      className="relative"
      // Tuck the next section's empty top padding (md:pt-40) under the stage: its heading arrives exactly as
      // the pin releases and the papers lift, without ever sitting beside the pinned page.
      style={pinned ? { height: "220vh", marginBottom: "-10rem" } : undefined}
    >
      <div
        className={clsx(
          "relative flex items-center overflow-hidden",
          pinned
            ? "pointer-events-none sticky top-[72px] z-[1] h-[calc(100dvh-72px)] min-h-[560px]"
            : "min-h-[calc(100dvh-72px)] py-16",
        )}
      >
        {!pinned && (
          <img
            src="/front/policy-stack.webp"
            alt=""
            width={2160}
            height={1242}
            className="pointer-events-none absolute inset-y-0 right-0 hidden h-full w-auto object-contain object-right md:block"
            onLoad={onReady}
            onError={onReady}
          />
        )}
        {mount3d && (
          <motion.div className="absolute inset-0" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.9 }}>
            <Suspense fallback={null}>
              <PolicyStack progress={scrollYProgress} exit={exitProgress} active={visible} eventSource={ref} onReady={onReady} />
            </Suspense>
          </motion.div>
        )}
        <motion.div
          style={reduce ? undefined : pinned ? { opacity: textOpacity, y: textY } : undefined}
          className="pointer-events-none relative mx-auto w-full max-w-[1400px] px-4 md:px-8"
        >
          <motion.h1
            id="hero-h"
            className="max-w-[15ch] pb-2 font-display text-[clamp(3rem,6.4vw,6rem)] font-bold leading-[1.02] tracking-[-0.012em]"
            {...rise(0.35)}
          >
            Your next move,{" "}
            <HighlightMark play={revealed} delay={entrance ? 1.05 : 0.45} duration={1.1}>
              backed by policy.
            </HighlightMark>
          </motion.h1>
          <motion.p className="mt-7 max-w-[40ch] text-xl leading-relaxed text-ink-2 md:text-[1.375rem]" {...rise(0.47)}>
            Tell Clause what you&rsquo;re planning. See which rules apply, what needs attention, and the exact words behind
            each finding.
          </motion.p>
          <motion.div
            className="pointer-events-auto mt-10 flex flex-wrap gap-3"
            style={pinned && !reduce ? { pointerEvents: ctaPointer } : undefined}
            {...rise(0.57)}
          >
            <ButtonLink to="/app" variant="mark" size="lg">
              Enter demo
            </ButtonLink>
            <Button variant="outline" size="lg" onClick={() => scrollTo("how")}>
              See how it works
            </Button>
          </motion.div>
          {!pinned && (
            <img
              src="/front/policy-stack.webp"
              alt=""
              width={2160}
              height={1242}
              className="-ml-[70%] mt-4 w-[170%] max-w-none md:hidden"
              onLoad={onReady}
              onError={onReady}
            />
          )}
        </motion.div>
      </div>
    </section>
  );
}

function ProductShot() {
  const frame = useRef<HTMLDivElement>(null);
  const reduce = useReducedMotion();
  const { scrollYProgress: enter } = useScroll({ target: frame, offset: ["start end", "start 0.18"] });
  const { scrollYProgress: pass } = useScroll({ target: frame, offset: ["start end", "end start"] });
  const rotateX = useTransform(enter, [0, 1], [14, 0]);
  const scale = useTransform(enter, [0, 1], [0.92, 1]);
  const bandY = useTransform(pass, [0, 1], [110, -110]);
  return (
    <section id="product" aria-labelledby="product-h" className="relative overflow-x-clip py-28 md:py-40">
      <div className="mx-auto max-w-[1400px] px-4 md:px-8">
        <H2 id="product-h" className="max-w-[17ch]">
          Know where your plan stands.
        </H2>
        <Lead>Sharing customer data? Giving a contractor access? Check the requirements before you go ahead, with the source beside every finding.</Lead>
        <div ref={frame} className="relative mt-16 md:mt-20" style={{ perspective: 1800 }}>
          <motion.div
            aria-hidden
            className="absolute -left-[4vw] -right-[4vw] top-[38%] h-[22%] bg-mark"
            style={reduce ? undefined : { y: bandY }}
          />
          <motion.div style={reduce ? undefined : { rotateX, scale, transformOrigin: "50% 0%" }}>
            <WorkspaceExhibit />
          </motion.div>
        </div>
      </div>
    </section>
  );
}

const FEATURES = [
  { id: "ask", title: "Ask a policy question", body: "Get a direct answer with the relevant passages ready to read.", Exhibit: LookupExhibit },
  { id: "assess", title: "Check your plan", body: "Describe the situation. Find the gaps and what to do next.", Exhibit: AssessExhibit },
  { id: "evidence", title: "Read the source", body: "Go straight from a finding to the policy text behind it.", Exhibit: EvidenceExhibit },
  { id: "hypothetical", title: "Explore a what-if", body: "See how different facts could change the outcome in this prototype.", Exhibit: HypotheticalExhibit },
] as const;
const ADVANCE_MS = 7000;

function FeatureTabs() {
  const ref = useRef<HTMLElement>(null);
  const reduce = useReducedMotion();
  const inView = useInView(ref, { amount: 0.35 });
  const [active, setActive] = useState(0);
  const [paused, setPaused] = useState(false);
  const [userChose, setUserChose] = useState(false);
  const [wide, setWide] = useState(true);

  useEffect(() => {
    const mq = window.matchMedia("(min-width: 1024px)");
    const on = () => setWide(mq.matches);
    on();
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, []);

  const auto = !reduce && wide && inView && !paused && !userChose;
  useEffect(() => {
    if (!auto) return;
    const t = window.setTimeout(() => setActive((a) => (a + 1) % FEATURES.length), ADVANCE_MS);
    return () => window.clearTimeout(t);
  }, [auto, active]);

  const current = FEATURES[active];
  return (
    <section
      ref={ref}
      aria-labelledby="features-h"
      className="border-t-2 border-ink py-28 md:py-36"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onFocus={() => setPaused(true)}
      onBlur={() => setPaused(false)}
    >
      <div className="mx-auto grid max-w-[1400px] gap-x-16 gap-y-12 px-4 md:px-8 lg:grid-cols-[minmax(0,5fr)_minmax(0,8fr)]">
        <div>
          <H2 id="features-h" className="max-w-[12ch]">
            A policy question deserves a clear answer.
          </H2>
          <div role="tablist" aria-label="Features" aria-orientation={wide ? "vertical" : "horizontal"} className="mt-10 flex gap-2 overflow-x-auto lg:block lg:space-y-0 lg:overflow-visible">
            {FEATURES.map((f, i) => {
              const selected = i === active;
              return (
                <button
                  key={f.id}
                  role="tab"
                  id={`tab-${f.id}`}
                  aria-selected={selected}
                  aria-controls={`panel-${f.id}`}
                  tabIndex={selected ? 0 : -1}
                  onClick={() => {
                    setActive(i);
                    setUserChose(true);
                  }}
                  onKeyDown={(e) => {
                    const next = e.key === "ArrowDown" || e.key === "ArrowRight" ? 1 : e.key === "ArrowUp" || e.key === "ArrowLeft" ? -1 : 0;
                    if (!next) return;
                    e.preventDefault();
                    const n = (i + next + FEATURES.length) % FEATURES.length;
                    setActive(n);
                    setUserChose(true);
                    document.getElementById(`tab-${FEATURES[n].id}`)?.focus();
                  }}
                  className={clsx(
                    "relative shrink-0 border-2 px-4 py-2 text-left transition-colors lg:block lg:w-full lg:border-0 lg:border-t-2 lg:px-0 lg:py-5",
                    selected ? "border-ink bg-ink text-paper lg:bg-transparent lg:text-ink" : "border-ink/40 text-ink-2 hover:text-ink lg:border-rule",
                  )}
                >
                  <span className="block font-semibold lg:font-display lg:text-2xl">{f.title}</span>
                  <span className={clsx("mt-1 hidden text-ink-2 lg:block", !selected && "lg:hidden")}>{f.body}</span>
                  {selected && wide && (
                    <span aria-hidden className="absolute inset-x-0 -top-[2px] h-[2px] bg-ink">
                      {auto && (
                        <motion.span
                          key={`${active}-bar`}
                          className="absolute inset-y-[-1px] left-0 w-full origin-left bg-mark"
                          initial={{ scaleX: 0 }}
                          animate={{ scaleX: 1 }}
                          transition={{ duration: ADVANCE_MS / 1000, ease: "linear" }}
                          style={{ height: 4 }}
                        />
                      )}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
          <p className="mt-4 text-ink-2 lg:hidden">{current.body}</p>
        </div>
        <div role="tabpanel" id={`panel-${current.id}`} aria-labelledby={`tab-${current.id}`} className="min-w-0 lg:pt-4">
          <AnimatePresence mode="wait">
            <motion.div
              key={current.id}
              initial={reduce ? false : { opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={reduce ? undefined : { opacity: 0, y: -8 }}
              transition={{ duration: 0.28, ease: [0.2, 0.8, 0.2, 1] }}
            >
              <current.Exhibit />
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
    </section>
  );
}

const STORY: Record<AgentRole, string> = {
  retrieval: "Finds the relevant clauses in the policies that applied on your chosen date.",
  analysis: "Compares your situation with each requirement and flags missing details.",
  risk: "Weighs how serious each gap is, using the facts available.",
  validation: "Checks whether the sources support each finding and requests more evidence when needed.",
  recommendation: "Suggests what to do next, with the policy reason for each action.",
};
const MESSAGES_AT = [1, 2, 3, 6, 7];

function stagesUpTo(idx: number): Record<AgentRole, StageStatus> {
  return Object.fromEntries(STAGES.map((s, i) => [s.role, i < idx ? "done" : i === idx ? "active" : "pending"])) as Record<
    AgentRole,
    StageStatus
  >;
}

function TraceExhibit({ idx }: { idx: number }) {
  return (
    <Exhibit
      width={900}
      height={760}
      label="The recorded trace of the vendor case: messages passed between retrieval, analysis, risk, validation and recommendation, including one repair request."
    >
      <div className="h-full bg-sheet p-10">
        <StageTrack stages={idx >= STAGES.length ? stagesUpTo(STAGES.length) : stagesUpTo(idx)} />
        <div className="mt-10 [&_li]:grid-cols-[5rem_minmax(0,1fr)] [&_li]:gap-4">
          <RunTimeline messages={vendorAgentMessages.slice(0, MESSAGES_AT[Math.min(idx, 4)])} />
          <ol aria-hidden className="border-l-2 border-rule">
            {Array.from({ length: vendorAgentMessages.length - MESSAGES_AT[Math.min(idx, 4)] }, (_, i) => (
              <li key={i} className="grid gap-4 py-3 pl-6 md:grid-cols-[5rem_minmax(0,1fr)]">
                <Skeleton className="h-4 w-10" />
                <div className="space-y-2">
                  <Skeleton className="h-4 w-48" />
                  <Skeleton className="h-4 w-80" />
                </div>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </Exhibit>
  );
}

function WorkflowStory() {
  const ref = useRef<HTMLElement>(null);
  const reduce = useReducedMotion();
  const [idx, setIdx] = useState(0);
  const [wide, setWide] = useState(true);
  useEffect(() => {
    const mq = window.matchMedia("(min-width: 1024px)");
    const on = () => setWide(mq.matches);
    on();
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, []);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start start", "end end"] });
  useMotionValueEvent(scrollYProgress, "change", (p) => {
    const next = Math.min(STAGES.length - 1, Math.floor(p * STAGES.length * 1.02));
    setIdx((cur) => (cur === next ? cur : next));
  });
  const pinned = wide && !reduce;

  const heading = (
    <>
      <H2 id="how-h" className="max-w-[13ch]">
        Follow the work behind the answer.
      </H2>
    </>
  );

  if (!pinned) {
    return (
      <section id="how" aria-labelledby="how-h" className="border-t-2 border-ink py-28">
        <div className="mx-auto grid max-w-[1400px] gap-x-16 gap-y-12 px-4 md:px-8 lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
          <div>
            {heading}
            <ol className="mt-10 space-y-8">
              {STAGES.map((s) => (
                <li key={s.role}>
                  <p className="font-display text-3xl font-bold">{s.label}</p>
                  <p className="mt-1 max-w-[52ch] text-lg text-ink-2">{STORY[s.role]}</p>
                </li>
              ))}
            </ol>
          </div>
          <div className="lg:pt-4">
            <TraceExhibit idx={STAGES.length} />
          </div>
        </div>
      </section>
    );
  }

  return (
    <section id="how" ref={ref} aria-labelledby="how-h" className="relative border-t-2 border-ink" style={{ height: "400vh" }}>
      <div className="sticky top-[72px] flex h-[calc(100dvh-72px)] items-center overflow-hidden">
        <div className="mx-auto grid w-full max-w-[1400px] items-center gap-x-16 px-4 md:px-8 lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
          <div>
            {heading}
            <ol className="mt-10 space-y-1" aria-label="Stages">
              {STAGES.map((s, i) => (
                <li key={s.role} aria-current={i === idx ? "step" : undefined}>
                  <p
                    className={clsx(
                      "font-display text-[clamp(1.75rem,2.8vw,2.75rem)] font-bold leading-[1.15] transition-colors duration-300",
                      i === idx ? "text-ink" : i < idx ? "text-ink-2" : "text-muted",
                    )}
                  >
                    {s.label}
                  </p>
                  <AnimatePresence initial={false}>
                    {i === idx && (
                      <motion.p
                        key={s.role}
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        exit={{ opacity: 0, height: 0 }}
                        transition={{ duration: 0.25 }}
                        className="max-w-[44ch] overflow-hidden pb-3 text-lg text-ink-2"
                      >
                        {STORY[s.role]}
                      </motion.p>
                    )}
                  </AnimatePresence>
                </li>
              ))}
            </ol>
          </div>
          <div className="hidden lg:block">
            <TraceExhibit idx={idx} />
          </div>
        </div>
      </div>
    </section>
  );
}

function Parallax({ children, amount = 40 }: { children: ReactNode; amount?: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const reduce = useReducedMotion();
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start end", "end start"] });
  const y = useTransform(scrollYProgress, [0, 1], [amount, -amount]);
  return (
    <motion.div ref={ref} style={reduce ? undefined : { y }}>
      {children}
    </motion.div>
  );
}

function Unknowns() {
  return (
    <section aria-labelledby="unknown-h" className="border-t-2 border-ink py-28 md:py-40">
      <div className="mx-auto grid max-w-[1400px] items-center gap-x-20 gap-y-14 px-4 md:px-8 lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
        <div>
          <H2 id="unknown-h">You don&rsquo;t have to know it all.</H2>
          <Lead>
            Was the vendor approved? Has anyone signed off? If you&rsquo;re unsure, &ldquo;I don&rsquo;t know&rdquo; is a valid
            answer. Clause keeps that question open so you can follow up.
          </Lead>
        </div>
        <Parallax>
          <ClarificationExhibit />
        </Parallax>
      </div>
    </section>
  );
}

function Versions() {
  return (
    <section aria-labelledby="versions-h" className="border-t-2 border-ink py-28 md:py-40">
      <div className="mx-auto max-w-[1400px] px-4 md:px-8">
        <H2 id="versions-h" className="max-w-[20ch]">
          Policies move on. Keep the full picture.
        </H2>
        <Lead>
          Each assessment keeps the policy version it used. Come back later and you can still see the rules behind the
          result, even after an update.
        </Lead>
        <div className="mt-14 lg:ml-[16%]">
          <Parallax amount={30}>
            <VersionExhibit />
          </Parallax>
        </div>
      </div>
    </section>
  );
}

function ReviewBento() {
  return (
    <section id="review" aria-labelledby="review-h" className="border-t-2 border-ink py-28 md:py-40">
      <div className="mx-auto max-w-[1400px] px-4 md:px-8">
        <H2 id="review-h" className="max-w-[16ch]">
          Read it. Question it. Take the next step.
        </H2>
        <div className="mt-14 grid gap-4 lg:grid-cols-[minmax(0,1.25fr)_minmax(0,1fr)] lg:grid-rows-[auto_1fr]">
          <div className="bg-sheet p-6 md:p-10 lg:row-span-2">
            <h3 className="font-display text-3xl font-bold">You make the call.</h3>
            <p className="mt-2 max-w-[44ch] text-ink-2">
              This review prototype shows how a person could accept a finding, challenge it, or ask for more detail,
              with their reasoning recorded alongside the original assessment.
            </p>
            <div className="mt-8">
              <ReviewExhibit />
            </div>
          </div>
          <div className="bg-ink p-6 text-paper md:p-8">
            <h3 className="font-display text-3xl font-bold">Take the sources with you.</h3>
            <p className="mt-2 max-w-[40ch] text-paper/75">See a sample export with the policy references attached, ready for a closer look.</p>
            <div className="mt-6">
              <ExportExcerpt />
            </div>
          </div>
          <div className="bg-mark p-6 text-on-mark md:p-8">
            <h3 className="font-display text-3xl font-bold">A little company along the way.</h3>
            <p className="mt-2 max-w-[40ch]">An optional companion reacts as your assessment progresses. Keep it around if you like.</p>
            <div className="mt-4">
              <AvatarExhibit />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function Close() {
  const heading = useRef<HTMLHeadingElement>(null);
  // Plays when the heading is on screen, not on mount far below the fold.
  const seen = useInView(heading, { once: true, amount: 0.8 });
  return (
    <section aria-labelledby="close-h" className="border-t-2 border-ink py-32 md:py-48">
      <div className="mx-auto max-w-[1400px] px-4 md:px-8">
        <h2 ref={heading} id="close-h" className="max-w-[14ch] pb-2 font-display text-[clamp(3rem,6.4vw,6rem)] font-bold leading-[1.02]">
          See what{" "}
          <HighlightMark play={seen} delay={0.25} duration={1.1}>
            Clause uncovers.
          </HighlightMark>
        </h2>
        <Lead>Start with a sample case. Follow the findings, read the policy, and see what needs to happen next.</Lead>
        <ButtonLink to="/app" variant="mark" size="lg" className="mt-10">
          Enter demo
        </ButtonLink>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="border-t-2 border-ink">
      <div className="mx-auto flex max-w-[1400px] flex-col gap-6 px-4 py-10 md:flex-row md:items-end md:justify-between md:px-8">
        <div>
          <Wordmark />
          <p className="mt-4 max-w-[60ch] text-sm text-ink-2">
            Clause is a capstone project. Kestrel Mutual, its policies, and the people and cases in this demo are fictional.
            The examples are for demonstration and do not provide legal advice.
          </p>
        </div>
        <nav aria-label="Footer" className="flex gap-6 text-sm font-semibold">
          <Link to="/app/cases" className="underline decoration-1 underline-offset-4">
            Cases
          </Link>
          <Link to="/app/policies" className="underline decoration-1 underline-offset-4">
            Policies
          </Link>
        </nav>
      </div>
    </footer>
  );
}

/* Everything below the hero. Memoized so the intro's reveal and handoff re-render only the hero and nav. */
const Sections = memo(function Sections() {
  return (
    <>
      <ProductShot />
      <FeatureTabs />
      <WorkflowStory />
      <Unknowns />
      <Versions />
      <ReviewBento />
      <Close />
    </>
  );
});

/* The intro plays once per page load, not on every client-side return to the front door. */
let introPlayed = false;

export function FrontDoor() {
  const reduce = useReducedMotion();
  const [intro, setIntro] = useState(() => !introPlayed);
  const [revealed, setRevealed] = useState(() => introPlayed);
  const [heroReady, setHeroReady] = useState(false);
  const onHeroReady = useCallback(() => setHeroReady(true), []);
  const navMark = useRef<HTMLSpanElement>(null);
  const page = (
    <div className="min-h-dvh bg-paper text-ink" inert={intro}>
      <a
        href="#main"
        className="sr-only z-50 bg-mark px-4 py-2 font-semibold text-on-mark focus:not-sr-only focus:fixed focus:left-4 focus:top-4"
      >
        Skip to content
      </a>
      <FrontNav markRef={navMark} markHidden={intro} />
      <main id="main" tabIndex={-1} className="outline-none">
        <Hero revealed={revealed} onReady={onHeroReady} />
        <Sections />
      </main>
      <Footer />
    </div>
  );
  const content = (
    <>
      {page}
      {intro && (
        <IntroLoader
          heroReady={heroReady}
          target={navMark}
          onReveal={() => setRevealed(true)}
          onDone={() => {
            introPlayed = true;
            setIntro(false);
          }}
        />
      )}
    </>
  );
  return (
    <QueryClientProvider client={exhibitClient}>
      {reduce ? content : <ReactLenis root options={{ lerp: 0.1, smoothWheel: true }}>{content}</ReactLenis>}
    </QueryClientProvider>
  );
}
