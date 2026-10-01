"""Per-verdict confidence: an evidence score computed in code, no model call.

Each finding, each overall result and each lookup answer gets a 0-100 score built only from
checks the workflow already records. For a finding (maximum points in brackets):

- validation [40]: the validation stage confirmed it (40), did not check it (10), or rejected it (0)
- quote [20]: a quote matched the stored clause word for word (20), only the whole clause
  could be cited (10), or no valid citation (0)
- facts [25]: a violated/met/conflict verdict rests on facts the requester stated (25), on
  some inferred facts (12), on an unknown fact (5) or on none (0); an unknown verdict names
  the missing fact (25) or not (10)
- search [15]: the requirement clause was ranked 1-3 by search (15), 4-10 (10), or added only
  as a related clause (5)

Bands: high >= 80, medium >= 50, otherwise low. The score ranks how well a verdict is backed;
it is not a probability of being correct. The evaluation reports status accuracy per band,
which is the measured link between the two.
"""

from typing import Literal

from app.domain.contracts import (
    AssessmentStatus,
    Citation,
    Confidence,
    ConfidenceFactor,
    EvidenceCoverage,
    Fact,
    FactOrigin,
    Finding,
    RequirementStatus,
    SupportState,
)
from app.workflow.retrieval import Evidence

HIGH = 80
MEDIUM = 50


def _band(score: int) -> Literal["high", "medium", "low"]:
    return "high" if score >= HIGH else "medium" if score >= MEDIUM else "low"


def _build(basis: str, factors: list[ConfidenceFactor]) -> Confidence:
    score = min(100, sum(f.points for f in factors))
    return Confidence(score=score, band=_band(score), basis=basis, factors=factors)


def _count(n: int, noun: str) -> str:
    return f"{n} {noun}" + ("" if n == 1 else "s")


def _factor(label: str, points: int, max_points: int) -> ConfidenceFactor:
    return ConfidenceFactor(label=label, points=points, max_points=max_points)


def search_ranks(evidence: Evidence) -> dict[str, int]:
    """1-based search rank of each clause search returned; related clauses are absent."""
    hits = [c.id for c in evidence.clauses if c.reason == "search"]
    return {cid: i + 1 for i, cid in enumerate(hits)}


def _search_factor(clause_ids: list[str], evidence: Evidence) -> ConfidenceFactor:
    ranks = search_ranks(evidence)
    found = [ranks[c] for c in clause_ids if c in ranks]
    if found:
        best = min(found)
        return _factor(f"Search ranked the clause #{best}", 15 if best <= 3 else 10, 15)
    if any(c in evidence.by_id() for c in clause_ids):
        return _factor("Clause added as related text, not ranked by search", 5, 15)
    return _factor("Clause was not among the retrieved text", 0, 15)


def score_finding(
    finding: Finding,
    citations: list[Citation],
    facts: list[Fact],
    evidence: Evidence,
    *,
    verified: set[str],
) -> Confidence:
    """`verified` holds the IDs of citations whose model quote was found word for word; the
    others fell back to the whole clause. A one-sentence clause quoted in full is verified."""
    factors: list[ConfidenceFactor] = []

    if finding.support == SupportState.VALIDATED:
        factors.append(_factor("Validation confirmed it against the cited text", 40, 40))
    elif finding.support == SupportState.PENDING:
        factors.append(_factor("Validation did not check it", 10, 40))
    elif finding.support == SupportState.CONTRADICTED:
        factors.append(_factor("Validation disputed it", 0, 40))
    else:
        factors.append(_factor("Validation could not confirm it", 0, 40))

    by_id = {c.id: c for c in citations}
    cited = [by_id[i] for i in finding.citation_ids if i in by_id]
    if any(c.id in verified for c in cited):
        factors.append(_factor("Quote found word for word in the clause", 20, 20))
    elif cited:
        factors.append(_factor("Only the whole clause could be cited", 10, 20))
    else:
        factors.append(_factor("No valid citation", 0, 20))

    if finding.status == RequirementStatus.UNKNOWN:
        if finding.missing_facts:
            factors.append(_factor("The missing fact is named", 25, 25))
        else:
            factors.append(_factor("No missing fact was named", 10, 25))
    else:
        fact_by_id = {f.id: f for f in facts}
        used = [fact_by_id[i] for i in finding.fact_ids if i in fact_by_id]
        if not used:
            factors.append(_factor("No stated fact behind it", 0, 25))
        elif any(f.value is None for f in used):
            factors.append(_factor("It relies on a fact that is unknown", 5, 25))
        elif all(f.origin == FactOrigin.PROVIDED or f.confirmed for f in used):
            factors.append(_factor("Deciding facts were stated by the requester", 25, 25))
        else:
            factors.append(_factor("Some deciding facts were inferred, not stated", 12, 25))

    factors.append(
        _search_factor([finding.requirement_id, *(c.clause_id for c in cited)], evidence)
    )
    return _build("Evidence score for this finding", factors)


def score_assessment(
    status: AssessmentStatus,
    findings: list[Finding],
    evidence: Evidence,
    coverage: EvidenceCoverage | None = None,
) -> Confidence:
    """Confidence in the headline result: the finding(s) that decided it.

    One established violation or conflict decides, so the strongest one counts. A compliant
    result needs every met finding to hold, so the weakest one counts.
    """
    if (
        status == AssessmentStatus.INSUFFICIENT_INFORMATION
        and coverage is not None
        and coverage.unresolved_clause_ids
    ):
        return _build(
            "Overall evidence checks are incomplete: retrieved candidates remain unresolved",
            [_factor("Coverage has unresolved retrieved candidates", 0, 100)],
        )
    numbered = [(i + 1, f) for i, f in enumerate(findings) if f.confidence is not None]
    established = [(n, f) for n, f in numbered if f.support == SupportState.VALIDATED]

    def pick(candidates: list[tuple[int, Finding]], weakest: bool = False) -> Confidence | None:
        if not candidates:
            return None
        n, f = (min if weakest else max)(candidates, key=lambda x: x[1].confidence.score)  # type: ignore[union-attr]
        c = f.confidence
        assert c is not None
        return c.model_copy(update={"basis": f"Decided by finding {n}: {f.title}"})

    if status == AssessmentStatus.NON_COMPLIANT:
        chosen = pick([x for x in established if x[1].status == RequirementStatus.VIOLATED])
    elif status == AssessmentStatus.CONFLICTING_POLICY:
        chosen = pick([x for x in established if x[1].status == RequirementStatus.CONFLICT])
    elif status == AssessmentStatus.COMPLIANT_WITHIN_SCOPE:
        met = [x for x in established if x[1].status == RequirementStatus.MET]
        chosen = pick(met, weakest=True)
    elif status == AssessmentStatus.INSUFFICIENT_INFORMATION:
        open_items = [
            x
            for x in numbered
            if x[1].status == RequirementStatus.UNKNOWN or x[1].support != SupportState.VALIDATED
        ]
        chosen = pick(open_items)
    else:
        chosen = None
    if chosen is not None:
        return chosen
    return _no_requirement(evidence, "No applicable requirement")


def _no_requirement(evidence: Evidence, basis: str) -> Confidence:
    """Nothing applies: there is no finding to check, so only search can back the result."""
    if not evidence.search_hits:
        return _build(basis, [_factor("Search found no clause for this text", 70, 100)])
    return _build(
        basis,
        [
            _factor(
                f"Search returned {evidence.search_hits} clauses but none applied; "
                "nothing could be checked against a quote",
                45,
                100,
            )
        ],
    )


def score_lookup(
    *,
    answerable: bool,
    citations: list[Citation],
    problems: int,
    evidence: Evidence,
    verified: set[str],
) -> Confidence:
    if not evidence.clauses:
        return _no_requirement(evidence, "No clause answers this question")
    if not answerable:
        return _no_requirement(evidence, "The retrieved clauses do not answer this question")
    if not citations:
        return _build("Answer withheld", [_factor("The answer cited no retrieved clause", 0, 100)])
    factors = [
        _factor("Every citation resolved to a retrieved clause", 40, 40)
        if problems == 0
        else _factor(f"{_count(problems, 'citation')} did not resolve", 15, 40)
    ]
    exact = sum(1 for c in citations if c.id in verified)
    factors.append(
        _factor(
            f"{exact} of {_count(len(citations), 'quote')} found word for word",
            round(20 * exact / len(citations)),
            20,
        )
    )
    factors.append(_factor(f"The answer cites {_count(len(citations), 'clause')}", 25, 25))
    factors.append(_search_factor([c.clause_id for c in citations], evidence))
    return _build("Evidence score for this answer", factors)
