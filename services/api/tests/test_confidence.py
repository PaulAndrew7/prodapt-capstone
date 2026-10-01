"""Per-verdict evidence scores (app/workflow/confidence.py). No database or model needed."""

from dataclasses import replace

from app.domain.contracts import (
    AssessmentStatus,
    Citation,
    Fact,
    FactOrigin,
    Finding,
    RequirementStatus,
    SupportState,
)
from app.workflow.confidence import score_assessment, score_finding, score_lookup
from app.workflow.retrieval import Evidence
from tests.scripted import DS_42, DS_42_QUOTE, VD_31
from tests.test_workflow_rules import DS_TEXT, EVIDENCE, finding

S, V = RequirementStatus, SupportState


def cite(cid: str, clause_id: str, quote: str) -> Citation:
    return Citation(
        id=cid,
        policy_version_id="ds_v1",
        clause_id=clause_id,
        page_index=0,
        section_path=["4.2"],
        quote=quote,
        source_url="/x",
    )


EXACT = cite("cite_1", DS_42, DS_42_QUOTE)
WHOLE = cite("cite_2", DS_42, DS_TEXT)
# Only cite_1's quote was checked word for word; cite_2 is the whole-clause fallback.
VERIFIED = {"cite_1"}
STATED = Fact(
    id="fact_1", key="k", label="Approval", value="no", origin=FactOrigin.PROVIDED, confirmed=True
)
GUESSED = Fact(
    id="fact_2", key="g", label="Guess", value="yes", origin=FactOrigin.INFERRED, confirmed=False
)


def with_(f: Finding, **update: object) -> Finding:
    return f.model_copy(update=update)


def points(f: Finding, citations: list[Citation], facts: list[Fact]) -> int:
    return score_finding(f, citations, facts, EVIDENCE, verified=VERIFIED).score


def test_a_confirmed_quoted_stated_top_ranked_violation_scores_full_marks() -> None:
    f = with_(finding(1, S.VIOLATED, V.VALIDATED), citation_ids=["cite_1"], fact_ids=["fact_1"])
    c = score_finding(f, [EXACT], [STATED], EVIDENCE, verified=VERIFIED)
    assert (c.score, c.band) == (100, "high")
    assert [x.max_points for x in c.factors] == [40, 20, 25, 15]
    assert sum(x.points for x in c.factors) == c.score


def test_each_weaker_signal_lowers_the_score() -> None:
    base = with_(finding(1, S.VIOLATED, V.VALIDATED), citation_ids=["cite_1"], fact_ids=["fact_1"])
    full = points(base, [EXACT], [STATED])
    assert points(with_(base, citation_ids=["cite_2"]), [WHOLE], [STATED]) == full - 10
    assert points(with_(base, fact_ids=["fact_2"]), [EXACT], [GUESSED]) == full - 13
    assert points(with_(base, fact_ids=[]), [EXACT], []) == full - 25
    assert points(with_(base, support=V.PENDING), [EXACT], [STATED]) == full - 30
    unconfirmed = score_finding(
        with_(base, support=V.CONTRADICTED), [EXACT], [STATED], EVIDENCE, verified=VERIFIED
    )
    assert unconfirmed.score == 60 and unconfirmed.band == "medium"


def test_an_unknown_verdict_is_backed_by_naming_the_missing_fact() -> None:
    f = with_(finding(1, S.UNKNOWN, V.VALIDATED, req=VD_31), missing_facts=["Vendor status"])
    named = score_finding(f, [], [], EVIDENCE, verified=VERIFIED)
    unnamed = score_finding(with_(f, missing_facts=[]), [], [], EVIDENCE, verified=VERIFIED)
    assert named.score - unnamed.score == 15


def test_search_rank_and_related_clauses() -> None:
    f = finding(1, S.MET, V.VALIDATED, req=VD_31)
    ranked = score_finding(f, [], [], EVIDENCE, verified=VERIFIED).factors[-1]
    assert ranked.label == "Search ranked the clause #2" and ranked.points == 15
    related = replace(
        EVIDENCE, clauses=[EVIDENCE.clauses[0], replace(EVIDENCE.clauses[1], reason="definition")]
    )
    assert score_finding(f, [], [], related, verified=VERIFIED).factors[-1].points == 5
    assert (
        score_finding(
            finding(1, S.MET, V.VALIDATED, req="nope"), [], [], EVIDENCE, verified=VERIFIED
        )
        .factors[-1]
        .points
        == 0
    )


def scored(*items: tuple[RequirementStatus, SupportState, int]) -> list[Finding]:
    out = []
    for n, (status, support, fact_points) in enumerate(items, start=1):
        f = with_(finding(n, status, support), citation_ids=["cite_1"])
        f = with_(f, fact_ids=["fact_1"] if fact_points else [])
        out.append(
            with_(f, confidence=score_finding(f, [EXACT], [STATED], EVIDENCE, verified=VERIFIED))
        )
    return out


def test_the_result_takes_the_strongest_breach_but_the_weakest_met_requirement() -> None:
    breaches = scored((S.VIOLATED, V.VALIDATED, 0), (S.VIOLATED, V.VALIDATED, 1))
    c = score_assessment(AssessmentStatus.NON_COMPLIANT, breaches, EVIDENCE)
    assert c.score == breaches[1].confidence.score  # type: ignore[union-attr]
    assert c.basis == "Decided by finding 2: Finding 2"

    met = scored((S.MET, V.VALIDATED, 0), (S.MET, V.VALIDATED, 1))
    c = score_assessment(AssessmentStatus.COMPLIANT_WITHIN_SCOPE, met, EVIDENCE)
    assert c.score == met[0].confidence.score  # type: ignore[union-attr]
    assert c.basis.startswith("Decided by finding 1")


def test_no_applicable_requirement_is_scored_from_search_alone() -> None:
    c = score_assessment(AssessmentStatus.OUT_OF_SCOPE, [], EVIDENCE)
    assert c.band == "low" and "none applied" in c.factors[0].label
    empty = Evidence("snap", EVIDENCE.as_of, [], 0)
    assert score_assessment(AssessmentStatus.OUT_OF_SCOPE, [], empty).band == "medium"


def test_lookup_scores() -> None:
    good = score_lookup(
        answerable=True, citations=[EXACT], problems=0, evidence=EVIDENCE, verified=VERIFIED
    )
    assert (good.score, good.band) == (100, "high")
    shaky = score_lookup(
        answerable=True, citations=[WHOLE], problems=1, evidence=EVIDENCE, verified=VERIFIED
    )
    assert shaky.score == 15 + 0 + 25 + 15 and shaky.band == "medium"
    withheld = score_lookup(
        answerable=True, citations=[], problems=1, evidence=EVIDENCE, verified=VERIFIED
    )
    assert withheld.score == 0 and withheld.basis == "Answer withheld"


def test_a_clause_quoted_in_full_counts_as_word_for_word() -> None:
    """A one-sentence clause quoted whole by the model is verified, not the fallback."""
    f = with_(finding(1, S.VIOLATED, V.VALIDATED), citation_ids=["cite_2"], fact_ids=["fact_1"])
    quoted = score_finding(f, [WHOLE], [STATED], EVIDENCE, verified={"cite_2"})
    fallback = score_finding(f, [WHOLE], [STATED], EVIDENCE, verified=set())
    assert quoted.factors[1].points == 20 and fallback.factors[1].points == 10
    answer = score_lookup(
        answerable=True, citations=[WHOLE], problems=0, evidence=EVIDENCE, verified={"cite_2"}
    )
    assert answer.factors[1].label == "1 of 1 quote found word for word"
