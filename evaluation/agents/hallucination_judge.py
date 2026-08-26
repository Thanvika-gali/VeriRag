"""Hallucination Detection Agent Interface (Milestone 2+ Specification).

Responsibility:
Performs claim-level decomposition and identifies unsupported, fabricated, or contradicted claims.
"""

from typing import Any, Dict, List, Optional


class HallucinationDetectionAgent:
    """Interface for claim-level hallucination and fabrication detection."""

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name
        self.status = "placeholder_m2"

    def evaluate(
        self,
        ai_response: str,
        retrieved_evidence: List[Dict[str, Any]],
        source_document: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Placeholder evaluation method to be implemented in Milestone 2."""
        return {
            "agent": "HallucinationDetectionAgent",
            "status": "not_implemented_m1",
            "message": "Hallucination detection will be activated in Milestone 2.",
            "hallucination_rate": None,
            "detected_hallucinations": [],
            "reasoning": None,
        }
