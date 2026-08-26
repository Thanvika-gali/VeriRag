"""Relevance Judge Agent Interface (Milestone 2+ Specification).

Responsibility:
Determines whether the AI-generated response directly and appropriately answers the user's prompt/question.
"""

from typing import Any, Dict, Optional


class RelevanceJudgeAgent:
    """Interface for evaluating question-response topical relevance and intent fulfillment."""

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name
        self.status = "placeholder_m2"

    def evaluate(
        self,
        question: str,
        ai_response: str,
        context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Placeholder evaluation method to be implemented in Milestone 2."""
        return {
            "agent": "RelevanceJudgeAgent",
            "status": "not_implemented_m1",
            "message": "Relevance evaluation will be activated in Milestone 2.",
            "score": None,
            "reasoning": None,
        }
