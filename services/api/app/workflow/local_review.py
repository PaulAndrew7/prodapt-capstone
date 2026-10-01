"""Model-independent evidence review: exact sources and explicit user dispositions.

This deliberately does not infer semantics from narrative text. Only recorded, enumerated
confirmations decide a finding. Missing checks remain unknown, even if the narrative sounds
positive. No evaluation labels or provider clients are used here.
"""

import uuid

from app.domain.contracts import (
    AssessmentStatus,
    ClarificationQuestion,
    ExecutionInfo,
    Fact,
    FactOrigin,
    Finding,
    LookupAnswer,
    Recommendation,
    RecommendationKind,
    RequirementStatus,
    SupportState,
)
from app.workflow.analysis import Analysis, Answer, EvidenceRef
from app.workflow.coverage import candidate_basis
from app.workflow.retrieval import Evidence
from app.workflow.validation import CitationSet, Validation, check_references

VERSION = "local-review-v1"
CHOICES = {
    "Applies and is satisfied": RequirementStatus.MET,
    "Applies and is breached": RequirementStatus.VIOLATED,
    "Does not apply": RequirementStatus.NOT_APPLICABLE,
}
ERROR_CODES = {
    "model_error",
    "model_auth",
    "model_bad_request",
    "model_not_found",
    "model_rate_limited",
    "model_unreachable",
    "model_timeout",
    "model_refused",
    "model_truncated",
    "invalid_model_output",
    "budget_exhausted",
    "deadline_exceeded",
    "model_not_configured",
}


def execution(
    *, forced: bool = False, error_code: str | None = None, stage: str | None = None
) -> ExecutionInfo:
    return ExecutionInfo(
        mode="local_review",
        reason="model_failure" if error_code else "forced_offline" if forced else "no_model",
        engine_version=VERSION,
        error_code=(error_code if error_code in ERROR_CODES else "model_error")
        if error_code
        else None,
        failed_stage=stage
        if stage in ("analysis", "validation", "recommendation", "lookup")
        else None,
    )


def fact_key(clause_id: str) -> str:
    return f"offline_{clause_id}"


def analyze(evidence: Evidence, answers: list[Answer], *, ask: bool) -> Analysis:
    given = {a.fact_key: a for a in answers}
    facts: list[Fact] = []
    findings: list[Finding] = []
    proposed: dict[str, list[EvidenceRef]] = {}
    questions: list[ClarificationQuestion] = []
    for clause in evidence.clauses:
        if candidate_basis(clause, []) is None:
            continue
        key = fact_key(clause.id)
        answer = given.get(key)
        value = answer.answer if answer else None
        status = CHOICES.get(value or "", RequirementStatus.UNKNOWN)
        fact = Fact(
            id=f"fact_{uuid.uuid4().hex}",
            key=key,
            label=f"Local confirmation: {clause.policy_title} §{clause.section}",
            value=value if value in CHOICES else None,
            origin=FactOrigin.PROVIDED if value in CHOICES else FactOrigin.UNKNOWN,
            confirmed=answer is not None,
            source_message_id=answer.message_id if answer else None,
        )
        facts.append(fact)
        fid = f"finding_{len(findings) + 1}"
        rationale = (
            f"You explicitly confirmed: {value}. This is a recorded user disposition; "
            "local source checks do not independently verify that interpretation."
            if status != RequirementStatus.UNKNOWN
            else "Local review has not established applicability or satisfaction. Narrative text "
            "is not semantically interpreted in this mode; an unknown check is not a breach."
        )
        findings.append(
            Finding(
                id=fid,
                requirement_id=clause.id,
                title=clause.heading,
                status=status,
                rationale=rationale,
                fact_ids=[fact.id],
                citation_ids=[],
                support=SupportState.PENDING,
                missing_facts=["Confirm whether this clause applies and is satisfied."]
                if status == RequirementStatus.UNKNOWN
                else [],
            )
        )
        proposed[fid] = [EvidenceRef(clause_id=clause.id, quote=clause.text)]
        if ask and answer is None and len(questions) < 3:
            questions.append(
                ClarificationQuestion(
                    id=f"offline_{clause.id}",
                    fact_key=key,
                    clause_ref=clause.id,
                    question=f"What can you confirm for {clause.policy_title} "
                    f"§{clause.section}: {clause.heading}?",
                    reason="Read the cited clause before choosing. This records your assessment "
                    "of its condition and requirement; the local engine does not infer it "
                    "from the scenario.",
                    answer_kind="choice",
                    choices=list(CHOICES),
                )
            )
    return Analysis(bool(findings), facts, findings, proposed, questions)


def validate(result: Analysis, evidence: Evidence) -> Validation:
    checked = check_references(result.findings, result.proposed_evidence, evidence)
    facts = {f.id: f for f in result.facts}
    allowed = evidence.by_id()
    updated: list[Finding] = []
    for finding in checked.findings:
        fact = facts.get(finding.fact_ids[0]) if len(finding.fact_ids) == 1 else None
        valid = (
            finding.support != SupportState.UNSUPPORTED
            and fact is not None
            and finding.requirement_id in allowed
            and candidate_basis(allowed[finding.requirement_id], []) is not None
            and fact.key == fact_key(finding.requirement_id)
            and (
                (fact.value is None and finding.status == RequirementStatus.UNKNOWN)
                or (fact.confirmed and fact.origin == FactOrigin.PROVIDED and fact.value in CHOICES)
            )
            and all(cid in checked.verified_quotes for cid in finding.citation_ids)
            and CHOICES.get(fact.value or "", RequirementStatus.UNKNOWN) == finding.status
        )
        support = SupportState.VALIDATED if valid else SupportState.UNSUPPORTED
        checked.notes[finding.id] = (
            "Source quote and recorded disposition checked in code. No semantic model validation."
            if valid
            else "Local confirmation did not match the retrieved candidate."
        )
        updated.append(finding.model_copy(update={"support": support, "confidence": None}))
    checked.findings = updated
    return checked


def recommend(checked: Validation) -> tuple[list[Recommendation], int]:
    actions: list[Recommendation] = []
    for f in checked.findings:
        if f.support != SupportState.VALIDATED or f.status not in (
            RequirementStatus.UNKNOWN,
            RequirementStatus.VIOLATED,
        ):
            continue
        breached = f.status == RequirementStatus.VIOLATED
        actions.append(
            Recommendation(
                id=f"action_{len(actions) + 1}",
                finding_ids=[f.id],
                citation_ids=f.citation_ids,
                action=(
                    f"Address the reported breach of ‘{f.title}’ against the cited requirement "
                    "before proceeding; confirm the corrective action with the policy owner."
                    if breached
                    else f"Read ‘{f.title}’ and record whether its condition applies and its "
                    "requirement is satisfied. Ask the policy owner if the interpretation "
                    "is unclear."
                ),
                suggested_role="Requester and policy owner",
                completion_criteria="Record the disposition and supporting facts, "
                "and resolve any reported breach.",
                kind=RecommendationKind.MANDATORY if breached else RecommendationKind.OPTIONAL,
            )
        )
    return actions, 0


def summary(status: AssessmentStatus, findings: list[Finding]) -> str:
    unknown = sum(f.status == RequirementStatus.UNKNOWN for f in findings)
    if status == AssessmentStatus.NON_COMPLIANT:
        return (
            "Your confirmations identify breached retrieved requirements. Check the "
            "cited clauses and resolve the reported breaches before proceeding."
        )
    if status == AssessmentStatus.COMPLIANT_WITHIN_SCOPE:
        return (
            "You confirmed every retrieved candidate is satisfied or does not apply. "
            "This local review does not independently interpret the scenario or "
            "establish full-policy coverage."
        )
    if status == AssessmentStatus.OUT_OF_SCOPE:
        return (
            "You confirmed that none of the retrieved candidates applies. Search can "
            "miss relevant policies; this is not a compliant result."
        )
    if not findings:
        return (
            "Local search found no requirement candidates to check. Browse the policy "
            "library or rephrase the scenario; no clearance is established."
        )
    return (
        f"Local review cannot establish a complete result: {unknown} retrieved checks "
        "remain unknown. These are unconfirmed dispositions, not established breaches "
        "or necessarily missing narrative facts."
    )


def lookup(
    question: str, evidence: Evidence, info: ExecutionInfo, *, limit: int = 4
) -> LookupAnswer:
    cites = CitationSet()
    for clause in evidence.clauses[:limit]:
        cites.add(clause, clause.text, verified=True)
    return LookupAnswer(
        question=question,
        answer="Local source excerpts for your question. Read the quoted clauses below; "
        "no language model interpreted or synthesized an answer."
        if cites.items
        else "Local search found no clauses for this question. Rephrase it or browse the "
        "policy library; absence of search results does not establish that no policy applies.",
        citations=cites.items,
        support=SupportState.VALIDATED if cites.items else SupportState.UNSUPPORTED,
        snapshot_id=evidence.snapshot_id,
        execution=info,
    )


LIMITATION = (
    "Local review uses source checks and your explicit confirmations, with no language-model "
    "semantic validation. Unknown checks may reflect unreviewed applicability or satisfaction, "
    "rather than facts omitted from the scenario. Exceptions and precedence require human "
    "interpretation. Reported dispositions remain unreviewed."
)
