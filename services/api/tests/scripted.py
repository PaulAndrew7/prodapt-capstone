"""A scripted stand-in for the language model. Tests queue replies per stage; each call pops
the next one. Nothing here is used by the application at runtime."""

import json
from collections.abc import Callable
from typing import Any

from app.workflow.llm import ModelReply

Reply = dict[str, Any] | str | Exception | Callable[[str], dict[str, Any]]


class ScriptedModel:
    name = "scripted:test"

    def __init__(self, **replies: list[Reply]) -> None:
        self.replies = {stage: list(queue) for stage, queue in replies.items()}
        self.calls: list[tuple[str, str]] = []

    def queue(self, stage: str, *replies: Reply) -> None:
        self.replies.setdefault(stage, []).extend(replies)

    def complete(
        self, *, stage: str, system: str, prompt: str, schema: dict[str, Any], timeout: float
    ) -> ModelReply:
        self.calls.append((stage, prompt))
        if not self.replies.get(stage):
            raise AssertionError(f"No scripted reply left for stage {stage!r}")
        reply = self.replies[stage].pop(0)
        if isinstance(reply, Exception):
            raise reply
        if callable(reply):
            reply = reply(prompt)
        text = reply if isinstance(reply, str) else json.dumps(reply)
        return ModelReply(text, input_tokens=100, output_tokens=50)

    def stages(self) -> list[str]:
        return [stage for stage, _ in self.calls]


# Worked scenario (plan §10) on the seeded Kestrel corpus.
SCENARIO = (
    "We plan to send customer records to an external analytics vendor. We have not obtained "
    "written data-owner approval. I do not know whether the vendor review is complete."
)
DS_42 = "ds_v1_4_4.2"
VD_31 = "vd_v1_3_3.1"
DS_42_QUOTE = "requires written approval from the data owner"
VD_31_QUOTE = "hold Approved status in the vendor register"

FACTS = [
    {
        "key": "recipient",
        "label": "Recipient",
        "value": "External analytics vendor",
        "origin": "provided",
    },
    {
        "key": "data_owner_approval",
        "label": "Data-owner approval",
        "value": "Not obtained",
        "origin": "provided",
    },
    {"key": "vendor_review_status", "label": "Vendor review", "value": None, "origin": "unknown"},
]


def analysis_reply(*, questions: bool = True, vendor_status: str = "unknown") -> dict[str, Any]:
    return {
        "in_scope": True,
        "facts": FACTS,
        "findings": [
            {
                "requirement_clause_id": DS_42,
                "title": "Data-owner approval is absent",
                "status": "violated",
                "rationale": "You said written data-owner approval has not been obtained.",
                "fact_keys": ["data_owner_approval", "recipient"],
                "evidence": [{"clause_id": DS_42, "quote": DS_42_QUOTE}],
                "missing_facts": [],
            },
            {
                "requirement_clause_id": VD_31,
                "title": "Vendor review status is unknown",
                "status": vendor_status,
                "rationale": "Nobody has said whether the vendor holds Approved status.",
                "fact_keys": ["vendor_review_status"],
                "evidence": [{"clause_id": VD_31, "quote": VD_31_QUOTE}],
                "missing_facts": ["Vendor register status"],
            },
        ],
        "questions": [
            {
                "fact_key": "vendor_review_status",
                "question": "Does the vendor hold Approved status in the vendor register?",
                "reason": "Clause 3.1 requires Approved status before customer data is shared.",
                "clause_id": VD_31,
                "answer_kind": "choice",
                "choices": ["Yes, approved", "No, not approved"],
            }
        ]
        if questions
        else [],
    }


def validation_reply(**verdicts: str) -> dict[str, Any]:
    ids = verdicts or {"finding_1": "supported", "finding_2": "supported"}
    return {
        "checks": [
            {"finding_id": fid, "verdict": v, "suggested_status": None, "reason": "Checked."}
            for fid, v in ids.items()
        ]
    }


RECOMMENDATION = {
    "actions": [
        {
            "finding_ids": ["finding_1"],
            "clause_ids": [DS_42],
            "action": "Get written approval from the data owner and record it before transfer.",
            "suggested_role": "Data owner",
            "completion_criteria": "An approval entry exists in the data-sharing register.",
            "kind": "mandatory",
        },
        {
            "finding_ids": ["finding_2"],
            "clause_ids": [VD_31],
            "action": "Confirm the vendor holds Approved status in the vendor register.",
            "suggested_role": "Vendor management",
            "completion_criteria": "The register shows Approved status.",
            "kind": "mandatory",
        },
    ]
}
