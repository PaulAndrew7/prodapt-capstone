from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import CurrentPrincipal, DbSession
from app.api.errors import AppError
from app.config import get_settings
from app.domain.contracts import LookupAnswer, SearchRequest, SearchResponse
from app.retrieval.embeddings import get_embedder
from app.retrieval.search import latest_snapshot_id, search
from app.workflow.llm import SETUP_HINT, ModelClient, ModelError, get_model_client
from app.workflow.lookup import lookup

router = APIRouter(prefix="/api/v1", tags=["search"])


@router.post("/search", response_model=SearchResponse)
def evidence_search(
    body: SearchRequest, session: DbSession, principal: CurrentPrincipal
) -> SearchResponse:
    """Ranked clauses with lexical/dense ranks and backend-built citations."""
    return search(session, principal.organization_id, body, get_embedder())


@router.post("/lookup", response_model=LookupAnswer)
def grounded_lookup(
    body: SearchRequest,
    session: DbSession,
    principal: CurrentPrincipal,
    model: Annotated[ModelClient | None, Depends(get_model_client)],
) -> LookupAnswer:
    """A short answer that cites the retrieved clauses it relies on (F06)."""
    if model is None:
        raise AppError(
            503,
            "model_not_configured",
            "No language model is configured, so questions cannot be answered. Use evidence "
            f"search, or: {SETUP_HINT}",
        )
    snapshot_id = latest_snapshot_id(session, principal.organization_id)
    if snapshot_id is None:
        raise AppError(503, "demo_not_seeded", "No policy snapshot exists. Seed the corpus first.")
    try:
        return lookup(
            session,
            principal.organization_id,
            body,
            snapshot_id=snapshot_id,
            model=model,
            embedder=get_embedder(),
            deadline_seconds=get_settings().run_deadline_seconds,
        )
    except ModelError as exc:
        raise AppError(502, exc.code, exc.message, retryable=exc.retryable) from exc
