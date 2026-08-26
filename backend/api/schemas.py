"""Pydantic schemas for VeriRAG Evaluation API."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EvaluationSubmissionRequest(BaseModel):
    """Evaluation submission payload."""
    question: str = Field(..., min_length=1, description="Question or prompt submitted by the user.")
    ai_response: str = Field(..., min_length=1, description="AI-generated response to be validated.")
    reference_answer: Optional[str] = Field(
        default=None,
        description="Optional ground truth or reference answer."
    )
    source_document: Optional[str] = Field(
        default=None,
        description="Optional raw text or extracted document content."
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Number of relevant evidence chunks to retrieve."
    )


class RetrievedEvidenceItem(BaseModel):
    """Schema representing an individual retrieved evidence chunk."""
    chunk_id: str
    text: str
    dataset_name: str
    similarity_score: float = Field(..., description="Cosine similarity score (0.0 to 1.0).")
    distance: float = Field(..., description="Raw vector distance.")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EvaluationSubmissionResponse(BaseModel):
    """Evaluation submission response with retrieved evidence."""
    submission_id: str
    question: str
    ai_response: str
    reference_answer: Optional[str] = None
    source_document: Optional[str] = None
    retrieved_evidence: List[RetrievedEvidenceItem] = Field(default_factory=list)
    status: str = "completed"
    created_at: str
    notice: str = (
        "Milestone 1 Scope: Evidence retrieval active. "
        "Judge agents (Relevance, Accuracy, Hallucination, Completeness, Verdict) are scheduled for Milestone 2."
    )


class SubmissionListItem(BaseModel):
    """Summary item for submission history listing."""
    submission_id: str
    question: str
    ai_response_snippet: str
    evidence_count: int
    created_at: str


class DocumentUploadResponse(BaseModel):
    """Response returned when a document is uploaded and extracted."""
    filename: str
    file_type: str
    extracted_text: str
    char_count: int
    word_count: int


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    database_connected: bool
    vector_store_ready: bool
    total_indexed_chunks: int
    embedding_model: str
    timestamp: str
