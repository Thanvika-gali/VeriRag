"""Relevance Judge Agent.

Evaluates whether an AI-generated response directly and appropriately
answers the submitted question using a defined 1-5 scale.
"""

import logging
from typing import Any, Dict, List, Optional
import re
from evaluation.llm_client import llm_client
from evaluation.schemas import RelevanceResult
from knowledge_base.embeddings.embedder import embedder

logger = logging.getLogger("verirag.relevance_judge")

RELEVANCE_SCALE = {
    5: "Fully Relevant",
    4: "Mostly Relevant",
    3: "Partially Relevant",
    2: "Mostly Irrelevant",
    1: "Completely Irrelevant",
}


class RelevanceJudgeAgent:
    """Evaluates question-response topical relevance and intent fulfillment."""

    def __init__(self):
        self.llm = llm_client

    def evaluate(
        self,
        question: str,
        ai_response: str,
        reference_answer: Optional[str] = None,
        retrieved_evidence: Optional[List[Dict[str, Any]]] = None,
    ) -> RelevanceResult:
        """Evaluate topical relevance of AI response to question on 1-5 scale."""
        q_clean = (question or "").strip()
        ans_clean = (ai_response or "").strip()

        if not q_clean or not ans_clean:
            return RelevanceResult(
                score=1,
                label=RELEVANCE_SCALE[1],
                reasoning="Empty question or AI response provided.",
            )

        # Attempt external LLM judge if configured
        if self.llm.is_configured():
            llm_result = self._evaluate_with_llm(
                q_clean,
                ans_clean,
                reference_answer=reference_answer,
                retrieved_evidence=retrieved_evidence,
            )
            if llm_result:
                return llm_result

        # Deterministic local semantic relevance evaluation
        return self._evaluate_locally(
            q_clean,
            ans_clean,
            reference_answer=reference_answer,
            retrieved_evidence=retrieved_evidence,
        )

    def _evaluate_with_llm(
        self,
        question: str,
        ai_response: str,
        reference_answer: Optional[str] = None,
        retrieved_evidence: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[RelevanceResult]:
        ref_ans_text = reference_answer.strip() if reference_answer and reference_answer.strip() else "None provided."
        evidence_snippets = [
            f"[{e.get('dataset_name', 'Knowledge Base')}]: {e.get('text', '')[:300]}"
            for e in (retrieved_evidence or [])[:3]
            if e.get("text")
        ]
        evidence_text = "\n\n".join(evidence_snippets) if evidence_snippets else "None retrieved."

        system_prompt = (
            "You are the VeriRAG Relevance Judge Agent. Evaluate whether the AI answer directly and "
            "appropriately answers the question.\n"
            "Scoring Scale:\n"
            "5 — Fully Relevant: The response directly answers the question and stays focused on the requested topic.\n"
            "4 — Mostly Relevant: The response addresses the question with minor tangential details.\n"
            "3 — Partially Relevant: The response addresses only part of the question or touches the topic without answering.\n"
            "2 — Mostly Irrelevant: The response mentions the topic tangentially but fails to address what was asked.\n"
            "1 — Completely Irrelevant: The response is completely unrelated or off-topic.\n\n"
            "Respond strictly with a JSON object:\n"
            '{"score": <1-5>, "reasoning": "<detailed justification>"}'
        )
        user_prompt = (
            f"QUESTION:\n{question}\n\n"
            f"AI RESPONSE:\n{ai_response}\n\n"
            f"REFERENCE ANSWER:\n{ref_ans_text}\n\n"
            f"RETRIEVED EVIDENCE:\n{evidence_text}\n\n"
            "Evaluate this response only. Do not consider any previous batch records."
        )

        try:
            res = self.llm.generate_json(system_prompt, user_prompt)
            if res and "score" in res:
                score = max(1, min(5, int(res["score"])))
                reasoning = str(res.get("reasoning", "Evaluated via configured LLM Judge."))
                return RelevanceResult(
                    score=score,
                    label=RELEVANCE_SCALE.get(score, "Evaluated"),
                    reasoning=reasoning,
                )
        except Exception as exc:
            logger.warning(f"LLM relevance evaluation failed, falling back to local: {exc}")
            raise

        return None

    def _evaluate_locally(
        self,
        question: str,
        ai_response: str,
        reference_answer: Optional[str] = None,
        retrieved_evidence: Optional[List[Dict[str, Any]]] = None,
    ) -> RelevanceResult:
        """Compute topical alignment using dense embeddings and semantic heuristics."""
        q_vec = embedder.embed_text(question)
        ans_vec = embedder.embed_text(ai_response)

        # Dot product of normalized unit vectors equals cosine similarity
        sim = max(0.0, min(1.0, sum(a * b for a, b in zip(q_vec, ans_vec))))

        # If verified reference answer is provided, check semantic alignment with reference
        if reference_answer and reference_answer.strip():
            ref_vec = embedder.embed_text(reference_answer.strip())
            sim_ref = max(0.0, min(1.0, sum(a * b for a, b in zip(ans_vec, ref_vec))))
            if sim_ref >= 0.70:
                # Strong corroboration that the response directly answers the core topic
                sim = max(sim, sim_ref * 0.95)

        # Lexical term overlap check (excluding common question framing and stop words)
        stop_words = {
            "what", "is", "the", "a", "an", "and", "or", "in", "of", "to", "for",
            "on", "with", "at", "by", "from", "up", "about", "into", "over", "after", "before",
            "can", "be", "seen", "does", "did", "do", "how", "why", "where", "who", "which", "whom",
            "happen", "happens", "happening", "tell", "explain", "describe", "give", "state", "list",
            "receive", "receives", "enough", "not", "have", "has", "had", "would", "could", "should",
            "there", "their", "they", "this", "that", "these", "those", "when"
        }
        q_tokens = {w.strip("?,.!;:\"'()").lower() for w in question.split() if len(w) > 2} - stop_words
        ans_tokens = {w.strip("?,.!;:\"'()").lower() for w in ai_response.split() if len(w) > 2}

        # Check token matches with morphological inflection/stem support
        matched_tokens = 0
        for qt in q_tokens:
            if qt in ans_tokens:
                matched_tokens += 1
                continue
            # Plural / tense stems
            stems = [qt[:-1] if qt.endswith("s") else qt + "s"]
            if any(s in ans_tokens for s in stems):
                matched_tokens += 1

        overlap = matched_tokens / max(1, len(q_tokens)) if q_tokens else 0.5

        # Combined topical relevance metric prioritizing semantic embedding similarity
        combined_rel = (sim * 0.75) + (overlap * 0.25)

        if sim >= 0.58 or combined_rel >= 0.55:
            score = 5
            reasoning = "The response directly addresses the question and stays closely focused on the requested subject matter."
        elif sim >= 0.46 or combined_rel >= 0.44:
            score = 4
            reasoning = "The response addresses the main subject of the question with high topical relevance."
        elif sim >= 0.32 or combined_rel >= 0.32:
            score = 3
            reasoning = "The response touches upon aspects of the question topic but does not provide a direct or complete answer."
        elif sim >= 0.20 or combined_rel >= 0.20:
            score = 2
            reasoning = "The response is largely peripheral, mentioning related concepts without addressing the actual question."
        else:
            score = 1
            reasoning = "The response is completely unrelated to the question topic (e.g. answering about a different subject entirely)."

        return RelevanceResult(
            score=score,
            label=RELEVANCE_SCALE[score],
            reasoning=reasoning,
        )


# Global singleton instance
relevance_judge = RelevanceJudgeAgent()
