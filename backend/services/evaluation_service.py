"""Evaluation Service Orchestrator.

Coordinates submission validation, evidence retrieval, multi-agent evaluation execution,
persistence to SQLite database, and structured response construction.
"""

from typing import Any, Dict, List, Optional
from backend.api.schemas import (
    EvaluationSubmissionRequest,
    EvaluationSubmissionResponse,
    RetrievedEvidenceItem,
)
from backend.database.sqlite_db import SubmissionDB, db_instance
from backend.rag.retriever import EvidenceRetriever, retriever
from evaluation.orchestrator import EvaluationOrchestrator, evaluation_orchestrator


class EvaluationService:
    """Coordinates submission processing, multi-agent evaluation, and SQLite persistence."""

    def __init__(
        self,
        db: Optional[SubmissionDB] = None,
        rag_retriever: Optional[EvidenceRetriever] = None,
        orchestrator: Optional[EvaluationOrchestrator] = None,
    ):
        self.db = db or db_instance
        self.retriever = rag_retriever or retriever
        self.orchestrator = orchestrator or evaluation_orchestrator

    def process_submission(
        self, request: EvaluationSubmissionRequest
    ) -> EvaluationSubmissionResponse:
        """Process evaluation submission:

        1. Validate Question & AI Response.
        2. Run multi-agent orchestrator:
           - Dual-query candidate expansion and semantic retrieval.
           - Relevance Judge Agent.
           - Accuracy Judge Agent (prioritizing user reference info).
           - Hallucination Detection Agent (with claim decomposition).
           - Transparent weighted score aggregation and rule-based verdict.
        3. Persist submission and complete evaluation metrics to SQLite.
        4. Return structured response.
        """
        top_k = request.top_k or 5

        # Execute full evaluation orchestration pipeline
        eval_output = self.orchestrator.evaluate_response(
            question=request.question,
            ai_response=request.ai_response,
            reference_answer=request.reference_answer,
            source_document=request.source_document,
            dataset_filter=request.dataset_filter,
            top_k=top_k,
        )

        raw_evidence = eval_output.get("evidence", [])
        relevance = eval_output.get("relevance", {})
        accuracy = eval_output.get("accuracy", {})
        hallucination = eval_output.get("hallucination", {})
        overall = eval_output.get("overall", {})

        overall_score = overall.get("overall_score", 0)
        verdict = overall.get("verdict", "REVIEW")
        verdict_reasoning = overall.get("verdict_reasoning", "")

        # Convert evidence to Pydantic models
        evidence_items: List[RetrievedEvidenceItem] = []
        for item in raw_evidence:
            dataset = str(item.get("dataset_name", "Knowledge Base"))
            sim = float(item.get("similarity_score", 0.0))
            dist = float(item.get("distance", 0.0))
            tier = item.get("match_tier") or ("strong" if sim >= 0.70 else "moderate" if sim >= 0.50 else "weak")

            evidence_items.append(
                RetrievedEvidenceItem(
                    chunk_id=str(item["chunk_id"]),
                    text=str(item["text"]),
                    dataset_name=dataset,
                    source=dataset,
                    similarity_score=sim,
                    similarity=sim,
                    distance=dist,
                    match_tier=tier,
                    metadata=dict(item.get("metadata", {})),
                )
            )

        # Convert raw additional matches to Pydantic models
        raw_additional = eval_output.get("additional_matches", [])
        additional_items: List[RetrievedEvidenceItem] = []
        for item in raw_additional:
            dataset = str(item.get("dataset_name", "Knowledge Base"))
            sim = float(item.get("similarity_score", 0.0))
            dist = float(item.get("distance", 0.0))
            tier = item.get("match_tier") or ("strong" if sim >= 0.70 else "moderate" if sim >= 0.50 else "weak")

            additional_items.append(
                RetrievedEvidenceItem(
                    chunk_id=str(item["chunk_id"]),
                    text=str(item["text"]),
                    dataset_name=dataset,
                    source=dataset,
                    similarity_score=sim,
                    similarity=sim,
                    distance=dist,
                    match_tier=tier,
                    metadata=dict(item.get("metadata", {})),
                )
            )

        top_sim = max([e.similarity_score for e in evidence_items], default=0.0)

        if not evidence_items:
            match_status = "none"
            match_label = "No strong supporting evidence found"
            match_message = "No matching reference evidence was found in the reference knowledge base."
        elif top_sim >= 0.70:
            match_status = "strong"
            match_label = "Strong evidence found"
            match_message = "Strong supporting evidence was found in the reference knowledge base."
        elif top_sim >= 0.50:
            match_status = "moderate"
            match_label = "Some supporting evidence found"
            match_message = "Moderate supporting evidence was found matching the inquiry."
        else:
            match_status = "weak"
            match_label = "Limited evidence found"
            match_message = "No strong supporting evidence was found in the current reference knowledge base."

        # Save to SQLite database with full evaluation metrics
        saved_record = self.db.create_submission(
            question=request.question,
            ai_response=request.ai_response,
            reference_answer=request.reference_answer,
            source_document=request.source_document,
            retrieved_evidence=[e.model_dump() for e in evidence_items],
            status="completed",
            overall_score=overall_score,
            verdict=verdict,
            relevance_score=relevance.get("score"),
            accuracy_score=accuracy.get("score"),
            hallucination_risk=hallucination.get("risk_level"),
            evaluation_result=eval_output,
        )

        return EvaluationSubmissionResponse(
            success=True,
            submission_id=saved_record["id"],
            question=saved_record["question"],
            ai_response=saved_record["ai_response"],
            reference_answer=saved_record["reference_answer"],
            source_document=saved_record["source_document"],
            retrieved_evidence=evidence_items,
            additional_matches=additional_items,
            candidate_count=eval_output.get("candidate_count", len(evidence_items) + len(additional_items)),
            match_status=match_status,
            match_label=match_label,
            match_message=match_message,
            top_similarity=round(top_sim, 4),
            overall_score=overall_score,
            verdict=verdict,
            verdict_reasoning=verdict_reasoning,
            relevance=relevance,
            accuracy=accuracy,
            hallucination=hallucination,
            status="completed",
            created_at=saved_record["created_at"],
            notice="AI Response Validation active across reference knowledge base.",
        )


# Global singleton instance
evaluation_service = EvaluationService()
