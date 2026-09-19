"""Comprehensive Audit Test Suite for PROOFRAG Milestones 1-3.

Validates:
1. Critical Override behavior on factual contradictions (e.g. Great Wall of China).
2. Completeness Judge Agent across Scenarios A through G.
3. Fail Scenarios 1 through 5 (Contradictions, Fabrications, Off-topic, Low Accuracy).
4. Batch CSV Parsing & Robustness (BOM, whitespace, delimiter auto-detection, invalid row handling).
"""

import pytest
from evaluation.agents.completeness_judge import CompletenessJudgeAgent
from evaluation.agents.verdict_agent import VerdictAgent
from evaluation.agents.relevance_judge import RelevanceJudgeAgent
from evaluation.agents.accuracy_judge import AccuracyJudgeAgent
from evaluation.agents.hallucination_judge import HallucinationDetectionAgent
from evaluation.orchestrator import EvaluationOrchestrator
from backend.services.batch_service import (
    clean_header_name,
    detect_delimiter,
    decode_csv_content,
    parse_and_validate_csv,
)


@pytest.fixture(scope="module")
def orchestrator():
    return EvaluationOrchestrator()


@pytest.fixture(scope="module")
def completeness_agent():
    return CompletenessJudgeAgent()


@pytest.fixture(scope="module")
def verdict_agent():
    return VerdictAgent()


# =====================================================================
# 1. CRITICAL OVERRIDE VALIDATION
# =====================================================================

def test_critical_override_great_wall_contradiction(orchestrator):
    """Test Critical Override: Direct contradiction of established truth forces FAIL."""
    question = "Can the Great Wall of China be seen from the Moon with the naked eye?"
    ai_response = "Yes, the Great Wall of China can easily be seen from the Moon with the naked eye due to its great length."

    result = orchestrator.evaluate_response(
        question=question,
        ai_response=ai_response,
        top_k=5,
    )

    # Must trigger critical override and force FAIL
    assert result["overall"]["critical_override_applied"] is True, (
        "Critical override should be applied when a claim is contradicted by TruthfulQA evidence."
    )
    assert result["verdict"] == "FAIL", f"Expected FAIL verdict, got {result['verdict']}"
    assert result["overall"]["critical_override_reason"], "Critical override reason must not be empty"

    # Hallucination check must identify contradicted claim
    claims = result["hallucination"].get("flagged_claims", [])
    contradicted = [c for c in claims if c.get("status") == "CONTRADICTED"]
    assert len(contradicted) >= 1, "At least one claim must be classified as CONTRADICTED"


# =====================================================================
# 2. COMPLETENESS JUDGE SCENARIOS (A - G)
# =====================================================================

def test_completeness_scenario_a_complete_coverage(completeness_agent):
    """Scenario A: Multi-part question with complete coverage across all parts."""
    question = "What is photosynthesis, where does it occur, and what does it produce?"
    ai_response = (
        "Photosynthesis is the process that converts solar energy into chemical energy. "
        "It occurs inside the chloroplasts of plant cells and produces glucose and oxygen."
    )
    res = completeness_agent.evaluate(question, ai_response)
    assert res.score >= 4, f"Expected score >= 4, got {res.score}"
    assert res.status == "COMPLETE"
    assert len(res.addressed_aspects) >= 2


def test_completeness_scenario_b_partial_coverage(completeness_agent):
    """Scenario B: Multi-part question with partial coverage (omits parts)."""
    question = "What is the capital of Australia, when was it founded, and what is its climate?"
    # Only mentions capital
    ai_response = "The capital of Australia is Canberra."
    res = completeness_agent.evaluate(question, ai_response)
    assert res.score <= 3, f"Expected score <= 3, got {res.score}"
    assert res.status in ("PARTIAL", "INCOMPLETE")
    assert len(res.missing_aspects) >= 1


def test_completeness_scenario_c_single_focus_complete(completeness_agent):
    """Scenario C: Single-focus inquiry with clear, direct answer."""
    question = "What is the boiling point of water at standard sea-level pressure?"
    ai_response = "The boiling point of water at standard atmospheric pressure is 100 degrees Celsius (212 degrees Fahrenheit)."
    res = completeness_agent.evaluate(question, ai_response)
    assert res.score >= 4
    assert res.status == "COMPLETE"


def test_completeness_scenario_d_irrelevant_response(completeness_agent):
    """Scenario D: Inquiry asks for X, response answers unrelated Y."""
    question = "How do solar panels generate electricity from sunlight?"
    ai_response = "Baking chocolate chip cookies requires flour, butter, brown sugar, eggs, and chocolate chips."
    res = completeness_agent.evaluate(question, ai_response)
    assert res.score <= 2
    assert res.status == "INCOMPLETE"


def test_completeness_scenario_e_evasive_response(completeness_agent):
    """Scenario E: Evasive or refusing answer."""
    question = "What are the key causes of the French Revolution?"
    ai_response = "I cannot help with historical questions because my knowledge base is limited."
    res = completeness_agent.evaluate(question, ai_response)
    assert res.score <= 2
    assert res.status == "INCOMPLETE"


def test_completeness_scenario_f_verbose_with_complete_answer(completeness_agent):
    """Scenario F: Verbose answer that nonetheless covers the inquiry thoroughly."""
    question = "What is the speed of light in vacuum?"
    ai_response = (
        "In physics, electromagnetic radiation travels at an exact constant in vacuum. "
        "The speed of light is precisely 299,792,458 meters per second, often rounded to 300,000 km/s. "
        "Albert Einstein based his theory of special relativity on the constancy of this speed."
    )
    res = completeness_agent.evaluate(question, ai_response)
    assert res.score >= 4
    assert res.status == "COMPLETE"


def test_completeness_scenario_g_missing_key_aspects(completeness_agent):
    """Scenario G: 'When, where, and by whom' inquiry with two omitted aspects."""
    question = "When was Project Apollo announced, where did President Kennedy give the speech, and in what year?"
    # Only provides year, misses location and details
    ai_response = "Project Apollo was conducted in the 1960s."
    res = completeness_agent.evaluate(question, ai_response)
    assert res.score <= 3
    assert res.status in ("PARTIAL", "INCOMPLETE")
    assert len(res.missing_aspects) >= 1


# =====================================================================
# 3. FAIL SCENARIOS (1 - 5)
# =====================================================================

def test_fail_scenario_1_factual_contradiction(verdict_agent):
    """FAIL Scenario 1: Severe factual contradiction with evidence forces FAIL."""
    from evaluation.schemas import AccuracyResult, HallucinationResult, RelevanceResult, CompletenessResult

    acc = AccuracyResult(score=1, label="INCORRECT", reasoning="Directly contradicts ground truth.")
    hal = HallucinationResult(
        risk_level="HIGH",
        hallucination_status="HIGH",
        flagged_claims=[{"claim": "The moon is made of cheddar", "status": "CONTRADICTED", "reasoning": "Factual contradiction."}],
        summary="Contradicted by factual evidence.",
    )
    rel = RelevanceResult(score=5, label="HIGHLY RELEVANT", reasoning="On topic.")
    comp = CompletenessResult(score=4, status="COMPLETE", reasoning="Answers the question.")

    verdict = verdict_agent.synthesize_verdict(
        accuracy_result=acc.model_dump(),
        hallucination_result=hal.model_dump(),
        relevance_result=rel.model_dump(),
        completeness_result=comp.model_dump(),
    )

    assert verdict.verdict == "FAIL"
    assert verdict.critical_override_applied is True
    assert "contradiction" in verdict.critical_override_reason.lower()


def test_fail_scenario_2_complete_fabrication(verdict_agent):
    """FAIL Scenario 2: Zero accuracy, high hallucination score."""
    from evaluation.schemas import AccuracyResult, HallucinationResult, RelevanceResult, CompletenessResult

    acc = AccuracyResult(score=1, label="INCORRECT", reasoning="Completely ungrounded and false.")
    hal = HallucinationResult(
        risk_level="HIGH",
        hallucination_status="HIGH",
        flagged_claims=[{"claim": "Olympus Prime has 3M residents", "status": "UNSUPPORTED", "reasoning": "Ungrounded entity."}],
        summary="No grounding found.",
    )
    rel = RelevanceResult(score=3, label="PARTIALLY RELEVANT", reasoning="Mentions Mars.")
    comp = CompletenessResult(score=3, status="PARTIAL", reasoning="Vague claim.")

    verdict = verdict_agent.synthesize_verdict(
        accuracy_result=acc.model_dump(),
        hallucination_result=hal.model_dump(),
        relevance_result=rel.model_dump(),
        completeness_result=comp.model_dump(),
    )

    assert verdict.verdict == "FAIL"
    assert verdict.critical_override_applied is True


def test_fail_scenario_3_completely_off_topic(verdict_agent):
    """FAIL Scenario 3: Irrelevant response scoring below passing threshold."""
    from evaluation.schemas import AccuracyResult, HallucinationResult, RelevanceResult, CompletenessResult

    acc = AccuracyResult(score=2, label="INCORRECT", reasoning="Irrelevant statements.")
    hal = HallucinationResult(risk_level="LOW", hallucination_status="NONE", summary="No hallucinations.")
    rel = RelevanceResult(score=1, label="IRRELEVANT", reasoning="Does not address query.")
    comp = CompletenessResult(score=1, status="INCOMPLETE", reasoning="Nothing addressed.")

    verdict = verdict_agent.synthesize_verdict(
        accuracy_result=acc.model_dump(),
        hallucination_result=hal.model_dump(),
        relevance_result=rel.model_dump(),
        completeness_result=comp.model_dump(),
    )

    assert verdict.verdict == "FAIL"
    assert verdict.overall_score < 60


def test_fail_scenario_4_multiple_contradictions(verdict_agent):
    """FAIL Scenario 4: Multiple contradictory claims."""
    from evaluation.schemas import AccuracyResult, HallucinationResult, RelevanceResult, CompletenessResult

    acc = AccuracyResult(score=1, label="INCORRECT", reasoning="Multiple false assertions.")
    hal = HallucinationResult(
        risk_level="HIGH",
        hallucination_status="HIGH",
        flagged_claims=[
            {"claim": "Claim 1", "status": "CONTRADICTED", "reasoning": "Contradiction 1"},
            {"claim": "Claim 2", "status": "CONTRADICTED", "reasoning": "Contradiction 2"},
        ],
        summary="Multiple contradictions detected.",
    )
    rel = RelevanceResult(score=4, label="RELEVANT", reasoning="On topic.")
    comp = CompletenessResult(score=4, status="COMPLETE", reasoning="All points addressed.")

    verdict = verdict_agent.synthesize_verdict(
        accuracy_result=acc.model_dump(),
        hallucination_result=hal.model_dump(),
        relevance_result=rel.model_dump(),
        completeness_result=comp.model_dump(),
    )

    assert verdict.verdict == "FAIL"
    assert verdict.critical_override_applied is True


def test_fail_scenario_5_withheld_pass_on_low_accuracy_high_risk(verdict_agent):
    """FAIL Scenario 5: Withheld pass if accuracy <= 2 or hallucination == HIGH even if math reaches 80."""
    from evaluation.schemas import AccuracyResult, HallucinationResult, RelevanceResult, CompletenessResult

    acc = AccuracyResult(score=2, label="POOR", reasoning="Low factual accuracy.")
    hal = HallucinationResult(risk_level="HIGH", hallucination_status="HIGH", summary="High risk.")
    rel = RelevanceResult(score=5, label="HIGHLY RELEVANT", reasoning="Direct match.")
    comp = CompletenessResult(score=5, status="COMPLETE", reasoning="Covers all aspects.")

    verdict = verdict_agent.synthesize_verdict(
        accuracy_result=acc.model_dump(),
        hallucination_result=hal.model_dump(),
        relevance_result=rel.model_dump(),
        completeness_result=comp.model_dump(),
    )

    # Even if other scores are 5, PASS must never be granted
    assert verdict.verdict != "PASS"
    assert verdict.verdict == "FAIL"
    assert verdict.critical_override_applied is True


# =====================================================================
# 4. BATCH CSV ROBUSTNESS & EDGE CASES
# =====================================================================

def test_csv_utf8_bom_stripping():
    """Validates that UTF-8 BOM (\ufeff) is cleanly stripped from headers and content."""
    bom_csv = "\ufeffquestion,ai_response\n\"What is DNA?\",\"DNA is deoxyribonucleic acid.\""
    raw_bytes = bom_csv.encode("utf-8")

    decoded = decode_csv_content(raw_bytes)
    assert not decoded.startswith("\ufeff"), "BOM was not stripped during decoding"

    clean_hdr = clean_header_name("\ufeff\"Question \"")
    assert clean_hdr == "question"


def test_csv_whitespace_and_mixed_case_headers():
    """Validates that headers with whitespace, quotes, or mixed casing resolve properly."""
    assert clean_header_name("  Query  ") == "query"
    assert clean_header_name("\"AI_Response\"") == "ai_response"
    assert clean_header_name("  Prompt   ") == "prompt"

    csv_text = "  Question  ,   AI Response   \n\"What is RNA?\",\"RNA is ribonucleic acid.\""
    valid_rows, val_errs, invalid_rows, col_map = parse_and_validate_csv(csv_text)

    assert len(valid_rows) == 1
    assert valid_rows[0]["question"] == "What is RNA?"
    assert valid_rows[0]["ai_response"] == "RNA is ribonucleic acid."
    assert col_map.get("question") == "Question"
    assert col_map.get("ai_response") == "AI Response"


def test_csv_semicolon_delimiter_detection():
    """Validates automatic detection of semicolon-delimited CSVs."""
    csv_text = "question;ai_response;reference_answer\nWhat is ATP?;ATP is adenosine triphosphate;Energy carrier"
    delim = detect_delimiter(csv_text)
    assert delim == ";", f"Expected semicolon delimiter, got {delim}"

    valid_rows, val_errs, invalid_rows, col_map = parse_and_validate_csv(csv_text)
    assert len(valid_rows) == 1
    assert valid_rows[0]["question"] == "What is ATP?"
    assert valid_rows[0]["ai_response"] == "ATP is adenosine triphosphate"


def test_csv_invalid_row_handling_without_halting_batch():
    """Validates that batches continue processing valid rows when invalid rows exist."""
    csv_text = (
        "question,ai_response\n"
        "\"Valid Q1\",\"Valid Ans1\"\n"
        "\"\",\"Missing Question Ans\"\n"  # Invalid: missing question
        "\"Valid Q2\",\"Valid Ans2\"\n"
        "\"Missing Answer Q\",\n"         # Invalid: missing answer
        "\"Valid Q3\",\"Valid Ans3\"\n"
    )

    valid_rows, val_errs, invalid_rows, col_map = parse_and_validate_csv(csv_text)

    assert len(valid_rows) == 3, f"Expected 3 valid rows, got {len(valid_rows)}"
    assert len(invalid_rows) == 2, f"Expected 2 invalid rows, got {len(invalid_rows)}"

    row_nums = [inv.row_number for inv in invalid_rows]
    assert 3 in row_nums, "Row 3 should be flagged as invalid"
    assert 5 in row_nums, "Row 5 should be flagged as invalid"
