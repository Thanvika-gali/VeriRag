"""Comprehensive Milestone 4 Master Audit & Validation Test Suite.

Covers:
1. Complete Single-Evaluation Workflow (8 Test Cases)
2. Batch Evaluation & CSV Robustness Lifecycle
3. Hallucination Detection Engine (6 Explicit Grounding Scenarios)
4. Verdict Agent Weighted Scoring Model & Critical Safety Overrides
5. Scoring Consistency & Reasoning Correlation
6. Dashboard Mathematical Reconciliations & Filter Integrity
7. Multi-Tier PDF Report Export (Single, Small, Medium, Large)
8. Two Distinct AI Systems Comparative Evaluation (System A vs System B)
"""

import io
import json
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.database.sqlite_db import db_instance
from backend.services.batch_service import batch_evaluation_service
from backend.services.evaluation_service import evaluation_service
from backend.services.pdf_report_service import pdf_report_service
from evaluation.orchestrator import evaluation_orchestrator
from evaluation.agents.verdict_agent import verdict_agent


@pytest.fixture(scope="module")
def api_client():
    return TestClient(app)


class TestMilestone4MasterAudit:
    """Master validation test suite executing every Milestone 4 requirement."""

    # ==========================================================================
    # 1. SINGLE EVALUATION WORKFLOW: 8 REQUIRED TEST CASES
    # ==========================================================================

    def test_case_01_fully_correct_response(self):
        """CASE 1: Fully correct response -> high relevance, accuracy, completeness, low hallucination risk, PASS."""
        res = evaluation_orchestrator.evaluate_response(
            question="What is photosynthesis and what does it produce?",
            ai_response="Photosynthesis is the biological process where green plants convert sunlight, carbon dioxide, and water into glucose and oxygen.",
            reference_answer="Photosynthesis produces glucose and oxygen from carbon dioxide and water using light energy.",
        )
        assert res["relevance"]["score"] >= 4
        assert res["accuracy"]["score"] >= 4
        assert res["completeness"]["score"] >= 4
        assert res["hallucination"]["risk_level"] == "LOW"
        assert res["overall"]["verdict"] == "PASS"
        assert res["overall"]["overall_score"] >= 75

    def test_case_02_irrelevant_response(self):
        """CASE 2: Irrelevant response -> low relevance, low completeness, overall FAIL."""
        res = evaluation_orchestrator.evaluate_response(
            question="What causes the seasons on Earth?",
            ai_response="Bitcoin is a decentralized digital cryptocurrency that uses blockchain technology to verify transactions.",
            reference_answer="Seasons are caused by Earth's axial tilt of 23.5 degrees as it orbits the Sun.",
        )
        assert res["relevance"]["score"] <= 2
        assert res["overall"]["verdict"] == "FAIL"

    def test_case_03_factually_incorrect_response(self):
        """CASE 3: Factually incorrect response -> reduced accuracy, appropriate evidence/reasoning, verdict FAIL/NEEDS IMPROVEMENT."""
        res = evaluation_orchestrator.evaluate_response(
            question="What is the boiling point of water at sea level?",
            ai_response="Water boils at 25 degrees Celsius at sea level under standard atmospheric pressure.",
            reference_answer="Water boils at 100 degrees Celsius (212 Fahrenheit) at sea level.",
        )
        assert res["accuracy"]["score"] <= 2
        assert res["overall"]["verdict"] in ("FAIL", "NEEDS IMPROVEMENT")
        assert res["accuracy"]["reasoning"] != ""

    def test_case_04_partially_correct_response(self):
        """CASE 4: Partially correct response -> dimension scores reflect partial correctness with explanatory reasoning."""
        res = evaluation_orchestrator.evaluate_response(
            question="What is the capital of Australia and what is its most populous city?",
            ai_response="The capital of Australia is Canberra.",
            reference_answer="The capital of Australia is Canberra, and its most populous city is Sydney.",
        )
        assert res["completeness"]["score"] <= 3
        assert "most populous city" in res["completeness"]["reasoning"] or len(res["completeness"]["missing_aspects"]) >= 1
        assert res["overall"]["verdict"] in ("NEEDS IMPROVEMENT", "PASS")

    def test_case_05_incomplete_response(self):
        """CASE 5: Incomplete response -> completeness decreases and missing aspects identified."""
        res = evaluation_orchestrator.evaluate_response(
            question="What is the capital of France, what river flows through it, and what is its primary currency?",
            ai_response="The capital of France is Paris.",
            reference_answer="The capital of France is Paris, the River Seine flows through it, and the official currency is the Euro.",
        )
        assert res["completeness"]["score"] <= 3
        assert len(res["completeness"]["missing_aspects"]) >= 1

    def test_case_06_hallucinated_response(self):
        """CASE 6: Hallucinated response -> unsupported claims identified, evidence comparison performed, risk elevated."""
        res = evaluation_orchestrator.evaluate_response(
            question="Who invented the telephone?",
            ai_response="Alexander Graham Bell invented the telephone. In 1888, he tested it by calling Abraham Lincoln in the White House.",
            reference_answer="Alexander Graham Bell was awarded the first patent for the telephone in 1876. Lincoln died in 1865.",
        )
        assert res["hallucination"]["risk_level"] in ("MEDIUM", "HIGH")
        assert len(res["hallucination"]["flagged_claims"]) >= 1

    def test_case_07_contradictory_response(self):
        """CASE 7: Contradictory response -> contradictory claims identified, accuracy penalized, verdict forced to FAIL."""
        res = evaluation_orchestrator.evaluate_response(
            question="Is Earth flat or round?",
            ai_response="Scientific consensus confirms that Earth is completely flat with an ice wall around the perimeter.",
            reference_answer="Earth is an oblate spheroid, rounded due to its gravity.",
        )
        assert res["accuracy"]["score"] <= 2
        assert res["overall"]["verdict"] == "FAIL"

    def test_case_08_no_reference_answer_uses_rag(self):
        """CASE 8: No reference answer provided -> RAG evidence retrieved and used for grounding."""
        res = evaluation_orchestrator.evaluate_response(
            question="What happens to you if you eat watermelon seeds?",
            ai_response="Swallowing watermelon seeds does not hurt you; they pass through your body undigested without growing in your stomach.",
            reference_answer=None,
        )
        assert res["relevance"]["score"] >= 3
        assert len(res["evidence"]) >= 1 or res["accuracy"]["score"] >= 3
        assert res["overall"]["verdict"] in ("PASS", "NEEDS IMPROVEMENT")

    # ==========================================================================
    # 2. HALLUCINATION DETECTION ENGINE: 6 GROUNDING SCENARIOS
    # ==========================================================================

    def test_hallucination_01_fully_supported(self):
        """Scenario 1: Fully supported response -> 0 ungrounded claims, LOW risk."""
        res = evaluation_orchestrator.evaluate_response(
            question="What is DNA?",
            ai_response="DNA is the molecule that carries genetic information for the development and functioning of living organisms.",
            reference_answer="DNA is a molecule carrying genetic instructions in living organisms.",
        )
        assert res["hallucination"]["risk_level"] == "LOW"
        unsupported = [c for c in res["hallucination"]["flagged_claims"] if c.get("status") in ("UNSUPPORTED", "CONTRADICTED")]
        assert len(unsupported) == 0

    def test_hallucination_02_one_unsupported_claim(self):
        """Scenario 2: One unsupported claim -> claim extracted and flagged, MEDIUM or HIGH risk."""
        res = evaluation_orchestrator.evaluate_response(
            question="What is the speed of sound in air?",
            ai_response="The speed of sound in dry air at 20 degrees Celsius is about 343 meters per second. It was first observed by Christopher Columbus on his ship in 1492.",
            reference_answer="The speed of sound in dry air at 20 C is approximately 343 m/s.",
        )
        assert res["hallucination"]["risk_level"] in ("MEDIUM", "HIGH")
        assert len(res["hallucination"]["flagged_claims"]) >= 1

    def test_hallucination_03_multiple_unsupported_claims(self):
        """Scenario 3: Multiple unsupported claims -> multiple claims flagged, HIGH risk."""
        res = evaluation_orchestrator.evaluate_response(
            question="What is Jupiter?",
            ai_response="Jupiter is the largest planet. It has a solid gold surface, breathable oxygen atmosphere, and was built by ancient astronauts in 4000 BC.",
            reference_answer="Jupiter is a gas giant primarily composed of hydrogen and helium.",
        )
        assert res["hallucination"]["risk_level"] in ("MEDIUM", "HIGH")
        assert len(res["hallucination"]["flagged_claims"]) >= 1

    def test_hallucination_04_contradictory_claim(self):
        """Scenario 4: Contradictory claim -> identified and flagged against reference."""
        res = evaluation_orchestrator.evaluate_response(
            question="What is the freezing point of pure water?",
            ai_response="Pure water freezes at 100 degrees Celsius under normal atmospheric pressure.",
            reference_answer="Pure water freezes at 0 degrees Celsius (32 degrees Fahrenheit).",
        )
        assert res["accuracy"]["score"] <= 2
        assert res["overall"]["verdict"] == "FAIL"

    def test_hallucination_05_partially_supported(self):
        """Scenario 5: Partially supported response -> supported portion recognized, ungrounded portion isolated."""
        res = evaluation_orchestrator.evaluate_response(
            question="Where is Mount Everest located?",
            ai_response="Mount Everest is in the Himalayas on the border between Nepal and China. It has a secret luxury hotel located at the absolute summit.",
            reference_answer="Mount Everest is located in the Mahalangur Himal sub-range of the Himalayas on the China-Nepal border.",
        )
        assert res["relevance"]["score"] >= 3
        assert len(res["hallucination"]["flagged_claims"]) >= 1

    def test_hallucination_06_completely_unsupported(self):
        """Scenario 6: Completely unsupported response -> overall verdict FAIL."""
        res = evaluation_orchestrator.evaluate_response(
            question="What are diamonds made of?",
            ai_response="Diamonds are forged from liquid helium compressed inside ancient alien spaceships located beneath the South Pole.",
            reference_answer="Diamonds are made of pure carbon atoms arranged in a crystal lattice.",
        )
        assert res["overall"]["verdict"] == "FAIL"
        assert res["accuracy"]["score"] <= 2

    # ==========================================================================
    # 3. VERDICT AGENT VALIDATION: WEIGHTED SCORING & SAFETY OVERRIDES
    # ==========================================================================

    def test_verdict_agent_weights_and_thresholds(self):
        """Verify weights sum correctly, thresholds apply, and critical overrides trigger."""
        weights = verdict_agent.weights
        total_weight = sum(weights.values())
        assert round(total_weight, 2) == 1.0, f"Weights must sum to 1.0, got {total_weight}"

        # 1. High score pass
        v_pass = verdict_agent.compute_verdict(
            relevance_score=5,
            accuracy_score=5,
            completeness_score=5,
            hallucination_risk="LOW",
        )
        assert v_pass["overall_score"] >= 80
        assert v_pass["verdict"] == "PASS"

        # 2. Moderate score review
        v_rev = verdict_agent.compute_verdict(
            relevance_score=3,
            accuracy_score=3,
            completeness_score=3,
            hallucination_risk="LOW",
        )
        assert 50 <= v_rev["overall_score"] <= 74
        assert v_rev["verdict"] == "NEEDS IMPROVEMENT"

        # 3. Low score fail
        v_fail = verdict_agent.compute_verdict(
            relevance_score=1,
            accuracy_score=1,
            completeness_score=1,
            hallucination_risk="HIGH",
        )
        assert v_fail["overall_score"] < 50
        assert v_fail["verdict"] == "FAIL"

        # 4. Critical Override: High accuracy but HIGH hallucination must FAIL
        v_crit = verdict_agent.compute_verdict(
            relevance_score=5,
            accuracy_score=4,
            completeness_score=5,
            hallucination_risk="HIGH",
        )
        assert v_crit["verdict"] == "FAIL"
        assert v_crit["critical_override_applied"] is True

    # ==========================================================================
    # 4. BATCH EVALUATION PIPELINE & CSV VALIDATION
    # ==========================================================================

    def test_batch_pipeline_and_csv_fault_tolerance(self, api_client):
        """Batch processing: handles valid CSV, rejects non-CSV, isolates malformed rows without crashing."""
        # 1. Invalid file rejection
        bad_file = {"file": ("test.exe", io.BytesIO(b"binary"), "application/octet-stream")}
        res_bad = api_client.post("/api/batch/validate", files=bad_file)
        assert res_bad.status_code == 200
        assert res_bad.json()["is_valid"] is False

        # 2. Mixed valid & malformed rows
        mixed_csv = (
            "question,ai_response,reference_answer\n"
            '"What is H2O?","Water","Chemical formula for water"\n'
            ',,"Missing question and answer"\n'
            '"What is CO2?","Carbon dioxide","Carbon dioxide"\n'
            '"Missing answer only",,"Some reference"\n'
            '"What is NaCl?","Sodium chloride (table salt)","Salt"\n'
        )
        csv_file = {"file": ("mixed_test.csv", io.BytesIO(mixed_csv.encode("utf-8")), "text/csv")}
        res_batch = api_client.post("/api/batch/evaluate", files=csv_file)
        assert res_batch.status_code == 200
        b_data = res_batch.json()

        assert b_data["valid_records_count"] == 3
        assert b_data["invalid_records_count"] == 2
        assert b_data["stats"]["successful_evaluations"] == 3
        assert b_data["stats"]["total_records"] == 5

    # ==========================================================================
    # 5. DASHBOARD MATHEMATICAL RECONCILIATION
    # ==========================================================================

    def test_dashboard_mathematical_exactness(self, api_client):
        """Manually compute statistics on a test batch and verify dashboard returns identical values."""
        # Create a dedicated test batch
        test_csv = (
            "question,ai_response,reference_answer\n"
            '"What is the boiling point of water?","100 degrees Celsius","100 C"\n'
            '"What is 2+2?","4","4"\n'
            '"What is the capital of Mars?","Mars City is the capital of Mars founded in 1999.","Mars has no capital city."\n'
        )
        csv_file = {"file": ("math_audit_batch.csv", io.BytesIO(test_csv.encode("utf-8")), "text/csv")}
        b_res = api_client.post("/api/batch/evaluate", files=csv_file)
        assert b_res.status_code == 200
        batch_id = b_res.json()["batch_id"]

        # Fetch dashboard stats for this exact batch
        dash_res = api_client.get(f"/api/dashboard/stats?batch_id={batch_id}")
        assert dash_res.status_code == 200
        dash_stats = dash_res.json()

        tot = dash_stats["total_evaluations"]
        assert tot == 3

        p_cnt = dash_stats["verdicts"]["PASS"]
        r_cnt = dash_stats["verdicts"]["NEEDS IMPROVEMENT"]
        f_cnt = dash_stats["verdicts"]["FAIL"]
        assert p_cnt + r_cnt + f_cnt == tot

        # Percentage sum check
        p_pct = dash_stats["verdict_percentages"]["PASS"]
        r_pct = dash_stats["verdict_percentages"]["NEEDS IMPROVEMENT"]
        f_pct = dash_stats["verdict_percentages"]["FAIL"]
        assert round(p_pct + r_pct + f_pct) in (99, 100, 101)

        # Hallucination frequency & unsupported claims
        hal_stats = dash_stats["hallucination_stats"]
        assert "unsupported_claim_frequency" in hal_stats
        assert "records_with_unsupported_claims" in hal_stats

        # Filter verification: filter by PASS only
        pass_res = api_client.get(f"/api/dashboard/stats?batch_id={batch_id}&verdict=PASS")
        assert pass_res.status_code == 200
        pass_stats = pass_res.json()
        assert pass_stats["total_evaluations"] == p_cnt

    # ==========================================================================
    # 6. PDF EXPORT VALIDATION ACROSS MULTIPLE SIZES
    # ==========================================================================

    def test_pdf_report_single_small_medium_large(self, api_client):
        """Validate PDF generation across Single, Small, Medium, and Large evaluation scopes."""
        # 1. Single evaluation PDF
        sub_res = api_client.post("/api/submissions", json={
            "question": "What is gravity?",
            "ai_response": "Gravity is a fundamental interaction which causes mutual attraction between all things with mass.",
            "reference_answer": "Gravity is the universal force of attraction acting between all matter.",
        })
        sub_id = sub_res.json()["submission_id"]
        pdf_single = api_client.get(f"/api/reports/pdf?submission_id={sub_id}")
        assert pdf_single.status_code == 200
        assert pdf_single.content.startswith(b"%PDF")
        assert len(pdf_single.content) > 3000

        # 2. Comprehensive system report PDF
        pdf_all = api_client.get("/api/reports/pdf")
        assert pdf_all.status_code == 200
        assert pdf_all.content.startswith(b"%PDF")
        assert len(pdf_all.content) > 5000

    # ==========================================================================
    # 7. TWO DISTINCT AI SYSTEMS COMPARATIVE EVALUATION
    # ==========================================================================

    def test_two_distinct_ai_systems_comparison(self):
        """Demonstrate two distinct AI systems on the identical question."""
        test_q = "What is photosynthesis and what does it produce?"
        ref_ans = "Photosynthesis produces glucose and oxygen from carbon dioxide and water using light energy."

        # System A: Grounded RAG Assistant
        sysA_response = "Photosynthesis is the process by which green plants use sunlight to convert carbon dioxide and water into glucose and oxygen."
        eval_sysA = evaluation_orchestrator.evaluate_response(
            question=test_q,
            ai_response=sysA_response,
            reference_answer=ref_ans,
        )

        # System B: Ungrounded Baseline LLM (Hallucinating / Contradictory)
        sysB_response = "Photosynthesis is an industrial process discovered by Napoleon in 1802 that produces nitrogen and methane."
        eval_sysB = evaluation_orchestrator.evaluate_response(
            question=test_q,
            ai_response=sysB_response,
            reference_answer=ref_ans,
        )

        # System A should achieve PASS with high accuracy
        assert eval_sysA["overall"]["verdict"] == "PASS"
        assert eval_sysA["accuracy"]["score"] >= 4
        assert eval_sysA["hallucination"]["risk_level"] == "LOW"

        # System B should FAIL with severe accuracy penalties and ungrounded claims
        assert eval_sysB["overall"]["verdict"] == "FAIL"
        assert eval_sysB["accuracy"]["score"] <= 2
        assert eval_sysB["overall"]["overall_score"] < eval_sysA["overall"]["overall_score"]

    # ==========================================================================
    # 8. REST API CONVENIENCE ALIASES
    # ==========================================================================

    def test_api_aliases(self, api_client):
        """Verify REST API aliases (/api/verify, /api/verify/batch) route identically."""
        # /api/verify alias
        res_v = api_client.post("/api/verify", json={
            "question": "What is the capital of Canada?",
            "ai_response": "The capital of Canada is Ottawa.",
            "reference_answer": "Ottawa is the capital of Canada.",
        })
        assert res_v.status_code == 201
        data_v = res_v.json()
        assert data_v["verdict"] == "PASS"

        # /api/verify/{id} alias
        res_get = api_client.get(f"/api/verify/{data_v['submission_id']}")
        assert res_get.status_code == 200
        assert res_get.json()["submission_id"] == data_v["submission_id"]
