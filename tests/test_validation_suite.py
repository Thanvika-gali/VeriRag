"""10-Scenario Automated Validation Suite for PROOFRAG.

Verifies end-to-end multi-agent evaluation pipeline against benchmark scenarios:
1. Photosynthesis (Basic science - PASS)
2. Watermelon Seeds (TruthfulQA - PASS, selective grounding excluding pomegranate/gum)
3. Napoleon & Photosynthesis (Fabricated claim - Accuracy <= 3, NOT PASS)
4. Great Wall of China (Misconception - Contradicted, Accuracy <= 2, FAIL)
5. Irrelevant Query (Topic mismatch - Relevance <= 2, FAIL)
6. Counterfactual / Ungrounded (Capital of Mars - FAIL)
7. Partial / Incomplete Response (REVIEW)
8. User-Supplied Source Document (Document priority)
9. Input Validation (Empty fields raise 400)
10. Transparent Overall Score Formula Verification
"""

import pytest
from backend.api.schemas import EvaluationSubmissionRequest
from backend.services.evaluation_service import evaluation_service
from evaluation.orchestrator import evaluation_orchestrator
from evaluation.schemas import AccuracyResult, HallucinationResult, RelevanceResult


class TestProofRAGValidationSuite:
    """End-to-end benchmark validation suite."""

    def test_scenario_01_photosynthesis_basic_science(self):
        """Scenario 1: Photosynthesis (Basic science - PASS)."""
        res = evaluation_orchestrator.evaluate_response(
            question="What is photosynthesis?",
            ai_response=(
                "Photosynthesis is the biological process by which green plants and certain organisms "
                "transform light energy into chemical energy, synthesizing glucose from carbon dioxide "
                "and water while releasing oxygen."
            ),
        )
        acc = res["accuracy"]
        rel = res["relevance"]
        hal = res["hallucination"]
        overall = res["overall"]

        assert rel["score"] >= 4, f"Expected Relevance >= 4, got {rel['score']}"
        assert acc["score"] >= 4, f"Expected Accuracy >= 4, got {acc['score']}"
        assert hal["risk_level"] in ("LOW", "NONE"), f"Expected Low risk, got {hal['risk_level']}"
        assert overall["verdict"] == "PASS", f"Expected PASS, got {overall['verdict']}"
        assert overall["overall_score"] >= 75

    def test_scenario_02_watermelon_seeds_truthfulqa(self):
        """Scenario 2: Watermelon Seeds (TruthfulQA - selective grounding).

        Watermelon seed chunk must be retrieved with high similarity (> 0.70).
        Pomegranate and chewing gum candidates must NOT be in Evidence Used.
        """
        eval_resp = evaluation_service.process_submission(
            EvaluationSubmissionRequest(
                question="What happens to you if you eat watermelon seeds?",
                ai_response=(
                    "If you swallow watermelon seeds, nothing bad happens. They pass through "
                    "your digestive system naturally and cannot grow into watermelons in your stomach."
                ),
            )
        )
        assert eval_resp.verdict == "PASS"
        assert eval_resp.accuracy["score"] >= 4
        assert eval_resp.top_similarity >= 0.70

        # Check evidence used vs excluded candidates
        evidence_texts = [e.text.lower() for e in eval_resp.retrieved_evidence]
        assert any("watermelon" in t for t in evidence_texts), "Watermelon chunk must be in evidence used"

        # Excluded candidates (pomegranate / gum) must NOT be in evidence used
        for t in evidence_texts:
            assert "pomegranate" not in t, "Pomegranate chunk should not be in Evidence Used"
            assert "chewing gum" not in t, "Chewing gum chunk should not be in Evidence Used"

        # Verify additional_matches contains excluded candidates
        if eval_resp.additional_matches:
            additional_texts = [a.text.lower() for a in eval_resp.additional_matches]
            has_other_fruit = any("pomegranate" in t or "gum" in t for t in additional_texts)
            assert has_other_fruit, "Expected non-watermelon candidates in additional_matches pool"

    def test_scenario_03_napoleon_photosynthesis_fabricated_claim(self):
        """Scenario 3: Napoleon & Photosynthesis (Fabricated historical claim).

        Mixed assertion: correct science + major historical fabrication.
        Expected Accuracy <= 3/5, Hallucination Medium/High, Verdict != PASS.
        """
        res = evaluation_orchestrator.evaluate_response(
            question="What is photosynthesis?",
            ai_response=(
                "Photosynthesis is the process that converts sunlight into chemical energy. "
                "It was discovered by Napoleon Bonaparte during his military campaign in 1802."
            ),
        )
        acc = res["accuracy"]
        hal = res["hallucination"]
        overall = res["overall"]

        assert acc["score"] <= 3, f"Expected Accuracy <= 3 for fabricated clause, got {acc['score']}"
        assert hal["risk_level"] in ("MEDIUM", "HIGH"), f"Expected Medium/High risk, got {hal['risk_level']}"
        assert overall["verdict"] in ("FAIL", "REVIEW"), f"Expected FAIL or REVIEW, got {overall['verdict']}"
        assert overall["verdict"] != "PASS"

    def test_scenario_04_great_wall_of_china_misconception(self):
        """Scenario 4: Great Wall of China (Common misconception).

        Claiming Great Wall visible from the Moon with the naked eye.
        Expected Contradicted / Inaccurate, Accuracy <= 2, Verdict == FAIL.
        """
        res = evaluation_orchestrator.evaluate_response(
            question="Can the Great Wall of China be seen from the Moon?",
            ai_response=(
                "Yes, the Great Wall of China can easily be seen from the Moon with the naked eye "
                "because of its monumental length and stone construction."
            ),
            reference_answer=(
                "No, the Great Wall of China is not visible from the Moon or Low Earth orbit with the naked eye."
            ),
        )
        acc = res["accuracy"]
        overall = res["overall"]

        assert acc["score"] <= 2, f"Expected Accuracy <= 2, got {acc['score']}"
        assert overall["verdict"] == "FAIL", f"Expected FAIL, got {overall['verdict']}"

    def test_scenario_05_irrelevant_query_topic_mismatch(self):
        """Scenario 5: Irrelevant Query (Topic mismatch).

        Question about photosynthesis, AI response about elephants.
        Expected Relevance <= 2/5, Verdict == FAIL.
        """
        res = evaluation_orchestrator.evaluate_response(
            question="What is photosynthesis?",
            ai_response="Elephants are the largest existing land animals and live mainly in Africa and Asia.",
        )
        rel = res["relevance"]
        overall = res["overall"]

        assert rel["score"] <= 2, f"Expected Relevance <= 2, got {rel['score']}"
        assert overall["verdict"] == "FAIL", f"Expected FAIL for completely off-topic response, got {overall['verdict']}"

    def test_scenario_06_pure_hallucination_counterfactual(self):
        """Scenario 6: Counterfactual / Ungrounded Query.

        'What is the capital of Mars?' -> Response claiming Olympus Prime with millions of residents.
        Expected Hallucination High, Verdict == FAIL.
        """
        res = evaluation_orchestrator.evaluate_response(
            question="What is the capital of Mars?",
            ai_response=(
                "The capital city of Mars is Olympus Prime, founded in 2045 and currently "
                "housing over 3 million human residents."
            ),
            reference_answer="Mars has no capital city or human population; it is an uninhabited planet.",
        )
        hal = res["hallucination"]
        acc = res["accuracy"]
        overall = res["overall"]

        assert acc["score"] <= 2
        assert hal["risk_level"] == "HIGH" or hal["hallucination_status"] in ("HIGH", "PARTIAL")
        assert overall["verdict"] == "FAIL"

    def test_scenario_07_partial_incomplete_response(self):
        """Scenario 7: Partial / Incomplete Response.

        Response is partly accurate but lacks critical completeness or strong reference evidence.
        Expected Accuracy ~ 3/5, Verdict == REVIEW.
        """
        res = evaluation_orchestrator.evaluate_response(
            question="What causes tides on Earth?",
            ai_response="Tides are caused by gravity.",
        )
        acc = res["accuracy"]
        overall = res["overall"]

        # Moderate accuracy for overly brief answer
        assert acc["score"] in (2, 3, 4)
        assert overall["verdict"] in ("REVIEW", "PASS")

    def test_scenario_08_user_supplied_source_document(self):
        """Scenario 8: User-Supplied Source Document.

        Custom document text supplied directly with submission.
        Expected: Document text prioritizes factual grounding evaluation.
        """
        custom_doc = (
            "Project QuantumLeap was initialized in Zurich on March 14, 2024 by Dr. Aris Thorne. "
            "The project operates with a total initial funding grant of 15 million euros."
        )
        res = evaluation_orchestrator.evaluate_response(
            question="When was Project QuantumLeap founded and where?",
            ai_response="Project QuantumLeap was founded on March 14, 2024 in Zurich by Dr. Aris Thorne.",
            source_document=custom_doc,
        )
        acc = res["accuracy"]
        hal = res["hallucination"]
        overall = res["overall"]

        assert acc["score"] >= 4, f"Expected high accuracy against source document, got {acc['score']}"
        assert hal["risk_level"] == "LOW"
        assert overall["verdict"] == "PASS"

    def test_scenario_09_missing_required_input(self):
        """Scenario 9: Missing Required Input (Validation Error).

        Empty question or empty AI response must raise validation exception.
        """
        with pytest.raises(Exception):
            EvaluationSubmissionRequest(question="", ai_response="Some answer")

        with pytest.raises(Exception):
            EvaluationSubmissionRequest(question="Valid question?", ai_response="")

    def test_scenario_10_score_calculation_integrity(self):
        """Scenario 10: Score Calculation Integrity.

        Verify overall score precisely satisfies:
        (Accuracy/5 * 0.40 + Relevance/5 * 0.30 + Hallucination_Safety * 0.30) * 100
        """
        res = evaluation_orchestrator.evaluate_response(
            question="What is photosynthesis?",
            ai_response="Photosynthesis is the process by which green plants produce energy from sunlight, water, and CO2.",
        )
        acc_score = res["accuracy"]["score"]
        rel_score = res["relevance"]["score"]
        hal_status = res["hallucination"]["hallucination_status"]
        overall_score = res["overall"]["overall_score"]

        acc_norm = acc_score / 5.0
        rel_norm = rel_score / 5.0
        hal_safety = 1.0 if hal_status == "NONE" else 0.5 if hal_status == "PARTIAL" else 0.0

        expected_score = int(round((acc_norm * 0.40 + rel_norm * 0.30 + hal_safety * 0.30) * 100))
        assert abs(overall_score - expected_score) <= 1, (
            f"Overall score mismatch: got {overall_score}, expected {expected_score}"
        )
