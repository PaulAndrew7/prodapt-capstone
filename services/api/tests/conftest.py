"""Test setup.

DB tests run against a separate `<db>_test` database on the configured server (created on
demand), migrated from scratch once per session and seeded with the demo corpus without
embeddings. Each test runs inside a transaction that is rolled back. Tests marked `db` are
skipped when Postgres is unreachable.
"""

import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

os.environ["APP_ENV"] = "test"
os.environ["EMBEDDINGS_ENABLED"] = "false"
os.environ["AUTH_MODE"] = "demo"
os.environ.setdefault("STORAGE_DIR", tempfile.mkdtemp(prefix="clause-test-storage-"))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.config import DEV_DATABASE_URL, get_settings

BASE_URL = make_url(os.environ.get("DATABASE_URL", DEV_DATABASE_URL))
TEST_DB = f"{BASE_URL.database}_test"
os.environ["DATABASE_URL"] = BASE_URL.set(database=TEST_DB).render_as_string(hide_password=False)
get_settings.cache_clear()

API_ROOT = Path(__file__).resolve().parents[1]


def _create_test_database() -> None:
    admin = create_engine(BASE_URL.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        exists = conn.scalar(text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": TEST_DB})
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{TEST_DB}"'))
    admin.dispose()


@pytest.fixture(scope="session")
def migrated_engine() -> Iterator[object]:
    try:
        _create_test_database()
    except OperationalError as exc:
        pytest.skip(f"Postgres unavailable: {exc.orig}")
    from alembic import command
    from alembic.config import Config

    from app.persistence.db import get_engine

    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))
    cfg = Config(str(API_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(API_ROOT / "migrations"))
    command.upgrade(cfg, "head")

    from app.seed import seed_demo
    from app.storage import get_storage

    with Session(engine) as session, session.begin():
        seed_demo(session, storage=get_storage(), embedder=None)
    yield engine


@pytest.fixture
def db(migrated_engine: object) -> Iterator[Session]:
    """A session whose work is rolled back after the test, even if the code commits."""
    from app.persistence.db import get_engine

    conn: Connection = get_engine().connect()
    outer = conn.begin()
    session = Session(bind=conn, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        outer.rollback()
        conn.close()


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    from app.main import app
    from app.persistence.db import get_session

    app.dependency_overrides[get_session] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def plain_client() -> Iterator[TestClient]:
    """No database dependency; for routes that must work without Postgres."""
    from app.main import app

    with TestClient(app) as c:
        yield c
