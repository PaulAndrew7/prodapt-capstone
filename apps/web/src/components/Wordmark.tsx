import type { Ref } from "react";
import clsx from "clsx";

/* Typographic wordmark: the name, with the highlighter under its baseline. */
export function Wordmark({ className, size = "md", ref }: { className?: string; size?: "md" | "lg"; ref?: Ref<HTMLSpanElement> }) {
  return (
    <span
      ref={ref}
      className={clsx(
        "relative inline-block font-display font-bold leading-none tracking-[-0.01em]",
        size === "md" ? "text-[1.6rem]" : "text-[2.4rem]",
        className,
      )}
    >
      <span aria-hidden className="wordmark-bar absolute inset-x-[-0.06em] bg-mark" />
      <span className="relative">Paul.ez</span>
    </span>
  );
}
