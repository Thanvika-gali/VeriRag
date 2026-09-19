"""FastAPI REST endpoints for VeriRAG."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from backend.api.schemas import (
    AnalyticsResponse,
    BatchEvaluationResult,
    BatchJobListItem,
    BatchValidationPreview,
    DatasetInfo,
    DocumentUploadResponse,
    EvaluationSubmissionRequest,
    EvaluationSubmissionResponse,
    HealthResponse,
    KnowledgeBaseStatsResponse,
    RetrievedEvidenceItem,
    SubmissionListItem,
)
from backend.database.sqlite_db import db_instance
from backend.rag.retriever import retriever
from backend.rag.vector_store import vector_store
from backend.services.batch_service import batch_evaluation_service
from backend.services.doc_parser import DocumentParser
from backend.services.evaluation_service import evaluation_service
from evaluation.orchestrator import evaluation_orchestrator

router = APIRouter(prefix="/api", tags=["Evaluation & Knowledge Base"])


@router.get("/health", response_model=HealthResponse)
def health_check():
    """System health check reporting database, vector store, and multi-agent subsystem status."""
    db_connected = True
    try:
        db_instance.list_submissions(limit=1)
    except Exception:
        db_connected = False

    vec_ready = True
    total_chunks = 0
    try:
        total_chunks = vector_store.count()
    except Exception:
        vec_ready = False

    agent_statuses = {
        "RAG / Evidence Retrieval": "ONLINE" if (retriever is not None and vec_ready) else "OFFLINE",
        "Relevance Judge Agent": "ONLINE" if (evaluation_orchestrator and evaluation_orchestrator.relevance_judge) else "OFFLINE",
        "Accuracy Judge Agent": "ONLINE" if (evaluation_orchestrator and evaluation_orchestrator.accuracy_judge) else "OFFLINE",
        "Hallucination Detection Agent": "ONLINE" if (evaluation_orchestrator and evaluation_orchestrator.hallucination_judge) else "OFFLINE",
        "Completeness Judge Agent": "ONLINE" if (evaluation_orchestrator and evaluation_orchestrator.completeness_judge) else "OFFLINE",
        "Verdict Agent": "ONLINE" if (evaluation_orchestrator and evaluation_orchestrator.verdict_agent) else "OFFLINE",
        "Evaluation Orchestrator": "ONLINE" if evaluation_orchestrator else "OFFLINE",
        "Batch Evaluation": "ONLINE" if batch_evaluation_service else "OFFLINE",
    }

    return HealthResponse(
        status="ok",
        version="2.0.0",
        database_connected=db_connected,
        vector_store_ready=vec_ready,
        total_indexed_chunks=total_chunks,
        embedding_model="all-MiniLM-L6-v2",
        timestamp=datetime.now(timezone.utc).isoformat(),
        agent_statuses=agent_statuses,
    )


@router.post(
    "/submissions",
    response_model=EvaluationSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit an AI response for evaluation",
)
def create_submission(request: EvaluationSubmissionRequest):
    """Validate request, retrieve relevant knowledge base evidence, and execute multi-agent evaluation."""
    try:
        response = evaluation_service.process_submission(request)
        return response
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        ) from val_err
    except Exception as exc:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to complete evaluation: {str(exc)}",
        ) from exc


@router.get(
    "/submissions",
    response_model=List[SubmissionListItem],
    summary="List past evaluation submissions",
)
def list_submissions(
    limit: int = Query(default=50, ge=1, le=100),
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
    """Retrieve full submission record, evidence, and evaluation metrics."""
    sub = db_instance.get_submission(submission_id)
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Submission '{submission_id}' not found.",
        )

    evidence_items = []
    for e in sub.get("retrieved_evidence", []):
        dataset = str(e.get("dataset_name") or e.get("source") or "Knowledge Base")
        sim = float(e.get("similarity_score") if e.get("similarity_score") is not None else e.get("similarity", 0.0))
        dist = float(e.get("distance", 0.0))
        tier = e.get("match_tier") or ("strong" if sim >= 0.70 else "moderate" if sim >= 0.50 else "weak")
        evidence_items.append(
            RetrievedEvidenceItem(
                chunk_id=str(e.get("chunk_id", "")),
                text=str(e.get("text", "")),
                dataset_name=dataset,
                source=dataset,
                similarity_score=sim,
                similarity=sim,
                distance=dist,
                match_tier=tier,
                metadata=dict(e.get("metadata", {})),
            )
        )

    eval_data = sub.get("evaluation_result") or {}
    overall = eval_data.get("overall", {})
    relevance = eval_data.get("relevance", {})
    accuracy = eval_data.get("accuracy", {})
    hallucination = eval_data.get("hallucination", {})
    completeness = eval_data.get("completeness", {})
    verdict_details = sub.get("verdict_details") or eval_data.get("verdict_details", {})

    top_sim = max([e.similarity_score for e in evidence_items], default=0.0)

    # Fallback to stored columns if eval_data dict is empty
    overall_score = sub.get("overall_score") or overall.get("overall_score") or 0
    verdict = sub.get("verdict") or overall.get("verdict") or "NEEDS IMPROVEMENT"
    verdict_reasoning = overall.get("verdict_reasoning") or ""

    if not relevance and sub.get("relevance_score") is not None:
        relevance = {"score": sub["relevance_score"], "label": f"{sub['relevance_score']}/5", "reasoning": "Retrieved from archive"}
    if not accuracy and sub.get("accuracy_score") is not None:
        accuracy = {"score": sub["accuracy_score"], "label": f"{sub['accuracy_score']}/5", "reasoning": "Retrieved from archive", "supporting_evidence": []}
    if not hallucination and sub.get("hallucination_risk") is not None:
        hallucination = {"hallucination_status": "NONE" if sub["hallucination_risk"] == "LOW" else "PARTIAL", "risk_level": sub["hallucination_risk"], "flagged_claims": [], "summary": "Retrieved from archive"}
    if not completeness and sub.get("completeness_score") is not None:
        completeness = {"score": sub["completeness_score"], "status": "COMPLETE" if sub["completeness_score"] >= 4 else "PARTIAL" if sub["completeness_score"] == 3 else "INCOMPLETE", "addressed_aspects": [], "missing_aspects": [], "reasoning": "Retrieved from archive"}

    return EvaluationSubmissionResponse(
        success=True,
        submission_id=sub["id"],
        question=sub["question"],
        ai_response=sub["ai_response"],
        reference_answer=sub["reference_answer"],
        source_document=sub["source_document"],
        retrieved_evidence=evidence_items,
        match_status="strong" if top_sim >= 0.70 else "moderate" if top_sim >= 0.50 else "weak",
        match_label="Strong evidence found" if top_sim >= 0.70 else "Some supporting evidence found" if top_sim >= 0.50 else "Limited evidence found",
        match_message="",
        top_similarity=round(top_sim, 4),
        overall_score=overall_score,
        verdict=verdict,
        verdict_reasoning=verdict_reasoning,
        relevance=relevance,
        accuracy=accuracy,
        hallucination=hallucination,
        completeness=completeness,
        verdict_details=verdict_details,
        status=sub["status"],
        created_at=sub["created_at"],
    )


@router.get(
    "/analytics",
    response_model=AnalyticsResponse,
    summary="Retrieve aggregate evaluation analytics",
)
def get_analytics():
    """Return aggregated real metrics calculated from stored evaluation records."""
    metrics = db_instance.get_analytics()
    return AnalyticsResponse(**metrics)


@router.get(
    "/knowledge-base/stats",
    response_model=KnowledgeBaseStatsResponse,
    summary="Retrieve knowledge base indexed statistics",
)
def get_knowledge_base_stats():
    """Return live dataset counts and status from ChromaDB vector store."""
    total_chunks = vector_store.count()

    # Query exact dataset representation from ChromaDB collection metadata
    tqa_count = 0
    squad_count = 0
    custom_count = 0
    try:
        tqa_res = vector_store.collection.get(where={"dataset_name": "TruthfulQA"})
        tqa_count = len(tqa_res.get("ids", []))
    except Exception:
        tqa_count = 0

    try:
        squad_res = vector_store.collection.get(where={"dataset_name": "SQuAD"})
        squad_count = len(squad_res.get("ids", []))
    except Exception:
        squad_count = 0

    try:
        custom_res = vector_store.collection.get(where={"dataset_name": "Custom"})
        custom_count = len(custom_res.get("ids", []))
    except Exception:
        custom_count = 0

    # Ensure counts reconcile dynamically from actual collection metadata
    if total_chunks > 0 and tqa_count == 0 and squad_count == 0:
        try:
            all_meta = vector_store.collection.get().get("metadatas", []) or []
            tqa_count = sum(1 for m in all_meta if m and m.get("dataset_name") == "TruthfulQA")
            squad_count = sum(1 for m in all_meta if m and m.get("dataset_name") == "SQuAD")
            custom_count = sum(1 for m in all_meta if m and m.get("dataset_name") == "Custom")
        except Exception:
            pass

    datasets = [
        DatasetInfo(
            name="TruthfulQA",
            chunks=tqa_count,
            status="Active & Indexed",
            source_type="Adversarial Benchmark / Misconceptions",
            description="Evaluates whether responses replicate popular false assertions and factual myths.",
        ),
        DatasetInfo(
            name="SQuAD",
            chunks=squad_count,
            status="Active & Indexed",
            source_type="Reading Comprehension / Wikipedia",
            description="Fact-based reference contexts extracted from high-quality encyclopedic articles.",
        ),
        DatasetInfo(
            name="Custom Documents",
            chunks=custom_count,
            status="Supported via Runtime Upload" if custom_count == 0 else "Active & Indexed",
            source_type="User-provided TXT, PDF, MD",
            description="Dynamic runtime reference context parsed directly during evaluation.",
        ),
    ]

    return KnowledgeBaseStatsResponse(
        total_indexed_chunks=total_chunks,
        embedding_model="all-MiniLM-L6-v2",
        status="Online & Persistent",
        datasets=datasets,
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


@router.get(
    "/evidence/search",
    summary="Search evidence library across indexed chunks",
)
def search_evidence(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(default=10, ge=1, le=50),
    dataset: Optional[str] = Query(default=None),
):
    """Semantic vector search across indexed knowledge base chunks with entity relevance classification."""
    from knowledge_base.embeddings.embedder import embedder

    clean_q = q.strip()
    if not clean_q:
        return {
            "query": q,
            "dataset_filter": "All",
            "embedding_model": embedder.model_name,
            "embedding_dimension": 384,
            "total_indexed_chunks": vector_store.count(),
            "results_count": 0,
            "results": [],
        }

    # Derive embedding vector
    emb = embedder.embed_text(clean_q)
    dimension = len(emb)

    # Normalize dataset filter mapping
    where_clause = None
    if dataset:
        clean_ds = dataset.strip()
        ds_lower = clean_ds.lower()
        if ds_lower not in ("all", "all datasets", "all knowledge", "none", ""):
            if "truthful" in ds_lower:
                where_clause = {"dataset_name": "TruthfulQA"}
            elif "squad" in ds_lower:
                where_clause = {"dataset_name": "SQuAD"}
            elif "custom" in ds_lower:
                where_clause = {"dataset_name": "Custom"}
            else:
                where_clause = {"dataset_name": clean_ds}

    # Fetch results from ChromaDB collection
    raw_results = vector_store.query(
        query_embedding=emb,
        n_results=limit,
        where=where_clause,
    )

    # Extract discriminating terms from query for relevance classification
    generic_words = {
        "what", "is", "are", "was", "were", "the", "a", "an", "and", "or", "in", "of", "to", "for",
        "on", "with", "at", "by", "from", "can", "you", "does", "did", "how", "why", "who", "which",
        "happen", "happens", "happening", "between", "eating", "eat", "eats", "when", "into", "over"
    }
    discriminating_terms = [
        w.strip("?,.!;:\"'()").lower() for w in clean_q.split()
        if len(w) > 3 and w.lower() not in generic_words
    ]

    enriched_results = []
    for item in raw_results:
        sim = float(item.get("similarity_score", 0.0))
        dist = float(item.get("distance", 0.0))
        meta = item.get("metadata", {}) or {}
        text = str(item.get("text", ""))
        text_lower = text.lower()

        # Determine match tier
        if sim >= 0.65:
            match_tier = "Strong"
        elif sim >= 0.50:
            match_tier = "Moderate"
        else:
            match_tier = "Weak"

        # Classify evidence relevance
        if sim >= 0.65:
            if discriminating_terms and any(t in text_lower for t in discriminating_terms):
                relevance_classification = "DIRECTLY RELEVANT"
            elif not discriminating_terms:
                relevance_classification = "DIRECTLY RELEVANT"
            else:
                relevance_classification = "RELATED BUT NOT SUFFICIENT"
        elif sim >= 0.50:
            if discriminating_terms and any(t in text_lower for t in discriminating_terms):
                relevance_classification = "DIRECTLY RELEVANT"
            else:
                relevance_classification = "RELATED BUT NOT SUFFICIENT"
        elif sim >= 0.35:
            relevance_classification = "WEAK"
        else:
            relevance_classification = "IRRELEVANT"

        # Extract structured question and answer from metadata or text
        question = str(meta.get("question") or "")
        answer = str(meta.get("best_answer") or meta.get("answer") or "")

        # If question is not in metadata, inspect if text starts with "Question: "
        if not question and "Question: " in text:
            try:
                parts = text.split("\n", 1)
                for line in text.split("\n"):
                    if line.startswith("Question:"):
                        question = line.replace("Question:", "").strip()
                    elif line.startswith("Best Verified Answer:"):
                        answer = line.replace("Best Verified Answer:", "").strip()
            except Exception:
                pass

        enriched_results.append({
            "chunk_id": item.get("chunk_id", ""),
            "dataset_name": item.get("dataset_name") or meta.get("dataset_name", "Knowledge Base"),
            "text": text,
            "similarity_score": round(sim, 4),
            "distance": round(dist, 4),
            "match_tier": match_tier,
            "relevance_classification": relevance_classification,
            "question": question,
            "answer": answer,
            "metadata": meta,
        })

    return {
        "query": clean_q,
        "dataset_filter": dataset or "All",
        "embedding_model": embedder.model_name,
        "embedding_dimension": dimension,
        "total_indexed_chunks": vector_store.count(),
        "results_count": len(enriched_results),
        "results": enriched_results,
    }


# ==============================================================================
# Milestone 3 — Batch Evaluation Endpoints
# ==============================================================================

@router.post(
    "/batch/validate",
    response_model=BatchValidationPreview,
    status_code=status.HTTP_200_OK,
    summary="Validate and preview batch CSV before execution",
)
async def validate_batch_csv(file: UploadFile = File(...)):
    """Parse and pre-validate CSV columns, normalize headers, and return preview rows."""
    filename = file.filename or "batch_upload.csv"
    if not filename.lower().endswith((".csv", ".txt")):
        return BatchValidationPreview(
            is_valid=False,
            filename=filename,
            total_rows=0,
            valid_rows_count=0,
            invalid_rows_count=0,
            error_message="Invalid file format. Please upload a CSV file (.csv).",
        )

    try:
        raw_bytes = await file.read()
        return batch_evaluation_service.validate_csv_preview(raw_bytes, filename=filename)
    except Exception as exc:
        return BatchValidationPreview(
            is_valid=False,
            filename=filename,
            total_rows=0,
            valid_rows_count=0,
            invalid_rows_count=0,
            error_message=f"Unable to read or parse CSV: {str(exc)}",
        )


@router.post(
    "/batch/evaluate",
    response_model=BatchEvaluationResult,
    status_code=status.HTTP_200_OK,
    summary="Upload CSV for batch AI response verification",
)
async def evaluate_batch_csv(
    file: UploadFile = File(...),
    dataset_filter: Optional[str] = Query(default=None),
    top_k: int = Query(default=5, ge=1, le=20),
):
    """Parse CSV, validate columns and rows, and execute complete verification pipeline for each record."""
    filename = file.filename or "batch_upload.csv"
    if not filename.lower().endswith((".csv", ".txt")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Please upload a CSV file (.csv).",
        )

    try:
        raw_bytes = await file.read()
        if not raw_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty.",
            )

        result = batch_evaluation_service.execute_batch(
            raw_bytes=raw_bytes,
            filename=filename,
            dataset_filter=dataset_filter,
            top_k=top_k,
        )
        return result
    except HTTPException:
        raise
    except Exception as exc:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch evaluation failure: {str(exc)}",
        ) from exc


@router.get(
    "/batch/{batch_id}",
    response_model=BatchEvaluationResult,
    summary="Retrieve batch evaluation results by ID",
)
def get_batch_results(batch_id: str):
    """Retrieve full batch evaluation summary, statistics, and individual records."""
    batch_res = batch_evaluation_service.get_batch_result(batch_id)
    if not batch_res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch evaluation job '{batch_id}' not found.",
        )
    return batch_res


@router.get(
    "/batch",
    response_model=List[BatchJobListItem],
    summary="List past batch evaluation jobs",
)
def list_batch_jobs(
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
):
    """Retrieve history of batch evaluation jobs."""
    return db_instance.list_batch_jobs(limit=limit, offset=offset)



