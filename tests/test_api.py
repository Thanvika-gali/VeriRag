"""Integration and unit tests for FastAPI REST endpoints."""

import io
import pytest
from fastapi.testclient import TestClient
from backend.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["project"] == "VeriRAG"
    assert "Milestone 1" in data["milestone"]


def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database_connected"] is True
    assert "all-MiniLM-L6-v2" in data["embedding_model"]


def test_submission_flow(client):
    payload = {
        "question": "What is the capital of France?",
        "ai_response": "The capital of France is Paris.",
        "reference_answer": "Paris",
        "top_k": 3,
    }
    # Create submission
    post_res = client.post("/api/submissions", json=payload)
    assert post_res.status_code == 201
    created_data = post_res.json()
    sub_id = created_data["submission_id"]
    assert sub_id is not None
    assert created_data["question"] == payload["question"]
    assert created_data["status"] == "completed"
    assert "retrieved_evidence" in created_data

    # Retrieve submission by ID
    get_res = client.get(f"/api/submissions/{sub_id}")
    assert get_res.status_code == 200
    fetched_data = get_res.json()
    assert fetched_data["submission_id"] == sub_id

    # List submissions
    list_res = client.get("/api/submissions?limit=10")
    assert list_res.status_code == 200
    items = list_res.json()
    assert len(items) >= 1
    assert any(item["submission_id"] == sub_id for item in items)


def test_upload_document_endpoint(client):
    file_content = b"This is a test source document uploaded via API for grounding."
    files = {"file": ("test_doc.txt", io.BytesIO(file_content), "text/plain")}
    res = client.post("/api/upload-document", files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["filename"] == "test_doc.txt"
    assert data["file_type"] == "txt"
    assert "grounding" in data["extracted_text"]
    assert data["word_count"] > 5
