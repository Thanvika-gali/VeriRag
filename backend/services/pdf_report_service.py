"""Milestone 4.2: PDF Evaluation Report Export Service.

Generates professional, publication-ready multi-page PDF evaluation audit reports
using ReportLab with auto-wrapping, multi-page table pagination, executive summaries,
dimension breakdowns, per-record audit matrices, and detailed problematic case investigations.
"""

import io
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

logger = logging.getLogger("proofrag.pdf_report")


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute and stamp total page count: 'Page X of Y'."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, total_pages: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))

        # Running Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, 750, "PROOFRAG — Evidence-Grounded AI Response Validation Audit")
            self.drawRightString(612 - 54, 750, f"Confidential Audit Report | Page {self._pageNumber} of {total_pages}")
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.5)
            self.line(54, 742, 612 - 54, 742)

        # Running Footer (all pages)
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        self.line(54, 45, 612 - 54, 45)

        self.drawString(54, 32, "PROOFRAG Validation Platform | TruthfulQA & SQuAD Reference Evaluation Engine")
        page_str = f"Page {self._pageNumber} of {total_pages}"
        self.drawRightString(612 - 54, 32, page_str)

        self.restoreState()


class PDFReportService:
    """Service generating comprehensive executive PDF evaluation reports."""

    def __init__(self):
        self._init_styles()

    def _init_styles(self):
        styles = getSampleStyleSheet()

        self.style_title = ParagraphStyle(
            "DocTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=4,
        )

        self.style_subtitle = ParagraphStyle(
            "DocSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#475569"),
            spaceAfter=14,
        )

        self.style_h1 = ParagraphStyle(
            "SectionH1",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#1e293b"),
            spaceBefore=14,
            spaceAfter=8,
            keepWithNext=True,
        )

        self.style_h2 = ParagraphStyle(
            "SectionH2",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=15,
            textColor=colors.HexColor("#334155"),
            spaceBefore=10,
            spaceAfter=4,
            keepWithNext=True,
        )

        self.style_body = ParagraphStyle(
            "BodyDark",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor("#334155"),
        )

        self.style_bold = ParagraphStyle(
            "BodyBold",
            parent=self.style_body,
            fontName="Helvetica-Bold",
        )

        self.style_muted = ParagraphStyle(
            "BodyMuted",
            parent=self.style_body,
            textColor=colors.HexColor("#64748b"),
            fontSize=8,
            leading=11,
        )

        self.style_cell = ParagraphStyle(
            "TableCell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10.5,
            textColor=colors.HexColor("#1e293b"),
        )

        self.style_cell_bold = ParagraphStyle(
            "TableCellBold",
            parent=self.style_cell,
            fontName="Helvetica-Bold",
        )

        self.style_cell_header = ParagraphStyle(
            "TableCellHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10.5,
            textColor=colors.white,
        )

        self.style_badge_pass = ParagraphStyle(
            "BadgePass",
            parent=self.style_cell_bold,
            textColor=colors.HexColor("#15803d"),
        )
        self.style_badge_review = ParagraphStyle(
            "BadgeReview",
            parent=self.style_cell_bold,
            textColor=colors.HexColor("#b45309"),
        )
        self.style_badge_fail = ParagraphStyle(
            "BadgeFail",
            parent=self.style_cell_bold,
            textColor=colors.HexColor("#b91c1c"),
        )

    def generate_pdf_report(
        self,
        report_data: Dict[str, Any],
    ) -> bytes:
        """Construct full PDF audit report document in-memory and return as raw bytes."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=54,
            rightMargin=54,
            topMargin=54,
            bottomMargin=54,
        )

        story: List[Any] = []

        report_mode = report_data.get("report_mode", "Batch Verification Report")
        batch_id = report_data.get("batch_id")
        batch_info = report_data.get("batch_info") or {}
        evaluations = report_data.get("evaluations", [])
        stats = report_data.get("stats") or {}
        total_records = len(evaluations)

        now_str = datetime.now(timezone.utc).strftime("%B %d, %Y - %H:%M UTC")

        # ----------------------------------------------------------------------
        # 1. Header & Title Block
        # ----------------------------------------------------------------------
        story.append(Paragraph("PROOFRAG", self.style_title))
        story.append(Paragraph("AI Response Validation & Multi-Agent Audit Report", self.style_subtitle))

        # Metadata Card
        meta_table_data = [
            [
                Paragraph("<b>Audit Mode:</b>", self.style_cell),
                Paragraph(report_mode, self.style_cell),
                Paragraph("<b>Generated:</b>", self.style_cell),
                Paragraph(now_str, self.style_cell),
            ],
            [
                Paragraph("<b>Batch / Job ID:</b>", self.style_cell),
                Paragraph(str(batch_id or "Single Evaluation Archive"), self.style_cell),
                Paragraph("<b>Total Records:</b>", self.style_cell),
                Paragraph(str(total_records), self.style_cell_bold),
            ],
            [
                Paragraph("<b>Source File:</b>", self.style_cell),
                Paragraph(str(batch_info.get("filename") or "Manual Submission"), self.style_cell),
                Paragraph("<b>Engine Version:</b>", self.style_cell),
                Paragraph("PROOFRAG v2.0 (ChromaDB + Sentence-Transformers)", self.style_cell),
            ],
        ]

        meta_table = Table(meta_table_data, colWidths=[90, 160, 85, 169])
        meta_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#f1f5f9")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 14))

        # If empty
        if total_records == 0:
            story.append(Paragraph("No evaluation records found matching the requested scope.", self.style_body))
            doc.build(story, canvasmaker=NumberedCanvas)
            return buffer.getvalue()

        # Compute or extract executive statistics
        verdicts = stats.get("verdicts", {})
        pass_cnt = verdicts.get("PASS", 0)
        rev_cnt = verdicts.get("NEEDS IMPROVEMENT", 0)
        fail_cnt = verdicts.get("FAIL", 0)

        # Fallback if stats dict is absent
        if not stats or ("PASS" not in verdicts and total_records > 0):
            pass_cnt = sum(1 for e in evaluations if e.get("verdict") == "PASS")
            rev_cnt = sum(1 for e in evaluations if e.get("verdict") in ("NEEDS IMPROVEMENT", "REVIEW"))
            fail_cnt = sum(1 for e in evaluations if e.get("verdict") == "FAIL")

        pass_pct = round((pass_cnt / total_records) * 100, 1) if total_records > 0 else 0.0
        rev_pct = round((rev_cnt / total_records) * 100, 1) if total_records > 0 else 0.0
        fail_pct = round((fail_cnt / total_records) * 100, 1) if total_records > 0 else 0.0

        scores = [e.get("overall_score") for e in evaluations if e.get("overall_score") is not None]
        avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0

        dim_avg = stats.get("dimension_averages", {})
        avg_acc = dim_avg.get("accuracy")
        avg_rel = dim_avg.get("relevance")
        avg_comp = dim_avg.get("completeness")
        avg_hal_safety = dim_avg.get("hallucination_safety")

        if avg_acc is None:
            accs = [e.get("accuracy_score") for e in evaluations if e.get("accuracy_score") is not None]
            avg_acc = round(sum(accs) / len(accs), 2) if accs else None
        if avg_rel is None:
            rels = [e.get("relevance_score") for e in evaluations if e.get("relevance_score") is not None]
            avg_rel = round(sum(rels) / len(rels), 2) if rels else None
        if avg_comp is None:
            comps = [e.get("completeness_score") for e in evaluations if e.get("completeness_score") is not None]
            avg_comp = round(sum(comps) / len(comps), 2) if comps else None
        if avg_hal_safety is None:
            hals = []
            for e in evaluations:
                hr = (e.get("hallucination_risk") or "LOW").upper()
                hals.append(5.0 if hr == "LOW" else 2.5 if hr == "MEDIUM" else 0.0)
            avg_hal_safety = round(sum(hals) / len(hals), 2) if hals else None

        hal_stats = stats.get("hallucination_stats", {})
        flagged_hal_count = hal_stats.get("flagged_count", sum(1 for e in evaluations if (e.get("hallucination_risk") or "").upper() in ("MEDIUM", "HIGH")))
        hal_frequency = hal_stats.get("frequency_percentage", round((flagged_hal_count / total_records) * 100, 1) if total_records > 0 else 0.0)
        unsupported_claims_cnt = hal_stats.get("unsupported_claims_count", 0)

        comp_stats = stats.get("completeness_stats", {})
        comp_complete_cnt = comp_stats.get("complete_count", sum(1 for e in evaluations if (e.get("completeness_score") or 0) >= 4))
        comp_partial_cnt = comp_stats.get("partially_complete_count", sum(1 for e in evaluations if (e.get("completeness_score") or 0) == 3))
        comp_incomplete_cnt = comp_stats.get("incomplete_count", sum(1 for e in evaluations if e.get("completeness_score") is not None and e.get("completeness_score") <= 2))
        missing_aspect_freq = comp_stats.get("missing_aspect_frequency", 0.0)

        # ----------------------------------------------------------------------
        # 2. Executive Summary
        # ----------------------------------------------------------------------
        story.append(Paragraph("1. Executive Summary", self.style_h1))
        exec_summary_text = (
            f"This audit represents an evidence-grounded verification of <b>{total_records}</b> AI-generated "
            f"response records evaluated against authoritative reference knowledge. Overall, <b>{pass_cnt}</b> "
            f"responses ({pass_pct}%) achieved a <b>PASS</b> verdict, <b>{rev_cnt}</b> ({rev_pct}%) were flagged as "
            f"<b>NEEDS IMPROVEMENT</b>, and <b>{fail_cnt}</b> ({fail_pct}%) received a <b>FAIL</b> verdict. "
            f"The mean overall verification score across all evaluated responses is <b>{avg_score} / 100</b>."
        )
        story.append(Paragraph(exec_summary_text, self.style_body))
        story.append(Spacer(1, 10))

        # Overall Statistics KPIs Grid Table
        kpi_table_data = [
            [
                Paragraph("<b>PASS</b>", self.style_badge_pass),
                Paragraph("<b>NEEDS IMPROVEMENT</b>", self.style_badge_review),
                Paragraph("<b>FAIL</b>", self.style_badge_fail),
                Paragraph("<b>PASS RATE</b>", self.style_cell_bold),
                Paragraph("<b>AVG SCORE</b>", self.style_cell_bold),
            ],
            [
                Paragraph(f"<font size=13 color='#15803d'><b>{pass_cnt}</b></font><br/>{pass_pct}%", self.style_cell),
                Paragraph(f"<font size=13 color='#b45309'><b>{rev_cnt}</b></font><br/>{rev_pct}%", self.style_cell),
                Paragraph(f"<font size=13 color='#b91c1c'><b>{fail_cnt}</b></font><br/>{fail_pct}%", self.style_cell),
                Paragraph(f"<font size=13><b>{pass_pct}%</b></font>", self.style_cell),
                Paragraph(f"<font size=13><b>{avg_score}</b></font> / 100", self.style_cell),
            ],
        ]
        kpi_table = Table(kpi_table_data, colWidths=[100, 114, 90, 100, 100])
        kpi_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#ffffff")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(kpi_table)
        story.append(Spacer(1, 14))

        # ----------------------------------------------------------------------
        # 3. Verification Dimensions Summary
        # ----------------------------------------------------------------------
        story.append(Paragraph("2. Dimension Summary & Calibrated Evaluation", self.style_h1))

        dim_table_data = [
            [
                Paragraph("Dimension", self.style_cell_header),
                Paragraph("Weight", self.style_cell_header),
                Paragraph("Average Score", self.style_cell_header),
                Paragraph("Calibrated Rating", self.style_cell_header),
                Paragraph("Primary Audit Focus", self.style_cell_header),
            ],
            [
                Paragraph("<b>Accuracy</b>", self.style_cell),
                Paragraph("35%", self.style_cell),
                Paragraph(f"{avg_acc} / 5.0" if avg_acc else "—", self.style_cell_bold),
                Paragraph("High Precision" if (avg_acc or 0) >= 4.0 else "Needs Review" if (avg_acc or 0) >= 3.0 else "Critical Risk", self.style_cell),
                Paragraph("Atomic claim-level factual consistency against reference corpus.", self.style_cell),
            ],
            [
                Paragraph("<b>Hallucination Safety</b>", self.style_cell),
                Paragraph("30%", self.style_cell),
                Paragraph(f"{avg_hal_safety} / 5.0" if avg_hal_safety else "—", self.style_cell_bold),
                Paragraph("Safe" if (avg_hal_safety or 0) >= 4.0 else "Moderate Flags" if (avg_hal_safety or 0) >= 2.5 else "Elevated Risk", self.style_cell),
                Paragraph("Detection of ungrounded or contradictory assertions.", self.style_cell),
            ],
            [
                Paragraph("<b>Relevance</b>", self.style_cell),
                Paragraph("20%", self.style_cell),
                Paragraph(f"{avg_rel} / 5.0" if avg_rel else "—", self.style_cell_bold),
                Paragraph("Aligned" if (avg_rel or 0) >= 4.0 else "Topic Drift", self.style_cell),
                Paragraph("Alignment with user prompt intent, avoiding evasion.", self.style_cell),
            ],
            [
                Paragraph("<b>Completeness</b>", self.style_cell),
                Paragraph("15%", self.style_cell),
                Paragraph(f"{avg_comp} / 5.0" if avg_comp else "—", self.style_cell_bold),
                Paragraph("Thorough" if (avg_comp or 0) >= 4.0 else "Partial" if (avg_comp or 0) >= 3.0 else "Incomplete", self.style_cell),
                Paragraph("Coverage of all required sub-questions and key facts.", self.style_cell),
            ],
        ]

        dim_table = Table(dim_table_data, colWidths=[100, 48, 85, 90, 181])
        dim_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#ffffff")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#ffffff"), colors.HexColor("#f8fafc")]),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(dim_table)
        story.append(Spacer(1, 14))

        # ----------------------------------------------------------------------
        # 4. Hallucination & Completeness Deep Dive
        # ----------------------------------------------------------------------
        story.append(Paragraph("3. Hallucination Risk & Completeness Statistics", self.style_h1))

        hal_comp_table_data = [
            [
                Paragraph("<b>Hallucination Statistics</b>", self.style_cell_bold),
                Paragraph(f"Flagged Responses: <b>{flagged_hal_count}</b> ({hal_frequency}%)<br/>Unsupported Claims Identified: <b>{unsupported_claims_cnt}</b>", self.style_cell),
                Paragraph("<b>Completeness Breakdown</b>", self.style_cell_bold),
                Paragraph(f"Complete: <b>{comp_complete_cnt}</b> | Partial: <b>{comp_partial_cnt}</b><br/>Incomplete: <b>{comp_incomplete_cnt}</b> | Missing Aspect Freq: <b>{missing_aspect_freq}%</b>", self.style_cell),
            ],
        ]
        hal_comp_table = Table(hal_comp_table_data, colWidths=[110, 142, 110, 142])
        hal_comp_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(hal_comp_table)
        story.append(Spacer(1, 14))

        # ----------------------------------------------------------------------
        # 5. Per-Record Evaluation Matrix (Multi-Page Table with Word Wrap)
        # ----------------------------------------------------------------------
        story.append(Paragraph("4. Per-Record Evaluation Matrix", self.style_h1))
        story.append(Paragraph(
            "The following table details individual verification scores for all evaluated records. "
            "Scores range from 1 to 5 for dimensions and 0 to 100 for overall weighted score.",
            self.style_body,
        ))
        story.append(Spacer(1, 6))

        matrix_headers = [
            Paragraph("#", self.style_cell_header),
            Paragraph("Question", self.style_cell_header),
            Paragraph("Score", self.style_cell_header),
            Paragraph("Acc", self.style_cell_header),
            Paragraph("Rel", self.style_cell_header),
            Paragraph("Comp", self.style_cell_header),
            Paragraph("Hal. Risk", self.style_cell_header),
            Paragraph("Verdict", self.style_cell_header),
        ]

        matrix_data = [matrix_headers]

        for idx, item in enumerate(evaluations, 1):
            q_text = str(item.get("question") or "")
            if len(q_text) > 85:
                q_text = q_text[:82] + "..."

            verdict = str(item.get("verdict") or "REVIEW")
            if verdict == "PASS":
                v_style = self.style_badge_pass
            elif verdict == "FAIL":
                v_style = self.style_badge_fail
            else:
                v_style = self.style_badge_review

            hal_risk = str(item.get("hallucination_risk") or "LOW").upper()
            hal_color = "#b91c1c" if hal_risk == "HIGH" else "#b45309" if hal_risk == "MEDIUM" else "#15803d"

            row = [
                Paragraph(str(idx), self.style_cell),
                Paragraph(q_text, self.style_cell),
                Paragraph(f"<b>{item.get('overall_score', 0)}</b>", self.style_cell_bold),
                Paragraph(str(item.get("accuracy_score") or "—"), self.style_cell),
                Paragraph(str(item.get("relevance_score") or "—"), self.style_cell),
                Paragraph(str(item.get("completeness_score") or "—"), self.style_cell),
                Paragraph(f"<font color='{hal_color}'><b>{hal_risk}</b></font>", self.style_cell),
                Paragraph(f"<b>{verdict}</b>", v_style),
            ]
            matrix_data.append(row)

        matrix_table = Table(
            matrix_data,
            colWidths=[24, 210, 40, 32, 32, 36, 58, 72],
            repeatRows=1,
        )
        matrix_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("ALIGN", (2, 0), (-1, -1), "CENTER"),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(matrix_table)
        story.append(Spacer(1, 14))

        # ----------------------------------------------------------------------
        # 6. Detailed Findings for Problematic & Flagged Responses
        # ----------------------------------------------------------------------
        problematic_items = [
            e for e in evaluations
            if e.get("verdict") in ("FAIL", "NEEDS IMPROVEMENT", "REVIEW")
            or (e.get("hallucination_risk") or "").upper() in ("MEDIUM", "HIGH")
            or (e.get("accuracy_score") or 5) <= 2
            or (e.get("completeness_score") or 5) <= 2
        ]

        if problematic_items:
            story.append(PageBreak())
            story.append(Paragraph("5. Detailed Findings: Flagged & Problematic Responses", self.style_h1))
            story.append(Paragraph(
                f"A total of <b>{len(problematic_items)}</b> response(s) were flagged with quality deficiencies, "
                f"unsupported assertions, factual contradictions, or significant omissions. "
                f"Detailed breakdowns of the top findings are provided below.",
                self.style_body,
            ))
            story.append(Spacer(1, 10))

            for p_idx, p_item in enumerate(problematic_items[:12], 1):
                eval_res = p_item.get("evaluation_result") or {}
                hal_obj = eval_res.get("hallucination", {})
                acc_obj = eval_res.get("accuracy", {})
                comp_obj = eval_res.get("completeness", {})
                v_details = p_item.get("verdict_details") or eval_res.get("verdict_details", {})

                q_txt = p_item.get("question", "")
                ans_txt = p_item.get("ai_response", "")
                flagged_claims = hal_obj.get("flagged_claims", [])
                missing_aspects = comp_obj.get("missing_aspects", [])
                reasoning = (
                    v_details.get("consolidated_reasoning")
                    or p_item.get("verdict_reasoning")
                    or acc_obj.get("reasoning")
                    or "Verification flagged errors against authoritative reference."
                )

                crit_override = v_details.get("critical_override_applied", False)
                crit_reason = v_details.get("critical_override_reason", "")

                verdict = p_item.get("verdict", "FAIL")
                v_color = "#b91c1c" if verdict == "FAIL" else "#b45309"

                card_elements = []
                header_p = Paragraph(
                    f"<b>Case #{p_idx} | Submission ID: {p_item.get('id', 'N/A')[:8]} | "
                    f"Verdict: <font color='{v_color}'>{verdict}</font> (Score: {p_item.get('overall_score', 0)}/100)</b>",
                    self.style_h2,
                )
                card_elements.append(header_p)

                if crit_override:
                    alert_p = Paragraph(
                        f"<b>CRITICAL OVERRIDE TRIGGERED:</b> {crit_reason}",
                        ParagraphStyle("Alert", parent=self.style_body, textColor=colors.HexColor("#b91c1c"), fontName="Helvetica-Bold"),
                    )
                    card_elements.append(alert_p)

                q_p = Paragraph(f"<b>Question:</b> {q_txt}", self.style_body)
                ans_p = Paragraph(f"<b>AI Response:</b> {ans_txt}", self.style_body)
                card_elements.append(q_p)
                card_elements.append(ans_p)

                if flagged_claims:
                    claims_text = "<br/>• ".join(f"<i>\"{fc.get('claim', fc) if isinstance(fc, dict) else fc}\"</i>" for fc in flagged_claims)
                    claims_p = Paragraph(
                        f"<b>Flagged / Unsupported Claims:</b><br/>• {claims_text}",
                        ParagraphStyle("Claim", parent=self.style_body, textColor=colors.HexColor("#991b1b")),
                    )
                    card_elements.append(claims_p)

                if missing_aspects:
                    miss_text = ", ".join(f"'{m}'" for m in missing_aspects)
                    miss_p = Paragraph(f"<b>Missing Requirements:</b> {miss_text}", self.style_body)
                    card_elements.append(miss_p)

                reason_p = Paragraph(f"<b>Auditor Reasoning:</b> {reasoning}", self.style_muted)
                card_elements.append(reason_p)

                # Wrap case card in single cell Table
                card_table = Table([[card_elements]], colWidths=[504])
                card_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ]))

                story.append(KeepTogether([card_table, Spacer(1, 10)]))

        # ----------------------------------------------------------------------
        # 7. Recommendations & Actionable Guidance
        # ----------------------------------------------------------------------
        story.append(Spacer(1, 6))
        story.append(Paragraph("6. Targeted System Recommendations", self.style_h1))

        recommendations = []
        if fail_cnt > 0 or flagged_hal_count > 0:
            recommendations.append(
                "<b>Enforce Strict RAG Grounding:</b> Responses with hallucination flags contained unverified assertions. "
                "Require the generative model to explicitly cite knowledge base passages and withhold ungrounded answers."
            )
        if (avg_acc or 5.0) < 4.0:
            recommendations.append(
                "<b>Factual Consistency Calibration:</b> Incorporate explicit contradiction-checking guardrails into prompt "
                "templates to catch known misconceptions (e.g. TruthfulQA adversarial questions)."
            )
        if comp_incomplete_cnt > 0 or comp_partial_cnt > 0:
            recommendations.append(
                "<b>Multi-Part Aspect Decomposition:</b> For compound questions, prompt the generative model to systematically "
                "address all sub-questions before completing generation to avoid partial omissions."
            )
        recommendations.append(
            "<b>Periodic Continuous Evaluation:</b> Track quality trends across evaluation batches to detect regression in model outputs."
        )

        rec_table_data = [
            [Paragraph(f"• {rec}", self.style_body)]
            for rec in recommendations
        ]
        rec_table = Table(rec_table_data, colWidths=[504])
        rec_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f0fdf4")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#86efac")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ]))
        story.append(rec_table)
        story.append(Spacer(1, 14))

        # ----------------------------------------------------------------------
        # 8. Final Summary & Sign-Off
        # ----------------------------------------------------------------------
        story.append(Paragraph("7. Final Summary & Certification", self.style_h1))
        final_summary_text = (
            f"This evaluation was computed deterministically by the PROOFRAG Verification Pipeline across {total_records} records. "
            f"All statistics, dimension scores, and hallucination flags reflect real verified reference data. "
            f"Audit Status: <b>{'PASSED' if pass_pct >= 70.0 and fail_pct <= 15.0 else 'ACTION REQUIRED'}</b>."
        )
        story.append(Paragraph(final_summary_text, self.style_body))

        # Build PDF with multi-page NumberedCanvas
        doc.build(story, canvasmaker=NumberedCanvas)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes


# Global singleton instance
pdf_report_service = PDFReportService()
