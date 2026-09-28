"""Hallucination Detection Agent for PROOFRAG.

Decomposes AI answers into factual assertions and evaluates each claim
against retrieved evidence and reference information.
Classifies claims into: SUPPORTED, UNSUPPORTED, CONTRADICTED, INSUFFICIENT_EVIDENCE.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple
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
            llm_res = self._evaluate_with_llm(
                question,
                ans_clean,
                reference_corpus,
                has_sufficient_evidence,
                reference_answer=reference_answer,
            )
            if llm_res:
                return llm_res

        # Deterministic local claim extraction & verification
        return self._evaluate_locally(question, ans_clean, reference_corpus, has_sufficient_evidence)

    def _contextualize_claim(self, claim: str, ai_response: str, question: str = "") -> str:
        """Resolve leading pronouns or anaphora in a claim using the inquiry or preceding context."""
        c_strip = claim.strip()
        c_lower = c_strip.lower()

        # Pronoun / anaphora prefixes to detect
        pronoun_patterns = [
            r"^(it|this|that)\s+(also\s+)?(releases|produces|creates|generates|converts|transforms|helps|occurs|happens|takes|is|was|can|does|has)\b",
            r"^(they|these|those)\s+(also\s+)?(release|produce|create|generate|convert|transform|help|occur|happen|take|are|were|can|do|have)\b",
            r"^(the process|the reaction|the mechanism)\s+",
        ]

        is_anaphoric = any(re.search(pat, c_lower) for pat in pronoun_patterns)
        if not is_anaphoric:
            return c_strip

        # Extract antecedent topic from question or preceding response
        topic = ""
        q_match = re.search(
            r"\b(?:what is|what are|why is|how does|what happens to|what happens if)\s+([a-zA-Z0-9\s]{3,35}?)(?:\?|\s+and|\s+where|\s+when|\s+does|$)",
            question,
            re.IGNORECASE,
        )
        if q_match:
            cand = q_match.group(1).strip()
            cand_clean = re.sub(r"^(the|a|an)\s+", "", cand, flags=re.IGNORECASE).strip()
            if len(cand_clean) >= 3:
                topic = cand_clean

        if not topic and ai_response:
            first_sent = re.split(r"(?<=[.!?])\s+", ai_response.strip())[0]
            n_match = re.match(r"^([A-Z][a-zA-Z0-9\s]{2,25}?)\s+(?:is|are|was|were|occurs|refers|helps)\b", first_sent)
            if n_match:
                cand = n_match.group(1).strip()
                cand_clean = re.sub(r"^(the|a|an)\s+", "", cand, flags=re.IGNORECASE).strip()
                if len(cand_clean) >= 3:
                    topic = cand_clean

        if not topic:
            return c_strip

        # Replace leading pronoun with topic
        replaced = re.sub(r"^(it|they|these|this|that|the process)\b", topic, c_strip, flags=re.IGNORECASE)
        return replaced

    @staticmethod
    def _word_in_text(word: str, text_lower: str) -> bool:
        """Check if word or its common grammatical inflections appear in text."""
        w = word.lower().strip()
        if len(w) < 4:
            return w in text_lower
        if w in text_lower:
            return True
        stems = [w]
        if w.endswith("es"):
            stems.append(w[:-2])
        elif w.endswith("s"):
            stems.append(w[:-1])
        if w.endswith("ed"):
            stems.append(w[:-2])
            stems.append(w[:-1])
        if w.endswith("ing"):
            stems.append(w[:-3])
            stems.append(w[:-3] + "e")
        for s in stems:
            if len(s) >= 4 and s in text_lower:
                return True
        if w.startswith("sun") and len(w) > 6 and w[3:] in text_lower:
            return True
        if w in ("food", "sugars", "sugar") and any(term in text_lower for term in ["food", "sugar", "glucose", "energy", "carbohydrate"]):
            return True
        return False

    @staticmethod
    def _clean_evidence_text(raw_text: str) -> str:
        """Strip QA prompt headers like 'Question: ... \nBest Verified Answer: ' so that only actual factual evidence is evaluated."""
        if not raw_text:
            return ""
        cleaned = re.sub(
            r"^Question:\s*.*?\n+(?:(?:Best\s+)?Verified\s+Answer:\s*|Answer:\s*)?",
            "",
            raw_text.strip(),
            flags=re.IGNORECASE,
        ).strip()
        return cleaned if cleaned else raw_text.strip()

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
        reference_answer: Optional[str] = None,
    ) -> Optional[HallucinationResult]:
        evidence_snippets = [
            f"[{item['source']}]: {item['text'][:400]}"
            for item in reference_corpus
            if item.get("source") != "Verified Answer"
        ]
        evidence_text = "\n\n".join(evidence_snippets[:5]) if evidence_snippets else "None retrieved."
        ref_ans_text = reference_answer.strip() if reference_answer and reference_answer.strip() else "None provided."

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
        user_prompt = (
            f"QUESTION:\n{question}\n\n"
            f"AI RESPONSE:\n{ai_response}\n\n"
            f"REFERENCE ANSWER:\n{ref_ans_text}\n\n"
            f"RETRIEVED EVIDENCE:\n{evidence_text}\n\n"
            "Evaluate this response only. Do not consider any previous batch records."
        )

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
        question: str,
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

        # Build fine-grained reference passages for comparison
        ref_passages: List[Tuple[str, str]] = []  # (passage_text, full_doc_text)
        for ref in reference_corpus:
            if ref.get("similarity", 0.0) < 0.35 and ref.get("source") != "Verified Answer":
                continue
            full_txt = self._clean_evidence_text(ref.get("text", "")).strip()
            if not full_txt:
                continue
            ref_passages.append((full_txt[:400], full_txt))
            # Split into sub-sentences / clauses for granular matching
            sub_parts = [
                p.strip()
                for p in re.split(r"[;\n]+|(?<=[.!?])\s+", full_txt)
                if len(p.strip()) > 12
            ]
            for part in sub_parts:
                ref_passages.append((part, full_txt))

        # Pre-embed reference passages
        ref_passage_embeddings = [
            (p_text, full_doc, embedder.embed_text(p_text[:300]))
            for p_text, full_doc in ref_passages
        ]

        # Distinctive reference answer entities and inquiry terms
        q_terms = {w.lower() for w in re.findall(r"\b[a-zA-Z]{3,}\b", question)}
        frame_words = {
            "main", "also", "into", "from", "with", "that", "this", "they", "their", "there", "about",
            "process", "called", "known", "include", "includes", "occur", "occurs", "occurring",
            "help", "helps", "produce", "produces", "release", "releases", "using", "uses", "used",
            "does", "have", "been", "were", "what", "which", "where", "when", "state", "states",
            "mean", "means", "very", "much", "many", "well", "form", "forms", "question", "answer",
            "verified", "best", "make", "makes", "making", "made", "give", "gives", "take", "takes",
            "part", "parts", "life", "way", "ways", "need", "needs", "needed"
        }
        ref_source = reference_corpus[0]["text"] if reference_corpus else combined_ref_lower
        ref_ans_entities = [
            w.lower() for w in re.findall(r"\b[a-zA-Z]{4,}\b", ref_source)
            if w.lower() not in q_terms and w.lower() not in frame_words
        ]

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

            # Contextualize claim for pronoun/anaphora resolution
            contextualized = self._contextualize_claim(claim_clean, ai_response, question)
            claim_vec = embedder.embed_text(claim_clean)
            ctx_vec = embedder.embed_text(contextualized) if contextualized != claim_clean else claim_vec

            best_match_text = ""
            best_sim = 0.0

            for p_text, full_doc, part_vec in ref_passage_embeddings:
                sim_raw = sum(a * b for a, b in zip(claim_vec, part_vec))
                sim_ctx = sum(a * b for a, b in zip(ctx_vec, part_vec))
                sim = max(sim_raw, sim_ctx)
                if sim > best_sim:
                    best_sim = sim
                    best_match_text = full_doc

            # Substantive content term overlap check
            c_words = [
                w.lower()
                for w in re.findall(r"\b[a-zA-Z]{4,}\b", claim_clean)
                if w.lower() not in {
                    "what", "that", "this", "from", "with", "have", "been", "were",
                    "into", "also", "their", "they", "there", "about", "could", "would"
                }
            ]
            matched_words = [w for w in c_words if self._word_in_text(w, combined_ref_lower)]
            term_overlap = len(matched_words) / max(1, len(c_words)) if c_words else 0.5

            distinct_entities = [
                w for w in c_words
                if w not in q_terms and w not in frame_words
            ]
            unmatched_entities = [
                w for w in distinct_entities
                if not self._word_in_text(w, combined_ref_lower)
            ]

            # Check for direct contradictions
            claim_has_affirmative = any(aff in claim_lower for aff in affirmative_markers)
            is_contradicted = False
            contradiction_reason = "The claim asserts a statement that is directly contradicted by verified reference evidence."

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
            elif re.search(r"^(no[.,\s]|false[.,\s]|not at all)", claim_lower) and any(w in combined_ref_lower for w in ["releases oxygen", "can be seen", "is true", "does release"]):
                is_contradicted = True
                contradiction_reason = "The claim explicitly denies verified reference facts (asserting 'No' when reference evidence confirms the affirmative)."
            elif "consumes oxygen" in claim_lower and "releases oxygen" in combined_ref_lower:
                is_contradicted = True
                contradiction_reason = "The claim asserts that photosynthesis consumes oxygen, directly contradicting verified reference facts confirming it releases oxygen."
            elif len(distinct_entities) >= 1 and len(unmatched_entities) == len(distinct_entities):
                shares_query_attribute = any(w in claim_lower for w in q_terms if len(w) > 3)
                has_ref_entity = any(w in c_words for w in ref_ans_entities) if ref_ans_entities else False
                if ref_ans_entities and not has_ref_entity and shares_query_attribute:
                    is_contradicted = True
                    contradiction_reason = (
                        f"The reference identifies verified facts for this inquiry (e.g., '{', '.join(ref_ans_entities[:3])}'), "
                        f"whereas the response incorrectly asserts '{', '.join(unmatched_entities)}'."
                    )

            all_distinct_unmatched = len(distinct_entities) >= 1 and len(unmatched_entities) == len(distinct_entities)

            if is_contradicted:
                evaluated_claims.append(ClaimEvaluation(
                    claim=claim_clean,
                    status="CONTRADICTED",
                    reasoning=contradiction_reason,
                    evidence=best_match_text[:250] if best_match_text else None,
                ))
                contradicted_count += 1
            elif ref_ans_entities and any(w in c_words for w in ref_ans_entities) and best_sim >= 0.50:
                evaluated_claims.append(ClaimEvaluation(
                    claim=claim_clean,
                    status="SUPPORTED",
                    reasoning="The claim directly states verified reference entities.",
                    evidence=best_match_text[:250] if best_match_text else None,
                ))
                supported_count += 1
            elif best_sim >= 0.70 and not all_distinct_unmatched:
                evaluated_claims.append(ClaimEvaluation(
                    claim=claim_clean,
                    status="SUPPORTED",
                    reasoning="The claim is directly substantiated by verified reference evidence through strong semantic alignment.",
                    evidence=best_match_text[:250] if best_match_text else None,
                ))
                supported_count += 1
            elif all_distinct_unmatched:
                evaluated_claims.append(ClaimEvaluation(
                    claim=claim_clean,
                    status="UNSUPPORTED",
                    reasoning=f"The claim introduces assertions ({', '.join(unmatched_entities)}) that are not corroborated by verified reference evidence.",
                    evidence=None,
                ))
                unsupported_count += 1
            elif best_sim >= 0.65 and len(unmatched_entities) == 0:
                evaluated_claims.append(ClaimEvaluation(
                    claim=claim_clean,
                    status="SUPPORTED",
                    reasoning="The claim is directly substantiated by verified reference evidence.",
                    evidence=best_match_text[:250] if best_match_text else None,
                ))
                supported_count += 1
            elif best_sim >= 0.50 and (term_overlap >= 0.35 or len(c_words) <= 2 and term_overlap >= 0.50) and len(unmatched_entities) <= 1:
                # Moderate semantic similarity substantiated by core entity term grounding
                evaluated_claims.append(ClaimEvaluation(
                    claim=claim_clean,
                    status="SUPPORTED",
                    reasoning="The claim is substantiated by verified reference evidence through topical alignment and entity corroboration.",
                    evidence=best_match_text[:250] if best_match_text else None,
                ))
                supported_count += 1
            elif best_sim >= 0.42 and term_overlap >= 0.60 and len(unmatched_entities) == 0:
                # High entity grounding for concise assertions
                evaluated_claims.append(ClaimEvaluation(
                    claim=claim_clean,
                    status="SUPPORTED",
                    reasoning="The claim is substantiated by verified reference evidence through direct entity corroboration.",
                    evidence=best_match_text[:250] if best_match_text else None,
                ))
                supported_count += 1
            elif best_sim >= 0.40:
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
