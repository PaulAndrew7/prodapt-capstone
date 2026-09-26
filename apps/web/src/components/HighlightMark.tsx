import { motion, useReducedMotion } from "motion/react";
import type { ReactNode } from "react";
import clsx from "clsx";

/*
  The signature highlighter sweep. Animates the --sweep custom property that sizes the
  mark background, so multi-line spans sweep line by line (box-decoration-break: clone).
  Paint-only on a few spans at a time; instant under reduced motion.
*/
export function HighlightMark({
  children,
  play = true,
  delay = 0,
  className,
  duration = 0.42,
}: {
  children: ReactNode;
  play?: boolean;
  delay?: number;
  className?: string;
  duration?: number;
}) {
  const reduce = useReducedMotion();
  return (
    <motion.mark
      className={clsx("mark-span bg-transparent", className)}
      initial={{ "--sweep": reduce ? "100%" : "0%" } as never}
      animate={{ "--sweep": play ? "100%" : "0%" } as never}
      transition={{ duration: reduce ? 0 : duration, delay: reduce ? 0 : delay, ease: [0.2, 0.8, 0.2, 1] }}
    >
      {children}
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
