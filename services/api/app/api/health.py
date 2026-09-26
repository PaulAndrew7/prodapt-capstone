from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import get_settings
from app.domain.contracts import HealthStatus
from app.persistence.db import get_engine
from app.storage import get_storage

router = APIRouter(prefix="/health", tags=["health"])
API_ROOT = Path(__file__).resolve().parents[2]


def _migration_head() -> str | None:
    cfg = Config(str(API_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(API_ROOT / "migrations"))
    return ScriptDirectory.from_config(cfg).get_current_head()


@router.get("/live", response_model=HealthStatus)
def live() -> HealthStatus:
    return HealthStatus(status="ok", checks={"process": "ok"})


@router.get("/ready", response_model=HealthStatus, responses={503: {"model": HealthStatus}})
def ready() -> JSONResponse:
    checks: dict[str, str] = {}
    try:
        with get_engine().connect() as conn:
            current = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
        head = _migration_head()
        checks["database"] = "ok"
        checks["migrations"] = "ok" if current == head else f"pending (at {current}, head {head})"
    except Exception as exc:
        checks["database"] = f"unavailable: {type(exc).__name__}"
        checks["migrations"] = "unknown"
    checks["storage"] = "ok" if get_storage().writable() else "not writable"
    s = get_settings()
    checks["embeddings"] = s.embedding_model if s.embeddings_enabled else "disabled"
    checks["llm_provider"] = "configured" if s.llm_provider != "none" else "not configured"
    critical = ("database", "migrations", "storage")
    ok = all(checks[c] == "ok" for c in critical)
    body = HealthStatus(status="ok" if ok else "unavailable", checks=checks)
    return JSONResponse(status_code=200 if ok else 503, content=body.model_dump())
