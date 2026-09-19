"""Automated Tests for Milestone 3.4: Batch Evaluation System.

Validates:
1. Valid CSV with multiple rows.
2. CSV with missing question.
3. CSV with missing AI response.
4. CSV with optional reference answers.
5. CSV with malformed rows.
6. Mixed valid and invalid rows (isolated errors, batch continues).
7. Multiple evaluation results.
8. Batch statistics calculation (accurate aggregate counts and averages).
9. Individual batch result inspection (fetching records and details).
10. Empty CSV handling.
11. Duplicate rows handling.
12. Large reasonable CSV handling.
"""

import io
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.batch_service import batch_evaluation_service


@pytest.fixture
def client():
    return TestClient(app)


def test_01_valid_csv_multiple_rows():
    """Test 1: Valid CSV with multiple standard rows executes complete pipeline."""
    csv_data = (
        "question,ai_response\n"
        '"What is photosynthesis?","Photosynthesis is the process that converts sunlight into glucose and oxygen."\n'
        '"What is water?","Water is a chemical compound consisting of two hydrogen atoms and one oxygen atom."\n'
    ).encode("utf-8")

    res = batch_evaluation_service.execute_batch(csv_data, filename="valid_test.csv")
    assert res.success is True
    assert res.valid_records_count == 2
    assert res.invalid_records_count == 0
    assert len(res.records) == 2
    for r in res.records:
        assert r.accuracy_score is not None
        assert r.relevance_score is not None
        assert r.completeness_score is not None
        assert r.verdict in ("PASS", "NEEDS IMPROVEMENT", "FAIL")


def test_02_csv_with_missing_question():
    """Test 2: CSV with missing question header or row-level question."""
    # Row-level missing question
    csv_data = (
        "question,ai_response\n"
        ',"Photosynthesis converts sunlight into glucose."\n'
        '"What is water?","Water is H2O."\n'
    ).encode("utf-8")

    res = batch_evaluation_service.execute_batch(csv_data)
    assert res.valid_records_count == 1
    assert res.invalid_records_count == 1
    assert any("missing question" in err.lower() for err in res.validation_errors)


def test_03_csv_with_missing_ai_response():
    """Test 3: CSV with missing AI response."""
    csv_data = (
        "question,ai_response\n"
        '"What is photosynthesis?",\n'
        '"What is water?","Water is H2O."\n'
    ).encode("utf-8")

    res = batch_evaluation_service.execute_batch(csv_data)
    assert res.valid_records_count == 1
    assert res.invalid_records_count == 1
    assert any("missing ai response" in err.lower() for err in res.validation_errors)


def test_04_csv_with_optional_reference_answers():
    """Test 4: CSV with optional reference_answer and source_information."""
    csv_data = (
        "question,ai_response,reference_answer,source_information\n"
        '"When was Project QuantumLeap founded?","Project QuantumLeap was founded on March 14, 2024.","Project QuantumLeap was founded on March 14, 2024 in Zurich.","Archival records"\n'
    ).encode("utf-8")

    res = batch_evaluation_service.execute_batch(csv_data)
    assert res.valid_records_count == 1
    assert res.records[0].reference_answer is not None
    assert "March 14, 2024" in res.records[0].reference_answer
    assert res.records[0].accuracy_score >= 4


def test_05_csv_with_malformed_rows():
    """Test 5: CSV with malformed row (too few columns, broken quotes)."""
    csv_data = (
        "question,ai_response\n"
        'Broken single column row\n'
        '"Valid question?","Valid answer."\n'
    ).encode("utf-8")

    res = batch_evaluation_service.execute_batch(csv_data)
    assert res.valid_records_count == 1
    assert res.invalid_records_count >= 1
    assert len(res.validation_errors) >= 1


def test_06_mixed_valid_and_invalid_rows():
    """Test 6: Mixed valid and invalid rows: invalid rows must not terminate the batch."""
    csv_data = (
        "prompt,response\n"
        '"What is photosynthesis?","Photosynthesis converts sunlight into energy."\n'
        ',\n'
        '"Missing answer?",\n'
        '"What is the capital of France?","Paris is the capital of France."\n'
    ).encode("utf-8")

    res = batch_evaluation_service.execute_batch(csv_data)
    # Valid rows 1 and 4 must succeed
    assert res.valid_records_count == 2
    assert res.invalid_records_count >= 1
    assert len(res.records) == 2


def test_07_multiple_evaluation_results():
    """Test 7: Verify distinct evaluation results across diverse questions."""
    csv_data = (
        "question,ai_response\n"
        '"What is photosynthesis?","Photosynthesis produces glucose and oxygen from sunlight and CO2."\n'
        '"Can the Great Wall be seen from the Moon?","Yes, easily visible from space with naked eye."\n'
        '"What is photosynthesis?","Python is a great programming language."\n'
    ).encode("utf-8")

    res = batch_evaluation_service.execute_batch(csv_data)
    assert len(res.records) == 3
    # First is accurate science -> likely PASS or high score
    # Second is misconception -> FAIL
    # Third is off-topic -> FAIL
    verdicts = [r.verdict for r in res.records]
    assert "FAIL" in verdicts


def test_08_batch_statistics_calculation():
    """Test 8: Batch statistics calculation check."""
    csv_data = (
        "question,ai_response\n"
        '"What is photosynthesis?","Process converting light into glucose and oxygen."\n'
        '"What is water?","Chemical compound H2O."\n'
    ).encode("utf-8")

    res = batch_evaluation_service.execute_batch(csv_data)
    stats = res.stats
    assert stats.total_records == 2
    assert stats.successful_evaluations == 2
    assert stats.failed_evaluations == 0
    assert stats.average_accuracy is not None
    assert stats.average_relevance is not None
    assert stats.average_completeness is not None
    assert stats.average_overall_score is not None
    assert (stats.pass_count + stats.needs_improvement_count + stats.fail_count) == 2


def test_09_individual_batch_result_inspection():
    """Test 9: Inspect individual batch result details."""
    csv_data = (
        "question,ai_response\n"
        '"What is photosynthesis?","Photosynthesis transforms light into chemical energy."\n'
    ).encode("utf-8")

    res = batch_evaluation_service.execute_batch(csv_data)
    batch_id = res.batch_id

    # Retrieve batch by ID
    retrieved = batch_evaluation_service.get_batch_result(batch_id)
    assert retrieved is not None
    assert retrieved.batch_id == batch_id
    assert len(retrieved.records) == 1
    rec = retrieved.records[0]
    assert rec.question == "What is photosynthesis?"
    assert rec.accuracy_score is not None
    assert rec.completeness_score is not None


def test_10_empty_csv():
    """Test 10: Empty CSV is safely rejected with validation error."""
    csv_data = b""
    res = batch_evaluation_service.execute_batch(csv_data)
    assert res.valid_records_count == 0
    assert len(res.validation_errors) >= 1
    assert "empty" in res.validation_errors[0].lower()


def test_11_duplicate_rows():
    """Test 11: Duplicate rows evaluated properly without collision."""
    csv_data = (
        "question,ai_response\n"
        '"What is water?","Water is H2O."\n'
        '"What is water?","Water is H2O."\n'
    ).encode("utf-8")

    res = batch_evaluation_service.execute_batch(csv_data)
    assert res.valid_records_count == 2
    assert len(res.records) == 2
    assert res.records[0].record_id == 1
    assert res.records[1].record_id == 2


def test_12_large_reasonable_csv():
    """Test 12: Reasonably sized batch CSV with multiple rows."""
    rows = ["question,ai_response"]
    for i in range(8):
        rows.append(f'"Question {i} regarding biology?","Answer {i} explaining biological cellular functions."')
    csv_data = "\n".join(rows).encode("utf-8")

    res = batch_evaluation_service.execute_batch(csv_data)
    assert res.valid_records_count == 8
    assert res.stats.successful_evaluations == 8
    assert len(res.records) == 8


def test_13_api_batch_evaluate_endpoint(client):
    """Test 13: POST /api/batch/evaluate endpoint with multipart file upload."""
    csv_content = (
        "question,ai_response\n"
        '"What is photosynthesis?","Photosynthesis converts light into chemical energy."\n'
    )
    files = {"file": ("test_batch.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}

    response = client.post("/api/batch/evaluate", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "batch_id" in data
    assert data["valid_records_count"] == 1
    assert len(data["records"]) == 1

    # Test GET /api/batch/{batch_id}
    batch_id = data["batch_id"]
    get_res = client.get(f"/api/batch/{batch_id}")
    assert get_res.status_code == 200
    assert get_res.json()["batch_id"] == batch_id
