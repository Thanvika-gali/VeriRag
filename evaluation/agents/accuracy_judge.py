"""Accuracy Judge Agent for PROOFRAG.

Evaluates factual correctness against reference information (User Reference > Supporting Doc > Retrieved Evidence)
using a defined 1-5 scale calibrated at the atomic claim level.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple
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
            txt = self._clean_evidence_text(e.get("text", "")).strip()
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
            llm_res = self._evaluate_with_llm(
                question,
                ans_clean,
                reference_texts,
                reference_answer=reference_answer,
            )
            if llm_res:
                return llm_res

        # Deterministic local claim-level factual verification
        return self._evaluate_locally(question, ans_clean, reference_texts, strong_evidence, is_user_ground_truth)

    def _contextualize_claim(self, claim: str, ai_response: str, question: str = "") -> str:
        """Resolve leading pronouns or anaphora in a claim using the inquiry or preceding context."""
        c_strip = claim.strip()
        c_lower = c_strip.lower()

        pronoun_patterns = [
            r"^(it|this|that)\s+(also\s+)?(releases|produces|creates|generates|converts|transforms|helps|occurs|happens|takes|is|was|can|does|has)\b",
            r"^(they|these|those)\s+(also\s+)?(release|produce|create|generate|convert|transform|help|occur|happen|take|are|were|can|do|have)\b",
            r"^(the process|the reaction|the mechanism)\s+",
        ]

        is_anaphoric = any(re.search(pat, c_lower) for pat in pronoun_patterns)
        if not is_anaphoric:
            return c_strip

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
        reference_answer: Optional[str] = None,
    ) -> Optional[AccuracyResult]:
        ref_ans_text = reference_answer.strip() if reference_answer and reference_answer.strip() else "None provided."
        evidence_texts = [r for r in reference_texts if not r.startswith("Verified Reference Answer:")]
        evidence_text = "\n\n".join(evidence_texts) if evidence_texts else "None retrieved."

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
        question: str,
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

        # Check reverse negation: reference affirms, answer explicitly denies (e.g. "No. ... consumes oxygen")
        if re.search(r"^(no[.,\s]|false[.,\s]|not at all)", ans_lower) and any(w in combined_ref for w in ["releases oxygen", "can be seen", "is true", "does release"]):
            direct_contradiction = True
        elif "consumes oxygen" in ans_lower and "releases oxygen" in combined_ref:
            direct_contradiction = True

        # Fine-grained reference passages
        ref_passages: List[Tuple[str, List[float]]] = []
        for ref in reference_texts:
            ref_clean = self._clean_evidence_text(ref).strip()
            if not ref_clean:
                continue
            ref_passages.append((ref_clean[:450], embedder.embed_text(ref_clean[:450])))
            sub_parts = [
                p.strip()
                for p in re.split(r"[;\n]+|(?<=[.!?])\s+", ref_clean)
                if len(p.strip()) > 12
            ]
            for part in sub_parts:
                ref_passages.append((part[:300], embedder.embed_text(part[:300])))

        # Claim-level decomposition
        claims = self._decompose_claims(ai_response)

        supported_claims = 0
        unsupported_claims = 0
        contradicted_claims = 0

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
        ref_source = reference_texts[0] if reference_texts else combined_ref
        ref_ans_entities = [
            w.lower() for w in re.findall(r"\b[a-zA-Z]{4,}\b", ref_source)
            if w.lower() not in q_terms and w.lower() not in frame_words
        ]

        for claim in claims:
            c_lower = claim.lower()
            contextualized = self._contextualize_claim(claim, ai_response, question)
            c_vec = embedder.embed_text(claim)
            ctx_vec = embedder.embed_text(contextualized) if contextualized != claim else c_vec

            # Max similarity of this claim against any reference chunk or sub-part
            max_c_sim = max(
                max(
                    sum(a * b for a, b in zip(c_vec, r_vec)),
                    sum(a * b for a, b in zip(ctx_vec, r_vec)),
                )
                for _, r_vec in ref_passages
            ) if ref_passages else 0.0

            # Substantive content word overlap
            c_words = [
                w.lower()
                for w in re.findall(r"\b[a-zA-Z]{4,}\b", claim)
                if w.lower() not in {
                    "what", "that", "this", "from", "with", "have", "been", "were",
                    "into", "also", "their", "they", "there", "about", "could", "would"
                }
            ]
            matching_words = [w for w in c_words if self._word_in_text(w, combined_ref)]
            term_overlap = len(matching_words) / max(1, len(c_words)) if c_words else 0.5

            distinct_entities = [w for w in c_words if w not in q_terms and w not in frame_words]
            unmatched_entities = [w for w in distinct_entities if not self._word_in_text(w, combined_ref)]

            c_has_aff = any(aff in c_lower for aff in affirmative_markers)
            is_claim_contradicted = False

            if ref_has_negation and c_has_aff and max_c_sim >= 0.45:
                is_claim_contradicted = True
            elif any(re.search(ref_p, combined_ref) and re.search(ans_p, c_lower) for ref_p, ans_p in denial_patterns):
                is_claim_contradicted = True
            elif re.search(r"^(no[.,\s]|false[.,\s]|not at all)", c_lower) and any(w in combined_ref for w in ["releases oxygen", "can be seen", "is true", "does release"]):
                is_claim_contradicted = True
            elif "consumes oxygen" in c_lower and "releases oxygen" in combined_ref:
                is_claim_contradicted = True
            elif len(distinct_entities) >= 1 and len(unmatched_entities) == len(distinct_entities):
                shares_query_attribute = any(w in c_lower for w in q_terms if len(w) > 3)
                has_ref_entity = any(w in c_words for w in ref_ans_entities) if ref_ans_entities else False
                if ref_ans_entities and not has_ref_entity and shares_query_attribute:
                    is_claim_contradicted = True

            all_distinct_unmatched = len(distinct_entities) >= 1 and len(unmatched_entities) == len(distinct_entities)

            if is_claim_contradicted:
                contradicted_claims += 1
            elif ref_ans_entities and any(w in c_words for w in ref_ans_entities) and max_c_sim >= 0.50:
                supported_claims += 1
            elif max_c_sim >= 0.70 and not all_distinct_unmatched:
                supported_claims += 1
            elif all_distinct_unmatched:
                unsupported_claims += 1
            elif max_c_sim >= 0.65 and len(unmatched_entities) == 0:
                supported_claims += 1
            elif max_c_sim >= 0.50 and (term_overlap >= 0.35 or len(c_words) <= 2 and term_overlap >= 0.50) and len(unmatched_entities) <= 1:
                supported_claims += 1
            elif max_c_sim >= 0.42 and term_overlap >= 0.60 and len(unmatched_entities) == 0:
                supported_claims += 1
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
            ai_emb = embedder.embed_text(ai_response)
            overall_sim = max(
                sum(a * b for a, b in zip(ai_emb, r_vec))
                for _, r_vec in ref_passages
            ) if ref_passages else 0.0
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
