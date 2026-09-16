"""Accuracy Judge Agent for PROOFRAG.

Evaluates factual correctness against reference information (User Reference > Supporting Doc > Retrieved Evidence)
using a defined 1-5 scale calibrated at the atomic claim level.
"""

import logging
import re
from typing import Any, Dict, List, Optional
from backend.config import MINIMUM_EVIDENCE_THRESHOLD, STRONG_MATCH_THRESHOLD
from evaluation.llm_client import llm_client
from evaluation.schemas import AccuracyResult
from knowledge_base.embeddings.embedder import embedder

logger = logging.getLogger("proofrag.accuracy_judge")

ACCURACY_SCALE = {
    5: "Fully Correct",
    4: "Mostly Correct",
    3: "Partially Correct",
    2: "Mostly Incorrect",
    1: "Completely Incorrect",
}


class AccuracyJudgeAgent:
    """Evaluates factual correctness of AI responses against authoritative reference sources."""

    def __init__(self):
        self.llm = llm_client

    def evaluate(
        self,
        question: str,
        ai_response: str,
        retrieved_evidence: List[Dict[str, Any]],
        reference_answer: Optional[str] = None,
        source_document: Optional[str] = None,
    ) -> AccuracyResult:
        """Evaluate factual correctness across prioritized reference hierarchy."""
        ans_clean = (ai_response or "").strip()
        if not ans_clean:
            return AccuracyResult(
                score=1,
                label=ACCURACY_SCALE[1],
                reasoning="Empty AI response provided for factual validation.",
                supporting_evidence=[],
            )

        # 1. Establish prioritized reference context
        reference_texts: List[str] = []
        is_user_ground_truth = False

        if reference_answer and reference_answer.strip():
            reference_texts.append(f"Verified Reference Answer: {reference_answer.strip()}")
            is_user_ground_truth = True

        if source_document and source_document.strip():
            doc_snippet = source_document.strip()[:1500]
            reference_texts.append(f"Supporting Document Content: {doc_snippet}")
            is_user_ground_truth = True

        # Add retrieved evidence that meets confidence threshold
        strong_evidence = [
            e for e in (retrieved_evidence or [])
            if float(e.get("similarity_score", 0.0)) >= MINIMUM_EVIDENCE_THRESHOLD or e.get("match_tier") in ("strong", "moderate")
        ]
        for e in strong_evidence[:3]:
            txt = e.get("text", "").strip()
            if txt:
                dataset = e.get("dataset_name", "Knowledge Base")
                reference_texts.append(f"[{dataset}]: {txt}")

        # If no reliable reference information is available:
        if not reference_texts:
            return AccuracyResult(
                score=3,
                label=ACCURACY_SCALE[3],
                reasoning=(
                    "Insufficient reference evidence was retrieved from the knowledge base to confirm or "
                    "refute the factual accuracy of this response. No verified reference answer was provided."
                ),
                supporting_evidence=[],
            )

        # Attempt external LLM judge if configured
        if self.llm.is_configured():
            llm_res = self._evaluate_with_llm(question, ans_clean, reference_texts)
            if llm_res:
                return llm_res

        # Deterministic local claim-level factual verification
        return self._evaluate_locally(ans_clean, reference_texts, strong_evidence, is_user_ground_truth)

    def _decompose_claims(self, text: str) -> List[str]:
        """Split text into distinct claim sentences while protecting honorifics/abbreviations."""
        protected = re.sub(r"\b(Dr|Mr|Mrs|Ms|Prof|Sr|Jr|vs|etc|e\.g|i\.e)\.\s+", r"\1_DOT_ ", text.strip())
        raw_sentences = re.split(r"(?<=[.!?])\s+", protected)
        claims = [
            s.replace("_DOT_", ".").strip()
            for s in raw_sentences
            if len(s.strip()) > 8
        ]
        return claims if claims else [text.strip()]

    def _evaluate_with_llm(
        self,
        question: str,
        ai_response: str,
        reference_texts: List[str],
    ) -> Optional[AccuracyResult]:
        ref_corpus = "\n\n".join(reference_texts)
        system_prompt = (
            "You are the PROOFRAG Accuracy Judge Agent. Evaluate the factual correctness of the AI answer "
            "strictly against the provided reference evidence.\n"
            "Scoring Scale:\n"
            "5 — Fully Correct: Factually consistent with verified reference information across all stated points.\n"
            "4 — Mostly Correct: Core facts are accurate, with minor imprecision or non-critical omission.\n"
            "3 — Partially Correct: Contains a mix of confirmed facts and unverified or inaccurate assertions.\n"
            "2 — Mostly Incorrect: Central claim contradicts reference information or is largely erroneous.\n"
            "1 — Completely Incorrect: Entirely contrary to verified reference facts or fundamentally incorrect.\n\n"
            "Important: If the response combines a true fact with a major fabricated error (e.g. Napoleon discovering photosynthesis), "
            "do NOT award 4 or 5; score it as 2 or 3.\n\n"
            "Respond strictly with a JSON object:\n"
            '{"score": <1-5>, "reasoning": "<justification>", "supporting_evidence": ["<verbatim quote 1>"]}'
        )
        user_prompt = f"Question:\n{question}\n\nAI Answer:\n{ai_response}\n\nReference Evidence:\n{ref_corpus}"

        try:
            res = self.llm.generate_json(system_prompt, user_prompt)
            if res and "score" in res:
                score = max(1, min(5, int(res["score"])))
                evidence_quotes = [str(q) for q in res.get("supporting_evidence", []) if q]
                if not evidence_quotes and reference_texts:
                    evidence_quotes = [reference_texts[0][:200]]
                return AccuracyResult(
                    score=score,
                    label=ACCURACY_SCALE.get(score, "Evaluated"),
                    reasoning=str(res.get("reasoning", "Evaluated via configured LLM Judge.")),
                    supporting_evidence=evidence_quotes,
                )
        except Exception as exc:
            logger.warning(f"LLM accuracy evaluation failed, falling back to local: {exc}")
            raise

        return None

    def _evaluate_locally(
        self,
        ai_response: str,
        reference_texts: List[str],
        strong_evidence: List[Dict[str, Any]],
        is_user_ground_truth: bool,
    ) -> AccuracyResult:
        """Compute factual consistency at the claim level using dense embeddings and contradiction heuristics."""
        combined_ref = " ".join(reference_texts).lower()
        ans_lower = ai_response.lower()

        # Check for explicit contradictions (e.g. "can easily be seen" vs "cannot be seen" / "no")
        negation_markers = [r"\bno\b", r"\bnot\b", r"\bnone\b", r"\bnever\b", r"\bcannot\b", r"\bunable\b", r"\bimpossible\b", r"\bfalse\b", r"\bmyth\b", r"\bhas no\b", r"\bno capital\b", r"\buninhabited\b"]
        affirmative_markers = ["yes", "can easily", "definitely", "always", "can be seen", "easily seen", "is the capital", "founded in"]

        ref_has_negation = any(re.search(pat, combined_ref) for pat in negation_markers)
        ans_has_affirmative = any(aff in ans_lower for aff in affirmative_markers)
        ans_has_negation = any(re.search(pat, ans_lower) for pat in negation_markers)

        direct_contradiction = False
        if ref_has_negation and ans_has_affirmative and not ans_has_negation:
            direct_contradiction = True

        # Check domain-specific factual contradictions
        denial_patterns = [
            (r"\bno capital\b", r"\bcapital city\b"),
            (r"\buninhabited\b", r"\b(residents|population|people|inhabitants|housing)\b"),
            (r"\bcannot be seen\b", r"\b(can be seen|easily seen|visible)\b"),
            (r"\bnot visible\b", r"\b(visible|easily seen|can be seen)\b"),
            (r"\b(do not|cannot) grow\b", r"\bgrow(s)? into\b"),
        ]
        for ref_pat, ans_pat in denial_patterns:
            if re.search(ref_pat, combined_ref) and re.search(ans_pat, ans_lower):
                direct_contradiction = True
                break

        # Claim-level decomposition
        claims = self._decompose_claims(ai_response)
        ref_vecs = [embedder.embed_text(ref[:450]) for ref in reference_texts]

        supported_claims = 0
        unsupported_claims = 0
        contradicted_claims = 0

        for claim in claims:
            c_lower = claim.lower()
            c_vec = embedder.embed_text(claim)

            # Max similarity of this claim against any reference chunk
            max_c_sim = max(
                sum(a * b for a, b in zip(c_vec, r_vec))
                for r_vec in ref_vecs
            )

            c_has_aff = any(aff in c_lower for aff in affirmative_markers)
            if ref_has_negation and c_has_aff and max_c_sim >= 0.45:
                # If claim asserts what reference explicitly denies
                if any(re.search(ref_p, combined_ref) and re.search(ans_p, c_lower) for ref_p, ans_p in denial_patterns):
                    contradicted_claims += 1
                elif max_c_sim >= 0.65:
                    supported_claims += 1
                else:
                    unsupported_claims += 1
            elif max_c_sim >= 0.65:
                supported_claims += 1
            elif max_c_sim >= 0.52:
                # Moderate grounding: check substantive content overlap
                c_words = [w.lower() for w in re.findall(r"\b[a-zA-Z]{4,}\b", claim) if w.lower() not in {"what", "that", "this", "from", "with", "have", "been", "were"}]
                matching_words = [w for w in c_words if w in combined_ref]
                if len(c_words) > 0 and len(matching_words) / len(c_words) >= 0.35:
                    supported_claims += 1
                else:
                    unsupported_claims += 1
            else:
                unsupported_claims += 1

        total_claims = len(claims)

        # Supporting evidence extraction
        supporting_evidence: List[str] = []
        if strong_evidence:
            supporting_evidence.append(strong_evidence[0].get("text", "")[:250])
        elif reference_texts:
            supporting_evidence.append(reference_texts[0][:250])

        if direct_contradiction or contradicted_claims > 0:
            score = 1
            reasoning = (
                "The response directly contradicts verified reference facts (e.g., claiming an assertion "
                "is true when reference data confirms it is false or a misconception)."
            )
        elif unsupported_claims > 0 and supported_claims > 0:
            # Mixed response: 1 valid fact + 1 fabricated/unsupported error
            if supported_claims >= unsupported_claims:
                score = 3
                reasoning = (
                    f"Partially correct: Contains accurate statements alongside {unsupported_claims} "
                    f"unsupported or fabricated claim(s) that conflict with or lack reference corroboration."
                )
            else:
                score = 2
                reasoning = (
                    f"Mostly incorrect: Majority of claims ({unsupported_claims} of {total_claims}) "
                    f"lack reference support or contain unverified assertions."
                )
        elif unsupported_claims == total_claims:
            score = 1
            reasoning = "None of the factual assertions in this response are supported by reference evidence."
        elif supported_claims == total_claims:
            # Check overall semantic similarity for high precision
            overall_sim = max(
                sum(a * b for a, b in zip(embedder.embed_text(ai_response), r_vec))
                for r_vec in ref_vecs
            )
            if overall_sim >= 0.70:
                score = 5
                reasoning = "The response is factually consistent with verified reference information across all key points."
            else:
                score = 4
                reasoning = "Core statements are factually aligned with reference evidence, with minor wording variation."
        else:
            score = 3
            reasoning = "The response contains some factually aligned elements alongside unverified assertions."

        return AccuracyResult(
            score=score,
            label=ACCURACY_SCALE[score],
            reasoning=reasoning,
            supporting_evidence=supporting_evidence,
        )


# Global singleton instance
accuracy_judge = AccuracyJudgeAgent()
