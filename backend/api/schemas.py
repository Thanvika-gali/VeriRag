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
        description="Optional verified reference answer."
    )
    source_document: Optional[str] = Field(
        default=None,
        description="Optional raw text or extracted document content."
    )
    dataset_filter: Optional[str] = Field(
        default=None,
        description="Optional knowledge base dataset filter (e.g. TruthfulQA, SQuAD, All Knowledge)."
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
    source: str = Field(default="", description="Evidence source dataset or document name.")
    similarity: float = Field(default=0.0, description="Normalized similarity score.")
    similarity_score: float = Field(..., description="Cosine similarity score (0.0 to 1.0).")
    distance: float = Field(..., description="Raw vector distance.")
    match_tier: str = Field(default="moderate", description="Relevance match tier (strong, moderate, weak).")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EvaluationSubmissionResponse(BaseModel):
    """Evaluation submission response with retrieved evidence and agent evaluations."""
    success: bool = True
    submission_id: str
    question: str
    ai_response: str
    reference_answer: Optional[str] = None
    source_document: Optional[str] = None
    retrieved_evidence: List[RetrievedEvidenceItem] = Field(default_factory=list)
    additional_matches: List[RetrievedEvidenceItem] = Field(default_factory=list, description="Retrieved candidate chunks that were filtered out or excluded from primary evidence.")
    candidate_count: int = Field(default=0, description="Total candidate pool size queried from vector database.")
    match_status: str = Field(default="moderate", description="Overall match status: strong, moderate, weak, none.")
    match_label: str = Field(default="Some supporting evidence found", description="Human-readable match label.")
    match_message: str = Field(default="", description="Detailed match interpretation.")
    top_similarity: float = Field(default=0.0, description="Highest similarity score among retrieved evidence.")

    # Agent evaluation metrics
    overall_score: int = Field(default=0, description="Overall weighted score (0-100).")
    verdict: str = Field(default="REVIEW", description="Final verdict: PASS, NEEDS IMPROVEMENT, or FAIL.")
    verdict_reasoning: str = Field(default="", description="Explanation of final verdict.")
    relevance: Dict[str, Any] = Field(default_factory=dict, description="Relevance Judge Agent evaluation.")
    accuracy: Dict[str, Any] = Field(default_factory=dict, description="Accuracy Judge Agent evaluation.")
    hallucination: Dict[str, Any] = Field(default_factory=dict, description="Hallucination Detection Agent evaluation.")
    completeness: Dict[str, Any] = Field(default_factory=dict, description="Completeness Judge Agent evaluation.")
    verdict_details: Dict[str, Any] = Field(default_factory=dict, description="Verdict Agent detailed synthesis and contributions.")

    status: str = "completed"
    created_at: str
    notice: str = "AI Response Validation active across reference knowledge base."


class ErrorResponse(BaseModel):
    """Structured error response schema."""
    success: bool = False
    error: str
    detail: Optional[str] = None


class SubmissionListItem(BaseModel):
    """Summary item for submission history listing."""
    submission_id: str
    question: str
    ai_response_snippet: str
    evidence_count: int
    overall_score: Optional[int] = None
    verdict: Optional[str] = None
    accuracy_score: Optional[int] = None
    relevance_score: Optional[int] = None
    completeness_score: Optional[int] = None
    hallucination_risk: Optional[str] = None
    created_at: str


class BatchRecord(BaseModel):
    """Record representation in batch verification."""
    record_id: int
    submission_id: Optional[str] = None
    question: str
    ai_response: str
    reference_answer: Optional[str] = None
    source_information: Optional[str] = None
    status: str = "success"  # "success" | "error"
    error: Optional[str] = None
    accuracy_score: Optional[int] = None
    relevance_score: Optional[int] = None
    completeness_score: Optional[int] = None
    completeness_status: Optional[str] = None
    hallucination_risk: Optional[str] = None
    hallucination_status: Optional[str] = None
    overall_score: Optional[int] = None
    verdict: Optional[str] = None
    evaluation: Optional[Dict[str, Any]] = None


class BatchSummaryStats(BaseModel):
    """Aggregated statistics across batch evaluation records."""
    total_records: int
    successful_evaluations: int
    failed_evaluations: int
    pass_count: int
    needs_improvement_count: int
    fail_count: int
    average_accuracy: Optional[float] = None
    average_relevance: Optional[float] = None
    average_completeness: Optional[float] = None
    hallucination_flag_frequency: float = 0.0
    average_overall_score: Optional[float] = None


class InvalidRowDetail(BaseModel):
    """Structured invalid row explanation."""
    row_number: int
    error: str
    reason: str


class BatchEvaluationResult(BaseModel):
    """Comprehensive result of batch evaluation job."""
    success: bool = True
    batch_id: str
    filename: str
    total_records: int
    valid_records_count: int
    invalid_records_count: int
    validation_errors: List[str] = Field(default_factory=list)
    invalid_rows: List[InvalidRowDetail] = Field(default_factory=list)
    stats: BatchSummaryStats
    records: List[BatchRecord] = Field(default_factory=list)
    created_at: str


class BatchValidationPreview(BaseModel):
    """Result of pre-validating a batch CSV before execution."""
    is_valid: bool
    filename: str
    total_rows: int
    valid_rows_count: int
    invalid_rows_count: int
    detected_columns: Dict[str, str] = Field(default_factory=dict)
    missing_required_columns: List[str] = Field(default_factory=list)
    preview_rows: List[Dict[str, Any]] = Field(default_factory=list)
    invalid_rows: List[InvalidRowDetail] = Field(default_factory=list)
    error_message: Optional[str] = None


class BatchJobListItem(BaseModel):
    """Listing item for batch evaluation history."""
    batch_id: str
    filename: str
    total_records: int
    processed_records: int
    status: str
    stats: Optional[Dict[str, Any]] = None
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
    agent_statuses: Optional[Dict[str, str]] = None


class AnalyticsResponse(BaseModel):
    """Real computed metrics from evaluation database."""
    total_evaluations: int
    evidence_retrieved_count: int
    average_accuracy: Optional[float] = None
    average_relevance: Optional[float] = None
    average_completeness: Optional[float] = None
    average_hallucination_safety: Optional[float] = None
    average_overall_score: Optional[float] = None
    pass_count: int
    review_count: int
    fail_count: int
    hallucination_flag_count: int
    hallucination_frequency: Optional[float] = None
    has_data: bool


class DatasetInfo(BaseModel):
    """Information regarding an indexed dataset."""
    name: str
    chunks: int
    status: str
    source_type: str
    description: str


class KnowledgeBaseStatsResponse(BaseModel):
    """Real information about indexed reference knowledge."""
    total_indexed_chunks: int
    embedding_model: str
    status: str
    datasets: List[DatasetInfo]
