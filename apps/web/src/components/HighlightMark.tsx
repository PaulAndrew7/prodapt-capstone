import { motion, useReducedMotion } from "motion/react";
import type { CSSProperties } from "react";
import clsx from "clsx";

/*
  A highlighter pass over a phrase. Each word is its own wrapping unit with three layers:
  the yellow fill sweeping in underneath, the text in its normal color, and an on-mark
  copy that fades in a little behind the marker's edge, so the words go from page ink to
  black as the highlighter crosses them. The copy is plain text, not transparent glyphs or
  background-clip:text, which break inside transformed/animated ancestors.
  --sweep runs 0..100; the per-word geometry lives in index.css.
*/
export function HighlightMark({
  children,
  play = true,
  delay = 0,
  className,
  duration = 0.7,
}: {
  children: string;
  play?: boolean;
  delay?: number;
  className?: string;
  duration?: number;
}) {
  const reduce = useReducedMotion();
  const words = children.match(/\S+\s*|\s+/g) ?? [];
  let offset = 0;
  return (
    <motion.mark
      className={clsx("mark-sweep bg-transparent", className)}
      initial={{ "--sweep": reduce && play ? 100 : 0 } as never}
      animate={{ "--sweep": play ? 100 : 0 } as never}
      transition={{ duration: reduce ? 0 : duration, delay: reduce ? 0 : delay, ease: [0.45, 0.05, 0.25, 1] }}
    >
      {words.map((word, i) => {
        const start = offset;
        offset += word.length;
        return (
          <span
            key={i}
            className="mark-word"
            style={{ "--word-start": (start / children.length) * 100, "--word-scale": children.length / word.length } as CSSProperties}
          >
            <span className="mark-word-fill" aria-hidden="true" />
            <span className="mark-word-base">{word}</span>
            <span className="mark-word-ink" aria-hidden="true" data-text={word} />
          </span>
        );
      })}
    </motion.mark>
  );
}

/* Renders clause text with the cited span marked, without guessing: the quote must be an exact substring. */
export function MarkedText({
  text,
  quote,
  play = true,
  delay = 0,
}: {
  text: string;
  quote?: string | null;
  play?: boolean;
  delay?: number;
}) {
  if (!quote) return <>{text}</>;
  const at = text.indexOf(quote);
  if (at < 0) return <>{text}</>;
  return (
    <>
      {text.slice(0, at)}
      <HighlightMark play={play} delay={delay}>
        {quote}
      </HighlightMark>
      {text.slice(at + quote.length)}
    </>
  );
}
