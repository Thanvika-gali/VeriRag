"""Pydantic schemas for VeriRAG Evaluation System."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class RelevanceResult(BaseModel):
    """Structured result from Relevance Judge Agent (1-5 scale)."""
    score: int = Field(..., ge=1, le=5, description="1 to 5 relevance score.")
    label: str = Field(..., description="Human-readable rating label.")
    reasoning: str = Field(..., description="Detailed justification for relevance score.")


class AccuracyResult(BaseModel):
    """Structured result from Accuracy Judge Agent (1-5 scale)."""
    score: int = Field(..., ge=1, le=5, description="1 to 5 accuracy score.")
    label: str = Field(..., description="Human-readable rating label.")
    reasoning: str = Field(..., description="Detailed justification for factual accuracy score.")
    supporting_evidence: List[str] = Field(
        default_factory=list,
        description="Reference evidence passages used to verify factual claims.",
    )


class ClaimEvaluation(BaseModel):
    """Evaluation of an individual factual assertion decomposed from AI response."""
    claim: str = Field(..., description="Atomic factual statement extracted from AI response.")
    status: Literal["SUPPORTED", "UNSUPPORTED", "CONTRADICTED", "INSUFFICIENT_EVIDENCE"] = Field(
        ...,
        description="Verification status against reference evidence.",
    )
    reasoning: str = Field(..., description="Explanation of why this claim was assigned this status.")
    evidence: Optional[str] = Field(
        default=None,
        description="Specific retrieved passage or reference text that supports or refutes the claim.",
    )


class HallucinationResult(BaseModel):
    """Structured result from Hallucination Detection Agent."""
    hallucination_status: Literal["NONE", "PARTIAL", "HIGH"] = Field(
        ...,
        description="Overall hallucination severity classification.",
    )
    risk_level: Literal["LOW", "MEDIUM", "HIGH"] = Field(
        ...,
        description="Hallucination risk assessment level.",
    )
    flagged_claims: List[ClaimEvaluation] = Field(
        default_factory=list,
        description="Decomposed claims and their individual grounding states.",
    )
    summary: str = Field(
        default="",
        description="Concise summary of hallucination detection findings.",
    )


class CompletenessResult(BaseModel):
    """Structured result from Completeness Judge Agent (1-5 scale)."""
    score: int = Field(..., ge=1, le=5, description="1 to 5 completeness score.")
    status: Literal["COMPLETE", "PARTIAL", "INCOMPLETE"] = Field(
        ...,
        description="Categorical completeness status: COMPLETE | PARTIAL | INCOMPLETE",
    )
    addressed_aspects: List[str] = Field(
        default_factory=list,
        description="Aspects and sub-questions adequately covered by the response.",
    )
    missing_aspects: List[str] = Field(
        default_factory=list,
        description="Unaddressed aspects, unanswered sub-questions, or insufficient details.",
    )
    reasoning: str = Field(..., description="Detailed explanation of the completeness evaluation.")


class VerdictResult(BaseModel):
    """Structured synthesis result from Verdict Agent."""
    overall_score: int = Field(..., ge=0, le=100, description="Weighted aggregated score from 0 to 100.")
    verdict: Literal["PASS", "NEEDS IMPROVEMENT", "FAIL", "REVIEW"] = Field(
        ...,
        description="Final verdict: PASS, NEEDS IMPROVEMENT, or FAIL.",
    )
    dimension_scores: Dict[str, Any] = Field(
        default_factory=dict,
        description="Raw scores for all 4 dimensions.",
    )
    normalized_scores: Dict[str, float] = Field(
        default_factory=dict,
        description="Normalized 0.0 to 1.0 scores for each dimension.",
    )
    weighted_contributions: Dict[str, float] = Field(
        default_factory=dict,
        description="Points contributed by each dimension to the overall score.",
    )
    weights: Dict[str, float] = Field(
        default_factory=dict,
        description="Configured weights used for aggregation.",
    )
    major_strengths: List[str] = Field(
        default_factory=list,
        description="Key positive aspects and grounded strengths identified.",
    )
    major_issues: List[str] = Field(
        default_factory=list,
        description="Critical issues, contradictions, or significant omissions.",
    )
    consolidated_reasoning: str = Field(
        ...,
        description="Consolidated reasoning explaining why the final verdict was reached.",
    )
    verdict_reasoning: str = Field(
        default="",
        description="Alias for consolidated reasoning for backward compatibility.",
    )
    critical_issues_detected: bool = Field(
        default=False,
        description="Flag indicating if a critical failure prevented a PASS verdict.",
    )
    critical_override_applied: bool = Field(
        default=False,
        description="Explicit indicator if critical override was triggered.",
    )
    critical_override_reason: str = Field(
        default="",
        description="Detailed explanation of why critical override was applied.",
    )


class OverallEvaluation(BaseModel):
    """Synthesized evaluation score and transparent verdict."""
    overall_score: int = Field(..., ge=0, le=100, description="Overall weighted score from 0 to 100.")
    verdict: Literal["PASS", "NEEDS IMPROVEMENT", "REVIEW", "FAIL"] = Field(
        ...,
        description="Rule-based transparent verdict: PASS, NEEDS IMPROVEMENT, REVIEW, or FAIL.",
    )
    verdict_reasoning: str = Field(..., description="Transparent explanation of the verdict determination.")
    accuracy_weight: float = Field(default=0.35, description="Weight assigned to accuracy.")
    hallucination_safety_weight: float = Field(default=0.30, description="Weight assigned to hallucination safety.")
    relevance_weight: float = Field(default=0.20, description="Weight assigned to relevance.")
    completeness_weight: float = Field(default=0.15, description="Weight assigned to completeness.")
    dimension_scores: Dict[str, Any] = Field(default_factory=dict)
    critical_override_applied: bool = Field(default=False)
    critical_override_reason: str = Field(default="")
    normalized_scores: Dict[str, float] = Field(default_factory=dict)
    weighted_contributions: Dict[str, float] = Field(default_factory=dict)
    major_strengths: List[str] = Field(default_factory=list)
    major_issues: List[str] = Field(default_factory=list)
    consolidated_reasoning: str = Field(default="")

