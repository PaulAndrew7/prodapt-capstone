"""Seed the fictional Kestrel Mutual demo organization from data/demo/manifest.json.

Idempotent: rerunning skips versions that already exist with the same bytes. PDF hashes
must match the manifest, so a stale or edited PDF is caught before ingestion.
"""

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import REPO_ROOT
from app.domain.contracts import PolicyVersionStatus, Role
from app.ingestion.pipeline import VersionInput, ingest_version
from app.persistence import models as m
from app.retrieval.embeddings import Embedder
from app.storage import Storage

DEMO_DIR = REPO_ROOT / "data" / "demo"
DEMO_ORG_ID = "org_kestrel"
DEMO_ADMIN_ID = "user_demo_admin"
DEMO_SNAPSHOT_ID = "snapshot_demo_v1"

# Fictional people; names match the web fixtures.
DEMO_USERS = [
    (DEMO_ADMIN_ID, "admin@kestrel.example", "Demo Admin", Role.ADMIN),
    ("user_priya", "priya.raman@kestrel.example", "Priya Raman", Role.REQUESTER),
    ("user_amara", "amara.okafor@kestrel.example", "Amara Okafor", Role.REVIEWER),
]


@dataclass
class SeedReport:
    created: list[str]
    skipped: list[str]
    snapshot_id: str


def load_manifest(demo_dir: Path = DEMO_DIR) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((demo_dir / "manifest.json").read_text(encoding="utf-8"))
    return data


def ensure_org_and_users(session: Session, org: dict[str, Any]) -> None:
    if session.get(m.Organization, org["id"]) is None:
        session.add(m.Organization(id=org["id"], slug=org["slug"], name=org["name"]))
    for user_id, email, name, role in DEMO_USERS:
        if session.get(m.User, user_id) is None:
            session.add(m.User(id=user_id, email=email, display_name=name))
        if session.get(m.Membership, (user_id, org["id"])) is None:
            session.add(m.Membership(user_id=user_id, organization_id=org["id"], role=role))
    session.flush()


def seed_demo(
    session: Session, *, storage: Storage, embedder: Embedder | None, demo_dir: Path = DEMO_DIR
) -> SeedReport:
    manifest = load_manifest(demo_dir)
    org = manifest["organization"]
    ensure_org_and_users(session, org)
    created: list[str] = []
    skipped: list[str] = []
    for doc in manifest["documents"]:
        data = (demo_dir / doc["pdf"]).read_bytes()
        if hashlib.sha256(data).hexdigest() != doc["pdf_sha256"]:
            raise ValueError(f"{doc['pdf']} does not match its manifest hash; rebuild the corpus")
        policy = session.get(m.Policy, doc["policy_id"])
        if policy is None:
            policy = m.Policy(
                id=doc["policy_id"],
                organization_id=org["id"],
                slug=doc["policy_id"],
                title=doc["title"],
                category=doc["category"],
                business_area=doc["business_area"],
                owner=doc["owner"],
            )
            session.add(policy)
            session.flush()
        result = ingest_version(
            session,
            data,
            VersionInput(
                policy=policy,
                version_id=doc["version_id"],
                label=doc["label"],
                effective_from=date.fromisoformat(doc["effective_from"]),
                effective_to=date.fromisoformat(doc["effective_to"])
                if doc["effective_to"]
                else None,
                status=PolicyVersionStatus(doc["status"]),
                provenance={**doc["provenance"], "manifest_source": doc["source"]},
            ),
            storage=storage,
            embedder=embedder,
        )
        (created if result.created else skipped).append(doc["version_id"])
        from app.ingestion.review_metadata import demo_candidates

        if "reviewed_candidates" not in result.version.provenance:
            result.version.provenance = {
                **result.version.provenance,
                "reviewed_candidates": demo_candidates().get(doc["version_id"], []),
            }

    if session.get(m.PolicySnapshot, DEMO_SNAPSHOT_ID) is None:
        session.add(
            m.PolicySnapshot(
                id=DEMO_SNAPSHOT_ID,
                organization_id=org["id"],
                description="Demo corpus: every non-draft Kestrel Mutual policy version.",
            )
        )
        session.flush()
        versions = session.scalars(
            select(m.PolicyVersion)
            .join(m.Policy)
            .where(
                m.Policy.organization_id == org["id"],
                m.PolicyVersion.status != PolicyVersionStatus.DRAFT,
            )
        )
        session.add_all(
            m.SnapshotVersion(
                snapshot_id=DEMO_SNAPSHOT_ID,
                policy_version_id=v.id,
                index_revision=v.index_revision or "",
            )
            for v in versions
        )
    session.flush()
    return SeedReport(created, skipped, DEMO_SNAPSHOT_ID)
