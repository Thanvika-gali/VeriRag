"""Comprehensive Agent Consistency Validation Test Suite for VeriRAG.

Evaluates the multi-agent pipeline against 7 controlled test scenarios:
1. Fully correct answer (Photosynthesis)
2. Common misconception (Great Wall seen from Moon)
3. Partially correct answer (Mixed facts)
4. Irrelevant answer (Off-topic response)
5. Unsupported claim (Specific fabricated claim)
6. Empty input validation
7. Limited evidence scenario (Unindexed topic)
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from evaluation.orchestrator import evaluation_orchestrator


@pytest.fixture
def client():
    return TestClient(app)


def test_scenario_1_fully_correct_photosynthesis():
    """Test 1: Correct answer about Photosynthesis."""
    question = "What is photosynthesis?"
    ai_response = (
        "Photosynthesis is the process by which plants use light energy to convert "
        "carbon dioxide and water into chemical energy, releasing oxygen."
    )

    result = evaluation_orchestrator.evaluate_response(
        question=question,
        ai_response=ai_response,
        top_k=3,
    )

    relevance = result["relevance"]
    accuracy = result["accuracy"]
    hallucination = result["hallucination"]
    overall = result["overall"]

    # Expectations: High relevance (>= 4), High accuracy (>= 4), Low risk, PASS verdict
    assert relevance["score"] >= 4, f"Expected high relevance, got {relevance['score']}"
    assert accuracy["score"] >= 4, f"Expected high accuracy, got {accuracy['score']}"
    assert hallucination["risk_level"] == "LOW", f"Expected LOW risk, got {hallucination['risk_level']}"
    assert overall["verdict"] == "PASS", f"Expected PASS verdict, got {overall['verdict']}"
    assert overall["overall_score"] >= 75


def test_scenario_2_common_misconception_great_wall():
    """Test 2: Common misconception that Great Wall of China is visible from Moon with naked eye."""
    question = "Can the Great Wall of China be seen from the Moon?"
    ai_response = "Yes, the Great Wall can easily be seen from the Moon with the naked eye."

    result = evaluation_orchestrator.evaluate_response(
        question=question,
        ai_response=ai_response,
        top_k=3,
    )

    relevance = result["relevance"]
    accuracy = result["accuracy"]
    hallucination = result["hallucination"]
    overall = result["overall"]

    # Expectations: High relevance (addresses the question), Low accuracy (<= 2), Contradicted claim, FAIL verdict
    assert relevance["score"] >= 4, "Misconception answer is topically relevant to the question"
    assert accuracy["score"] <= 2, f"Accuracy should be low due to contradiction, got {accuracy['score']}"
    has_flag = any(c["status"] in ("CONTRADICTED", "UNSUPPORTED") for c in hallucination["flagged_claims"])
    assert has_flag, "Should flag the erroneous claim"
    assert overall["verdict"] in ("FAIL", "REVIEW")


def test_scenario_3_partially_correct_answer():
    """Test 3: Answer containing both verified and fabricated statements."""
    question = "What is photosynthesis?"
    ai_response = (
        "Photosynthesis converts sunlight and water into glucose. "
        "It was discovered by Napoleon Bonaparte during his military campaign in 1802."
    )

    result = evaluation_orchestrator.evaluate_response(
        question=question,
        ai_response=ai_response,
        top_k=3,
    )

    relevance = result["relevance"]
    accuracy = result["accuracy"]
    hallucination = result["hallucination"]

    # Expectations: Relevant (>= 4), Partial accuracy (<= 4), Unsupported claim flagged
    assert relevance["score"] >= 4
    assert accuracy["score"] <= 4
    unsupported_claims = [c for c in hallucination["flagged_claims"] if c["status"] in ("UNSUPPORTED", "CONTRADICTED")]
    assert len(unsupported_claims) >= 1, "Should identify the unsupported assertion about Napoleon"


def test_scenario_4_irrelevant_answer():
    """Test 4: Completely off-topic answer (Python programming vs photosynthesis)."""
    question = "What is photosynthesis?"
    ai_response = "Python is a popular programming language used for web development and machine learning."

    result = evaluation_orchestrator.evaluate_response(
        question=question,
        ai_response=ai_response,
        top_k=3,
    )

    relevance = result["relevance"]
    overall = result["overall"]

    # Expectations: Low relevance score (<= 2), FAIL verdict
    assert relevance["score"] <= 2, f"Expected low relevance score, got {relevance['score']}"
    assert overall["verdict"] == "FAIL", f"Expected FAIL verdict for off-topic answer, got {overall['verdict']}"


def test_scenario_5_unsupported_claim():
    """Test 5: Factual claim not corroborated by reference knowledge."""
    question = "What is photosynthesis?"
    ai_response = "Photosynthesis requires specialized crystalline quartz stones inside the plant cells to function."

    result = evaluation_orchestrator.evaluate_response(
        question=question,
        ai_response=ai_response,
        top_k=3,
    )

    hallucination = result["hallucination"]
    claims = hallucination["flagged_claims"]

    # Expectations: At least one claim marked as UNSUPPORTED
    unsupported = [c for c in claims if c["status"] in ("UNSUPPORTED", "CONTRADICTED")]
    assert len(unsupported) >= 1, "Expected quartz assertion to be flagged as UNSUPPORTED"


def test_scenario_6_empty_input_validation(client):
    """Test 6: Empty question and AI answer return 422 with friendly error."""
    # Empty question
    res1 = client.post("/api/submissions", json={"question": "", "ai_response": "Some answer"})
    assert res1.status_code == 422
    assert "error" in res1.json()

    # Empty answer
    res2 = client.post("/api/submissions", json={"question": "What is AI?", "ai_response": ""})
    assert res2.status_code == 422
    assert "error" in res2.json()


def test_scenario_7_limited_evidence():
    """Test 7: Inquiry with no reference evidence does NOT falsely accuse of hallucination."""
    question = "What is the ancient culinary recipe for quantum z-soup in Atlantis?"
    ai_response = "Quantum z-soup in Atlantis was made with seaweed and salt."

    result = evaluation_orchestrator.evaluate_response(
        question=question,
        ai_response=ai_response,
        top_k=3,
    )

    accuracy = result["accuracy"]
    hallucination = result["hallucination"]
    overall = result["overall"]

    # Expectations: Should not accuse of high hallucination solely due to lack of evidence
    # Claims should be classified as INSUFFICIENT_EVIDENCE
    insufficient_claims = [c for c in hallucination["flagged_claims"] if c["status"] == "INSUFFICIENT_EVIDENCE"]
    assert len(insufficient_claims) >= 1, "Expected claims to be marked as INSUFFICIENT_EVIDENCE"
    assert overall["verdict"] in ("REVIEW", "NEEDS IMPROVEMENT"), "Should recommend review/improvement for unrepresented topics"

