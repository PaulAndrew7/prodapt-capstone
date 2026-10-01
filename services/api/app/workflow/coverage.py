"""Account for retrieved obligations independently of which findings the model emits.

The gate is conservative: a retrieved candidate is not necessarily applicable. The model
must assess it or justify inapplicability, and validation must confirm that disposition.
This does not detect clauses retrieval missed or prove an interpretation is correct.
"""

from typing import Literal

from app.api.citations import source_url
from app.domain.contracts import (
    ClauseKind,
    CoverageRow,
    EvidenceCoverage,
    Finding,
    RequirementStatus,
    SupportState,
)
from app.ingestion.review_metadata import demo_candidates
from app.workflow.retrieval import Evidence, EvidenceClause

GATE_VERSION = "retrieved-candidates-v1"

# Compatibility export for the corpus audit test. Live selection reads saved version
# review metadata carried by EvidenceClause, including newly uploaded policies.
REVIEWED_GENERAL_CLAUSES = frozenset(
    f"{version}_{section.split('.')[0]}_{section}"
    for version, sections in demo_candidates().items()
    for section in sections
)


def candidate_basis(
    clause: EvidenceClause, findings: list[Finding]
) -> Literal["clause_kind", "reviewed_corpus", "proposed_finding"] | None:
    if clause.kind == ClauseKind.DEFINITION:
        return None
    if clause.kind in (ClauseKind.REQUIREMENT, ClauseKind.EXCEPTION):
        return "clause_kind"
    if clause.reviewed_candidate:
        return "reviewed_corpus"
    if findings:
        return "proposed_finding"
    return None


def inspect(evidence: Evidence, findings: list[Finding]) -> EvidenceCoverage:
    by_requirement: dict[str, list[Finding]] = {}
    for finding in findings:
        by_requirement.setdefault(finding.requirement_id, []).append(finding)
    rows: list[CoverageRow] = []
    for clause in evidence.clauses:
        items = by_requirement.get(clause.id, [])
        basis = candidate_basis(clause, items)
        if basis is None:
            continue
        state: Literal["assessed", "not_applicable", "unassessed", "unconfirmed"]
        if not items:
            state = "unassessed"
            note = "The analysis emitted no finding for this retrieved candidate."
        elif any(f.support != SupportState.VALIDATED for f in items):
            state = "unconfirmed"
            note = "Validation did not confirm every finding for this candidate."
        elif len({f.status for f in items}) != 1:
            state = "unconfirmed"
            note = "Findings disagree about this candidate's status; a review is needed."
        else:
            state = (
                "not_applicable"
                if items[0].status == RequirementStatus.NOT_APPLICABLE
                else "assessed"
            )
            note = " ".join(f.rationale for f in items)
        rows.append(
            CoverageRow(
                clause_id=clause.id,
                policy_title=clause.policy_title,
                policy_version_id=clause.version_id,
                version_label=clause.version_label,
                section=clause.section,
                heading=clause.heading,
                text=clause.text,
                page_index=clause.page_start,
                source_url=source_url(clause.version_id, clause.page_start),
                retrieval_reason=clause.reason,
                candidate_basis=basis,
                finding_ids=[f.id for f in items],
                state=state,
                note=note,
            )
        )
    unresolved = [r.clause_id for r in rows if r.state in ("unassessed", "unconfirmed")]
    return EvidenceCoverage(
        candidate_count=len(rows),
        accounted_count=len(rows) - len(unresolved),
        unresolved_clause_ids=unresolved,
        rows=rows,
    )
