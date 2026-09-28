/*
  First-load intro for the front door. The wordmark is set across the screen and its mark bar
  is the progress bar, driven by real readiness: the display face, every font, the window load
  and the hero's first frame. When everything is in, the wordmark flies into the nav's logo slot
  while a paper curtain, edged with an ink rule, lifts off the page.
  The big wordmark mirrors Wordmark's geometry (same classes, em-based bar), so scaling it down
  to the nav's font size lands it exactly on the real logo, which appears as the loader leaves.
*/
import { useEffect, useRef, useState, type RefObject } from "react";
import { animate, motion, useAnimationFrame, useReducedMotion } from "motion/react";
import { useLenis } from "lenis/react";

/* The bar never fills faster than this, so a warm cache still reads as a deliberate beat. */
const MIN_FILL_MS = 1300;
/* Never hold the page longer than this, whatever is still loading. */
const MAX_WAIT_MS = 6000;
const EASE_IN_OUT: [number, number, number, number] = [0.76, 0, 0.24, 1];

export function IntroLoader({
  heroReady,
  target,
  onReveal,
  onDone,
}: {
  heroReady: boolean;
  target: RefObject<HTMLElement | null>;
  onReveal: () => void;
  onDone: () => void;
}) {
  const reduce = useReducedMotion();
  const lenis = useLenis();
  const root = useRef<HTMLDivElement>(null);
  const curtain = useRef<HTMLDivElement>(null);
  const mark = useRef<HTMLSpanElement>(null);
  const bar = useRef<HTMLSpanElement>(null);

  const [displayFont, setDisplayFont] = useState(false);
  const [fonts, setFonts] = useState(false);
  const [windowLoaded, setWindowLoaded] = useState(() => document.readyState === "complete");
  const [timedOut, setTimedOut] = useState(false);

  useEffect(() => {
    let alive = true;
    // The letters wait for their face so they never rise in the fallback and swap.
    const fontCap = window.setTimeout(() => alive && setDisplayFont(true), 1500);
    document.fonts.load("700 1em 'Clash Display'").finally(() => alive && setDisplayFont(true));
    document.fonts.ready.then(() => alive && setFonts(true));
    const onLoad = () => setWindowLoaded(true);
    window.addEventListener("load", onLoad);
    const cap = window.setTimeout(() => alive && setTimedOut(true), MAX_WAIT_MS);
    return () => {
      alive = false;
      window.clearTimeout(fontCap);
      window.clearTimeout(cap);
      window.removeEventListener("load", onLoad);
    };
  }, []);

  // Hold the page at rest. The gutter stays reserved, so the scrollbar's return shifts nothing.
  useEffect(() => {
    const html = document.documentElement;
    const prev = { overflow: html.style.overflow, gutter: html.style.scrollbarGutter };
    html.style.scrollbarGutter = "stable";
    html.style.overflow = "hidden";
    return () => {
      html.style.overflow = prev.overflow;
      html.style.scrollbarGutter = prev.gutter;
    };
  }, []);
  useEffect(() => {
    lenis?.stop();
    return () => lenis?.start();
  }, [lenis]);

  const ready = timedOut ? 1 : (Number(displayFont) + Number(fonts) + Number(windowLoaded) + Number(heroReady)) / 4;
  const readyRef = useRef(ready);
  readyRef.current = ready;

  const run = useRef({ start: -1, shown: 0, leaving: false });
  const leave = async () => {
    await new Promise((r) => window.setTimeout(r, 160));
    onReveal();
    const el = mark.current;
    const dest = target.current;
    if (reduce || !el || !dest || !root.current || !curtain.current) {
      if (root.current) await animate(root.current, { opacity: 0 }, { duration: reduce ? 0.2 : 0.4 });
      onDone();
      return;
    }
    const from = el.getBoundingClientRect();
    const to = dest.getBoundingClientRect();
    const scale = parseFloat(getComputedStyle(dest).fontSize) / parseFloat(getComputedStyle(el).fontSize);
    const flight = animate(el, { x: to.left - from.left, y: to.top - from.top, scale }, { duration: 1.1, ease: EASE_IN_OUT });
    animate(curtain.current, { y: "-100%" }, { duration: 1.0, delay: 0.06, ease: EASE_IN_OUT });
    await flight;
    onDone();
  };

  useAnimationFrame((t, dt) => {
    const s = run.current;
    if (!displayFont || s.leaving) return;
    if (s.start < 0) s.start = t;
    // Real readiness, capped by a minimum pace that starts once the letters are on their way up.
    const pace = Math.max(0, Math.min(1, (t - s.start - 250) / MIN_FILL_MS));
    const goal = Math.min(readyRef.current, pace);
    s.shown += (goal - s.shown) * Math.min(1, (dt / 1000) * 7);
    if (goal >= 1 && s.shown > 0.996) s.shown = 1;
    if (bar.current) bar.current.style.transform = `scaleX(${s.shown.toFixed(4)})`;
    if (s.shown === 1) {
      s.leaving = true;
      void leave();
    }
  });

  return (
    <div ref={root} className="fixed inset-0 z-50" role="status">
      <span className="sr-only">Loading Clause</span>
      <div ref={curtain} className="absolute inset-x-0 top-0 -bottom-[2px] border-b-2 border-ink bg-paper" />
      <div className="absolute inset-0 flex items-center justify-center">
        <span
          ref={mark}
          aria-hidden
          className="relative inline-block font-display font-bold leading-none tracking-[-0.01em] text-ink"
          style={{ fontSize: "min(25vw, 46vh)", transformOrigin: "0 0" }}
        >
          <span ref={bar} className="wordmark-bar absolute inset-x-[-0.06em] origin-left bg-mark" style={{ transform: "scaleX(0)" }} />
          {/* Clipped only at the bottom, so the letters rise out of the baseline. */}
          <span className="relative block" style={{ clipPath: "inset(-50% -20% 0 -20%)" }}>
            {"Clause".split("").map((ch, i) => (
              <motion.span
                key={i}
                className="inline-block"
                initial={reduce ? false : { y: "110%" }}
                animate={displayFont ? { y: "0%" } : undefined}
                transition={{ duration: 0.95, delay: 0.055 * i, ease: [0.16, 1, 0.3, 1] }}
              >
                {ch}
              </motion.span>
            ))}
          </span>
        </span>
      </div>
    </div>
  );
}
