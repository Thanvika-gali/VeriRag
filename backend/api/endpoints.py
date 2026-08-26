"""FastAPI REST endpoints for VeriRAG."""

from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from backend.api.schemas import (
    DocumentUploadResponse,
    EvaluationSubmissionRequest,
    EvaluationSubmissionResponse,
    HealthResponse,
    RetrievedEvidenceItem,
    SubmissionListItem,
)
from backend.database.sqlite_db import db_instance
from backend.rag.vector_store import vector_store
from backend.services.doc_parser import DocumentParser
from backend.services.evaluation_service import evaluation_service


router = APIRouter(prefix="/api", tags=["Evaluation & Knowledge Base"])


@router.get("/health", response_model=HealthResponse)
def health_check():
    """System health check reporting database and vector store status."""
    db_connected = True
    try:
        db_instance.list_submissions(limit=1)
    except Exception:
        db_connected = False

    total_chunks = vector_store.count()
    return HealthResponse(
        status="ok",
        version="1.0.0-m1",
        database_connected=db_connected,
        vector_store_ready=True,
        total_indexed_chunks=total_chunks,
        embedding_model="all-MiniLM-L6-v2",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.post(
    "/submissions",
    response_model=EvaluationSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit an AI response for evidence grounding evaluation",
)
def create_submission(request: EvaluationSubmissionRequest):
    """Validate request, retrieve relevant knowledge base evidence, and store in SQLite."""
    try:
        response = evaluation_service.process_submission(request)
        return response
    except Exception as exc:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing evaluation submission: {str(exc)} | {traceback.format_exc()}",
        ) from exc


@router.get(
    "/submissions",
    response_model=List[SubmissionListItem],
    summary="List past evaluation submissions",
)
def list_submissions(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """Retrieve paginated list of past submissions."""
    return db_instance.list_submissions(limit=limit, offset=offset)


@router.get(
    "/submissions/{submission_id}",
    response_model=EvaluationSubmissionResponse,
    summary="Retrieve evaluation submission details by ID",
)
def get_submission(submission_id: str):
    """Retrieve full submission record and its associated retrieved evidence."""
    sub = db_instance.get_submission(submission_id)
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Submission '{submission_id}' not found.",
        )

    evidence_items = [
        RetrievedEvidenceItem(
            chunk_id=str(e.get("chunk_id", "")),
            text=str(e.get("text", "")),
            dataset_name=str(e.get("dataset_name", "Unknown")),
            similarity_score=float(e.get("similarity_score", 0.0)),
            distance=float(e.get("distance", 0.0)),
            metadata=dict(e.get("metadata", {})),
        )
        for e in sub.get("retrieved_evidence", [])
    ]

    return EvaluationSubmissionResponse(
        submission_id=sub["id"],
        question=sub["question"],
        ai_response=sub["ai_response"],
        reference_answer=sub["reference_answer"],
        source_document=sub["source_document"],
        retrieved_evidence=evidence_items,
        status=sub["status"],
        created_at=sub["created_at"],
    )


@router.post(
    "/upload-document",
    response_model=DocumentUploadResponse,
    summary="Extract text from uploaded TXT or PDF document",
)
async def upload_document(file: UploadFile = File(...)):
    """Upload a TXT or PDF file and extract its text content."""
    try:
        content = await file.read()
        parsed = DocumentParser.parse_file(file.filename, content)
        return DocumentUploadResponse(**parsed)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to process uploaded document: {str(exc)}",
        ) from exc
