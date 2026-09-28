import { useEffect, useRef } from "react";
import { useQueries } from "@tanstack/react-query";
import { motion, useReducedMotion } from "motion/react";
import { ArrowUpRight, X } from "@phosphor-icons/react";
import { Link } from "react-router";
import type { Citation, RequirementStatus } from "@/lib/api/types";
import { api } from "@/lib/api";
import { MarkedText } from "@/components/HighlightMark";
import { RequirementStatusWord } from "@/components/Status";
import { ErrorNotice, Skeleton } from "@/components/Feedback";
import { formatDate } from "@/lib/format";

/*
  Finding -> clause -> original page, without leaving the case. The cited span is marked
  only when the stored quote is an exact substring of the clause text; nothing is guessed.
*/
export function EvidenceDrawer({
  title,
  status,
  citations,
  focusCitationId,
  onClose,
}: {
  title: string;
  status?: RequirementStatus;
  citations: Citation[];
  focusCitationId: string;
  onClose: () => void;
}) {
  const reduce = useReducedMotion();
  const headingRef = useRef<HTMLHeadingElement>(null);
  const ordered = [...citations].sort((a, b) =>
    a.id === focusCitationId ? -1 : b.id === focusCitationId ? 1 : 0,
  );
  const versionIds = [...new Set(ordered.map((c) => c.policy_version_id))];
  const versions = useQueries({
    queries: versionIds.map((id) => ({
      queryKey: ["policy-version", id],
      queryFn: () => api.getPolicyVersion(id),
      staleTime: Infinity,
    })),
  });
  const byId = new Map(versions.filter((q) => q.data).map((q) => [q.data!.id, q.data!]));

  useEffect(() => {
    headingRef.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose, focusCitationId]);

  return (
    <motion.aside
      aria-labelledby="evidence-h"
      className="absolute inset-y-0 right-0 z-20 flex w-full flex-col border-l-2 border-ink bg-sheet md:w-[min(640px,92%)]"
      initial={reduce ? false : { x: "100%" }}
      animate={{ x: 0 }}
      exit={reduce ? undefined : { x: "100%" }}
      transition={{ duration: 0.28, ease: [0.2, 0.8, 0.2, 1] }}
    >
      <div className="flex items-start justify-between gap-4 border-b-2 border-ink px-6 py-5">
        <div className="min-w-0">
          <h2 ref={headingRef} id="evidence-h" tabIndex={-1} className="text-lg font-semibold leading-snug outline-none">
            {title}
          </h2>
          {status && <RequirementStatusWord status={status} className="mt-1" />}
        </div>
        <button
          type="button"
          onClick={onClose}
          className="flex size-10 shrink-0 items-center justify-center border-2 border-ink hover:bg-ink hover:text-paper"
          aria-label="Close evidence"
        >
          <X aria-hidden />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto overscroll-contain px-6 py-6">
        <ol className="space-y-10">
          {ordered.map((c, i) => {
            const version = byId.get(c.policy_version_id);
            const query = versions[versionIds.indexOf(c.policy_version_id)];
            const clause = version?.clauses.find((cl) => cl.id === c.clause_id);
            const number = c.section_path[c.section_path.length - 1];
            return (
              <li key={c.id}>
                {query.isError ? (
                  <ErrorNotice
                    title="This evidence could not be loaded"
                    body="The saved finding is unchanged. Retry to read its policy source."
                    onRetry={() => query.refetch()}
                  />
                ) : !version ? (
                  <div className="space-y-3">
                    <Skeleton className="h-4 w-2/3" />
                    <Skeleton className="h-14 w-24" />
                    <Skeleton className="h-4 w-full" />
                    <Skeleton className="h-4 w-5/6" />
                  </div>
                ) : (
                  <article aria-label={`${version.policy_title} clause ${number}`}>
                    {!clause && (
                      <p role="status" className="mb-4 border-2 border-ink p-3 text-sm">
                        This clause is missing from the policy version. The saved quote below could not be checked against the current source.
                      </p>
                    )}
                    <p className="font-semibold">{version.policy_title}</p>
                    <p className="tnum text-sm text-ink-2">
                      {version.label}, effective {formatDate(version.effective_from)}
                      {version.effective_to ? ` to ${formatDate(version.effective_to)}` : ""}
                    </p>
                    <p className="tnum text-sm text-ink-2">Page {c.page_index + 1}</p>
                    <div className="mt-5 flex items-baseline gap-4">
                      <span className="tnum font-display text-6xl font-bold leading-none">{number}</span>
                      {clause && <span className="text-lg font-semibold">{clause.heading}</span>}
                    </div>
                    <p className="mt-4 max-w-[62ch] text-[1.125rem] leading-[1.7]">
                      {clause ? <MarkedText text={clause.text} quote={c.quote || null} delay={0.25 + i * 0.12} /> : c.quote}
                    </p>
                    {c.quote && clause?.text.includes(c.quote) && (
                      <p className="mt-3 text-sm text-ink-2">The marked words match the stored clause text exactly.</p>
                    )}
                    <Link
                      to={`/app/policies/${version.policy_id}/versions/${version.id}?clause=${encodeURIComponent(c.clause_id)}${c.quote ? `&q=${encodeURIComponent(c.quote)}` : ""}`}
                      className="mt-4 inline-flex items-center gap-1.5 font-semibold underline decoration-1 underline-offset-4 hover:bg-mark hover:text-on-mark hover:no-underline"
                    >
                      Open in policy <ArrowUpRight size={16} aria-hidden />
                    </Link>
                  </article>
                )}
              </li>
            );
          })}
        </ol>
      </div>
    </motion.aside>
  );
}
