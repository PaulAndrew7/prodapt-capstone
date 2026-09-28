import { motion, useReducedMotion } from "motion/react";
import type { CSSProperties } from "react";
import clsx from "clsx";

/*
  Keep normal text underneath a clipped copy with its own yellow background.
  Each word is a wrapping unit, so the overlay never relies on transparent glyphs
  or background-clip:text inside transformed/animated ancestors.
*/
export function HighlightMark({
  children,
  play = true,
  delay = 0,
  className,
  duration = 0.42,
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
      initial={{ "--sweep": reduce && play ? "100%" : "0%" } as never}
      animate={{ "--sweep": play ? "100%" : "0%" } as never}
      transition={{ duration: reduce ? 0 : duration, delay: reduce ? 0 : delay, ease: [0.2, 0.8, 0.2, 1] }}
    >
      {words.map((word, i) => {
        const start = offset;
        offset += word.length;
        return (
          <span
            key={i}
            className="mark-word"
            style={{ "--word-start": `${(start / children.length) * 100}%`, "--word-scale": children.length / word.length } as CSSProperties}
          >
            {word}
            <span className="mark-word-overlay" aria-hidden="true" data-text={word} />
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
