"""Evaluation Service Orchestrator for Milestone 1."""

from typing import Any, Dict, List, Optional
from backend.api.schemas import (
    EvaluationSubmissionRequest,
    EvaluationSubmissionResponse,
    RetrievedEvidenceItem,
)
from backend.database.sqlite_db import SubmissionDB, db_instance
from backend.rag.retriever import EvidenceRetriever, retriever


class EvaluationService:
    """Coordinates submission processing, SQLite persistence, and RAG evidence retrieval for M1."""

    def __init__(
        self,
        db: Optional[SubmissionDB] = None,
        rag_retriever: Optional[EvidenceRetriever] = None,
    ):
        self.db = db or db_instance
        self.retriever = rag_retriever or retriever

    def process_submission(
        self, request: EvaluationSubmissionRequest
    ) -> EvaluationSubmissionResponse:
        """Process evaluation submission:

        1. Receive Question & AI Response (+ optional Reference Answer & Source Document).
        2. Perform Semantic Retrieval against indexed Reference Knowledge Base.
        3. Persist submission record and retrieved evidence into SQLite.
        4. Return structured response with evidence metadata.
        """
        query_text = f"{request.question} {request.ai_response}".strip()
        top_k = request.top_k or 5

        # Query semantic retriever
        raw_evidence = self.retriever.retrieve(query=query_text, top_k=top_k)

        # Convert to Pydantic items
        evidence_items: List[RetrievedEvidenceItem] = []
        for item in raw_evidence:
            evidence_items.append(
                RetrievedEvidenceItem(
                    chunk_id=str(item["chunk_id"]),
                    text=str(item["text"]),
                    dataset_name=str(item["dataset_name"]),
                    similarity_score=float(item["similarity_score"]),
                    distance=float(item["distance"]),
                    metadata=dict(item.get("metadata", {})),
                )
            )

        # Save to SQLite database
        saved_record = self.db.create_submission(
            question=request.question,
            ai_response=request.ai_response,
            reference_answer=request.reference_answer,
            source_document=request.source_document,
            retrieved_evidence=[e.model_dump() for e in evidence_items],
            status="completed",
        )

        return EvaluationSubmissionResponse(
            submission_id=saved_record["id"],
            question=saved_record["question"],
            ai_response=saved_record["ai_response"],
            reference_answer=saved_record["reference_answer"],
            source_document=saved_record["source_document"],
            retrieved_evidence=evidence_items,
            status="completed",
            created_at=saved_record["created_at"],
        )


# Global singleton instance
evaluation_service = EvaluationService()
