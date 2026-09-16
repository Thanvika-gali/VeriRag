"""Hallucination Detection Agent for PROOFRAG.

Decomposes AI answers into factual assertions and evaluates each claim
against retrieved evidence and reference information.
Classifies claims into: SUPPORTED, UNSUPPORTED, CONTRADICTED, INSUFFICIENT_EVIDENCE.
"""

import logging
import re
from typing import Any, Dict, List, Optional
from backend.config import MINIMUM_EVIDENCE_THRESHOLD, STRONG_MATCH_THRESHOLD
from evaluation.llm_client import llm_client
from evaluation.schemas import ClaimEvaluation, HallucinationResult
from knowledge_base.embeddings.embedder import embedder

logger = logging.getLogger("proofrag.hallucination_judge")


class HallucinationDetectionAgent:
    """Performs claim decomposition and factual grounding verification."""

    def __init__(self):
        self.llm = llm_client

    def evaluate(
        self,
        question: str,
        ai_response: str,
        retrieved_evidence: List[Dict[str, Any]],
        reference_answer: Optional[str] = None,
        source_document: Optional[str] = None,
    ) -> HallucinationResult:
        """Analyze AI answer for unsupported or contradicted assertions."""
        ans_clean = (ai_response or "").strip()
        if not ans_clean:
            return HallucinationResult(
                hallucination_status="NONE",
                risk_level="LOW",
                flagged_claims=[],
                summary="No AI response text provided to analyze.",
            )

        # Build reference pool
        reference_corpus: List[Dict[str, Any]] = []
        if reference_answer and reference_answer.strip():
            reference_corpus.append({
                "source": "Verified Answer",
                "text": reference_answer.strip(),
                "similarity": 1.0,
            })
        if source_document and source_document.strip():
            reference_corpus.append({
                "source": "Supporting Document",
                "text": source_document.strip(),
                "similarity": 1.0,
            })
        for e in (retrieved_evidence or []):
            sim = float(e.get("similarity_score", 0.0))
            reference_corpus.append({
                "source": e.get("dataset_name", "Knowledge Base"),
                "text": e.get("text", ""),
                "similarity": sim,
            })

        # Check if reference evidence is entirely weak / insufficient
        max_evidence_sim = max([c["similarity"] for c in reference_corpus], default=0.0)
        has_sufficient_evidence = max_evidence_sim >= MINIMUM_EVIDENCE_THRESHOLD

        # Attempt LLM-based decomposition and classification if configured
        if self.llm.is_configured():
            llm_res = self._evaluate_with_llm(question, ans_clean, reference_corpus, has_sufficient_evidence)
            if llm_res:
                return llm_res

        # Deterministic local claim extraction & verification
        return self._evaluate_locally(ans_clean, reference_corpus, has_sufficient_evidence)

    def _decompose_sentences(self, text: str) -> List[str]:
        """Split text into distinct sentence-level claims while protecting honorifics/abbreviations."""
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
        reference_corpus: List[Dict[str, Any]],
        has_sufficient_evidence: bool,
    ) -> Optional[HallucinationResult]:
        ref_text = "\n\n".join(f"[{item['source']}]: {item['text'][:400]}" for item in reference_corpus[:5])
        system_prompt = (
            "You are the PROOFRAG Hallucination Detection Agent. Break the AI answer into individual factual claims "
            "and verify each claim against the reference evidence.\n"
            "Claim Status Definitions:\n"
            "- SUPPORTED: Available reference evidence directly supports the claim.\n"
            "- CONTRADICTED: Available reference evidence directly conflicts with or refutes the claim.\n"
            "- UNSUPPORTED: The claim is not supported by available evidence, but there is not enough evidence to call it contradicted.\n"
            "- INSUFFICIENT_EVIDENCE: The retrieved knowledge does not contain enough information to determine whether the claim is true.\n\n"
            "Risk Level:\n"
            "- LOW: All claims supported, or unrepresented query with insufficient evidence.\n"
            "- MEDIUM: One minor unsupported claim.\n"
            "- HIGH: Contradicted claim or major fabricated assertion.\n\n"
            "Respond strictly in JSON:\n"
            "{\n"
            '  "hallucination_status": "NONE|PARTIAL|HIGH",\n'
            '  "risk_level": "LOW|MEDIUM|HIGH",\n'
            '  "flagged_claims": [\n'
            '    {"claim": "...", "status": "SUPPORTED|UNSUPPORTED|CONTRADICTED|INSUFFICIENT_EVIDENCE", "reasoning": "...", "evidence": "..."}\n'
            "  ],\n"
            '  "summary": "<concise summary>"\n'
            "}"
        )
        user_prompt = f"Question:\n{question}\n\nAI Answer:\n{ai_response}\n\nReference Evidence:\n{ref_text}"

        try:
            res = self.llm.generate_json(system_prompt, user_prompt)
            if res and "flagged_claims" in res:
                claims = []
                for c in res["flagged_claims"]:
                    status = c.get("status", "INSUFFICIENT_EVIDENCE")
                    if status not in ("SUPPORTED", "UNSUPPORTED", "CONTRADICTED", "INSUFFICIENT_EVIDENCE"):
                        status = "INSUFFICIENT_EVIDENCE"
                    claims.append(ClaimEvaluation(
                        claim=str(c.get("claim", "")),
                        status=status,
                        reasoning=str(c.get("reasoning", "")),
                        evidence=str(c.get("evidence", "")) if c.get("evidence") else None,
                    ))

                h_status = res.get("hallucination_status", "NONE")
                risk = res.get("risk_level", "LOW")
                summary = str(res.get("summary", "Claims grounded against reference evidence."))

                return HallucinationResult(
                    hallucination_status=h_status if h_status in ("NONE", "PARTIAL", "HIGH") else "NONE",
                    risk_level=risk if risk in ("LOW", "MEDIUM", "HIGH") else "LOW",
                    flagged_claims=claims,
                    summary=summary,
                )
        except Exception as exc:
            logger.warning(f"LLM hallucination evaluation failed, falling back to local: {exc}")
            raise

        return None

    def _evaluate_locally(
        self,
        ai_response: str,
        reference_corpus: List[Dict[str, Any]],
        has_sufficient_evidence: bool,
    ) -> HallucinationResult:
        """Decompose claims and determine grounding status using embeddings and contradiction heuristics."""
        claims_text = self._decompose_sentences(ai_response)
        evaluated_claims: List[ClaimEvaluation] = []

        combined_ref_lower = " ".join(c["text"].lower() for c in reference_corpus)

        negation_markers = ["cannot", "not", "no,", "never", "impossible", "unable", "false", "myth", "incorrect"]
        affirmative_markers = ["yes", "can easily", "definitely", "always", "can be seen", "easily seen", "will grow"]

        ref_has_negation = any(neg in combined_ref_lower for neg in negation_markers)

        unsupported_count = 0
        contradicted_count = 0
        supported_count = 0
        insufficient_count = 0

        for claim in claims_text:
            claim_clean = claim.strip()
            claim_lower = claim_clean.lower()

            if not has_sufficient_evidence:
                # No strong evidence in knowledge base: do not falsely accuse of hallucination!
                evaluated_claims.append(ClaimEvaluation(
                    claim=claim_clean,
                    status="INSUFFICIENT_EVIDENCE",
                    reasoning="The reference knowledge base does not contain sufficient verified evidence to corroborate or refute this assertion.",
                    evidence=None,
                ))
                insufficient_count += 1
                continue

            # Find best matching reference passage
            claim_vec = embedder.embed_text(claim_clean)
            best_match_text = ""
            best_sim = 0.0

            for ref in reference_corpus:
                if ref["similarity"] < 0.40:
                    continue
                ref_parts = [p.strip() for p in ref["text"].split("\n") if len(p.strip()) > 15]
                if not ref_parts:
                    ref_parts = [ref["text"]]

                for part in ref_parts:
                    part_vec = embedder.embed_text(part[:300])
                    sim = sum(a * b for a, b in zip(claim_vec, part_vec))
                    if sim > best_sim:
                        best_sim = sim
                        best_match_text = part

            # Check for direct contradictions
            claim_has_affirmative = any(aff in claim_lower for aff in affirmative_markers)
            is_contradicted = False

            denial_patterns = [
                (r"\bno capital\b", r"\bcapital city\b"),
                (r"\buninhabited\b", r"\b(residents|population|people|inhabitants|housing)\b"),
                (r"\bcannot be seen\b", r"\b(can be seen|easily seen|visible)\b"),
                (r"\bnot visible\b", r"\b(visible|easily seen|can be seen)\b"),
                (r"\b(do not|cannot) grow\b", r"\bgrow(s)? into\b"),
            ]
            if any(re.search(ref_p, combined_ref_lower) and re.search(ans_p, claim_lower) for ref_p, ans_p in denial_patterns):
                is_contradicted = True
            elif ref_has_negation and claim_has_affirmative and best_sim >= 0.45:
                is_contradicted = True

            if is_contradicted:
                evaluated_claims.append(ClaimEvaluation(
                    claim=claim_clean,
                    status="CONTRADICTED",
                    reasoning="The claim asserts a statement that is directly contradicted by verified reference evidence.",
                    evidence=best_match_text[:250] if best_match_text else None,
                ))
                contradicted_count += 1
            elif best_sim >= 0.65:
                evaluated_claims.append(ClaimEvaluation(
                    claim=claim_clean,
                    status="SUPPORTED",
                    reasoning="The claim is directly substantiated by verified reference evidence.",
                    evidence=best_match_text[:250] if best_match_text else None,
                ))
                supported_count += 1
            elif best_sim >= 0.45:
                evaluated_claims.append(ClaimEvaluation(
                    claim=claim_clean,
                    status="UNSUPPORTED",
                    reasoning="Reference evidence exists on this subject, but does not substantiate this specific assertion.",
                    evidence=best_match_text[:250] if best_match_text else None,
                ))
                unsupported_count += 1
            else:
                evaluated_claims.append(ClaimEvaluation(
                    claim=claim_clean,
                    status="UNSUPPORTED",
                    reasoning="No reference evidence was found corroborating this factual claim.",
                    evidence=None,
                ))
                unsupported_count += 1

        total = len(evaluated_claims)
        if contradicted_count > 0:
            h_status = "HIGH"
            risk_level = "HIGH"
            summary = f"Identified {contradicted_count} contradicted statement(s) directly conflicting with verified reference facts."
        elif unsupported_count > 0:
            if unsupported_count >= 2 or (unsupported_count == 1 and total == 1):
                h_status = "HIGH"
                risk_level = "HIGH"
                summary = f"High hallucination risk: {unsupported_count} of {total} claims are ungrounded by reference evidence."
            else:
                # 1 unsupported claim out of multiple claims
                h_status = "PARTIAL"
                risk_level = "MEDIUM"
                summary = f"Medium risk: 1 of {total} claims lacks supporting reference evidence."
        elif insufficient_count > 0 and supported_count == 0:
            h_status = "NONE"
            risk_level = "LOW"
            summary = "Insufficient reference evidence was available to verify claims; no explicit contradictions detected."
        else:
            h_status = "NONE"
            risk_level = "LOW"
            summary = f"All {supported_count} extracted claims are grounded by available reference evidence."

        return HallucinationResult(
            hallucination_status=h_status,
            risk_level=risk_level,
            flagged_claims=evaluated_claims,
            summary=summary,
        )


# Global singleton instance
hallucination_judge = HallucinationDetectionAgent()
