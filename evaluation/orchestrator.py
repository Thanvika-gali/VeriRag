"""Evaluation Orchestrator.

Coordinates complete verification workflow:
1. Input validation
2. Evidence retrieval via ChromaDB RAG
3. Relevance Judge Agent execution
4. Accuracy Judge Agent execution
5. Hallucination Detection Agent execution
6. Completeness Judge Agent execution (Milestone 3)
7. Transparent Verdict Agent synthesis with configurable 4-dimension weighted scoring
"""

import logging
from typing import Any, Dict, List, Optional
from backend.config import (
    WEIGHT_ACCURACY,
    WEIGHT_COMPLETENESS,
    WEIGHT_HALLUCINATION,
    WEIGHT_RELEVANCE,
)
from backend.rag.retriever import EvidenceRetriever, retriever
from evaluation.agents.accuracy_judge import AccuracyJudgeAgent, accuracy_judge
from evaluation.agents.completeness_judge import CompletenessJudgeAgent, completeness_judge
from evaluation.agents.hallucination_judge import HallucinationDetectionAgent, hallucination_judge
from evaluation.agents.relevance_judge import RelevanceJudgeAgent, relevance_judge
from evaluation.agents.verdict_agent import VerdictAgent, verdict_agent
from evaluation.schemas import (
    AccuracyResult,
    CompletenessResult,
    HallucinationResult,
    OverallEvaluation,
    RelevanceResult,
    VerdictResult,
)

logger = logging.getLogger("proofrag.orchestrator")


class EvaluationOrchestrator:
    """Orchestrates multi-agent evaluation pipeline and computes transparent verdict."""

    def __init__(
        self,
        rag_retriever: Optional[EvidenceRetriever] = None,
        rel_judge: Optional[RelevanceJudgeAgent] = None,
        acc_judge: Optional[AccuracyJudgeAgent] = None,
        hal_judge: Optional[HallucinationDetectionAgent] = None,
        comp_judge: Optional[CompletenessJudgeAgent] = None,
        v_agent: Optional[VerdictAgent] = None,
        accuracy_weight: Optional[float] = None,
        relevance_weight: Optional[float] = None,
        hallucination_weight: Optional[float] = None,
        completeness_weight: Optional[float] = None,
    ):
        self.retriever = rag_retriever or retriever
        self.relevance_judge = rel_judge or relevance_judge
        self.accuracy_judge = acc_judge or accuracy_judge
        self.hallucination_judge = hal_judge or hallucination_judge
        self.completeness_judge = comp_judge or completeness_judge
        self.verdict_agent = v_agent or verdict_agent

        self.w_accuracy = accuracy_weight if accuracy_weight is not None else WEIGHT_ACCURACY
        self.w_hallucination = hallucination_weight if hallucination_weight is not None else WEIGHT_HALLUCINATION
        self.w_relevance = relevance_weight if relevance_weight is not None else WEIGHT_RELEVANCE
        self.w_completeness = completeness_weight if completeness_weight is not None else WEIGHT_COMPLETENESS

    def evaluate_response(
        self,
        question: str,
        ai_response: str,
        reference_answer: Optional[str] = None,
        source_document: Optional[str] = None,
        dataset_filter: Optional[str] = None,
        top_k: int = 5,
    ) -> Dict[str, Any]:
        """Execute full 4-dimension evaluation pipeline and return structured results."""
        q_clean = question.strip()
        ans_clean = ai_response.strip()

        # Step 1: Semantic Evidence Retrieval & Candidate Filtering
        filter_res = self.retriever.retrieve_and_filter_candidates(
            question=q_clean,
            ai_response=ans_clean,
            candidate_pool_size=max(top_k * 2, 10),
            dataset_filter=dataset_filter,
        )
        raw_evidence = filter_res["relevant_evidence"][:top_k]
        additional_matches = filter_res["additional_matches"]
        candidate_count = filter_res["candidate_count"]

        # Step 2: Relevance Judge Agent
        relevance_res: RelevanceResult = self.relevance_judge.evaluate(
            question=q_clean,
            ai_response=ans_clean,
        )

        # Step 3: Accuracy Judge Agent
        accuracy_res: AccuracyResult = self.accuracy_judge.evaluate(
            question=q_clean,
            ai_response=ans_clean,
            retrieved_evidence=raw_evidence,
            reference_answer=reference_answer,
            source_document=source_document,
        )

        # Step 4: Hallucination Detection Agent
        hallucination_res: HallucinationResult = self.hallucination_judge.evaluate(
            question=q_clean,
            ai_response=ans_clean,
            retrieved_evidence=raw_evidence,
            reference_answer=reference_answer,
            source_document=source_document,
        )

        # Step 5: Completeness Judge Agent
        completeness_res: CompletenessResult = self.completeness_judge.evaluate(
            question=q_clean,
            ai_response=ans_clean,
            retrieved_evidence=raw_evidence,
            reference_answer=reference_answer,
            source_document=source_document,
        )

        # Step 6: Dedicated Verdict Agent & Weighted Synthesis
        verdict_res: VerdictResult = self.verdict_agent.synthesize_verdict(
            accuracy_result=accuracy_res.model_dump(),
            relevance_result=relevance_res.model_dump(),
            hallucination_result=hallucination_res.model_dump(),
            completeness_result=completeness_res.model_dump(),
        )

        # Build OverallEvaluation for backward compatibility
        overall_eval = OverallEvaluation(
            overall_score=verdict_res.overall_score,
            verdict=verdict_res.verdict,
            verdict_reasoning=verdict_res.consolidated_reasoning,
            accuracy_weight=self.w_accuracy,
            hallucination_safety_weight=self.w_hallucination,
            relevance_weight=self.w_relevance,
            completeness_weight=self.w_completeness,
            dimension_scores=verdict_res.dimension_scores,
            normalized_scores=verdict_res.normalized_scores,
            weighted_contributions=verdict_res.weighted_contributions,
            major_strengths=verdict_res.major_strengths,
            major_issues=verdict_res.major_issues,
            consolidated_reasoning=verdict_res.consolidated_reasoning,
            critical_override_applied=verdict_res.critical_override_applied,
            critical_override_reason=verdict_res.critical_override_reason,
        )

        return {
            "verdict": overall_eval.verdict,
            "overall_score": overall_eval.overall_score,
            "evidence": raw_evidence,
            "additional_matches": additional_matches,
            "candidate_count": candidate_count,
            "relevance": relevance_res.model_dump(),
            "accuracy": accuracy_res.model_dump(),
            "hallucination": hallucination_res.model_dump(),
            "completeness": completeness_res.model_dump(),
            "overall": overall_eval.model_dump(),
            "verdict_details": verdict_res.model_dump(),
        }


# Global singleton instance
evaluation_orchestrator = EvaluationOrchestrator()
