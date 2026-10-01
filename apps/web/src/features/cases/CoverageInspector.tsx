import { useId } from "react";
import clsx from "clsx";
import type { Assessment, CoverageRow } from "@/lib/api/types";

const stateLabel: Record<CoverageRow["state"], string> = {
  assessed: "Assessed",
  not_applicable: "Excluded with evidence",
  unassessed: "Unassessed",
  unconfirmed: "Unconfirmed",
};

const basisLabel: Record<CoverageRow["candidate_basis"], string> = {
  clause_kind: "Requirement or exception clause",
  reviewed_corpus: "Obligation identified in the reviewed demo corpus",
  proposed_finding: "Proposed as a requirement by analysis",
};

export function CoverageInspector({
  assessment,
  onOpenEvidence,
}: {
  assessment: Assessment;
  onOpenEvidence: (findingId: string, citationId: string) => void;
}) {
  const headingId = useId();
  const coverage = assessment.coverage;
  if (!coverage) {
    return (
      <section aria-labelledby={headingId} className="mt-6 border-y border-rule py-4 text-sm text-ink-2">
        <h2 id={headingId} className="font-semibold text-ink">Evidence coverage</h2>
        <p className="mt-1">Coverage was not recorded for this saved assessment. Its findings do not establish complete coverage.</p>
      </section>
    );
  }
  const unresolved = coverage.unresolved_clause_ids.length;
  const withheld = unresolved > 0 && assessment.status === "insufficient_information";
  return (
    <section aria-labelledby={headingId} className="mt-6 border-2 border-ink bg-paper p-4 md:p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <h2 id={headingId} className="font-display text-2xl font-semibold">Evidence coverage</h2>
        <span className={clsx("text-sm font-semibold", unresolved > 0 && "text-unknown")}>
          {unresolved > 0 ? "Review needed" : coverage.candidate_count > 0 ? "Retrieved candidates accounted for" : "No requirement candidates retrieved"}
        </span>
      </div>
      <dl className="mt-4 grid grid-cols-3 gap-3 border-y border-rule py-3">
        {[
          ["Retrieved", coverage.candidate_count],
          ["Accounted for", coverage.accounted_count],
          ["Unresolved", unresolved],
        ].map(([label, count]) => (
          <div key={label}>
            <dt className="text-sm text-ink-2">{label}</dt>
            <dd className={clsx("tnum mt-1 font-display text-3xl font-bold", label === "Unresolved" && unresolved > 0 && "text-unknown")}>{count}</dd>
          </div>
        ))}
      </dl>
      <p className="mt-3 text-sm">
        {withheld
          ? "A compliant result is withheld until these candidates have a confirmed assessment or justified exclusion."
          : unresolved > 0
            ? "The established findings decide this result. Other retrieved candidates still need assessment or review."
            : assessment.execution?.mode === "local_review"
              ? "Each retrieved candidate has a recorded disposition. Unknown checks still prevent clearance."
              : "Each retrieved candidate has a confirmed assessment or justified exclusion."}
      </p>
      <p className="mt-2 text-sm text-ink-2">This checks the retrieved candidates. It cannot detect requirements search missed or prove that an interpretation is correct.</p>
      {coverage.rows.length > 0 && (
        <details className="mt-4">
          <summary className="cursor-pointer font-semibold underline decoration-1 underline-offset-4">Inspect {coverage.candidate_count} retrieved candidates</summary>
          <ul className="mt-3 divide-y divide-rule border-y border-rule">
            {coverage.rows.map((row) => {
              const finding = assessment.findings.find((f) => row.finding_ids.includes(f.id));
              const citation = finding && assessment.citations.find((c) => finding.citation_ids.includes(c.id) && c.clause_id === row.clause_id);
              return (
                <li key={row.clause_id} className="py-3">
                  <details>
                    <summary className="cursor-pointer text-sm">
                      <span className="font-semibold">§{row.section} · {row.heading}</span>{" "}
                      <span className={clsx("ml-2 font-semibold", (row.state === "unassessed" || row.state === "unconfirmed") && "text-unknown")}>{stateLabel[row.state]}</span>
                    </summary>
                    <div className="mt-3 space-y-2 text-sm">
                      <p className="text-ink-2">{row.policy_title} · {row.version_label} · page {row.page_index + 1}</p>
                      <blockquote className="border-l-2 border-ink pl-3 leading-relaxed">{row.text}</blockquote>
                      <p>{row.note}</p>
                      <p className="text-ink-2">Included by retrieval: {row.retrieval_reason}. {basisLabel[row.candidate_basis]}.</p>
                      <div className="flex flex-wrap gap-4 font-semibold">
                        <a href={row.source_url} target="_blank" rel="noopener noreferrer" aria-label={`Open original PDF for §${row.section} ${row.heading} · page ${row.page_index + 1}`} className="underline decoration-1 underline-offset-4">Open original PDF · page {row.page_index + 1}</a>
                        {finding && citation && (
                          <button type="button" onClick={() => onOpenEvidence(finding.id, citation.id)} className="underline decoration-1 underline-offset-4">Open finding evidence</button>
                        )}
                      </div>
                    </div>
                  </details>
                </li>
              );
            })}
          </ul>
        </details>
      )}
    </section>
  );
}
