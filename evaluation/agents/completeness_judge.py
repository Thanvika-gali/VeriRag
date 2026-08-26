"""Completeness Judge Agent Interface (Milestone 2+ Specification).

Responsibility:
Checks whether all key aspects, sub-questions, and constraints of the user's prompt were fully addressed.
"""

from typing import Any, Dict, Optional


class CompletenessJudgeAgent:
    """Interface for evaluating multi-faceted question completeness and coverage."""

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name
        self.status = "placeholder_m2"

    def evaluate(
        self,
        question: str,
        ai_response: str,
        reference_answer: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Placeholder evaluation method to be implemented in Milestone 2."""
        return {
            "agent": "CompletenessJudgeAgent",
            "status": "not_implemented_m1",
            "message": "Completeness evaluation will be activated in Milestone 2.",
            "completeness_score": None,
            "missing_aspects": [],
            "reasoning": None,
        }
