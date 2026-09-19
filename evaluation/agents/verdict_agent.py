"""Verdict Agent and Weighted Scoring Engine for PROOFRAG.

Synthesizes the four evaluation dimensions:
1. Accuracy (35%)
2. Hallucination Safety (30%)
3. Relevance (20%)
4. Completeness (15%)

Computes transparent normalized contributions, enforces critical-issue overrides
(severe hallucinations or factual contradictions block PASS), and generates
consolidated justification.
"""

import logging
from typing import Any, Dict, List, Optional
from backend.config import (
    VERDICT_NEEDS_IMPROVEMENT_THRESHOLD,
    VERDICT_PASS_THRESHOLD,
    WEIGHT_ACCURACY,
    WEIGHT_COMPLETENESS,
    WEIGHT_HALLUCINATION,
    WEIGHT_RELEVANCE,
)
from evaluation.schemas import VerdictResult

logger = logging.getLogger("proofrag.verdict_agent")


class VerdictAgent:
    """Multi-agent evaluation synthesizer and transparent weighted verdict engine."""

    def __init__(
        self,
        weight_accuracy: Optional[float] = None,
        weight_hallucination: Optional[float] = None,
        weight_relevance: Optional[float] = None,
        weight_completeness: Optional[float] = None,
        pass_threshold: Optional[int] = None,
        needs_improvement_threshold: Optional[int] = None,
    ):
        self.w_accuracy = weight_accuracy if weight_accuracy is not None else WEIGHT_ACCURACY
        self.w_hallucination = weight_hallucination if weight_hallucination is not None else WEIGHT_HALLUCINATION
        self.w_relevance = weight_relevance if weight_relevance is not None else WEIGHT_RELEVANCE
        self.w_completeness = weight_completeness if weight_completeness is not None else WEIGHT_COMPLETENESS

        self.pass_threshold = pass_threshold if pass_threshold is not None else VERDICT_PASS_THRESHOLD
        self.needs_improvement_threshold = (
            needs_improvement_threshold if needs_improvement_threshold is not None else VERDICT_NEEDS_IMPROVEMENT_THRESHOLD
        )

    def synthesize_verdict(
        self,
        accuracy_result: Dict[str, Any],
        relevance_result: Dict[str, Any],
        hallucination_result: Dict[str, Any],
        completeness_result: Optional[Dict[str, Any]] = None,
    ) -> VerdictResult:
        """Synthesize all evaluation dimensions into transparent weighted score and final verdict."""
        completeness_data = completeness_result or {
            "score": 4,
            "status": "COMPLETE",
            "addressed_aspects": [],
            "missing_aspects": [],
            "reasoning": "Default coverage",
        }

        # 1. Extract raw scores
        acc_raw = accuracy_result.get("score")
        acc_score = int(acc_raw) if acc_raw is not None else 3
        rel_raw = relevance_result.get("score")
        rel_score = int(rel_raw) if rel_raw is not None else 3
        comp_raw = completeness_data.get("score")
        comp_score = int(comp_raw) if comp_raw is not None else 3

        hal_status = str(hallucination_result.get("hallucination_status", "NONE")).upper()
        hal_risk = str(hallucination_result.get("risk_level", "LOW")).upper()
        flagged_claims = hallucination_result.get("flagged_claims", []) or []

        has_contradicted = any(
            (c.get("status") if isinstance(c, dict) else getattr(c, "status", "")) == "CONTRADICTED"
            for c in flagged_claims
        )

        # 2. Consistent normalization to 0.0 - 1.0 range
        acc_norm = max(0.0, min(1.0, acc_score / 5.0))
        rel_norm = max(0.0, min(1.0, rel_score / 5.0))
        comp_norm = max(0.0, min(1.0, comp_score / 5.0))

        if has_contradicted or hal_risk == "HIGH" or hal_status == "HIGH":
            hal_safety = 0.0
        elif hal_risk == "MEDIUM" or hal_status == "PARTIAL":
            hal_safety = 0.5
        else:
            hal_safety = 1.0

        # 3. Weighted score calculation
        w_total = self.w_accuracy + self.w_hallucination + self.w_relevance + self.w_completeness
        # Normalize weights if they do not sum to 1.0
        w_acc = self.w_accuracy / w_total
        w_hal = self.w_hallucination / w_total
        w_rel = self.w_relevance / w_total
        w_comp = self.w_completeness / w_total

        raw_overall = (
            (acc_norm * w_acc)
            + (hal_safety * w_hal)
            + (rel_norm * w_rel)
            + (comp_norm * w_comp)
        ) * 100.0

        overall_score = max(0, min(100, int(round(raw_overall))))

        # 4. Dimension contributions to overall score
        contributions = {
            "accuracy": round(acc_norm * w_acc * 100.0, 1),
            "hallucination": round(hal_safety * w_hal * 100.0, 1),
            "relevance": round(rel_norm * w_rel * 100.0, 1),
            "completeness": round(comp_norm * w_comp * 100.0, 1),
        }

        # 5. Identify Major Strengths and Major Issues
        major_strengths: List[str] = []
        major_issues: List[str] = []

        if acc_score >= 4:
            major_strengths.append(f"Strong factual accuracy ({acc_score}/5) grounded in reference evidence.")
        if rel_score >= 4:
            major_strengths.append(f"High topical relevance ({rel_score}/5) addressing the core inquiry.")
        if comp_score >= 4:
            major_strengths.append(f"Comprehensive coverage ({comp_score}/5) of inquiry requirements.")
        if hal_safety == 1.0 and not has_contradicted:
            major_strengths.append("Zero hallucination risk detected across evaluated claims.")

        if has_contradicted:
            major_issues.append("Direct factual contradiction detected conflicting with verified reference evidence.")
        if acc_score <= 2:
            major_issues.append(f"Low factual accuracy ({acc_score}/5): response contains incorrect statements.")
        if hal_risk == "HIGH" or hal_status == "HIGH":
            major_issues.append("High hallucination risk: assertions lack reference corroboration.")
        if rel_score <= 2:
            major_issues.append(f"Low topical relevance ({rel_score}/5): response is largely off-topic.")
        if comp_score <= 2:
            missing_items = completeness_data.get("missing_aspects", [])
            missing_text = f" (missing: {', '.join(missing_items[:2])})" if missing_items else ""
            major_issues.append(f"Substantial incompleteness ({comp_score}/5): major requirements unanswered{missing_text}.")

        # 6. Critical-Issue Handling & Final Verdict Assignment
        critical_issues_detected = False
        critical_override_applied = False
        critical_override_reason = ""
        verdict = "NEEDS IMPROVEMENT"
        consolidated_reasoning = ""

        # Severe Critical Failure Conditions -> Strictly FAIL
        if has_contradicted or acc_score <= 2:
            critical_issues_detected = True
            critical_override_applied = True
            verdict = "FAIL"
            critical_override_reason = (
                "Severe factual contradiction detected conflicting with verified reference evidence."
                if has_contradicted else
                f"Low factual accuracy ({acc_score}/5) triggers mandatory critical FAIL override."
            )
            consolidated_reasoning = (
                "Critical factual failure: The response contains factual contradictions or fundamental "
                "inaccuracies conflicting with reference evidence. Cannot pass despite other dimension scores."
            )
        elif rel_score <= 2:
            critical_issues_detected = True
            critical_override_applied = True
            verdict = "FAIL"
            critical_override_reason = f"Severe topical irrelevance ({rel_score}/5) triggers mandatory critical FAIL override."
            consolidated_reasoning = (
                f"Critical relevance failure: The response is off-topic or fails to address the question "
                f"(Relevance: {rel_score}/5)."
            )
        elif hal_risk == "HIGH" or hal_status == "HIGH":
            critical_issues_detected = True
            critical_override_applied = True
            verdict = "FAIL"
            critical_override_reason = "High hallucination risk: significant ungrounded or fabricated assertions."
            consolidated_reasoning = (
                "Critical hallucination failure: High hallucination risk detected with significant ungrounded "
                "or fabricated assertions."
            )
        else:
            # Baseline threshold evaluation
            if overall_score >= self.pass_threshold:
                # Moderate issue check: cannot PASS if accuracy is mediocre, hallucination is medium, or relevance is low
                if acc_score < 4 or hal_safety < 1.0 or rel_score < 3:
                    critical_issues_detected = True
                    critical_override_applied = True
                    verdict = "NEEDS IMPROVEMENT"
                    critical_override_reason = (
                        f"Overall weighted score ({overall_score}/100) met pass threshold, but PASS was withheld "
                        f"due to quality concerns (Accuracy: {acc_score}/5, Hallucination Safety: {int(hal_safety * 100)}%)."
                    )
                    consolidated_reasoning = (
                        f"Overall weighted score ({overall_score}/100) is high, but PASS is withheld due to "
                        f"moderate concerns (Accuracy: {acc_score}/5, Hallucination Safety: {hal_safety * 100:.0f}%)."
                    )
                else:
                    verdict = "PASS"
                    consolidated_reasoning = (
                        f"Passed verification (Score: {overall_score}/100). High accuracy ({acc_score}/5), "
                        f"relevance ({rel_score}/5), and completeness ({comp_score}/5) with claims grounded in reference evidence."
                    )
            elif overall_score >= self.needs_improvement_threshold:
                verdict = "NEEDS IMPROVEMENT"
                consolidated_reasoning = (
                    f"Needs improvement (Score: {overall_score}/100). The response contains partially grounded "
                    f"elements or notable omissions requiring refinement before deployment."
                )
            else:
                verdict = "FAIL"
                consolidated_reasoning = (
                    f"Failed verification (Score: {overall_score}/100, below threshold of {self.needs_improvement_threshold}). "
                    f"Low composite scores across key evaluation dimensions."
                )

        return VerdictResult(
            overall_score=overall_score,
            verdict=verdict,
            dimension_scores={
                "accuracy": acc_score,
                "relevance": rel_score,
                "hallucination": hal_risk,
                "completeness": comp_score,
            },
            normalized_scores={
                "accuracy": round(acc_norm, 3),
                "relevance": round(rel_norm, 3),
                "hallucination": round(hal_safety, 3),
                "completeness": round(comp_norm, 3),
            },
            weighted_contributions=contributions,
            weights={
                "accuracy": round(w_acc, 2),
                "hallucination": round(w_hal, 2),
                "relevance": round(w_rel, 2),
                "completeness": round(w_comp, 2),
            },
            major_strengths=major_strengths,
            major_issues=major_issues,
            consolidated_reasoning=consolidated_reasoning,
            verdict_reasoning=consolidated_reasoning,
            critical_issues_detected=critical_issues_detected,
            critical_override_applied=critical_override_applied,
            critical_override_reason=critical_override_reason,
        )


# Global singleton instance
verdict_agent = VerdictAgent()
