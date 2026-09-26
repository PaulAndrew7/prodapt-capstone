from fastapi import APIRouter

from app.api.deps import CurrentPrincipal, DbSession
from app.api.errors import not_implemented
from app.domain.contracts import LookupAnswer, SearchRequest, SearchResponse
from app.retrieval.embeddings import get_embedder
from app.retrieval.search import search

router = APIRouter(prefix="/api/v1", tags=["search"])


@router.post("/search", response_model=SearchResponse)
def evidence_search(
    body: SearchRequest, session: DbSession, principal: CurrentPrincipal
) -> SearchResponse:
    """Ranked clauses with lexical/dense ranks and backend-built citations."""
    return search(session, principal.organization_id, body, get_embedder())


@router.post("/lookup", response_model=LookupAnswer, responses={501: {"description": "F06"}})
def grounded_lookup(body: SearchRequest, principal: CurrentPrincipal) -> LookupAnswer:
    """Cited natural-language answer (F06). Needs the runtime model provider."""
    raise not_implemented("Grounded policy lookup")
