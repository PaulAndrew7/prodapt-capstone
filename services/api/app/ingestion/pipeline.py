"""Ingest one policy version from PDF bytes (plan §6.1).

Everything for a version is written in the caller's transaction and only marked
`index_status=ready` after integrity checks pass, so a half-built index is never visible:
either the whole version commits or none of it does. Re-ingesting identical bytes for the
same policy and label is a no-op; different bytes under an existing label are rejected
(publish them as a new version instead).
"""

import hashlib
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.domain.contracts import ClauseKind, IndexStatus, PolicyVersionStatus
from app.ingestion.chunking import CHUNKER_VERSION, chunk_clause, chunk_prefix
from app.ingestion.pdf import IngestionError, extract_pages
from app.ingestion.segment import merge_spans, segment
from app.persistence import models as m
from app.retrieval.embeddings import MAX_INPUT_TOKENS, Embedder
from app.storage import Storage


@dataclass
class VersionInput:
    policy: m.Policy
    version_id: str
    label: str
    effective_from: date
    effective_to: date | None
    status: PolicyVersionStatus
    provenance: dict[str, Any]
    upload_id: str | None = None


@dataclass
class IngestResult:
    version: m.PolicyVersion
    created: bool
    clauses: int
    chunks: int
    warnings: list[str]


def _clause_id(version_id: str, section_path: list[str]) -> str:
    # Matches the web fixtures: ds_v1 + ["4", "4.2"] -> "ds_v1_4_4.2"
    return "_".join([version_id, *section_path])


def ingest_version(
    session: Session,
    data: bytes,
    spec: VersionInput,
    *,
    storage: Storage,
    embedder: Embedder | None,
) -> IngestResult:
    sha = hashlib.sha256(data).hexdigest()
    existing = session.scalar(
        select(m.PolicyVersion).where(
            m.PolicyVersion.policy_id == spec.policy.id, m.PolicyVersion.label == spec.label
        )
    )
    if existing is not None:
        if existing.original_sha256 != sha:
            raise IngestionError(
                "version_conflict",
                f"{spec.policy.title} {spec.label} already exists with different content. "
                "Upload it as a new version.",
            )
        return IngestResult(existing, False, len(existing.clauses), 0, [])

    pages = extract_pages(data, max_pages=get_settings().max_pdf_pages)
    seg = segment(pages)
    if not seg.clauses:
        raise IngestionError("no_clauses", "; ".join(seg.warnings) or "No clauses found.")

    key = storage.put_original(spec.policy.organization_id, sha, data, ".pdf")
    version = m.PolicyVersion(
        id=spec.version_id,
        policy_id=spec.policy.id,
        label=spec.label,
        effective_from=spec.effective_from,
        effective_to=spec.effective_to,
        status=PolicyVersionStatus.DRAFT,
        index_status=IndexStatus.INDEXING,
        original_sha256=sha,
        storage_key=key,
        upload_id=spec.upload_id,
        page_count=len(pages),
        provenance=spec.provenance,
        extraction_warnings=seg.warnings,
    )
    session.add(version)
    session.flush()
    session.add_all(
        m.DocumentPage(
            policy_version_id=version.id,
            page_index=p.index,
            page_label=p.label,
            raw_text=p.raw_text,
            warnings=p.warnings,
        )
        for p in pages
    )

    by_key: dict[str, m.Clause] = {}
    chunk_rows: list[m.Chunk] = []
    for ordinal, sc in enumerate(seg.clauses):
        clause = m.Clause(
            id=_clause_id(version.id, sc.section_path),
            policy_version_id=version.id,
            clause_key=sc.key,
            section_path=sc.section_path,
            section_headings=sc.section_headings,
            heading=sc.heading,
            kind=sc.kind,
            text=sc.text,
            ordinal=ordinal,
            page_start=sc.page_start,
            page_end=sc.page_end,
            extraction_quality=m.ExtractionQuality.WARNING
            if sc.warnings
            else m.ExtractionQuality.OK,
        )
        session.add(clause)
        by_key[sc.key] = clause
        for span in merge_spans(sc.pieces):
            session.add(
                m.SourceSpan(
                    id=f"{clause.id}#p{span.page_index}",
                    clause_id=clause.id,
                    page_index=span.page_index,
                    page_label=pages[span.page_index].label,
                    char_start=span.char_start,
                    char_end=span.char_end,
                    text_start=span.text_start,
                    text_end=span.text_end,
                )
            )
        prefix = chunk_prefix(spec.policy.title, sc.section_path, sc.section_headings)
        for draft in chunk_clause(prefix, sc.text):
            if draft.token_count > MAX_INPUT_TOKENS:
                raise IngestionError(
                    "chunk_too_long",
                    f"Clause {sc.key} produced a chunk over {MAX_INPUT_TOKENS} tokens.",
                )
            chunk_rows.append(
                m.Chunk(
                    id=f"{clause.id}~{draft.ordinal}",
                    clause_id=clause.id,
                    policy_version_id=version.id,
                    ordinal=draft.ordinal,
                    prefix=draft.prefix,
                    text=draft.text,
                    token_count=draft.token_count,
                    content_hash=draft.content_hash,
                )
            )
    session.flush()

    for sc in seg.clauses:
        source = by_key[sc.key]
        for ref in sc.references:
            target = by_key.get(ref)
            if target is None:
                version.extraction_warnings = [
                    *version.extraction_warnings,
                    f"Clause {sc.key} refers to clause {ref}, which was not found.",
                ]
                continue
            # Unreviewed heuristic: a clause classed as an exception carves out the clauses
            # it cites. Reviewers confirm relations before any rule depends on them.
            relation = (
                m.RelationKind.EXCEPTS
                if sc.kind == ClauseKind.EXCEPTION
                else m.RelationKind.REFERENCES
            )
            session.add(
                m.ClauseRelation(
                    id=f"rel_{source.id}_{relation.value}_{target.id}",
                    source_clause_id=source.id,
                    target_clause_id=target.id,
                    relation=relation,
                    provenance="extracted",
                )
            )

    if embedder is not None:
        vectors = embedder.embed_passages([f"{c.prefix}\n{c.text}" for c in chunk_rows])
        for chunk, vector in zip(chunk_rows, vectors, strict=True):
            chunk.embedding = vector
            chunk.embedding_model = embedder.revision
    session.add_all(chunk_rows)
    session.flush()

    _check_integrity(session, version, pages_count=len(pages))
    version.index_status = IndexStatus.READY
    version.index_revision = f"{CHUNKER_VERSION}+" + (
        embedder.revision if embedder is not None else "lexical-only"
    )
    if spec.status != PolicyVersionStatus.DRAFT:
        version.status = spec.status
        version.published_at = datetime.now(UTC)
    session.flush()
    return IngestResult(version, True, len(seg.clauses), len(chunk_rows), seg.warnings)


def _check_integrity(session: Session, version: m.PolicyVersion, pages_count: int) -> None:
    """Every clause has a source span inside its page text; every chunk has a clause."""
    pages = {
        p.page_index: p.raw_text
        for p in session.scalars(
            select(m.DocumentPage).where(m.DocumentPage.policy_version_id == version.id)
        )
    }
    clauses = session.scalars(select(m.Clause).where(m.Clause.policy_version_id == version.id))
    for clause in clauses:
        if not clause.spans:
            raise IngestionError("integrity", f"Clause {clause.clause_key} has no source span.")
        for span in clause.spans:
            raw = pages.get(span.page_index)
            if raw is None or span.char_end > len(raw) or span.page_index >= pages_count:
                raise IngestionError(
                    "integrity", f"Clause {clause.clause_key} points outside its page."
                )
    orphan = session.scalar(
        select(m.Chunk.id)
        .outerjoin(m.Clause, m.Clause.id == m.Chunk.clause_id)
        .where(m.Chunk.policy_version_id == version.id, m.Clause.id.is_(None))
        .limit(1)
    )
    if orphan is not None:
        raise IngestionError("integrity", f"Chunk {orphan} has no clause.")
