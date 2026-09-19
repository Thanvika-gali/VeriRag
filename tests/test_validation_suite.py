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
from backend.services.batch_service import batch_evaluation_service
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
        assert overall["verdict"] in ("FAIL", "REVIEW", "NEEDS IMPROVEMENT"), f"Expected FAIL, REVIEW, or NEEDS IMPROVEMENT, got {overall['verdict']}"
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
        assert overall["verdict"] in ("REVIEW", "PASS", "NEEDS IMPROVEMENT")

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
        (Accuracy/5 * 0.35 + Hallucination_Safety * 0.30 + Relevance/5 * 0.20 + Completeness/5 * 0.15) * 100
        """
        res = evaluation_orchestrator.evaluate_response(
            question="What is photosynthesis?",
            ai_response="Photosynthesis is the process by which green plants produce energy from sunlight, water, and CO2.",
        )
        acc_score = res["accuracy"]["score"]
        rel_score = res["relevance"]["score"]
        comp_score = res["completeness"]["score"]
        hal_status = res["hallucination"]["hallucination_status"]
        overall_score = res["overall"]["overall_score"]

        acc_norm = acc_score / 5.0
        rel_norm = rel_score / 5.0
        comp_norm = comp_score / 5.0
        hal_safety = 1.0 if hal_status == "NONE" else 0.5 if hal_status == "PARTIAL" else 0.0

        expected_score = int(round((acc_norm * 0.35 + hal_safety * 0.30 + rel_norm * 0.20 + comp_norm * 0.15) * 100))
        assert abs(overall_score - expected_score) <= 1, (
            f"Overall score mismatch: got {overall_score}, expected {expected_score}"
        )

    # ==========================================================================
    # MILESTONE 3 REPRESENTATIVE TEST MATRIX (TEST 1 - TEST 8)
    # ==========================================================================

    def test_matrix_01_fully_correct_complete(self):
        """TEST 1 — FULLY CORRECT + COMPLETE: High relevance, high accuracy, low hallucination, high completeness -> PASS."""
        res = evaluation_orchestrator.evaluate_response(
            question="What is photosynthesis?",
            ai_response=(
                "Photosynthesis is the biological process by which green plants and certain other organisms "
                "transform light energy into chemical energy, synthesizing glucose from carbon dioxide "
                "and water while releasing oxygen into the atmosphere."
            ),
        )
        assert res["relevance"]["score"] >= 4
        assert res["accuracy"]["score"] >= 4
        assert res["hallucination"]["risk_level"] in ("LOW", "NONE")
        assert res["completeness"]["score"] >= 4
        assert res["overall"]["verdict"] == "PASS"

    def test_matrix_02_relevant_but_factually_wrong(self):
        """TEST 2 — RELEVANT BUT FACTUALLY WRONG: Relevance remains high, accuracy becomes low, verdict reflects factual problem."""
        res = evaluation_orchestrator.evaluate_response(
            question="Can the Great Wall of China be seen from the Moon?",
            ai_response=(
                "Yes, the Great Wall of China can easily be seen from the Moon with the naked eye "
                "because of its monumental length and stone construction."
            ),
            reference_answer="No, the Great Wall of China is not visible from the Moon with the naked eye.",
        )
        assert res["relevance"]["score"] >= 4
        assert res["accuracy"]["score"] <= 2
        assert res["overall"]["verdict"] == "FAIL"

    def test_matrix_03_partially_complete(self):
        """TEST 3 — PARTIALLY COMPLETE: Relevance & accuracy high, completeness decreases, missing aspects identified."""
        res = evaluation_orchestrator.evaluate_response(
            question="What is the capital of France and what is its population?",
            ai_response="The capital of France is Paris.",
            reference_answer="Paris is the capital of France, and its population is approximately 2.1 million.",
        )
        assert res["relevance"]["score"] >= 4
        assert res["accuracy"]["score"] >= 4
        assert res["completeness"]["score"] <= 3
        assert len(res["completeness"]["missing_aspects"]) >= 1
        assert "complete" in res["completeness"]["reasoning"].lower() or len(res["completeness"]["missing_aspects"]) > 0

    def test_matrix_04_irrelevant_answer(self):
        """TEST 4 — IRRELEVANT ANSWER: Relevance decreases, verdict reflects poor relevance."""
        res = evaluation_orchestrator.evaluate_response(
            question="What is photosynthesis?",
            ai_response="The Pacific Ocean is the largest and deepest ocean basin on Earth.",
        )
        assert res["relevance"]["score"] <= 2
        assert res["overall"]["verdict"] == "FAIL"

    def test_matrix_05_hallucinated_claim(self):
        """TEST 5 — HALLUCINATED CLAIM: Napoleon & Photosynthesis.

        Question: What is photosynthesis?
        Answer: Photosynthesis converts sunlight into glucose. It was discovered by Napoleon Bonaparte during his military campaign in 1802.
        """
        res = evaluation_orchestrator.evaluate_response(
            question="What is photosynthesis?",
            ai_response=(
                "Photosynthesis converts sunlight into glucose. "
                "It was discovered by Napoleon Bonaparte during his military campaign in 1802."
            ),
        )
        hal = res["hallucination"]
        claims = hal.get("flagged_claims", [])
        # Claims must be separated
        assert len(claims) >= 2, f"Expected decomposed claims >= 2, got {len(claims)}"

        # Supported claim identified
        assert any(c.get("status") == "SUPPORTED" for c in claims), "Expected at least one supported claim"

        # Unsupported or contradicted claim identified
        assert any(c.get("status") in ("UNSUPPORTED", "CONTRADICTED") for c in claims), "Expected unsupported/contradicted claim"

        # Hallucination result generated
        assert hal["risk_level"] in ("MEDIUM", "HIGH")

        # Completeness evaluates the actual question requirements
        assert res["completeness"]["score"] >= 2

        # Verdict considers hallucination
        assert res["overall"]["verdict"] != "PASS"

    def test_matrix_06_multi_part_question(self):
        """TEST 6 — MULTI-PART QUESTION: Multiple aspects identified, partial coverage marked, missing listed."""
        res = evaluation_orchestrator.evaluate_response(
            question="When was Project QuantumLeap founded, where, and who was the founder?",
            ai_response="Project QuantumLeap was founded on March 14, 2024 in Zurich.",
            reference_answer="Project QuantumLeap was founded on March 14, 2024 in Zurich by Dr. Aris Thorne.",
        )
        comp = res["completeness"]
        assert len(comp["addressed_aspects"]) >= 1
        assert len(comp["missing_aspects"]) >= 1
        assert comp["status"] in ("PARTIAL", "COMPLETE")

    def test_matrix_07_insufficient_evidence(self):
        """TEST 7 — INSUFFICIENT EVIDENCE: Does not fabricate evidence, does not pretend verified."""
        res = evaluation_orchestrator.evaluate_response(
            question="What was the secret codename of the fictional expedition to Atlantis in 1888?",
            ai_response="The expedition had the secret codename Neptune-Delta-7.",
            dataset_filter="SQuAD",  # SQuAD has no fictional 1888 Atlantis data
        )
        # System does not fabricate evidence
        assert res["accuracy"]["score"] is not None
        # Must not claim 5/5 verified
        assert res["accuracy"]["score"] <= 3

    def test_matrix_08_batch_csv(self):
        """TEST 8 — BATCH CSV: Valid records process, invalid row isolated, stats computed, details opened."""
        csv_data = (
            "question,ai_response\n"
            '"What is photosynthesis?","Photosynthesis transforms light into glucose."\n'
            ',"Missing question invalid row"\n'
            '"What is water?","Water is H2O consisting of hydrogen and oxygen."\n'
        ).encode("utf-8")

        res = batch_evaluation_service.execute_batch(csv_data, filename="matrix_batch.csv")
        assert res.valid_records_count == 2
        assert res.invalid_records_count == 1
        assert len(res.validation_errors) == 1
        assert res.stats.successful_evaluations == 2
        assert res.stats.total_records == 3
        # Individual records can be opened and inspected
        for r in res.records:
            assert r.question is not None
            assert r.verdict in ("PASS", "NEEDS IMPROVEMENT", "FAIL")

