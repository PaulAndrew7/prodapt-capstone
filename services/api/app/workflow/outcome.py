"""Final checks (plan §5.2, §7.2): the overall result, summary and limitations, in plain Python.

Only findings the validation stage confirmed ("validated") are established. The ordered rules:
1. an established violation                                  -> non_compliant
2. otherwise an established conflict                         -> conflicting_policy
3. otherwise an established unknown, any violated/met/conflict/not-applicable claim that
   validation did not confirm, an unknown that validation disputed, or an unresolved
   retrieved requirement candidate
                                                              -> insufficient_information
4. otherwise at least one established met requirement        -> compliant_within_scope
5. otherwise (no applicable requirement)                      -> out_of_scope
An unconfirmed claim or omitted retrieved candidate can never produce a compliant result.
"""

from app.domain.contracts import (
    AssessmentStatus,
    EvidenceCoverage,
    Finding,
    RequirementStatus,
    SupportState,
)

# Claims that must be confirmed before a result can be compliant. A disputed "not applicable"
# means the requirement may apply after all, so it blocks compliance like the others.
CLAIMS = (
    RequirementStatus.VIOLATED,
    RequirementStatus.MET,
    RequirementStatus.CONFLICT,
    RequirementStatus.NOT_APPLICABLE,
)


def derive_status(
    findings: list[Finding], coverage: EvidenceCoverage | None = None
) -> AssessmentStatus:
    established = [f for f in findings if f.support == SupportState.VALIDATED]
    statuses = {f.status for f in established}
    if RequirementStatus.VIOLATED in statuses:
        return AssessmentStatus.NON_COMPLIANT
    if RequirementStatus.CONFLICT in statuses:
        return AssessmentStatus.CONFLICTING_POLICY
    unconfirmed = any(
        f.support != SupportState.VALIDATED
        and (f.status in CLAIMS or f.support == SupportState.CONTRADICTED)
        for f in findings
    )
    if (
        RequirementStatus.UNKNOWN in statuses
        or unconfirmed
        or (coverage is not None and coverage.unresolved_clause_ids)
    ):
        return AssessmentStatus.INSUFFICIENT_INFORMATION
    if RequirementStatus.MET in statuses:
        return AssessmentStatus.COMPLIANT_WITHIN_SCOPE
    return AssessmentStatus.OUT_OF_SCOPE


def _titles(findings: list[Finding]) -> str:
    names = [f.title.rstrip(".").lower() for f in findings]
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def _count(n: int, noun: str) -> str:
    return f"{n} {noun}" + ("" if n == 1 else "s")


WORDS = ["No", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten"]


def _sentence_count(n: int, noun: str) -> str:
    """A count that can start a sentence: "One other requirement", "12 other requirements"."""
    number = WORDS[n] if n < len(WORDS) else str(n)
    return f"{number} {noun}" + ("" if n == 1 else "s")


def summarize(
    status: AssessmentStatus,
    findings: list[Finding],
    coverage: EvidenceCoverage | None = None,
) -> str:
    established = [f for f in findings if f.support == SupportState.VALIDATED]

    def having(s: RequirementStatus) -> list[Finding]:
        return [f for f in established if f.status == s]

    violated, unknown = having(RequirementStatus.VIOLATED), having(RequirementStatus.UNKNOWN)
    open_note = (
        f" {_sentence_count(len(unknown), 'other requirement')} cannot be checked until "
        "missing facts are known."
        if unknown
        else ""
    )
    if status == AssessmentStatus.NON_COMPLIANT:
        return (
            f"The plan breaches {_count(len(violated), 'requirement')}: {_titles(violated)}."
            + open_note
        )
    if status == AssessmentStatus.CONFLICTING_POLICY:
        conflicts = having(RequirementStatus.CONFLICT)
        return (
            f"Applicable clauses conflict: {_titles(conflicts)}. The policy owners need to "
            "decide which one applies." + open_note
        )
    if status == AssessmentStatus.INSUFFICIENT_INFORMATION:
        unresolved_count = len(coverage.unresolved_clause_ids) if coverage is not None else 0
        coverage_note = (
            f"{_sentence_count(unresolved_count, 'retrieved requirement candidate')} "
            f"{'has' if unresolved_count == 1 else 'have'} no confirmed assessment or "
            "justified exclusion. A compliant result is withheld "
            "until this coverage gap is reviewed."
            if unresolved_count
            else ""
        )
        if unknown:
            return (
                f"The result depends on facts that are not known yet: {_titles(unknown)}. "
                "No breach is established from the facts given."
                + (f" {coverage_note}" if coverage_note else "")
            )
        if coverage_note:
            return coverage_note
        return (
            "Some findings could not be confirmed against the cited policy text, so no "
            "overall result is given."
        )
    if status == AssessmentStatus.COMPLIANT_WITHIN_SCOPE:
        met = having(RequirementStatus.MET)
        return (
            f"Every applicable requirement found ({_count(len(met), 'requirement')}) is met on "
            "the facts given. Only the policies retrieved for this case were checked."
        )
    return (
        "No policy in the demo corpus sets requirements for this activity. This is not a "
        "compliant result."
    )


def limitations(
    *,
    snapshot_id: str,
    as_of: str,
    findings: list[Finding],
    quote_mismatches: int,
    invalid_references: int,
    dropped_actions: int,
    unanswered: int,
    coverage: EvidenceCoverage | None = None,
) -> list[str]:
    notes = [
        f"Assessed only against the fictional Kestrel Mutual demo policies in snapshot "
        f"{snapshot_id}, in force on {as_of}. Laws, regulations and other policies were not "
        "considered.",
    ]
    unconfirmed = [f for f in findings if f.support != SupportState.VALIDATED]
    if coverage is not None:
        notes.append(
            f"Coverage accounts for {coverage.accounted_count} of {coverage.candidate_count} "
            "retrieved requirement candidates. It uses clause classifications and a reviewed "
            "demo-corpus catalog; it cannot detect requirements retrieval missed or prove "
            "that a validated interpretation is correct."
        )
        if coverage.unresolved_clause_ids:
            notes.append(
                "Unresolved coverage: " + ", ".join(coverage.unresolved_clause_ids) + ". "
                "These candidates are not established violations or missing business facts."
            )
    if unconfirmed:
        notes.append(
            f"{_count(len(unconfirmed), 'finding')} could not be confirmed against the cited text "
            "and did not decide the result."
        )
    if invalid_references:
        notes.append(
            f"{_count(invalid_references, 'proposed citation')} pointed outside the retrieved "
            "clauses and were removed."
        )
    if quote_mismatches:
        notes.append(
            f"{_count(quote_mismatches, 'quoted passage')} did not match the stored clause text; "
            "the whole clause is cited instead."
        )
    if dropped_actions:
        notes.append(
            f"{_count(dropped_actions, 'proposed action')} did not link to a validated finding "
            "and were left out."
        )
    if unanswered:
        notes.append(
            f"{_count(unanswered, 'clarifying question')} went unanswered; those facts stay "
            "unknown."
        )
    notes.append(
        "This is an automated reading of policy text, not legal advice. Check decisive "
        "findings against the cited source."
    )
    return notes
