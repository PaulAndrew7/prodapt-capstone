from collections.abc import Callable, Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


@lru_cache
def get_engine() -> Engine:
    return create_engine(get_settings().database_url, pool_pre_ping=True)


@lru_cache
def _session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def ensure_database(url: URL) -> None:
    """Creates the database named in `url` on its server if it does not exist yet."""
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as conn:
            query = text("SELECT 1 FROM pg_database WHERE datname = :n")
            if not conn.scalar(query, {"n": url.database}):
                conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    finally:
        admin.dispose()


def new_session() -> Session:
    return _session_factory()()


def get_session() -> Iterator[Session]:
    """FastAPI dependency: one session per request, rolled back unless committed."""
    session = new_session()
    try:
        yield session
    finally:
        session.close()


def get_session_factory() -> Callable[[], Session]:
    """FastAPI dependency for work that outlives a request (background runs, event streams).
    Tests override it so that work shares the test transaction."""
    return new_session
