"""Integration tests for semantic evidence retrieval against ChromaDB."""

import pytest
from backend.rag.retriever import EvidenceRetriever
from backend.rag.vector_store import VectorStoreManager
from knowledge_base.embeddings.embedder import EmbeddingGenerator


def test_vector_store_populated():
    store = VectorStoreManager()
    count = store.count()
    assert count > 0, "ChromaDB collection should contain indexed chunks from build_kb."


def test_semantic_retrieval_truthfulqa():
    retriever = EvidenceRetriever()
    # Test query about Moon visibility misconception
    query = "Can you see the Great Wall of China from the Moon?"
    results = retriever.retrieve(query=query, top_k=3)

    assert len(results) > 0
    assert "chunk_id" in results[0]
    assert "similarity_score" in results[0]
    assert "text" in results[0]
    assert results[0]["similarity_score"] >= 0.0


def test_semantic_retrieval_metadata_preservation():
    retriever = EvidenceRetriever()
    query = "oxygen discovery and chemical properties"
    results = retriever.retrieve(query=query, top_k=3)

    assert len(results) > 0
    top_hit = results[0]
    assert "metadata" in top_hit
    assert "dataset_name" in top_hit["metadata"]
    assert "doc_id" in top_hit["metadata"]
    assert "chunk_id" in top_hit["metadata"]
