"""Local dense embeddings with fastembed (ONNX build of BAAI/bge-small-en-v1.5).

The model downloads once into MODEL_CACHE_DIR on first use (about 70 MB). Passages are
embedded as-is; queries get the BGE retrieval instruction, as the model card recommends.
"""

import threading
from functools import lru_cache
from importlib.metadata import version

from app.config import get_settings

BGE_QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "
MAX_INPUT_TOKENS = 512


class Embedder:
    def __init__(self, model_name: str, cache_dir: str, dimension: int) -> None:
        from fastembed import TextEmbedding  # heavy import; keep it lazy

        self.model_name = model_name
        self.dimension = dimension
        self.revision = f"{model_name}@fastembed-{version('fastembed')}"
        self._model = TextEmbedding(model_name=model_name, cache_dir=cache_dir)
        self._lock = threading.Lock()

    def _embed(self, texts: list[str]) -> list[list[float]]:
        with self._lock:
            vectors = [v.tolist() for v in self._model.embed(texts, batch_size=32)]
        for v in vectors:
            if len(v) != self.dimension:
                raise ValueError(f"Expected {self.dimension}-d embeddings, got {len(v)}")
        return vectors

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts) if texts else []

    def embed_query(self, text: str) -> list[float]:
        return self._embed([BGE_QUERY_INSTRUCTION + text])[0]


@lru_cache
def get_embedder() -> Embedder | None:
    s = get_settings()
    if not s.embeddings_enabled:
        return None
    s.model_cache_dir.mkdir(parents=True, exist_ok=True)
    return Embedder(s.embedding_model, str(s.model_cache_dir), s.embedding_dimension)
