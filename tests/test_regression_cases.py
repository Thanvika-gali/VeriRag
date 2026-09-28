"""Deterministic Regression Test Suite for Batch Evaluation System.

Validates the 6 critical benchmark cases specified in Milestone 3 Batch Verification:
CASE 1 — Correct response (high relevance, high accuracy, low hallucination, high completeness).
CASE 2 — Factual contradiction / incorrect answer (low accuracy).
CASE 3 — Off-topic / irrelevant response (low relevance).
CASE 4 — Partially accurate with fabricated claim (flagged unsupported/false assertion).
CASE 5 — Incomplete multi-part response (reduced completeness, missing aspects identified).
CASE 6 — Semantically correct paraphrase with reference (high relevance, high accuracy, low hallucination, high completeness).
"""

import pytest
from evaluation.orchestrator import EvaluationOrchestrator, evaluation_orchestrator
from backend.services.batch_service import batch_evaluation_service


@pytest.fixture(scope="module")
def orchestrator():
    return EvaluationOrchestrator()


def test_case_01_correct_photosynthesis_outputs(orchestrator):
    """CASE 1 — Correct: High relevance, high accuracy, low hallucination, high completeness."""
    question = "What are the outputs of photosynthesis?"
    response = "The outputs are glucose and oxygen."
    reference = "The main outputs of photosynthesis are glucose and oxygen."

    res = orchestrator.evaluate_response(
        question=question,
        ai_response=response,
        reference_answer=reference,
    )

    acc = res["accuracy"]
    rel = res["relevance"]
    hal = res["hallucination"]
    comp = res["completeness"]

    assert rel["score"] >= 4, f"Expected high relevance (>=4), got {rel['score']}"
    assert acc["score"] >= 4, f"Expected high accuracy (>=4), got {acc['score']}"
    assert hal["risk_level"] == "LOW", f"Expected LOW hallucination risk, got {hal['risk_level']}"
    assert comp["score"] >= 4, f"Expected high completeness (>=4), got {comp['score']}"
    assert res["verdict"] == "PASS", f"Expected PASS verdict, got {res['verdict']}"


def test_case_02_incorrect_factual_contradiction(orchestrator):
    """CASE 2 — Incorrect: Low accuracy on fabricated/contradicted outputs."""
    question = "What are the outputs of photosynthesis?"
    response = "The outputs are nitrogen and methane."
    reference = "The outputs of photosynthesis are glucose and oxygen."

    res = orchestrator.evaluate_response(
        question=question,
        ai_response=response,
        reference_answer=reference,
    )

    acc = res["accuracy"]
    assert acc["score"] <= 2, f"Expected low accuracy (<=2) for incorrect outputs, got {acc['score']}"
    assert res["verdict"] in ("FAIL", "NEEDS IMPROVEMENT")


def test_case_03_irrelevant_off_topic(orchestrator):
    """CASE 3 — Irrelevant: Low relevance on completely off-topic response."""
    question = "What are the outputs of photosynthesis?"
    response = "Java is an object-oriented programming language."

    res = orchestrator.evaluate_response(
        question=question,
        ai_response=response,
    )

    rel = res["relevance"]
    assert rel["score"] <= 2, f"Expected low relevance (<=2) for off-topic response, got {rel['score']}"
    assert res["verdict"] == "FAIL"


def test_case_04_hallucinated_napoleon_claim(orchestrator):
    """CASE 4 — Hallucinated claim: Specific unsupported/false claim flagged."""
    question = "What is photosynthesis?"
    response = "Photosynthesis allows plants to produce glucose and oxygen. It was discovered by Napoleon Bonaparte."
    reference = "Photosynthesis is the process by which green plants transform light energy into chemical energy, synthesizing glucose and releasing oxygen."

    res = orchestrator.evaluate_response(
        question=question,
        ai_response=response,
        reference_answer=reference,
    )

    hal = res["hallucination"]
    acc = res["accuracy"]

    # Unsupported / hallucinated claim must be flagged
    claims = hal.get("flagged_claims", [])
    flagged = [c for c in claims if c.get("status") in ("UNSUPPORTED", "CONTRADICTED")]
    assert len(flagged) >= 1, "Expected at least one unsupported/contradicted claim flagged"
    assert any("napoleon" in c.get("claim", "").lower() for c in flagged), "Napoleon claim must be flagged"

    # Hallucination risk must be elevated and accuracy must not be 5
    assert hal["risk_level"] in ("MEDIUM", "HIGH")
    assert acc["score"] <= 3, f"Expected accuracy <= 3 due to fabricated claim, got {acc['score']}"


def test_case_05_incomplete_multipart_answer(orchestrator):
    """CASE 5 — Incomplete multi-part answer: Reduced completeness with missing aspects identified."""
    question = "Explain photosynthesis, its inputs, and its outputs."
    response = "Photosynthesis is the process by which plants make food."
    reference = "Photosynthesis converts carbon dioxide, water, and sunlight (inputs) into glucose and oxygen (outputs)."

    res = orchestrator.evaluate_response(
        question=question,
        ai_response=response,
        reference_answer=reference,
    )

    comp = res["completeness"]
    assert comp["score"] <= 3, f"Expected reduced completeness (<=3), got {comp['score']}"
    assert comp["status"] in ("PARTIAL", "INCOMPLETE")
    assert len(comp["missing_aspects"]) >= 1, "Expected at least one missing aspect identified"
    missing_str = " ".join(comp["missing_aspects"]).lower()
    assert "input" in missing_str or "output" in missing_str, f"Missing aspects should mention inputs/outputs: {missing_str}"


def test_case_06_semantically_correct_paraphrase(orchestrator):
    """CASE 6 — Semantically correct paraphrase: High relevance, high accuracy, low hallucination, high completeness."""
    question = "What happens if a plant does not receive enough light?"
    response = "Photosynthesis can decrease because less light energy is available."
    reference = "A lack of sufficient light can reduce the rate of photosynthesis because less light energy is available."

    res = orchestrator.evaluate_response(
        question=question,
        ai_response=response,
        reference_answer=reference,
    )

    acc = res["accuracy"]
    rel = res["relevance"]
    hal = res["hallucination"]
    comp = res["completeness"]

    assert rel["score"] >= 4, f"Expected high relevance (>=4), got {rel['score']}"
    assert acc["score"] >= 4, f"Expected high accuracy (>=4), got {acc['score']}"
    assert hal["risk_level"] == "LOW", f"Expected LOW hallucination risk, got {hal['risk_level']}"
    assert comp["score"] >= 4, f"Expected high completeness (>=4), got {comp['score']}"
    assert res["verdict"] == "PASS", f"Expected PASS verdict, got {res['verdict']}"


def test_batch_sample_csv_isolated_and_independent():
    """Verify that batch evaluation executes each row independently without leaking state."""
    csv_content = (
        'question,ai_response,reference_answer\n'
        '"What are the outputs of photosynthesis?","The outputs are glucose and oxygen.","The outputs are glucose and oxygen."\n'
        '"What are the outputs of photosynthesis?","Java is an object-oriented programming language.","The outputs are glucose and oxygen."\n'
        '"What happens if a plant does not receive enough light?","Photosynthesis can decrease because less light energy is available.","A lack of sufficient light can reduce the rate of photosynthesis because less light energy is available."\n'
    ).encode("utf-8")

    batch_res = batch_evaluation_service.execute_batch(csv_content, filename="regression_test.csv")
    assert batch_res.success is True
    assert len(batch_res.records) == 3

    r1, r2, r3 = batch_res.records

    # Row 1 is fully correct -> PASS
    assert r1.accuracy_score >= 4
    assert r1.relevance_score >= 4
    assert r1.verdict == "PASS"

    # Row 2 is completely off-topic -> FAIL
    assert r2.relevance_score <= 2
    assert r2.verdict == "FAIL"

    # Row 3 is semantically correct paraphrase -> PASS
    assert r3.accuracy_score >= 4
    assert r3.relevance_score >= 4
    assert r3.completeness_score >= 4
    assert r3.verdict == "PASS"

    # Ensure IDs, questions, and responses are independent
    assert r1.record_id == 1 and r2.record_id == 2 and r3.record_id == 3
    assert r1.ai_response != r2.ai_response
    assert r2.ai_response != r3.ai_response
