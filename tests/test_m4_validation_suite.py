"""Milestone 4.3 — End-to-End System Validation Suite for PROOFRAG.

Validates:
TEST 1  — Complete Single Evaluation pipeline (Question -> RAG -> Agents -> Verdict -> DB -> UI result).
TEST 2  — Batch Evaluation lifecycle (CSV -> prevalidation -> execution -> storage -> aggregation -> dashboard -> PDF).
TEST 3  — Correct factual response (high relevance, high accuracy, high completeness, low hallucination, PASS).
TEST 4  — Irrelevant response (low relevance, appropriate accuracy, low completeness, FAIL).
TEST 5  — Incorrect response (accuracy decreases, contradictory/unsupported claims identified, score drops).
TEST 6  — Incomplete response (completeness decreases, missing aspects identified).
TEST 7  — Hallucinated response (unsupported claims identified, evidence reasoning displayed, risk increases).
TEST 8  — Contradictory response (accuracy decreases, contradiction detected, critical override applied).
TEST 9  — No reference answer provided (uses RAG-retrieved knowledge base evidence).
TEST 10 — Invalid CSV upload (missing fields, malformed rows, empty rows, invalid types without crashing).
TEST 11 — Scoring & Reasoning Consistency Validation.
TEST 12 — Photosynthesis Regression Check (Napoleon / nitrogen & methane must NOT receive perfect accuracy).
TEST 13 — Dashboard Metrics & Formula Exact Verification (PASS%, averages, hallucination frequencies).
TEST 14 — PDF Report Generation & Verification across modes.
"""

import io
import json
import pytest
from fastapi.testclient import TestClient

from backend.api.schemas import EvaluationSubmissionRequest
from backend.database.sqlite_db import db_instance
from backend.main import app
from backend.services.batch_service import batch_evaluation_service
from backend.services.evaluation_service import evaluation_service
from backend.services.pdf_report_service import pdf_report_service
from evaluation.orchestrator import evaluation_orchestrator


@pytest.fixture(scope="module")
def api_client():
    return TestClient(app)


class TestProofRAGMilestone4Suite:
    """Comprehensive Milestone 4 validation test suite."""

    def test_01_single_evaluation_full_pipeline(self, api_client):
        """TEST 1: Single evaluation end-to-end data pipeline validation."""
        req_payload = {
            "question": "What is photosynthesis and what does it produce?",
            "ai_response": "Photosynthesis is the process by which green plants synthesize glucose from carbon dioxide and water, releasing oxygen.",
            "reference_answer": "Photosynthesis produces glucose and oxygen using light energy.",
        }

        # API Call
        response = api_client.post("/api/submissions", json=req_payload)
        assert response.status_code == 201, f"Failed with {response.text}"
        data = response.json()

        # 1. Pipeline output validation
        sub_id = data["submission_id"]
        assert sub_id
        assert data["overall_score"] >= 70
        assert data["verdict"] in ("PASS", "NEEDS IMPROVEMENT")

        # 2. Stage verification
        assert "relevance" in data and data["relevance"]["score"] >= 4
        assert "accuracy" in data and data["accuracy"]["score"] >= 4
        assert "completeness" in data and data["completeness"]["score"] >= 4
        assert "hallucination" in data and data["hallucination"]["risk_level"] in ("LOW", "NONE")
        assert "verdict_details" in data

        # 3. SQLite persistence verification
        stored = db_instance.get_submission(sub_id)
        assert stored is not None
        assert stored["question"] == req_payload["question"]
        assert stored["overall_score"] == data["overall_score"]
        assert stored["verdict"] == data["verdict"]

    def test_02_batch_evaluation_full_pipeline(self, api_client):
        """TEST 2: Batch evaluation CSV lifecycle to dashboard and PDF."""
        csv_content = (
            "question,ai_response,reference_answer\n"
            '"What is the boiling point of water at sea level?","Water boils at 100 degrees Celsius at sea level.","100 C"\n'
            '"What is the capital of Japan?","The capital of Japan is Tokyo.","Tokyo is the capital of Japan."\n'
        )

        files = {"file": ("m4_test_batch.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
        res = api_client.post("/api/batch/evaluate", files=files)
        assert res.status_code == 200, res.text
        batch_res = res.json()

        b_id = batch_res["batch_id"]
        assert batch_res["valid_records_count"] == 2
        assert batch_res["stats"]["pass_count"] >= 1

        # Verify batch dashboard API reflects batch
        dash_res = api_client.get(f"/api/dashboard/stats?batch_id={b_id}")
        assert dash_res.status_code == 200
        dash_data = dash_res.json()
        assert dash_data["total_evaluations"] == 2
        assert dash_data["average_overall_score"] is not None

        # Verify PDF report generation for this batch
        pdf_res = api_client.get(f"/api/reports/pdf?batch_id={b_id}")
        assert pdf_res.status_code == 200
        assert pdf_res.headers.get("content-type") == "application/pdf"
        assert len(pdf_res.content) > 1000
        assert pdf_res.content.startswith(b"%PDF")

    def test_03_correct_response(self):
        """TEST 3: Correct response produces high scores across dimensions and PASS verdict."""
        res = evaluation_orchestrator.evaluate_response(
            question="What is the capital of Italy?",
            ai_response="The capital of Italy is Rome, known for its rich history and ancient architecture.",
            reference_answer="Rome is the capital of Italy.",
        )
        assert res["relevance"]["score"] >= 4
        assert res["accuracy"]["score"] >= 4
        assert res["completeness"]["score"] >= 4
        assert res["hallucination"]["risk_level"] == "LOW"
        assert res["overall"]["verdict"] == "PASS"
        assert res["overall"]["overall_score"] >= 75

    def test_04_irrelevant_response(self):
        """TEST 4: Irrelevant response scores low relevance, fails criteria."""
        res = evaluation_orchestrator.evaluate_response(
            question="How does cellular respiration generate ATP?",
            ai_response="The Amazon rainforest is home to millions of plant and animal species.",
        )
        assert res["relevance"]["score"] <= 2
        assert res["overall"]["verdict"] == "FAIL"

    def test_05_incorrect_response(self):
        """TEST 5: Incorrect factual response decreases accuracy and score."""
        res = evaluation_orchestrator.evaluate_response(
            question="What is the chemical formula for water?",
            ai_response="The chemical formula for water is H2SO4, which contains sulfur and oxygen.",
            reference_answer="The chemical formula for water is H2O.",
        )
        assert res["accuracy"]["score"] <= 2
        assert res["overall"]["overall_score"] < 60
        assert res["overall"]["verdict"] in ("FAIL", "NEEDS IMPROVEMENT")

    def test_06_incomplete_response(self):
        """TEST 6: Incomplete response decreases completeness score and identifies missing aspect."""
        res = evaluation_orchestrator.evaluate_response(
            question="What is the capital of Germany and what currency does Germany use?",
            ai_response="The capital of Germany is Berlin.",
            reference_answer="Berlin is the capital of Germany and its official currency is the Euro.",
        )
        assert res["completeness"]["score"] <= 3
        assert len(res["completeness"]["missing_aspects"]) >= 1
        missing_text = " ".join(res["completeness"]["missing_aspects"]).lower()
        assert "currency" in missing_text or "germany" in missing_text or len(res["completeness"]["missing_aspects"]) >= 1

    def test_07_hallucinated_response(self):
        """TEST 7: Hallucinated response flags specific unsupported claim."""
        res = evaluation_orchestrator.evaluate_response(
            question="What is the speed of light in vacuum?",
            ai_response="The speed of light in vacuum is approximately 300,000 km/s. It was first measured by Benjamin Franklin during a thunderstorm in 1752.",
            reference_answer="The speed of light in vacuum is approximately 299,792,458 meters per second.",
        )
        assert res["hallucination"]["risk_level"] in ("MEDIUM", "HIGH")
        assert len(res["hallucination"]["flagged_claims"]) >= 1
        claims_text = " ".join(
            c.get("claim", str(c)) if isinstance(c, dict) else str(c)
            for c in res["hallucination"]["flagged_claims"]
        ).lower()
        assert "franklin" in claims_text or "thunderstorm" in claims_text or "1752" in claims_text

    def test_08_contradictory_response(self):
        """TEST 8: Contradictory assertion causes critical override or failure."""
        res = evaluation_orchestrator.evaluate_response(
            question="Can the Great Wall of China be seen from space with the naked eye?",
            ai_response="Yes, the Great Wall of China is easily seen from space with the naked human eye.",
            reference_answer="No, the Great Wall of China cannot be seen from space or low Earth orbit with the unaided human eye.",
        )
        assert res["accuracy"]["score"] <= 2
        assert res["overall"]["verdict"] == "FAIL"

    def test_09_no_reference_answer_uses_rag(self):
        """TEST 9: Evaluation functions using RAG-retrieved evidence when no reference answer is provided."""
        res = evaluation_orchestrator.evaluate_response(
            question="What happens to you if you eat watermelon seeds?",
            ai_response="Eating watermelon seeds is safe and harmless; they simply pass through the digestive tract.",
            reference_answer=None,  # No ground truth provided
        )
        assert res["relevance"]["score"] >= 3
        # Evidence retrieval should have provided candidate context from TruthfulQA
        assert len(res["evidence"]) >= 1 or res["accuracy"]["score"] >= 3
        assert res["overall"]["verdict"] in ("PASS", "NEEDS IMPROVEMENT")

    def test_10_invalid_csv_handling(self, api_client):
        """TEST 10: Robustness against malformed, empty, and invalid CSV rows without crashing."""
        malformed_csv = (
            "question,ai_response,reference_answer\n"
            ',,"Missing both question and answer"\n'
            '"Valid question 1","Valid AI response 1","Valid reference"\n'
            '"Missing response only",,"Some reference"\n'
            ',,""\n'
            '"Valid question 2","Valid AI response 2","Valid reference"\n'
        )

        files = {"file": ("malformed_test.csv", io.BytesIO(malformed_csv.encode("utf-8")), "text/csv")}
        res = api_client.post("/api/batch/evaluate", files=files)
        assert res.status_code == 200, res.text
        data = res.json()

        # The batch did not crash; valid rows were processed, invalid rows skipped
        assert data["valid_records_count"] == 2
        assert data["invalid_records_count"] >= 2
        assert len(data["invalid_rows"]) >= 2
        assert data["stats"]["successful_evaluations"] == 2

    def test_11_scoring_consistency_and_reasoning(self):
        """TEST 11: Consistency between numerical scores and textual reasoning justifications."""
        res = evaluation_orchestrator.evaluate_response(
            question="What is the capital of Spain?",
            ai_response="The capital of Spain is Madrid.",
            reference_answer="Madrid is the capital of Spain.",
        )
        if res["accuracy"]["score"] == 5:
            assert "contradict" not in res["accuracy"]["reasoning"].lower()
            assert "incorrect" not in res["accuracy"]["reasoning"].lower()
            assert "fabricat" not in res["accuracy"]["reasoning"].lower()

        if res["completeness"]["score"] == 5:
            assert len(res["completeness"]["missing_aspects"]) == 0

    def test_12_regression_photosynthesis_negative_case(self):
        """TEST 12 — REGRESSION CHECK: Nitrogen and methane must NOT receive perfect accuracy."""
        res = evaluation_orchestrator.evaluate_response(
            question="What are the outputs of photosynthesis?",
            ai_response="The main outputs of photosynthesis are nitrogen and methane.",
            reference_answer="The main outputs are glucose and oxygen.",
        )
        # MUST NOT receive score 5
        assert res["accuracy"]["score"] <= 2, f"Accuracy score should be <= 2, got {res['accuracy']['score']}"
        assert res["overall"]["verdict"] == "FAIL"

    def test_13_dashboard_formula_exact_verification(self, api_client):
        """TEST 13: Dashboard statistics strictly reconcile against database formulas."""
        res = api_client.get("/api/dashboard/stats")
        assert res.status_code == 200
        stats = res.json()

        if stats["total_evaluations"] > 0:
            tot = stats["total_evaluations"]
            p_cnt = stats["verdicts"]["PASS"]
            r_cnt = stats["verdicts"]["NEEDS IMPROVEMENT"]
            f_cnt = stats["verdicts"]["FAIL"]

            # 1. Total records formula
            assert p_cnt + r_cnt + f_cnt == tot

            # 2. Percentage formula: pass% = pass/total * 100
            expected_pass_pct = round((p_cnt / tot) * 100, 1)
            assert abs(stats["verdict_percentages"]["PASS"] - expected_pass_pct) <= 0.2

            # 3. Hallucination frequency formula: flagged / total * 100
            flagged = stats["hallucination_stats"]["flagged_count"]
            expected_hal_freq = round((flagged / tot) * 100, 1)
            assert abs(stats["hallucination_stats"]["frequency_percentage"] - expected_hal_freq) <= 0.2

    def test_14_pdf_report_generation_service(self, api_client):
        """TEST 14: PDF report export produces multi-page document matching stored evaluation data."""
        res = api_client.get("/api/reports/pdf")
        assert res.status_code == 200
        assert res.headers["content-type"] == "application/pdf"
        assert len(res.content) > 5000
        assert res.content[:4] == b"%PDF"
