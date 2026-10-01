"""Policy-derived review metadata, independent of scenario labels and model prompts."""

import json
from functools import lru_cache
from typing import Any

from app.config import REPO_ROOT


@lru_cache
def demo_candidates() -> dict[str, list[str]]:
    data = json.loads(
        (REPO_ROOT / "data/demo/reviewed-candidates.json").read_text(encoding="utf-8")
    )
    return {str(k): [str(s) for s in v] for k, v in data.items()}


def reviewed_candidates(version_id: str, provenance: dict[str, Any]) -> set[str]:
    # Compatibility for demo versions seeded before review metadata was persisted.
    # Uploaded versions have their own saved classifications and never use this catalog.
    saved = provenance.get("reviewed_candidates")
    if isinstance(saved, list):
        return {s for s in saved if isinstance(s, str)}
    return set(demo_candidates().get(version_id, []))
