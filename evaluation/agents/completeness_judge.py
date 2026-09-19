"""Completeness Judge Agent for PROOFRAG.

Evaluates whether an AI-generated response thoroughly covers all requirements,
sub-questions, and expected information from the submitted question.
Compares requirements with the AI response, verified reference answers,
and RAG-retrieved evidence.

Produces structured CompletenessResult on a 1-5 scale:
- 5: Fully complete (COMPLETE)
- 4: Mostly complete (COMPLETE)
- 3: Partially complete (PARTIAL)
- 2: Substantially incomplete (INCOMPLETE)
- 1: Completely incomplete (INCOMPLETE)
"""

import logging
import re
from typing import Any, Dict, List, Optional
from evaluation.llm_client import llm_client
from evaluation.schemas import CompletenessResult
from knowledge_base.embeddings.embedder import embedder

logger = logging.getLogger("proofrag.completeness_judge")

COMPLETENESS_SCALE = {
    5: "Fully Complete",
    4: "Mostly Complete",
    3: "Partially Complete",
    2: "Substantially Incomplete",
    1: "Completely Incomplete",
}


class CompletenessJudgeAgent:
    """Evaluates question requirement fulfillment, facet coverage, and omitted information."""

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name
        self.llm = llm_client

    def evaluate(
        self,
        question: str,
        ai_response: str,
        retrieved_evidence: Optional[List[Dict[str, Any]]] = None,
        reference_answer: Optional[str] = None,
        source_document: Optional[str] = None,
    ) -> CompletenessResult:
        """Evaluate coverage of question requirements and sub-questions on 1-5 scale."""
        q_clean = (question or "").strip()
        ans_clean = (ai_response or "").strip()

        if not q_clean or not ans_clean:
            return CompletenessResult(
                score=1,
                status="INCOMPLETE",
                addressed_aspects=[],
                missing_aspects=["No response text provided to satisfy inquiry."],
                reasoning="Empty question or AI response provided for completeness evaluation.",
            )

        # Build reference context for completeness baseline
        reference_corpus: List[str] = []
        if reference_answer and reference_answer.strip():
            reference_corpus.append(reference_answer.strip())
        if source_document and source_document.strip():
            reference_corpus.append(source_document.strip()[:1000])
        for ev in (retrieved_evidence or [])[:3]:
            txt = ev.get("text", "").strip()
            if txt:
                reference_corpus.append(txt)

        # Attempt LLM-based evaluation if configured
        if self.llm.is_configured():
            llm_res = self._evaluate_with_llm(q_clean, ans_clean, reference_corpus)
            if llm_res:
                return llm_res

        # Deterministic local aspect decomposition and coverage analysis
        return self._evaluate_locally(q_clean, ans_clean, reference_corpus)

    def _decompose_question_requirements(self, question: str) -> List[str]:
        """Extract individual requirements, sub-questions, and facets from inquiry."""
        raw_q = question.strip()

        # Check for multiple sentences or question marks
        parts: List[str] = []
        sentence_splits = re.split(r"[?!;]+", raw_q)
        for s in sentence_splits:
            cleaned = s.strip()
            if len(cleaned) > 5:
                parts.append(cleaned)

        # Check for list or enumeration after a colon (e.g. "Describe the three stages: A, B, and C")
        if ":" in raw_q:
            colon_splits = raw_q.split(":", 1)
            preamble = colon_splits[0].strip()
            list_part = colon_splits[1].strip()
            items = re.split(r",\s*(?:and\s+)?|\s+and\s+", list_part, flags=re.IGNORECASE)
            sub_items = [it.strip(" .?!;") for it in items if len(it.strip(" .?!;")) > 3]
            if len(sub_items) >= 2:
                parts = sub_items

        # If only 1 sentence, check compound clauses or coordinating conjunctions
        if len(parts) <= 1:
            compound_patterns = [
                r"\b(?:and|as well as|along with)\s+(?:what|how|why|when|where|who|which|explain|describe|give)\b",
                r"\b(?:and|as well as)\s+(?:also\s+)?(?:state|list|compare|clarify|detail|elaborate)\b",
                r",\s*(?:and\s+)?(?:where|when|who|why|how|what)\b",
            ]
            split_found = False
            for pat in compound_patterns:
                splits = re.split(pat, raw_q, flags=re.IGNORECASE)
                if len(splits) > 1 and all(len(sp.strip()) > 8 for sp in splits):
                    parts = [sp.strip() for sp in splits if len(sp.strip()) > 5]
                    split_found = True
                    break

            # Check question phrases like "When was X founded, where, and by whom?"
            if not split_found and ("," in raw_q or " and " in raw_q.lower()):
                # Test wh-words in phrase
                wh_matches = list(re.finditer(r"\b(when|where|who|whom|why|how|what)\b", raw_q, re.IGNORECASE))
                if len(wh_matches) >= 2:
                    sub_parts = []
                    last_idx = 0
                    for i in range(len(wh_matches)):
                        start = wh_matches[i].start()
                        end = wh_matches[i + 1].start() if i + 1 < len(wh_matches) else len(raw_q)
                        segment = raw_q[start:end].strip(" ,.?&")
                        if segment:
                            sub_parts.append(segment)
                    if len(sub_parts) >= 2:
                        parts = sub_parts
                        split_found = True

        # Fallback to single requirement if no sub-questions split
        if not parts:
            parts = [raw_q]

        # Clean aspects
        aspects = []
        for p in parts:
            p_clean = re.sub(r"^(and|also|moreover|furthermore|additionally|or)\s+", "", p, flags=re.IGNORECASE).strip()
            if len(p_clean) > 4:
                aspects.append(p_clean)

        return aspects if aspects else [raw_q]

    def _evaluate_with_llm(
        self,
        question: str,
        ai_response: str,
        reference_corpus: List[str],
    ) -> Optional[CompletenessResult]:
        ref_text = "\n\n".join(reference_corpus[:3]) if reference_corpus else "No reference text available."
        system_prompt = (
            "You are the PROOFRAG Completeness Judge Agent. Evaluate how thoroughly the AI response "
            "answers all aspects, requirements, and sub-questions of the user's prompt.\n"
            "Scoring Scale (1-5):\n"
            "5 — Fully Complete: All requirements, sub-questions, and nuances are thoroughly covered.\n"
            "4 — Mostly Complete: Core questions answered; minor omission or slight brevity on a secondary aspect.\n"
            "3 — Partially Complete: Only partially answers the prompt; leaves important sub-questions or aspects unanswered.\n"
            "2 — Substantially Incomplete: Very brief or only touches one minor facet; major core requirements omitted.\n"
            "1 — Completely Incomplete: Fails to address the question's core subject or provides an empty/unrelated answer.\n\n"
            "Status: 'COMPLETE' for 4-5, 'PARTIAL' for 3, 'INCOMPLETE' for 1-2.\n\n"
            "Respond strictly with a JSON object:\n"
            "{\n"
            '  "score": <1-5>,\n'
            '  "status": "COMPLETE | PARTIAL | INCOMPLETE",\n'
            '  "addressed_aspects": ["<aspect 1>", ...],\n'
            '  "missing_aspects": ["<aspect missing>", ...],\n'
            '  "reasoning": "<concise justification distinguishing fully, mostly, partially, or substantially incomplete>"\n'
            "}"
        )
        user_prompt = (
            f"Question:\n{question}\n\nAI Response:\n{ai_response}\n\nReference Information:\n{ref_text}"
        )

        try:
            res = self.llm.generate_json(system_prompt, user_prompt)
            if res and "score" in res:
                score = max(1, min(5, int(res["score"])))
                status = res.get("status", "PARTIAL")
                if score >= 4:
                    status = "COMPLETE"
                elif score == 3:
                    status = "PARTIAL"
                else:
                    status = "INCOMPLETE"

                addressed = [str(a) for a in res.get("addressed_aspects", []) if a]
                missing = [str(m) for m in res.get("missing_aspects", []) if m]
                reasoning = str(res.get("reasoning", "Evaluated via configured LLM Completeness Judge."))

                return CompletenessResult(
                    score=score,
                    status=status,
                    addressed_aspects=addressed,
                    missing_aspects=missing,
                    reasoning=reasoning,
                )
        except Exception as exc:
            logger.warning(f"LLM completeness evaluation failed, falling back to local: {exc}")
            raise

        return None

    def _evaluate_locally(
        self,
        question: str,
        ai_response: str,
        reference_corpus: List[str],
    ) -> CompletenessResult:
        """Deterministic local coverage evaluation using aspect extraction and semantic matching."""
        aspects = self._decompose_question_requirements(question)
        ans_clean = ai_response.strip()
        ans_lower = ans_clean.lower()
        ans_words = set(re.findall(r"\b[a-zA-Z]{3,}\b", ans_lower))

        stop_words = {
            "what", "is", "are", "was", "were", "the", "a", "an", "and", "or", "in", "of", "to", "for",
            "on", "with", "at", "by", "from", "can", "you", "does", "did", "how", "why", "who", "which",
            "when", "where", "whom", "tell", "explain", "describe", "about", "into", "over"
        }

        # Embeddings of AI response sentences
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", ans_clean) if len(s.strip()) > 5]
        if not sentences:
            sentences = [ans_clean]
        sentence_vecs = [embedder.embed_text(s) for s in sentences]

        addressed_aspects: List[str] = []
        missing_aspects: List[str] = []
        insufficient_aspects: List[str] = []

        aspect_coverage_scores: List[float] = []

        for aspect in aspects:
            asp_clean = aspect.strip()
            asp_lower = asp_clean.lower()
            asp_vec = embedder.embed_text(asp_clean)

            # Max similarity of this aspect against any sentence in AI response
            max_sim = max(
                sum(a * b for a, b in zip(asp_vec, s_vec))
                for s_vec in sentence_vecs
            ) if sentence_vecs else 0.0

            # Lexical keyword overlap with morphological inflection support (plurals and verb tenses)
            asp_keywords = {w for w in re.findall(r"\b[a-zA-Z]{3,}\b", asp_lower) if w not in stop_words}
            matched_keywords = 0
            for kw in asp_keywords:
                if kw in ans_words:
                    matched_keywords += 1
                    continue
                # Inflection check (e.g., produce -> produces/producing/produced)
                inflections = {kw + "s", kw + "es", kw + "d", kw + "ed", kw + "ing"}
                if kw.endswith("e"):
                    inflections.add(kw[:-1] + "ing")
                    inflections.add(kw[:-1] + "ed")
                if kw.endswith("ing") and len(kw) > 5:
                    inflections.add(kw[:-3])
                    inflections.add(kw[:-3] + "e")
                if kw.endswith("ed") and len(kw) > 4:
                    inflections.add(kw[:-2])
                    inflections.add(kw[:-1])
                if kw.endswith("s") and len(kw) > 3:
                    inflections.add(kw[:-1])

                if any(inf in ans_words for inf in inflections):
                    matched_keywords += 1

            overlap = matched_keywords / max(1, len(asp_keywords)) if asp_keywords else 0.5

            # Combined coverage score for this aspect (0.0 to 1.0)
            aspect_score = (max_sim * 0.65) + (overlap * 0.35)
            aspect_coverage_scores.append(aspect_score)

            if aspect_score >= 0.52:
                addressed_aspects.append(asp_clean)
            elif aspect_score >= 0.38:
                # Partially addressed or brief mention
                addressed_aspects.append(f"{asp_clean} (partially addressed)")
                insufficient_aspects.append(asp_clean)
            else:
                missing_aspects.append(asp_clean)

        total_aspects = len(aspects)
        fully_addressed_count = len(addressed_aspects) - len(insufficient_aspects)
        coverage_ratio = sum(aspect_coverage_scores) / max(1, total_aspects)

        # Factor in response elaboration depth
        word_count = len(ans_clean.split())
        is_overly_brief = word_count < 6 and total_aspects >= 1

        # Check reference corpus for omitted key facts if single question
        if reference_corpus and total_aspects == 1 and not missing_aspects:
            ref_combined = " ".join(reference_corpus[:2]).lower()
            ref_keywords = {w for w in re.findall(r"\b[a-zA-Z]{4,}\b", ref_combined) if w not in stop_words}
            if ref_keywords:
                missed_ref_keywords = [w for w in ref_keywords if w not in ans_words]
                # If AI response is very short and missed more than 60% of reference content
                if is_overly_brief and len(missed_ref_keywords) > 5:
                    missing_aspects.append("Comprehensive explanation and supporting details")
                    coverage_ratio = min(coverage_ratio, 0.45)

        # Scale 1-5 determination
        if coverage_ratio >= 0.72 and len(missing_aspects) == 0 and not is_overly_brief:
            score = 5
            status = "COMPLETE"
            reasoning = "Fully complete: The response thoroughly addresses all identified requirements and facets of the inquiry."
        elif coverage_ratio >= 0.55 and len(missing_aspects) <= 1 and not is_overly_brief:
            score = 4
            status = "COMPLETE"
            if missing_aspects:
                reasoning = f"Mostly complete: The main requirements are addressed, though minor details regarding '{missing_aspects[0]}' were omitted."
            else:
                reasoning = "Mostly complete: Core questions are answered with adequate coverage across stated points."
        elif coverage_ratio >= 0.38 and (len(addressed_aspects) >= len(missing_aspects) or coverage_ratio >= 0.45):
            score = 3
            status = "PARTIAL"
            missing_str = ", ".join(f"'{m}'" for m in missing_aspects) if missing_aspects else "extended context"
            reasoning = f"Partially complete: Some requirements are addressed, but significant aspects remain unanswered: {missing_str}."
        elif coverage_ratio >= 0.18 or len(addressed_aspects) > 0:
            score = 2
            status = "INCOMPLETE"
            reasoning = "Substantially incomplete: The response leaves most required aspects and sub-questions unanswered or provides insufficient explanation."
        else:
            score = 1
            status = "INCOMPLETE"
            reasoning = "Completely incomplete: The response fails to address the core subject or expected requirements of the inquiry."

        if not addressed_aspects and not missing_aspects:
            if score >= 4:
                addressed_aspects = [question]
            else:
                missing_aspects = [question]

        return CompletenessResult(
            score=score,
            status=status,
            addressed_aspects=addressed_aspects,
            missing_aspects=missing_aspects,
            reasoning=reasoning,
        )


# Global singleton instance
completeness_judge = CompletenessJudgeAgent()
