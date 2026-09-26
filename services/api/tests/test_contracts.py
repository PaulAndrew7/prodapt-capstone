"""The backend contracts, the shared JSON fixture and the web client's types must agree."""

import json
import re
from enum import StrEnum
from pathlib import Path

import pytest

from app.domain import contracts as c

REPO = Path(__file__).resolve().parents[3]
FIXTURES = REPO / "packages" / "contracts" / "fixtures"
TS_TYPES = REPO / "apps" / "web" / "src" / "lib" / "api" / "types.ts"


def test_vendor_assessment_fixture_validates() -> None:
    data = json.loads((FIXTURES / "assessment.vendor-sharing.json").read_text(encoding="utf-8"))
    assessment = c.Assessment.model_validate(data)
    assert assessment.status == c.AssessmentStatus.NON_COMPLIANT
    citation_ids = {x.id for x in assessment.citations}
    finding_ids = {f.id for f in assessment.findings}
    for f in assessment.findings:
        assert set(f.citation_ids) <= citation_ids, f"{f.id} cites an unknown citation"
    for r in [*assessment.risks, *assessment.recommendations]:
        assert set(r.finding_ids) <= finding_ids
    # A supported violation decides the displayed status (§5.2 rule 1).
    assert any(f.status == c.RequirementStatus.VIOLATED for f in assessment.findings)


def test_run_event_fixture_validates() -> None:
    events = json.loads((FIXTURES / "run-events.vendor-sharing.json").read_text(encoding="utf-8"))
    parsed = [c.RunEvent.model_validate(e) for e in events]
    assert [e.sequence for e in parsed] == list(range(1, len(parsed) + 1))
    assert len({e.event_id for e in parsed}) == len(parsed)


def _ts_union(name: str) -> set[str]:
    source = TS_TYPES.read_text(encoding="utf-8")
    m = re.search(rf"export type {name} =(.*?);", source, re.DOTALL)
    assert m, f"{name} not found in types.ts"
    return set(re.findall(r'"([^"]+)"', m.group(1)))


@pytest.mark.parametrize(
    ("ts_name", "enum"),
    [
        ("AssessmentStatus", c.AssessmentStatus),
        ("RequirementStatus", c.RequirementStatus),
        ("SupportState", c.SupportState),
        ("FactOrigin", c.FactOrigin),
        ("RunState", c.RunState),
        ("AgentRole", c.AgentRole),
        ("ReviewState", c.ReviewState),
    ],
)
def test_enums_match_web_types(ts_name: str, enum: type[StrEnum]) -> None:
    assert _ts_union(ts_name) == {e.value for e in enum}


def test_event_types_match_web_types() -> None:
    source = TS_TYPES.read_text(encoding="utf-8")
    block = source[source.index("export interface RunEvent") :]
    block = block[: block.index("payload")]
    assert set(re.findall(r'"([a-z]+\.[a-z]+)"', block)) == {e.value for e in c.EventType}
