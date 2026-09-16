"""Evaluation Orchestrator.

Coordinates complete verification workflow:
1. Input validation
2. Evidence retrieval via ChromaDB RAG
3. Relevance Judge Agent execution
4. Accuracy Judge Agent execution
5. Hallucination Detection Agent execution
6. Transparent Score Aggregation (40% Accuracy, 30% Relevance, 30% Hallucination Safety)
7. Rule-based Final Verdict synthesis (PASS, REVIEW, FAIL)
"""

import logging
from typing import Any, Dict, List, Optional
from backend.rag.retriever import EvidenceRetriever, retriever
from evaluation.agents.accuracy_judge import AccuracyJudgeAgent, accuracy_judge
from evaluation.agents.hallucination_judge import HallucinationDetectionAgent, hallucination_judge
from evaluation.agents.relevance_judge import RelevanceJudgeAgent, relevance_judge
from evaluation.schemas import (
    AccuracyResult,
    HallucinationResult,
    OverallEvaluation,
    RelevanceResult,
)

logger = logging.getLogger("verirag.orchestrator")


class EvaluationOrchestrator:
    """Orchestrates multi-agent evaluation pipeline and computes transparent verdict."""

    def __init__(
        self,
        rag_retriever: Optional[EvidenceRetriever] = None,
        rel_judge: Optional[RelevanceJudgeAgent] = None,
        acc_judge: Optional[AccuracyJudgeAgent] = None,
        hal_judge: Optional[HallucinationDetectionAgent] = None,
        accuracy_weight: float = 0.40,
        relevance_weight: float = 0.30,
        hallucination_weight: float = 0.30,
    ):
        self.retriever = rag_retriever or retriever
        self.relevance_judge = rel_judge or relevance_judge
        self.accuracy_judge = acc_judge or accuracy_judge
        self.hallucination_judge = hal_judge or hallucination_judge

        self.w_accuracy = accuracy_weight
        self.w_relevance = relevance_weight
        self.w_hallucination = hallucination_weight

    def evaluate_response(
        self,
        question: str,
        ai_response: str,
        reference_answer: Optional[str] = None,
        source_document: Optional[str] = None,
        dataset_filter: Optional[str] = None,
        top_k: int = 5,
    ) -> Dict[str, Any]:
        """Execute full evaluation pipeline and return structured results."""
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

        # Step 5: Overall Score Aggregation
        acc_norm = accuracy_res.score / 5.0
        rel_norm = relevance_res.score / 5.0

        if hallucination_res.hallucination_status == "NONE":
            hal_safety = 1.0
        elif hallucination_res.hallucination_status == "PARTIAL":
            hal_safety = 0.5
        else:
            hal_safety = 0.0

        raw_score = (
            (acc_norm * self.w_accuracy)
            + (rel_norm * self.w_relevance)
            + (hal_safety * self.w_hallucination)
        ) * 100.0
        overall_score = max(0, min(100, int(round(raw_score))))

        # Step 6: Rule-Based Final Verdict Determination
        verdict, verdict_reasoning = self._compute_verdict(
            accuracy=accuracy_res,
            relevance=relevance_res,
            hallucination=hallucination_res,
            overall_score=overall_score,
            has_strong_evidence=bool(raw_evidence and float(raw_evidence[0].get("similarity_score", 0.0)) >= 0.50),
        )

        overall_eval = OverallEvaluation(
            overall_score=overall_score,
            verdict=verdict,
            verdict_reasoning=verdict_reasoning,
            accuracy_weight=self.w_accuracy,
            relevance_weight=self.w_relevance,
            hallucination_safety_weight=self.w_hallucination,
        )

        return {
            "evidence": raw_evidence,
            "additional_matches": additional_matches,
            "candidate_count": candidate_count,
            "relevance": relevance_res.model_dump(),
            "accuracy": accuracy_res.model_dump(),
            "hallucination": hallucination_res.model_dump(),
            "overall": overall_eval.model_dump(),
        }

    def _compute_verdict(
        self,
        accuracy: AccuracyResult,
        relevance: RelevanceResult,
        hallucination: HallucinationResult,
        overall_score: int,
        has_strong_evidence: bool,
    ) -> tuple:
        """Compute transparent rule-based verdict based on actual agent metrics."""
        has_contradicted = any(c.status == "CONTRADICTED" for c in hallucination.flagged_claims)
        all_insufficient = (
            len(hallucination.flagged_claims) > 0
            and all(c.status == "INSUFFICIENT_EVIDENCE" for c in hallucination.flagged_claims)
        )

        # FAIL conditions:
        # Irrelevant (<= 2), clearly incorrect (<= 2), contradicted claims, or high risk with low score
        if relevance.score <= 2:
            return "FAIL", f"The response is off-topic or fails to address the question (Relevance: {relevance.score}/5)."
        if accuracy.score <= 2 or has_contradicted:
            return "FAIL", "The response contains direct factual contradictions or fundamental inaccuracies conflicting with reference evidence."
        if hallucination.risk_level == "HIGH" or hallucination.hallucination_status == "HIGH":
            return "FAIL", "High hallucination risk detected: response contains significant unsupported or contradictory claims."

        # PASS conditions:
        # High relevance (>= 4), high accuracy (>= 4), low hallucination risk, overall score >= 75
        if (
            relevance.score >= 4
            and accuracy.score >= 4
            and hallucination.risk_level == "LOW"
            and overall_score >= 75
        ):
            return "PASS", "Strong accuracy and relevance with claims verified against reference evidence."

        # REVIEW conditions (default fallback for mixed, partial, or insufficient evidence):
        if all_insufficient or not has_strong_evidence:
            return "REVIEW", "Limited reference evidence available in the knowledge base; manual verification recommended."
        if hallucination.risk_level == "MEDIUM" or hallucination.hallucination_status == "PARTIAL":
            return "REVIEW", "Mixed evaluation: some assertions are grounded while others lack conclusive reference evidence."

        return "REVIEW", "Evaluation indicates partial correctness or moderate relevance requiring review."


# Global singleton instance
evaluation_orchestrator = EvaluationOrchestrator()
