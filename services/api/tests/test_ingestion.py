import hashlib
import io
from datetime import date

import pytest
from pypdf import PdfReader, PdfWriter
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.domain.contracts import IndexStatus, PolicyVersionStatus
from app.ingestion.pdf import IngestionError
from app.ingestion.pipeline import VersionInput, ingest_version
from app.persistence import models as m
from app.seed import DEMO_DIR, DEMO_ORG_ID, load_manifest
from app.storage import get_storage
from tests.pdfs import blank_pdf, make_pdf

pytestmark = pytest.mark.db


@pytest.mark.parametrize("failure", ["file_too_large", "too_many_pages", "encrypted_pdf"])
def test_ingestion_limits_publish_nothing(
    db: Session, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    data = make_pdf([["A sufficiently long first page of policy text."], ["Second page."]])
    settings = get_settings()
    if failure == "file_too_large":
        monkeypatch.setattr(settings, "max_upload_bytes", len(data) - 1)
    elif failure == "too_many_pages":
        monkeypatch.setattr(settings, "max_pdf_pages", 1)
    else:
        writer = PdfWriter()
        writer.append(PdfReader(io.BytesIO(data)))
        writer.encrypt("test-password")
        output = io.BytesIO()
        writer.write(output)
        data = output.getvalue()
    storage = get_storage()
    before = set(storage.root.rglob("*.pdf"))
    with pytest.raises(IngestionError) as exc:
        _ingest(db, data, _spec(_policy(db)))
    assert exc.value.category == failure
    assert db.scalar(select(func.count()).where(m.PolicyVersion.policy_id == "tp")) == 0
    assert set(storage.root.rglob("*.pdf")) == before


def _spec(policy: m.Policy, label: str = "v1") -> VersionInput:
    return VersionInput(
        policy=policy,
        version_id=f"{policy.id}_{label}",
        label=label,
        effective_from=date(2026, 1, 1),
        effective_to=None,
        status=PolicyVersionStatus.PUBLISHED,
        provenance={"kind": "synthetic", "test": True},
    )


def _policy(db: Session, policy_id: str = "tp") -> m.Policy:
    policy = m.Policy(
        id=policy_id,
        organization_id=DEMO_ORG_ID,
        slug=policy_id,
        title="Test Policy",
        category="Testing",
        business_area="QA",
        owner="Tester",
    )
    db.add(policy)
    db.flush()
    return policy


def _ingest(db: Session, data: bytes, spec: VersionInput) -> object:
    return ingest_version(db, data, spec, storage=get_storage(), embedder=None)


def test_every_seeded_clause_traces_to_its_original_page(db: Session) -> None:
    pages = {
        (p.policy_version_id, p.page_index): p.raw_text for p in db.scalars(select(m.DocumentPage))
    }
    clauses = db.scalars(select(m.Clause)).all()
    assert len(clauses) == sum(d["clauses"] for d in load_manifest()["documents"])
    for clause in clauses:
        assert clause.spans, clause.id
        covered = ""
        for span in clause.spans:
            raw = pages[(clause.policy_version_id, span.page_index)][
                span.char_start : span.char_end
            ]
            assert " ".join(raw.split()) == clause.text[span.text_start : span.text_end]
            covered += clause.text[span.text_start : span.text_end]
        assert len(covered) <= len(clause.text)


def test_every_chunk_has_a_clause_and_a_published_snapshot(db: Session) -> None:
    orphans = db.scalar(
        select(func.count(m.Chunk.id)).outerjoin(m.Clause).where(m.Clause.id.is_(None))
    )
    assert orphans == 0
    ready = db.scalars(select(m.PolicyVersion)).all()
    assert all(v.index_status == IndexStatus.READY for v in ready)
    in_snapshot = set(
        db.scalars(
            select(m.SnapshotVersion.policy_version_id).where(
                m.SnapshotVersion.snapshot_id == "snapshot_demo_v1"
            )
        )
    )
    assert "cm_v2" not in in_snapshot  # drafts are never in a published snapshot
    assert {"ds_v1", "ds_v2", "ea_v1", "ea_v2"} <= in_snapshot


def test_reingesting_identical_bytes_is_a_no_op(db: Session) -> None:
    doc = next(d for d in load_manifest()["documents"] if d["version_id"] == "ds_v1")
    data = (DEMO_DIR / doc["pdf"]).read_bytes()
    policy = db.get(m.Policy, "ds")
    assert policy is not None
    before = db.scalar(select(func.count(m.Clause.id)))
    result = _ingest(db, data, _spec(policy))
    assert result.created is False  # type: ignore[attr-defined]
    assert db.scalar(select(func.count(m.Clause.id))) == before


def test_changed_bytes_under_an_existing_label_are_rejected(db: Session) -> None:
    policy = db.get(m.Policy, "ds")
    assert policy is not None
    other = make_pdf([["1 Purpose", "Different text."], ["2 Scope", "More."]])
    with pytest.raises(IngestionError) as exc:
        _ingest(db, other, _spec(policy))
    assert exc.value.category == "version_conflict"


@pytest.mark.parametrize(
    ("data", "category"),
    [
        (b"hello, not a pdf", "not_pdf"),
        (b"%PDF-1.7\n this is not really a pdf", "corrupt_pdf"),
        (blank_pdf(), "no_text_layer"),
    ],
)
def test_unreadable_files_fail_with_a_category_and_write_nothing(
    db: Session, data: bytes, category: str
) -> None:
    policy = _policy(db)
    with pytest.raises(IngestionError) as exc:
        _ingest(db, data, _spec(policy))
    assert exc.value.category == category
    assert db.scalar(select(func.count()).where(m.PolicyVersion.policy_id == "tp")) == 0


def test_multi_page_clause_gets_a_span_per_page(db: Session) -> None:
    data = make_pdf(
        [
            ["Test Policy", "Cover page"],
            [
                "1 Purpose",
                "This policy exists for testing.",
                "2 Records",
                "2.1 Keeping records",
                "Records must be kept for six years after the",
            ],
            ["account closes, then deleted.", "2.2 Deletion", "Deletion must be recorded."],
        ]
    )
    policy = _policy(db)
    result = _ingest(db, data, _spec(policy))
    version = result.version  # type: ignore[attr-defined]
    clause = db.get(m.Clause, f"{version.id}_2_2.1")
    assert clause is not None
    assert (
        clause.text == "Records must be kept for six years after the account closes, then deleted."
    )
    assert [s.page_index for s in clause.spans] == [1, 2]
    assert (clause.page_start, clause.page_end) == (1, 2)
    # Footer lines were recognised as running text, not clause content.
    assert "Page" not in db.get(m.Clause, f"{version.id}_2_2.2").text  # type: ignore[union-attr]
    stored = get_storage().path_for(version.storage_key).read_bytes()
    assert hashlib.sha256(stored).hexdigest() == version.original_sha256


def test_unresolved_cross_reference_is_reported(db: Session) -> None:
    data = make_pdf(
        [
            ["Cover"],
            ["1 Rules", "1.1 Approval", "Changes require approval under clause 9.9."],
            ["2 End", "Done."],
        ]
    )
    result = _ingest(db, data, _spec(_policy(db)))
    warnings = result.version.extraction_warnings  # type: ignore[attr-defined]
    assert any("clause 9.9" in w for w in warnings)
