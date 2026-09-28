import { createPortal } from "react-dom";
import type { CaseDetail } from "@/lib/api/types";
import "./printReport.css";

const words = (value: string) => value.replaceAll("_", " ");

/** A complete paper view, independent of selected tabs and collapsed findings. */
export function PrintReport({ detail }: { detail: CaseDetail }) {
  const assessment = detail.assessment;
  if (!assessment) return null;
  return createPortal(
    <article className="assessment-print" aria-label="Printable assessment">
      <header>
        <p>Clause · {assessment.hypothetical ? "Hypothetical assessment" : "Assessment report"}</p>
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
            "Review state": words(assessment.review_state),
          }).map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}
        </dl>
        <p>{assessment.summary}</p>
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
          {finding.missing_facts.length > 0 && <p>Missing facts: {finding.missing_facts.join("; ")}</p>}
          <p>Facts used: {finding.fact_ids.map((id) => detail.facts.find((f) => f.id === id)?.label ?? id).join("; ") || "None"}</p>
          <p>Evidence: {finding.citation_ids.join(", ") || "None"}</p>
        </div>)}
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
      </section>
    </article>,
    document.body,
  );
}
