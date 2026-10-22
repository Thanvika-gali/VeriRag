"""Sentence-transformers local embedding generator with lazy loading and memory optimization."""

import os
from typing import Any, Dict, List, Optional, Union

# Restrict thread pools to reduce memory overhead in memory-constrained cloud environments
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("VECLIB_MAXIMUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

DEFAULT_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")


class EmbeddingGenerator:
    """Generates local dense embeddings using sentence-transformers (all-MiniLM-L6-v2)."""

    # Class-level model registry to ensure at most one model instance per process across all callers
    _shared_models: Dict[str, Any] = {}

    def __init__(self, model_name: str = DEFAULT_MODEL_NAME):
        self.model_name = model_name
        self._cache: Dict[str, List[float]] = {}
        self._max_cache_size = 512

    @property
    def model(self) -> Any:
        """Lazy-load the sentence-transformers model once per process."""
        if self.model_name not in self._shared_models:
            try:
                import torch
                torch.set_num_threads(1)
                try:
                    torch.set_num_interop_threads(1)
                except Exception:
                    pass
            except ImportError:
                pass

            from sentence_transformers import SentenceTransformer
            self._shared_models[self.model_name] = SentenceTransformer(self.model_name)

        return self._shared_models[self.model_name]

    def embed_text(self, text: str) -> List[float]:
        """Generate embedding vector for a single string with bounded memory caching."""
        if not text:
            return []

        if text in self._cache:
            return self._cache[text]

        embedding = self.model.encode(
            text,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        vec = embedding.tolist()

        if len(self._cache) >= self._max_cache_size:
            # Evict oldest entries
            old_keys = list(self._cache.keys())[:64]
            for k in old_keys:
                self._cache.pop(k, None)

        self._cache[text] = vec
        return vec

    def embed_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """Generate embedding vectors for a batch of strings."""
        if not texts:
            return []
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return embeddings.tolist()


# Global singleton instance
embedder = EmbeddingGenerator()

