"""Risk stage (plan §7.2): a small documented rubric in plain Python, no model call.

demo-risk-v1:
- high: a supported breach of a mandatory clause that concerns customer data or access;
- medium: a supported breach of any other mandatory clause, or an unresolved conflict
  between applicable clauses;
- low: a breach of a clause that recommends rather than requires.
Unknown requirements get no severity: their impact depends on facts nobody has stated.
Likelihood is always "unknown"; the facts given do not support estimating it. Findings that
validation marked unsupported or contradicted carry no risk.
"""

import re

from app.domain.contracts import (
    Finding,
    Likelihood,
    RequirementStatus,
    Risk,
    Severity,
    SupportState,
)
from app.workflow.retrieval import EvidenceClause

RUBRIC_VERSION = "demo-risk-v1"

MANDATORY = re.compile(
    r"\b(must|shall|requires?|required|may only|may not|must not|prohibited|not permitted|"
    r"never)\b",
    re.IGNORECASE,
)
SENSITIVE = re.compile(
    r"\b(customer data|customer records?|personal data|production|access|"
    r"credentials?|privileged)\b",
    re.IGNORECASE,
)


def _ref(clause: EvidenceClause | None) -> str:
    return f"§{clause.section} {clause.policy_title}" if clause else "the cited clause"


ORDER = {Severity.CRITICAL: 0, Severity.HIGH: 1, Severity.MEDIUM: 2, Severity.LOW: 3}


def assess(findings: list[Finding], clauses: dict[str, EvidenceClause]) -> list[Risk]:
    scored: list[tuple[Severity, str, Finding]] = []
    for f in findings:
        if f.support in (SupportState.UNSUPPORTED, SupportState.CONTRADICTED):
            continue
        clause = clauses.get(f.requirement_id)
        if f.status == RequirementStatus.VIOLATED:
            if clause is not None and not MANDATORY.search(clause.text):
                scored.append((Severity.LOW, "A recommended practice is not followed", f))
            elif clause is not None and SENSITIVE.search(f"{clause.policy_title} {clause.text}"):
                why = "A mandatory requirement about customer data or access is breached"
                scored.append((Severity.HIGH, why, f))
            else:
                scored.append((Severity.MEDIUM, "A mandatory requirement is breached", f))
        elif f.status == RequirementStatus.CONFLICT:
            why = "Applicable clauses conflict and no clause says which one wins"
            scored.append((Severity.MEDIUM, why, f))
    scored.sort(key=lambda item: ORDER[item[0]])
    return [
        Risk(
            id=f"risk_{n}",
            finding_ids=[f.id],
            severity=severity,
            likelihood=Likelihood.UNKNOWN,
            description=f"{why} ({_ref(clauses.get(f.requirement_id))}): {f.title}.",
            rubric_version=RUBRIC_VERSION,
        )
        for n, (severity, why, f) in enumerate(scored, start=1)
    ]
