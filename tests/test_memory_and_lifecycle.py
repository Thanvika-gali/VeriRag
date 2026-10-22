"""Tests for startup, lazy initialization, first/subsequent evaluations, and missing data handling.

Verifies memory optimization requirements:
1. Embedding model is loaded lazily and at most once per process.
2. ChromaDB client is shared per persist directory.
3. Startup and health checks execute cleanly without requiring premature model loads.
4. First evaluation request triggers lazy model initialization without failure.
5. Subsequent evaluations execute reliably with model and client reuse.
6. Missing, empty, or unavailable data queries return robust, structured responses.
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import create_app
from backend.rag.vector_store import VectorStoreManager, vector_store
from knowledge_base.embeddings.embedder import EmbeddingGenerator, embedder


@pytest.fixture(scope="module")
def app_client():
    app = create_app()
    return TestClient(app)


def test_startup_and_health_check(app_client):
    """Verify application starts and health check returns OK with live subsystem statuses."""
    response = app_client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database_connected"] is True
    assert data["vector_store_ready"] is True
    assert "agent_statuses" in data
    assert data["agent_statuses"]["RAG / Evidence Retrieval"] == "ONLINE"
    assert data["agent_statuses"]["Evaluation Orchestrator"] == "ONLINE"


def test_root_endpoint_availability(app_client):
    """Verify root endpoint serves service identity."""
    response = app_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["health"] == "/api/health"


def test_knowledge_base_stats_include_mode(app_client):
    """Verify /api/knowledge-base/stats returns counts without loading document contents."""
    response = app_client.get("/api/knowledge-base/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["total_indexed_chunks"] >= 0
    assert len(data["datasets"]) >= 2
    for ds in data["datasets"]:
        assert "name" in ds
        assert "chunks" in ds
        assert isinstance(ds["chunks"], int)


def test_first_evaluation_request_lazy_init(app_client):
    """Verify first evaluation request properly initializes the pipeline and produces valid results."""
    payload = {
        "question": "What is the capital of Japan?",
        "ai_response": "The capital of Japan is Tokyo.",
        "reference_answer": "Tokyo",
        "top_k": 3,
    }
    response = app_client.post("/api/submissions", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert data["submission_id"] is not None
    assert data["verdict"] in ("PASS", "NEEDS IMPROVEMENT", "FAIL")
    assert 0 <= data["overall_score"] <= 100
    assert "relevance" in data
    assert "accuracy" in data
    assert "hallucination" in data
    assert "completeness" in data
    assert "verdict_details" in data

    # Verify model is now initialized in shared cache
    assert len(EmbeddingGenerator._shared_models) >= 1
    assert embedder.model_name in EmbeddingGenerator._shared_models


def test_subsequent_evaluations_model_reuse(app_client):
    """Verify subsequent evaluations reuse existing model singleton without reallocating models."""
    initial_model_count = len(EmbeddingGenerator._shared_models)
    model_ref = EmbeddingGenerator._shared_models[embedder.model_name]

    payloads = [
        {
            "question": "What is water composed of?",
            "ai_response": "Water is composed of hydrogen and oxygen molecules (H2O).",
            "reference_answer": "Two hydrogen atoms and one oxygen atom.",
        },
        {
            "question": "How many days are in a standard leap year?",
            "ai_response": "A standard leap year has 366 days instead of 365.",
            "reference_answer": "366 days.",
        },
    ]

    for p in payloads:
        res = app_client.post("/api/submissions", json=p)
        assert res.status_code == 201
        data = res.json()
        assert data["verdict"] in ("PASS", "NEEDS IMPROVEMENT", "FAIL")

    # Shared model count must not have grown
    assert len(EmbeddingGenerator._shared_models) == initial_model_count
    # Model reference must be identical
    assert EmbeddingGenerator._shared_models[embedder.model_name] is model_ref


def test_missing_or_unavailable_reference_data(app_client):
    """Verify evaluation handles queries with zero reference answer or unmatched knowledge base data."""
    payload = {
        "question": "ZXY987RandomQueryTopicWithoutReference?",
        "ai_response": "This is a response to an inquiry with no matching reference data in the KB.",
        "reference_answer": None,
        "source_document": None,
        "top_k": 3,
    }
    response = app_client.post("/api/submissions", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert data["submission_id"] is not None
    assert data["verdict"] in ("PASS", "NEEDS IMPROVEMENT", "FAIL")
    assert isinstance(data["overall_score"], int)
    assert isinstance(data["retrieved_evidence"], list)


def test_empty_query_resilience(app_client):
    """Verify empty query triggers 422 validation error and whitespace query is handled safely without crashing."""
    # 1. Empty string triggers 422 validation
    r_empty = app_client.post("/api/submissions", json={"question": "", "ai_response": "Some response."})
    assert r_empty.status_code == 422

    # 2. Whitespace-only inquiry is handled safely without 500 server crash
    r_spaces = app_client.post("/api/submissions", json={"question": "   ", "ai_response": "Some response."})
    assert r_spaces.status_code in (201, 400, 422)


def test_vector_store_client_singleton():
    """Verify VectorStoreManager reuses PersistentClient across multiple instances."""
    store1 = VectorStoreManager()
    store2 = VectorStoreManager()
    # Both instances should share the underlying client for the same path
    assert store1.client is store2.client
    assert store1.client is vector_store.client


def test_embedding_generator_singleton():
    """Verify multiple EmbeddingGenerator instances share the exact same underlying model instance."""
    gen1 = EmbeddingGenerator("all-MiniLM-L6-v2")
    gen2 = EmbeddingGenerator("all-MiniLM-L6-v2")
    assert gen1.model is gen2.model
    assert gen1.model is embedder.model
