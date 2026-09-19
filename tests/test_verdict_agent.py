"""Automated Tests for Milestone 3.2: Verdict Agent & Configurable Weighted Scoring.

Validates:
1. High scores across all dimensions -> PASS.
2. Moderate scores -> NEEDS IMPROVEMENT.
3. Low scores -> FAIL.
4. High score but severe hallucination -> critical issue blocks PASS.
5. High relevance but low accuracy -> must not produce PASS solely due to high relevance.
6. Complete but factually incorrect -> completeness high while accuracy low -> FAIL.
7. Weighted contributions calculation check.
"""

import pytest
from evaluation.agents.verdict_agent import VerdictAgent


@pytest.fixture
def verdict_agent():
    return VerdictAgent()


def test_01_high_scores_across_dimensions_pass(verdict_agent):
    """Test 1: High scores across all dimensions -> PASS."""
    res = verdict_agent.synthesize_verdict(
        accuracy_result={"score": 5, "reasoning": "Fully correct"},
        relevance_result={"score": 5, "reasoning": "Fully relevant"},
        hallucination_result={"hallucination_status": "NONE", "risk_level": "LOW", "flagged_claims": []},
        completeness_result={"score": 5, "status": "COMPLETE", "addressed_aspects": ["A", "B"], "missing_aspects": []},
    )

    assert res.verdict == "PASS"
    assert res.overall_score >= 80
    assert len(res.major_strengths) >= 2
    assert not res.critical_issues_detected


def test_02_moderate_scores_needs_improvement(verdict_agent):
    """Test 2: Moderate scores -> NEEDS IMPROVEMENT."""
    res = verdict_agent.synthesize_verdict(
        accuracy_result={"score": 3, "reasoning": "Partially correct"},
        relevance_result={"score": 4, "reasoning": "Mostly relevant"},
        hallucination_result={"hallucination_status": "PARTIAL", "risk_level": "MEDIUM", "flagged_claims": []},
        completeness_result={"score": 3, "status": "PARTIAL", "addressed_aspects": ["A"], "missing_aspects": ["B"]},
    )

    assert res.verdict == "NEEDS IMPROVEMENT"
    assert 60 <= res.overall_score < 80


def test_03_low_scores_fail(verdict_agent):
    """Test 3: Low scores across dimensions -> FAIL."""
    res = verdict_agent.synthesize_verdict(
        accuracy_result={"score": 1, "reasoning": "Completely incorrect"},
        relevance_result={"score": 1, "reasoning": "Completely irrelevant"},
        hallucination_result={"hallucination_status": "HIGH", "risk_level": "HIGH", "flagged_claims": []},
        completeness_result={"score": 1, "status": "INCOMPLETE", "addressed_aspects": [], "missing_aspects": ["All"]},
    )

    assert res.verdict == "FAIL"
    assert res.overall_score < 60
    assert len(res.major_issues) >= 2


def test_04_high_score_with_severe_hallucination_critical_override(verdict_agent):
    """Test 4: High score but severe hallucination -> Critical issue must prevent PASS."""
    # Even if relevance and completeness are 5/5
    res = verdict_agent.synthesize_verdict(
        accuracy_result={"score": 3, "reasoning": "Mixed accuracy"},
        relevance_result={"score": 5, "reasoning": "High topical relevance"},
        hallucination_result={
            "hallucination_status": "HIGH",
            "risk_level": "HIGH",
            "flagged_claims": [{"claim": "Made up fact", "status": "CONTRADICTED"}],
        },
        completeness_result={"score": 5, "status": "COMPLETE", "addressed_aspects": ["All"], "missing_aspects": []},
    )

    # Must NOT produce PASS!
    assert res.verdict != "PASS"
    assert res.verdict == "FAIL"
    assert res.critical_issues_detected is True
    assert any("contradiction" in issue.lower() or "hallucination" in issue.lower() for issue in res.major_issues)


def test_05_high_relevance_low_accuracy_must_not_pass(verdict_agent):
    """Test 5: High relevance but low accuracy -> must not produce PASS solely because relevance is high."""
    res = verdict_agent.synthesize_verdict(
        accuracy_result={"score": 1, "reasoning": "Completely false misconception"},
        relevance_result={"score": 5, "reasoning": "Directly addresses the misconception question"},
        hallucination_result={
            "hallucination_status": "HIGH",
            "risk_level": "HIGH",
            "flagged_claims": [{"claim": "Direct contradiction", "status": "CONTRADICTED"}],
        },
        completeness_result={"score": 5, "status": "COMPLETE", "addressed_aspects": ["Question"], "missing_aspects": []},
    )

    assert res.verdict == "FAIL"
    assert res.critical_issues_detected is True


def test_06_complete_but_factually_incorrect(verdict_agent):
    """Test 6: Complete coverage (5/5) but factually incorrect (Accuracy 1/5) -> Must FAIL."""
    res = verdict_agent.synthesize_verdict(
        accuracy_result={"score": 1, "reasoning": "Contains false information contradicting reference"},
        relevance_result={"score": 4, "reasoning": "Topically aligned"},
        hallucination_result={"hallucination_status": "HIGH", "risk_level": "HIGH", "flagged_claims": []},
        completeness_result={"score": 5, "status": "COMPLETE", "addressed_aspects": ["All aspects covered with false info"], "missing_aspects": []},
    )

    assert res.verdict == "FAIL"
    assert res.dimension_scores["completeness"] == 5
    assert res.dimension_scores["accuracy"] == 1
    assert res.critical_issues_detected is True


def test_07_weighted_contributions_integrity(verdict_agent):
    """Test 7: Verify weighted contributions sum up approximately to overall score."""
    res = verdict_agent.synthesize_verdict(
        accuracy_result={"score": 4, "reasoning": "Mostly correct"},
        relevance_result={"score": 4, "reasoning": "Mostly relevant"},
        hallucination_result={"hallucination_status": "NONE", "risk_level": "LOW", "flagged_claims": []},
        completeness_result={"score": 4, "status": "COMPLETE", "addressed_aspects": ["Aspects"], "missing_aspects": []},
    )

    contribs = res.weighted_contributions
    total_contrib = sum(contribs.values())
    # Should equal overall score within rounding margin of 1 pt
    assert abs(total_contrib - res.overall_score) <= 1.5
    assert contribs["accuracy"] > 0
    assert contribs["hallucination"] > 0
    assert contribs["relevance"] > 0
    assert contribs["completeness"] > 0


def test_08_boundary_thresholds_exact_cases(verdict_agent):
    """Test 8: Explicitly validate all required boundary score conditions: 100, 80, 79, 60, 59, 0."""
    # Boundary 100: Max scores across all dimensions -> PASS
    res_100 = verdict_agent.synthesize_verdict(
        accuracy_result={"score": 5},
        relevance_result={"score": 5},
        hallucination_result={"hallucination_status": "NONE", "risk_level": "LOW"},
        completeness_result={"score": 5, "status": "COMPLETE"},
    )
    assert res_100.overall_score == 100
    assert res_100.verdict == "PASS"

    # Boundary 80: Exactly at PASS threshold (80-100) -> PASS
    # acc=4 (28pts) + hal=1.0 (30pts) + rel=4 (16pts) + comp=2 (6pts) = 80 pts
    res_80 = verdict_agent.synthesize_verdict(
        accuracy_result={"score": 4},
        relevance_result={"score": 4},
        hallucination_result={"hallucination_status": "NONE", "risk_level": "LOW"},
        completeness_result={"score": 2, "status": "INCOMPLETE"},
    )
    assert res_80.overall_score == 80
    assert res_80.verdict == "PASS"

    # Boundary 79: Just below PASS threshold (60-79) -> NEEDS IMPROVEMENT
    # acc=4 (28) + hal=1.0 (30) + rel=3.5 -> rel=3 (12) + comp=3 (9) = 79 pts
    res_79 = verdict_agent.synthesize_verdict(
        accuracy_result={"score": 4},
        relevance_result={"score": 3},
        hallucination_result={"hallucination_status": "NONE", "risk_level": "LOW"},
        completeness_result={"score": 3, "status": "PARTIAL"},
    )
    assert res_79.overall_score == 79
    assert res_79.verdict == "NEEDS IMPROVEMENT"

    # Boundary 60: Exactly at NEEDS IMPROVEMENT threshold (60-79) -> NEEDS IMPROVEMENT
    # acc=3 (21) + hal=0.5 (15) + rel=3 (12) + comp=4 (12) = 60 pts
    res_60 = verdict_agent.synthesize_verdict(
        accuracy_result={"score": 3},
        relevance_result={"score": 3},
        hallucination_result={"hallucination_status": "PARTIAL", "risk_level": "MEDIUM"},
        completeness_result={"score": 4, "status": "COMPLETE"},
    )
    assert res_60.overall_score == 60
    assert res_60.verdict == "NEEDS IMPROVEMENT"

    # Boundary 59: Just below NEEDS IMPROVEMENT threshold (<60) -> FAIL
    # acc=3 (21) + hal=0.5 (15) + rel=4 (16) + comp=2 (6) = 58-59 pts
    res_59 = verdict_agent.synthesize_verdict(
        accuracy_result={"score": 3},
        relevance_result={"score": 4},
        hallucination_result={"hallucination_status": "PARTIAL", "risk_level": "MEDIUM"},
        completeness_result={"score": 2, "status": "INCOMPLETE"},
    )
    assert res_59.overall_score in (58, 59)
    assert res_59.verdict == "FAIL"

    # Boundary 0: Complete failure across all dimensions -> FAIL
    res_0 = verdict_agent.synthesize_verdict(
        accuracy_result={"score": 0},
        relevance_result={"score": 0},
        hallucination_result={"hallucination_status": "HIGH", "risk_level": "HIGH", "flagged_claims": [{"status": "CONTRADICTED"}]},
        completeness_result={"score": 0, "status": "INCOMPLETE"},
    )
    assert res_0.overall_score == 0
    assert res_0.verdict == "FAIL"


def test_09_configurable_thresholds_and_weights():
    """Test 9: Configurable verdict thresholds and custom dimension weighting."""
    custom_agent = VerdictAgent(
        weight_accuracy=0.40,
        weight_hallucination=0.30,
        weight_relevance=0.15,
        weight_completeness=0.15,
        pass_threshold=85,
        needs_improvement_threshold=65,
    )
    assert custom_agent.pass_threshold == 85
    assert custom_agent.needs_improvement_threshold == 65

    # A score of 80 with pass_threshold=85 should now be NEEDS IMPROVEMENT instead of PASS
    res = custom_agent.synthesize_verdict(
        accuracy_result={"score": 4},
        relevance_result={"score": 4},
        hallucination_result={"hallucination_status": "NONE", "risk_level": "LOW"},
        completeness_result={"score": 2, "status": "INCOMPLETE"},
    )
    assert res.overall_score < 85
    assert res.verdict == "NEEDS IMPROVEMENT"
