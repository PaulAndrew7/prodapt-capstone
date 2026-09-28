"""Convert stored clause records into public contracts. Citations are always built here,
from database rows, never from model output (plan §6.3)."""

import re

from app.domain.contracts import Citation, Clause
from app.persistence import models as m

_FOLD = str.maketrans({"“": '"', "”": '"', "‘": "'", "’": "'", "–": "-", "—": "-", " ": " "})


def canonical(text: str) -> str:
    """Quote/dash/whitespace-folded form used only for matching, never for display."""
    return re.sub(r"\s+", " ", text.translate(_FOLD)).strip()


def quote_in_clause(quote: str, clause_text: str) -> bool:
    return bool(quote.strip()) and canonical(quote) in canonical(clause_text)


def clause_contract(clause: m.Clause) -> Clause:
    return Clause(
        id=clause.id,
        policy_id=clause.version.policy_id,
        policy_version_id=clause.policy_version_id,
        section_path=list(clause.section_path),
        heading=clause.heading,
        text=clause.text,
        page_index=clause.page_start,
        kind=clause.kind,
    )


def source_url(policy_version_id: str, page_index: int) -> str:
    return f"/api/v1/policy-versions/{policy_version_id}/source?page={page_index + 1}"


def quote_page(
    clause_text: str, quote: str, page_start: int, spans: list[tuple[int, int, int]]
) -> int:
    """Page where the quote starts. `spans` holds (text_start, text_end, page_index)."""
    start = canonical(clause_text).find(canonical(quote))
    for text_start, text_end, page_index in spans:
        if text_start <= start < text_end:
            return page_index
    return page_start


def citation_for(citation_id: str, clause: m.Clause, quote: str) -> Citation:
    if not quote_in_clause(quote, clause.text):
        raise ValueError(f"Quote is not part of clause {clause.id}")
    spans = [(s.text_start, s.text_end, s.page_index) for s in clause.spans]
    page = quote_page(clause.text, quote, clause.page_start, spans)
    return Citation(
        id=citation_id,
        policy_version_id=clause.policy_version_id,
        clause_id=clause.id,
        page_index=page,
        section_path=list(clause.section_path),
        quote=quote,
        source_url=source_url(clause.policy_version_id, page),
    )
