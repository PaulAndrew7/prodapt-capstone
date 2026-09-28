"""The evaluation answer keys (data/evaluation/*/scenarios.json) must only name clauses that
exist in the Kestrel corpus and are in force, in a published version, on the scenario date.
Related scenario families must stay within one split (plan §13.1)."""

import json
import re
from datetime import date
from typing import Any

import pytest

from app.config import REPO_ROOT

CORPUS = REPO_ROOT / "data" / "demo"
EVAL = REPO_ROOT / "data" / "evaluation"
REQUIREMENT_STATES = {"met", "violated", "unknown", "not_applicable", "conflict"}
ASSESSMENT_STATES = {
    "non_compliant",
    "conflicting_policy",
    "insufficient_information",
    "compliant_within_scope",
    "out_of_scope",
}
FIELDS = {
    "id", "split", "family", "category", "tags", "scenario", "as_of", "facts", "requirements",
    "evidence_sets", "expected_missing_facts", "acceptable_status", "recommendation_clauses",
    "notes", "review",
}  # fmt: skip


def _clauses() -> dict[str, dict[str, Any]]:
    """Clause ID -> the version's status and effective dates, from the authored Markdown."""
    manifest = json.loads((CORPUS / "manifest.json").read_text(encoding="utf-8"))
    out: dict[str, dict[str, Any]] = {}
    for doc in manifest["documents"]:
        version = {
            "status": doc["status"],
            "from": date.fromisoformat(doc["effective_from"]),
            "to": date.fromisoformat(doc["effective_to"]) if doc["effective_to"] else None,
        }
        text = (CORPUS / doc["source"]).read_text(encoding="utf-8")
        # Numbered clauses become ds_v1_4_4.2; a section with no numbered clauses (such as
        # "# 1 Purpose") is itself a clause, ds_v1_1.
        numbered = re.findall(r"^## (\d+)\.(\d+) ", text, flags=re.MULTILINE)
        for section, sub in numbered:
            out[f"{doc['version_id']}_{section}_{section}.{sub}"] = version
        for section in re.findall(r"^# (\d+) \S", text, flags=re.MULTILINE):
            if section not in {s for s, _ in numbered}:
                out[f"{doc['version_id']}_{section}"] = version
    return out


def _load(split: str) -> list[dict[str, Any]]:
    data: list[dict[str, Any]] = json.loads(
        (EVAL / split / "scenarios.json").read_text(encoding="utf-8")
    )
    return data


SPLITS = ["dev", "test"]
CLAUSES = _clauses()


def test_corpus_parse_finds_every_clause() -> None:
    assert len(CLAUSES) == 111


@pytest.mark.parametrize("split", SPLITS)
def test_scenarios_are_well_formed(split: str) -> None:
    scenarios = _load(split)
    assert len({s["id"] for s in scenarios}) == len(scenarios)
    for s in scenarios:
        assert set(s) == FIELDS, s["id"]
        assert s["split"] == split and s["id"].startswith(f"{split}-")
        assert set(s["requirements"].values()) <= REQUIREMENT_STATES, s["id"]
        assert s["acceptable_status"] and set(s["acceptable_status"]) <= ASSESSMENT_STATES
        assert s["review"] in {"authored", "reviewed", "disputed"}
        assert {f["origin"] for f in s["facts"]} <= {"provided", "inferred", "unknown"}
        unknown_facts = {f["key"] for f in s["facts"] if f["origin"] == "unknown"}
        assert set(s["expected_missing_facts"]) <= unknown_facts, s["id"]
        if "out_of_scope" in s["acceptable_status"]:
            assert not s["requirements"] and not s["evidence_sets"], s["id"]


@pytest.mark.parametrize("split", SPLITS)
def test_labelled_clauses_exist_and_are_in_force(split: str) -> None:
    for s in _load(split):
        as_of = date.fromisoformat(s["as_of"])
        named = set(s["requirements"]) | set(s["recommendation_clauses"])
        named |= {c for group in s["evidence_sets"] for c in group}
        for clause_id in named:
            assert clause_id in CLAUSES, f"{s['id']}: unknown clause {clause_id}"
            v = CLAUSES[clause_id]
            assert v["status"] != "draft", f"{s['id']}: {clause_id} is in a draft version"
            in_force = v["from"] <= as_of and (v["to"] is None or as_of <= v["to"])
            assert in_force, f"{s['id']}: {clause_id} is not in force on {as_of}"


def test_families_do_not_cross_splits() -> None:
    dev = {s["family"] for s in _load("dev")}
    test = {s["family"] for s in _load("test")}
    assert not dev & test


def test_answer_keys_stay_out_of_the_corpus() -> None:
    corpus_files = {p.resolve() for p in CORPUS.rglob("*") if p.is_file()}
    assert not any(EVAL.resolve() in p.parents for p in corpus_files)
    for split in SPLITS:
        for s in _load(split):
            assert s["id"] not in (CORPUS / "manifest.json").read_text(encoding="utf-8")
