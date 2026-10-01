import { createPortal } from "react-dom";
import type { CaseDetail } from "@/lib/api/types";
import { CONFIDENCE_NOTE } from "@/components/Confidence";
import "./printReport.css";

const words = (value: string) => value.replaceAll("_", " ");

/** A complete paper view, independent of selected tabs and collapsed findings. */
export function PrintReport({ detail }: { detail: CaseDetail }) {
  const assessment = detail.assessment;
  if (!assessment) return null;
  return createPortal(
    <article className="assessment-print" aria-label="Printable assessment">
      <header>
        <p>Paul.ez · {assessment.hypothetical ? "Hypothetical assessment" : "Assessment report"}</p>
        <h1>{detail.title}</h1>
        <p>Fictional Kestrel Mutual policies. This report does not certify compliance.</p>
        <dl>
          {Object.entries({
            Case: detail.id,
            Run: assessment.run_id,
            Revision: assessment.case_revision_id,
            "Policy snapshot": assessment.policy_snapshot_id,
            "As of": assessment.as_of,
            Scope: assessment.scope,
            Result: words(assessment.status),
            ...(assessment.confidence && {
              "Evidence score": `${assessment.confidence.score}/100 (${assessment.confidence.band}) · ${assessment.confidence.basis}`,
            }),
            "Review state": words(assessment.review_state),
            ...(assessment.execution && {
              "Execution mode": words(assessment.execution.mode),
              "Execution reason": words(assessment.execution.reason),
              "Engine version": assessment.execution.engine_version ?? "Configured model",
              ...(assessment.execution.failed_stage && { "Failed model stage": assessment.execution.failed_stage }),
            }),
          }).map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}
        </dl>
        <p>{assessment.summary}</p>
        {assessment.execution?.mode === "local_review" && <p>Local review used source checks and explicit user confirmations. No language model semantically validated this result.</p>}
      </header>
      <section>
        <h2>Scenario and facts</h2>
        <p>{detail.scenario_text}</p>
        <ul>{detail.facts.map((fact) => <li key={fact.id}>
          {fact.label}: {fact.value ?? "unknown"} ({words(fact.origin)}; {fact.confirmed ? "confirmed" : "unconfirmed"})
        </li>)}</ul>
      </section>
      <section>
        <h2>Findings</h2>
        {assessment.findings.map((finding, index) => <div key={finding.id}>
          <h3>{index + 1}. {finding.title} — {words(finding.status)}</h3>
          <p>{finding.rationale}</p>
          <p>Evidence check: {words(finding.support)}. {finding.support !== "validated" && "This finding did not decide the result."}</p>
          {finding.confidence && <p>
            Evidence score: {finding.confidence.score}/100 ({finding.confidence.band}) —{" "}
            {finding.confidence.factors.map((f) => `${f.label} ${f.points}/${f.max_points}`).join("; ")}
          </p>}
          {finding.missing_facts.length > 0 && <p>Missing facts: {finding.missing_facts.join("; ")}</p>}
          <p>Facts used: {finding.fact_ids.map((id) => detail.facts.find((f) => f.id === id)?.label ?? id).join("; ") || "None"}</p>
          <p>Evidence: {finding.citation_ids.join(", ") || "None"}</p>
        </div>)}
      </section>
      <section>
        <h2>Evidence coverage</h2>
        {assessment.coverage ? <>
          <p>Retrieved candidates: {assessment.coverage.candidate_count}. Accounted for: {assessment.coverage.accounted_count}. Unresolved: {assessment.coverage.unresolved_clause_ids.length}.</p>
          <p>Coverage checks the retrieved candidates; it cannot detect requirements search missed or prove that an interpretation is correct.</p>
          {assessment.coverage.rows.map((row) => <div key={row.clause_id}>
            <h3>§{row.section} {row.heading} — {words(row.state)}</h3>
            <p>{row.policy_title} · {row.version_label} · Page {row.page_index + 1}. Included by retrieval: {row.retrieval_reason}.</p>
            <blockquote>{row.text}</blockquote>
            <p>{row.note}</p>
            <p>Source: {new URL(row.source_url, window.location.href).href}</p>
          </div>)}
        </> : <p>Coverage was not recorded for this saved assessment. Its findings do not establish complete coverage.</p>}
      </section>
      <section>
        <h2>Gaps and risks</h2>
        {assessment.risks.map((risk) => <p key={risk.id}>
          <strong>{words(risk.severity)}</strong> · likelihood: {words(risk.likelihood)} — {risk.description}
        </p>)}
      </section>
      <section>
        <h2>Recommended actions</h2>
        {assessment.recommendations.map((rec) => <div key={rec.id}>
          <h3>{rec.action}</h3>
          <p>{words(rec.kind)} · Suggested role: {rec.suggested_role}</p>
          <p>Complete when: {rec.completion_criteria}</p>
          <p>Evidence: {rec.citation_ids.join(", ") || "None"}</p>
        </div>)}
      </section>
      <section>
        <h2>Evidence and sources</h2>
        {assessment.citations.map((citation) => <div key={citation.id}>
          <h3>{citation.id} · {citation.section_path.join(" / ")}</h3>
          <p>Version: {citation.policy_version_id} · Clause: {citation.clause_id} · Page {citation.page_index + 1}</p>
          <blockquote>{citation.quote}</blockquote>
          <p>Source: {new URL(citation.source_url, window.location.href).href}</p>
        </div>)}
      </section>
      <section>
        <h2>Limitations</h2>
        <ul>{assessment.limitations.map((limitation, index) => <li key={index}>{limitation}</li>)}</ul>
        {assessment.confidence && <p>{CONFIDENCE_NOTE}</p>}
      </section>
    </article>,
    document.body,
  );
}
