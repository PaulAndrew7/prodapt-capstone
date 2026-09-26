import { motion, useReducedMotion } from "motion/react";
import clsx from "clsx";
import type { AgentRole } from "@/lib/api/types";
import { STAGES, type StageStatus } from "@/lib/events/runStore";

/*
  Five-role progress driven only by real run events. The active stage carries a
  moving mark to say "work is happening now"; it stops the moment the stage completes.
*/
export function StageTrack({
  stages,
  compact = false,
}: {
  stages: Record<AgentRole, StageStatus>;
  compact?: boolean;
}) {
  const reduce = useReducedMotion();
  const active = STAGES.find((s) => stages[s.role] === "active");
  return (
    <div>
      <ol className={clsx("grid grid-cols-5", compact ? "gap-1.5" : "gap-2")}>
        {STAGES.map((s) => {
          const st = stages[s.role];
          return (
            <li key={s.role} className="min-w-0">
              <div className="relative h-1.5 overflow-hidden bg-rule">
                {st === "done" && (
                  <motion.div
                    className="absolute inset-0 origin-left bg-ink"
                    initial={reduce ? false : { scaleX: 0 }}
                    animate={{ scaleX: 1 }}
                    transition={{ duration: 0.35, ease: [0.2, 0.8, 0.2, 1] }}
                  />
                )}
                {st === "active" &&
                  (reduce ? (
                    <div className="absolute inset-y-0 left-0 w-1/2 bg-mark" />
                  ) : (
                    <motion.div
                      className="absolute inset-y-0 w-2/5 bg-mark"
                      initial={{ x: "-100%" }}
                      animate={{ x: "250%" }}
                      transition={{ duration: 1.1, repeat: Infinity, ease: "easeInOut" }}
                    />
                  ))}
              </div>
              {!compact && (
                <p
                  className={clsx(
                    "mt-2 truncate text-sm",
                    st === "pending" && "text-ink-2",
                    st === "skipped" && "text-muted line-through decoration-1",
                    (st === "done" || st === "active") && "font-semibold text-ink",
                  )}
                >
                  {s.label}
                </p>
              )}
            </li>
          );
        })}
      </ol>
      <p className="sr-only" aria-live="polite">
        {active ? `${active.label} in progress` : ""}
      </p>
    </div>
  );
}
