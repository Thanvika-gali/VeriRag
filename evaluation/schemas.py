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


class OverallEvaluation(BaseModel):
    """Synthesized evaluation score and transparent verdict."""
    overall_score: int = Field(..., ge=0, le=100, description="Overall weighted score from 0 to 100.")
    verdict: Literal["PASS", "REVIEW", "FAIL"] = Field(
        ...,
        description="Rule-based transparent verdict: PASS, REVIEW, or FAIL.",
    )
    verdict_reasoning: str = Field(..., description="Transparent explanation of the verdict determination.")
    accuracy_weight: float = Field(default=0.40, description="Weight assigned to accuracy.")
    relevance_weight: float = Field(default=0.30, description="Weight assigned to relevance.")
    hallucination_safety_weight: float = Field(default=0.30, description="Weight assigned to hallucination safety.")
