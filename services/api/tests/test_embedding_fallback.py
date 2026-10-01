from datetime import date
from pathlib import Path
from unittest.mock import Mock

import pytest
from sqlalchemy.orm import Session

from app.config import Settings
from app.domain.contracts import SearchRequest
from app.retrieval import embeddings
from app.retrieval.search import search
from app.seed import DEMO_ORG_ID


def test_unavailable_embedding_model_is_cached_as_lexical_only(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = Settings(_env_file=None, embeddings_enabled=True, model_cache_dir=tmp_path)
    constructor = Mock(side_effect=RuntimeError("Download unavailable"))
    monkeypatch.setattr(embeddings, "get_settings", lambda: settings)
    monkeypatch.setattr(embeddings, "Embedder", constructor)
    embeddings.get_embedder.cache_clear()
    try:
        assert embeddings.get_embedder() is None
        assert embeddings.get_embedder() is None
        constructor.assert_called_once()
    finally:
        embeddings.get_embedder.cache_clear()


@pytest.mark.db
def test_query_embedding_failure_preserves_lexical_sources(db: Session) -> None:
    broken = Mock(spec=embeddings.Embedder)
    broken.embed_query.side_effect = RuntimeError("Inference unavailable")
    request = SearchRequest(
        question="Who approves external customer data sharing?", as_of=date(2026, 9, 26)
    )
    expected = search(db, DEMO_ORG_ID, request, None)
    actual = search(db, DEMO_ORG_ID, request, broken)
    assert actual.channels == ["lexical"] and actual.hits
    assert actual.hits == expected.hits
    broken.embed_query.assert_called_once()
