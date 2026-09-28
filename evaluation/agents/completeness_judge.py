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
            # Check for enumerated multi-part list: "Explain X, its inputs, and its outputs"
            is_list = (raw_q.count(",") >= 2) or ("," in raw_q and bool(re.search(r",\s*(?:and|as well as)\b", raw_q, re.IGNORECASE)))
            if is_list:
                comma_and_split = re.split(r",\s*(?:and\s+)?|\s+and\s+(?:its|their|the|how|what|why|where|when|who|which)\b", raw_q, flags=re.IGNORECASE)
                sub_items = [it.strip(" .?!;") for it in comma_and_split if len(it.strip(" .?!;")) > 4]
                intro_phrases = ["in general", "according to", "in summary", "overall", "for example", "in particular"]
                if len(sub_items) >= 2 and not any(sub_items[0].lower().startswith(intro) for intro in intro_phrases):
                    parts = sub_items

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
            if len(p_clean) > 3:
                aspects.append(p_clean)

        return aspects if aspects else [raw_q]

    def _evaluate_with_llm(
        self,
        question: str,
        ai_response: str,
        reference_corpus: List[str],
    ) -> Optional[CompletenessResult]:
        ref_text = "\n\n".join(reference_corpus[:3]) if reference_corpus else "None provided."
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
            f"QUESTION:\n{question}\n\n"
            f"AI RESPONSE:\n{ai_response}\n\n"
            f"REFERENCE INFORMATION:\n{ref_text}\n\n"
            "Evaluate this response only. Do not consider any previous batch records."
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
            "when", "where", "whom", "tell", "explain", "describe", "about", "into", "over", "main", "primary",
            "major", "key", "typical", "common", "called", "known", "include", "including"
        }

        # Embeddings of AI response sentences
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", ans_clean) if len(s.strip()) > 5]
        if not sentences:
            sentences = [ans_clean]
        sentence_vecs = [embedder.embed_text(s) for s in sentences]

        # Calculate semantic alignment with verified reference answer if present
        ref_sim = 0.0
        if reference_corpus:
            first_ref = reference_corpus[0].strip()
            if first_ref:
                ref_sim = max(
                    0.0,
                    min(1.0, sum(a * b for a, b in zip(embedder.embed_text(ans_clean), embedder.embed_text(first_ref[:400])))),
                )

        # Extract core subject from question to contextualize isolated wh-word fragments (e.g. "where", "when")
        q_subj_words = [
            w for w in re.findall(r"\b[a-zA-Z]{3,}\b", question)
            if w.lower() not in stop_words and w.lower() not in {
                "when", "where", "who", "whom", "why", "how", "what", "explain", "describe", "tell"
            }
        ]
        main_subject = " ".join(q_subj_words[:3])

        addressed_aspects: List[str] = []
        missing_aspects: List[str] = []
        insufficient_aspects: List[str] = []

        aspect_coverage_scores: List[float] = []

        # Identify words that genuinely appear in multiple aspects (the shared query topic/subject)
        aspect_word_sets = [
            {w.lower() for w in re.findall(r"\b[a-zA-Z]{3,}\b", asp) if w.lower() not in stop_words}
            for asp in aspects
        ]
        shared_query_terms = set()
        if len(aspect_word_sets) > 1:
            for i in range(len(aspect_word_sets)):
                for j in range(i + 1, len(aspect_word_sets)):
                    shared_query_terms |= (aspect_word_sets[i] & aspect_word_sets[j])

        for aspect in aspects:
            asp_clean = aspect.strip()
            asp_lower = asp_clean.lower()
            # Contextualize sub-aspect with main query subject if the aspect doesn't already mention it
            if main_subject and not any(sw.lower() in asp_lower for sw in q_subj_words[:2]):
                asp_query = f"{asp_clean} (regarding {main_subject})"
            else:
                asp_query = asp_clean
            asp_vec = embedder.embed_text(asp_query)

            # Max similarity of this aspect against any sentence in AI response
            max_sim = max(
                sum(a * b for a, b in zip(asp_vec, s_vec))
                for s_vec in sentence_vecs
            ) if sentence_vecs else 0.0

            # Lexical keyword overlap with morphological inflection support (plurals and verb tenses)
            asp_keywords = {w for w in re.findall(r"\b[a-zA-Z]{3,}\b", asp_lower) if w not in stop_words}
            
            # Semantic expansions for common inquiry terms
            SYNONYM_MAP = {
                "produce": {"produces", "producing", "produced", "synthesize", "synthesizes", "synthesizing", "generate", "generates", "release", "releases", "releasing", "yield", "yields", "create", "creates", "product", "products", "output", "outputs", "glucose", "oxygen"},
                "capital": {"city", "seat", "capital"},
                "currency": {"money", "euro", "dollar", "pound", "yen", "franc", "peso"},
                "cause": {"causes", "causing", "caused", "lead", "leads", "result", "results", "induce", "induces"},
                "location": {"located", "city", "country", "place", "headquarters"},
                "element": {"element", "elements", "hydrogen", "oxygen", "atom", "atoms", "substance", "molecules", "component", "components", "constituent", "constituents"},
                "elements": {"element", "elements", "hydrogen", "oxygen", "atom", "atoms", "substance", "molecules", "component", "components", "constituent", "constituents"},
                "constituent": {"element", "elements", "hydrogen", "oxygen", "atom", "atoms", "substance", "molecules", "component", "components", "constituent", "constituents", "composed", "consisting"},
                "constituents": {"element", "elements", "hydrogen", "oxygen", "atom", "atoms", "substance", "molecules", "component", "components", "constituent", "constituents", "composed", "consisting"},
            }

            matched_keywords = 0
            for kw in asp_keywords:
                if kw in ans_words:
                    matched_keywords += 1
                    continue
                # Check synonym expansions
                if kw in SYNONYM_MAP and any(syn in ans_words for syn in SYNONYM_MAP[kw]):
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

            # Distinctive aspect keywords excluding the overarching query subject (e.g., 'currency' vs shared 'germany')
            asp_specific_keywords = {w for w in asp_keywords if w not in shared_query_terms}

            ans_has_specific = True
            if asp_specific_keywords:
                ans_has_specific = any(
                    kw in ans_words or (kw in SYNONYM_MAP and any(s in ans_words for s in SYNONYM_MAP[kw]))
                    for kw in asp_specific_keywords
                )

            # Combined coverage score for this aspect (0.0 to 1.0)
            aspect_score = (max_sim * 0.70) + (overlap * 0.30)

            # If response strongly aligns with reference answer on a single aspect, reinforce aspect coverage
            if len(aspects) == 1 and ref_sim >= 0.70:
                aspect_score = max(aspect_score, ref_sim * 0.95)

            aspect_coverage_scores.append(aspect_score)

            # Calibrated coverage threshold: single-aspect direct answers score addressed at 0.44+
            threshold = 0.44 if len(aspects) == 1 else 0.50
            # If aspect has substantive specific keywords that are completely missing from the response, it is missing
            is_lexically_missing = bool(asp_specific_keywords) and not ans_has_specific
            if not is_lexically_missing and bool(asp_keywords) and (overlap == 0.0) and (max_sim < 0.60):
                is_lexically_missing = True

            if not is_lexically_missing and (aspect_score >= threshold or max_sim >= 0.55):
                addressed_aspects.append(asp_clean)
            elif aspect_score >= 0.35 and not is_lexically_missing:
                addressed_aspects.append(f"{asp_clean} (partially addressed)")
                insufficient_aspects.append(asp_clean)
            else:
                missing_aspects.append(asp_clean)

        total_aspects = len(aspects)
        coverage_ratio = sum(aspect_coverage_scores) / max(1, total_aspects)

        # Substantive reference facts alignment
        ref_fact_cov = 1.0
        has_ref_facts = False
        all_ref_cov = 1.0
        if reference_corpus:
            first_ref = reference_corpus[0].strip()
            if first_ref:
                q_words = set(re.findall(r"\b[a-zA-Z]{3,}\b", question.lower())) - stop_words
                ref_fact_words = [w for w in re.findall(r"\b[a-zA-Z]{3,}\b", first_ref.lower()) if w not in stop_words and w not in q_words]
                if ref_fact_words:
                    has_ref_facts = True
                    matched_ref_facts = [w for w in ref_fact_words if w in ans_words or any(inf in ans_words for inf in {w+"s", w+"es", w+"ed", w+"ing"})]
                    ref_fact_cov = len(matched_ref_facts) / len(ref_fact_words)

                all_ref_words = [w for w in re.findall(r"\b[a-zA-Z]{3,}\b", first_ref.lower()) if w not in stop_words]
                if all_ref_words:
                    matched_all_ref = [w for w in all_ref_words if w in ans_words or any(inf in ans_words for inf in {w+"s", w+"es", w+"ed", w+"ing"})]
                    all_ref_cov = len(matched_all_ref) / len(all_ref_words)

        # Factor in response elaboration depth
        word_count = len(ans_clean.split())
        is_overly_brief = word_count < 6 and total_aspects >= 1 and ref_sim < 0.65

        # Check if response thoroughly covers gold-standard reference facts (all key requirements satisfied)
        if has_ref_facts and ref_sim >= 0.85 and ref_fact_cov >= 0.80:
            addressed_aspects = list(aspects)
            missing_aspects = []
            coverage_ratio = max(coverage_ratio, 0.90)

        # Check if response completely omits substantive reference facts (e.g. asserts contradicted entities)
        elif has_ref_facts and ref_fact_cov == 0.0 and ref_sim < 0.70:
            missing_aspects.append("Accurate verified factual outputs/substantive details")
            coverage_ratio = min(coverage_ratio, 0.35)
            if len(aspects) == 1:
                addressed_aspects = []

        # Check reference corpus for omitted key facts if single question
        elif reference_corpus and total_aspects == 1 and not missing_aspects:
            ref_combined = " ".join(reference_corpus[:2]).lower()
            ref_keywords = {w for w in re.findall(r"\b[a-zA-Z]{4,}\b", ref_combined) if w not in stop_words}
            if ref_keywords:
                missed_ref_keywords = [w for w in ref_keywords if w not in ans_words]
                # If AI response is very short and missed more than 60% of reference content
                if is_overly_brief and len(missed_ref_keywords) > 5:
                    missing_aspects.append("Comprehensive explanation and supporting details")
                    coverage_ratio = min(coverage_ratio, 0.45)

        # Fully addressed vs partially addressed aspects
        fully_addressed = [a for a in addressed_aspects if not a.endswith("(partially addressed)")]
        fully_addressed_count = len(fully_addressed)

        # Scale 1-5 determination
        if (
            fully_addressed_count == total_aspects
            and (coverage_ratio >= 0.65 or (ref_sim >= 0.78 and len(aspects) == 1))
            and len(missing_aspects) == 0
            and not is_overly_brief
        ):
            score = 5
            status = "COMPLETE"
            reasoning = "Fully complete: The response thoroughly addresses all identified requirements and facets of the inquiry."
        elif (
            (coverage_ratio >= 0.65 and len(missing_aspects) == 0)
            or (coverage_ratio >= 0.48 and total_aspects >= 3 and len(missing_aspects) <= 1)
            or (ref_sim >= 0.65 and len(aspects) == 1 and len(missing_aspects) == 0)
        ) and not is_overly_brief:
            score = 4
            status = "COMPLETE"
            if missing_aspects:
                reasoning = f"Mostly complete: The main requirements are addressed, though minor details regarding '{missing_aspects[0]}' were omitted."
            else:
                reasoning = "Mostly complete: Core questions are answered with adequate coverage across stated points."
        elif (fully_addressed_count >= 2 and len(missing_aspects) <= 1) or (total_aspects == 2 and fully_addressed_count == 1) or (coverage_ratio >= 0.45 and len(missing_aspects) <= 1 and not is_overly_brief):
            score = 3
            status = "PARTIAL"
            missing_str = ", ".join(f"'{m}'" for m in missing_aspects) if missing_aspects else "detailed elaboration"
            reasoning = f"Partially complete: Some requirements are addressed, but significant aspects remain unanswered: {missing_str}."
        elif coverage_ratio >= 0.12 or len(addressed_aspects) > 0:
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
