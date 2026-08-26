"""Semantic retrieval service for evidence grounding."""

from typing import Any, Dict, List, Optional
from backend.rag.vector_store import VectorStoreManager, vector_store
from knowledge_base.embeddings.embedder import EmbeddingGenerator, embedder


class EvidenceRetriever:
    """Orchestrates query embedding generation and ChromaDB semantic similarity search."""

    def __init__(
        self,
        store: Optional[VectorStoreManager] = None,
        generator: Optional[EmbeddingGenerator] = None,
    ):
        self.store = store or vector_store
        self.generator = generator or embedder

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        dataset_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve top-K evidence chunks matching the query string.

        Flow:
        1. User Question -> 2. Query Embedding -> 3. Vector Search -> 4. Top-K Chunks
        """
        if not query or not query.strip():
            return []

        # Step 1: Generate dense query vector
        query_vector = self.generator.embed_text(query.strip())

        # Step 2: Build optional metadata filter
        where_clause = None
        if dataset_filter:
            where_clause = {"dataset_name": dataset_filter}

        # Step 3: Execute vector similarity search in ChromaDB
        results = self.store.query(
            query_embedding=query_vector,
            n_results=top_k,
            where=where_clause,
        )

        return results


# Global singleton instance
retriever = EvidenceRetriever()
