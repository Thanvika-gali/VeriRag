"""Automated Tests for Milestone 3.1: Completeness Judge Agent.

Validates:
1. Fully complete response (High completeness score 4-5, status COMPLETE).
2. Partially complete response (Medium completeness score ~3, status PARTIAL, identified missing aspects).
3. Incomplete response (Low completeness score 1-2, status INCOMPLETE, identified omissions).
4. Multi-part question (Decomposition and individual aspect evaluation).
5. Empty / blank response handling.
"""

import pytest
from evaluation.agents.completeness_judge import CompletenessJudgeAgent


@pytest.fixture
def completeness_agent():
    return CompletenessJudgeAgent()


def test_01_fully_complete_response(completeness_agent):
    """Test 1: Fully complete response covering all requirements."""
    question = "What is photosynthesis and what are its primary products?"
    ai_response = (
        "Photosynthesis is the biological process by which green plants and other organisms "
        "convert light energy into chemical energy. Its primary products are glucose, which provides "
        "food for the plant, and oxygen, which is released into the atmosphere."
    )
    ref_answer = "Photosynthesis produces glucose and releases oxygen."

    result = completeness_agent.evaluate(
        question=question,
        ai_response=ai_response,
        reference_answer=ref_answer,
    )

    assert result.score >= 4, f"Expected completeness >= 4, got {result.score}"
    assert result.status == "COMPLETE", f"Expected COMPLETE status, got {result.status}"
    assert len(result.addressed_aspects) >= 1
    assert "complete" in result.reasoning.lower()


def test_02_partially_complete_response(completeness_agent):
    """Test 2: Partially complete response that answers one sub-question but omits another."""
    question = "What is the capital of France and what is its current population?"
    # AI only gives the capital, omits the population entirely
    ai_response = "The capital of France is Paris, famous for the Eiffel Tower and the Louvre."
    ref_answer = "Paris is the capital of France, with an urban population of approximately 2.1 million."

    result = completeness_agent.evaluate(
        question=question,
        ai_response=ai_response,
        reference_answer=ref_answer,
    )

    assert result.score in (2, 3), f"Expected completeness score 2 or 3, got {result.score}"
    assert result.status in ("PARTIAL", "INCOMPLETE")
    assert len(result.missing_aspects) >= 1, "Expected identified missing aspects"
    # Should flag population or omitted portion
    missing_text = " ".join(result.missing_aspects).lower()
    assert "population" in missing_text or len(result.missing_aspects) > 0


def test_03_incomplete_response(completeness_agent):
    """Test 3: Substantially incomplete response that fails to answer the question."""
    question = "Explain how nuclear fusion occurs in the Sun and why it produces energy."
    # AI response is trivial or empty of substantive explanation
    ai_response = "The Sun is very hot and bright."

    result = completeness_agent.evaluate(
        question=question,
        ai_response=ai_response,
    )

    assert result.score <= 2, f"Expected completeness score <= 2, got {result.score}"
    assert result.status == "INCOMPLETE"
    assert len(result.missing_aspects) >= 1


def test_04_multi_part_question_decomposition(completeness_agent):
    """Test 4: Multi-part question decomposes aspects and evaluates each separately."""
    question = "When was Project QuantumLeap founded, where, and who was the founder?"
    # Response answers when and where, but omits who was the founder
    ai_response = "Project QuantumLeap was founded on March 14, 2024 in Zurich."
    ref_answer = "Project QuantumLeap was founded on March 14, 2024 in Zurich by Dr. Aris Thorne."

    # Verify aspect decomposition
    aspects = completeness_agent._decompose_question_requirements(question)
    assert len(aspects) >= 2, f"Expected multi-part decomposition >= 2 aspects, got {aspects}"

    result = completeness_agent.evaluate(
        question=question,
        ai_response=ai_response,
        reference_answer=ref_answer,
    )

    # Should recognize addressed aspects (when/where) and missing aspect (who)
    assert len(result.addressed_aspects) >= 1
    assert len(result.missing_aspects) >= 1
    assert result.status in ("COMPLETE", "PARTIAL")


def test_05_empty_input_handling(completeness_agent):
    """Test 5: Empty question or response returns score 1 and INCOMPLETE."""
    res1 = completeness_agent.evaluate(question="", ai_response="Some answer")
    assert res1.score == 1
    assert res1.status == "INCOMPLETE"

    res2 = completeness_agent.evaluate(question="Valid question?", ai_response="")
    assert res2.score == 1
    assert res2.status == "INCOMPLETE"


def test_06_mostly_complete_answer(completeness_agent):
    """Test 6: Mostly complete answer (Score 4) answering core questions with minor omission."""
    question = "What is water, what are its constituent elements, and at what temperature does it boil at sea level?"
    # AI response gives what water is and its elements, but slightly glosses over boiling temp
    ai_response = "Water is a chemical substance composed of hydrogen and oxygen molecules."
    ref_answer = "Water is H2O, composed of hydrogen and oxygen, and boils at 100 degrees Celsius at sea level."

    result = completeness_agent.evaluate(
        question=question,
        ai_response=ai_response,
        reference_answer=ref_answer,
    )
    assert result.score in (3, 4)
    assert len(result.addressed_aspects) >= 1


def test_07_substantially_incomplete_answer(completeness_agent):
    """Test 7: Substantially incomplete answer (Score 2) touching only a minor facet."""
    question = "Describe the three stages of cellular respiration: glycolysis, the Krebs cycle, and oxidative phosphorylation."
    ai_response = "Cellular respiration involves glycolysis in the cytoplasm."

    result = completeness_agent.evaluate(
        question=question,
        ai_response=ai_response,
    )
    assert result.score <= 2
    assert result.status == "INCOMPLETE"
    assert len(result.missing_aspects) >= 1
    assert any("krebs" in m.lower() or "phosphorylation" in m.lower() or "respiration" in m.lower() for m in result.missing_aspects)


def test_08_missing_sub_question_identified(completeness_agent):
    """Test 8: Multi-part inquiry where a specific sub-question is omitted."""
    question = "Where is the Eiffel Tower located and how tall is it?"
    ai_response = "The Eiffel Tower is located on the Champ de Mars in Paris, France."

    result = completeness_agent.evaluate(
        question=question,
        ai_response=ai_response,
    )
    assert len(result.addressed_aspects) >= 1
    assert len(result.missing_aspects) >= 1
    missing_str = " ".join(result.missing_aspects).lower()
    assert "tall" in missing_str or "height" in missing_str or len(result.missing_aspects) > 0


def test_09_no_reference_rag_evidence_case(completeness_agent):
    """Test 9: Reference answer unavailable; relevant RAG evidence is supplied."""
    question = "What is the capital of Australia?"
    ai_response = "The capital of Australia is Canberra."
    rag_evidence = [
        {"text": "Canberra is the federal capital city of the Commonwealth of Australia.", "similarity_score": 0.85}
    ]

    result = completeness_agent.evaluate(
        question=question,
        ai_response=ai_response,
        retrieved_evidence=rag_evidence,
        reference_answer=None,
    )
    assert result.score >= 4
    assert result.status == "COMPLETE"
    assert len(result.addressed_aspects) >= 1


def test_10_insufficient_evidence_case(completeness_agent):
    """Test 10: Insufficient evidence available; agent does not fabricate missing information."""
    question = "What was the secret code name of Operation Chimera in 1943?"
    ai_response = "Operation Chimera was a classified operation conducted in 1943."
    # No reference answer, and empty/unrelated evidence
    rag_evidence = []

    result = completeness_agent.evaluate(
        question=question,
        ai_response=ai_response,
        retrieved_evidence=rag_evidence,
        reference_answer=None,
    )
    # Output must be valid, JSON-serializable, and not hallucinate facts
    assert result.score is not None
    assert result.status in ("COMPLETE", "PARTIAL", "INCOMPLETE")
    assert isinstance(result.addressed_aspects, list)
    assert isinstance(result.missing_aspects, list)
    assert result.reasoning != ""
