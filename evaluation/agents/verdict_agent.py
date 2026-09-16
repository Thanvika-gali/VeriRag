"""Verdict Agent.

Provides synthesis interface for multi-agent evaluation outputs.
"""

from typing import Any, Dict, Optional
from evaluation.schemas import AccuracyResult, HallucinationResult, OverallEvaluation, RelevanceResult


class VerdictAgent:
    """Interface for multi-agent synthesis and final structured verdict generation."""

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name

    def synthesize_verdict(
        self,
        relevance_result: Dict[str, Any],
        accuracy_result: Dict[str, Any],
        hallucination_result: Dict[str, Any],
        completeness_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Synthesize dimensions into final verdict and score."""
        acc_score = accuracy_result.get("score", 3) or 3
        rel_score = relevance_result.get("score", 3) or 3
        hal_status = hallucination_result.get("hallucination_status", "NONE")
        risk_level = hallucination_result.get("risk_level", "LOW")

        acc_norm = acc_score / 5.0
        rel_norm = rel_score / 5.0
        hal_safety = 1.0 if hal_status == "NONE" else 0.5 if hal_status == "PARTIAL" else 0.0

        overall_score = int(round(((acc_norm * 0.40) + (rel_norm * 0.30) + (hal_safety * 0.30)) * 100))

        if rel_score <= 2 or acc_score <= 2 or risk_level == "HIGH":
            verdict = "FAIL"
            reasoning = "Evaluation detected low topical relevance, factual contradiction, or high hallucination risk."
        elif rel_score >= 4 and acc_score >= 4 and risk_level == "LOW" and overall_score >= 75:
            verdict = "PASS"
            reasoning = "High accuracy and relevance with grounded assertions."
        else:
            verdict = "REVIEW"
            reasoning = "Partial correctness, moderate relevance, or unverified claims requiring review."

        return {
            "overall_score": overall_score,
            "verdict": verdict,
            "reasoning": reasoning,
            "confidence_score": round(overall_score / 100.0, 2),
            "summary": reasoning,
        }


# Global instance
verdict_agent = VerdictAgent()
