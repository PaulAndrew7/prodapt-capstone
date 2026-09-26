import {
  CheckCircle,
  CircleDashed,
  MinusCircle,
  Question,
  Scales,
  XCircle,
  type Icon,
} from "@phosphor-icons/react";
import { motion, useReducedMotion } from "motion/react";
import clsx from "clsx";
import type { AssessmentStatus, RequirementStatus } from "@/lib/api/types";
import {
  assessmentTone,
  requirementLabel,
  requirementTone,
  statusLabel,
  toneText,
  verdictCopy,
  type Tone,
} from "@/lib/status";

const toneIcon: Record<Tone, Icon> = {
  violated: XCircle,
  unknown: Question,
  met: CheckCircle,
  muted: MinusCircle,
  conflict: Scales,
};

export function StatusWord({
  tone,
  label,
  size = 18,
  className,
}: {
  tone: Tone;
  label: string;
  size?: number;
  className?: string;
}) {
  const Glyph = tone === "muted" && label.startsWith("Out") ? CircleDashed : toneIcon[tone];
  return (
    <span className={clsx("inline-flex items-center gap-1.5 font-semibold", toneText[tone], className)}>
      <Glyph size={size} aria-hidden />
      {label}
    </span>
  );
}

export function RequirementStatusWord({ status, className }: { status: RequirementStatus; className?: string }) {
  return <StatusWord tone={requirementTone[status]} label={requirementLabel[status]} className={className} />;
}

export function AssessmentStatusWord({ status, className }: { status: AssessmentStatus; className?: string }) {
  return <StatusWord tone={assessmentTone[status]} label={statusLabel[status]} className={className} />;
}

/* The verdict, set big. Words rise out of a line mask when a result arrives. */
export function VerdictHeadline({
  status,
  reveal = true,
  size = "lg",
  as: Tag = "h2",
}: {
  status: AssessmentStatus;
  reveal?: boolean;
  size?: "md" | "lg" | "xl";
  as?: "h1" | "h2" | "p";
}) {
  const reduce = useReducedMotion();
  const words = verdictCopy[status].split(" ");
  const sizeClass = {
    md: "text-[clamp(2.25rem,3.4vw,3.5rem)]",
    lg: "text-[clamp(2.75rem,4.8vw,5.25rem)]",
    xl: "text-[clamp(3rem,6.6vw,6rem)]",
  }[size];
  const animate = reveal && !reduce;
  return (
    <Tag className={clsx("font-display font-bold leading-[1.05] tracking-[-0.01em] text-ink", sizeClass)}>
      <span className="sr-only">{verdictCopy[status]}</span>
      {words.map((w, i) => (
        <span key={`${status}-${i}`} aria-hidden className="inline-block overflow-hidden pb-[0.08em] align-top">
          <motion.span
            className="inline-block"
            initial={animate ? { y: "108%" } : false}
            animate={{ y: 0 }}
            transition={{ duration: 0.6, delay: 0.08 * i, ease: [0.16, 1, 0.3, 1] }}
          >
            {w}
            {i < words.length - 1 ? " " : ""}
          </motion.span>
        </span>
      ))}
    </Tag>
  );
}
