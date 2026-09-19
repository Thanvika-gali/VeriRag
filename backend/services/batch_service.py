"""Batch Evaluation Service for PROOFRAG.

Coordinates CSV parsing, validation, column alias resolution, robust row-by-row
multi-agent evaluation pipeline execution, aggregate statistics calculation,
and SQLite persistence.
"""

import csv
import io
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from backend.api.schemas import (
    BatchEvaluationResult,
    BatchRecord,
    BatchSummaryStats,
    BatchValidationPreview,
    InvalidRowDetail,
    RetrievedEvidenceItem,
)
from backend.database.sqlite_db import SubmissionDB, db_instance
from evaluation.orchestrator import EvaluationOrchestrator, evaluation_orchestrator

logger = logging.getLogger("proofrag.batch_service")

# Safe column alias mappings (case-insensitive)
COLUMN_ALIASES = {
    "question": [
        "question",
        "prompt",
        "query",
        "input",
        "user_question",
        "inquiry",
        "user_prompt",
    ],
    "ai_response": [
        "ai_response",
        "response",
        "answer",
        "model_output",
        "output",
        "ai_answer",
        "prediction",
        "generated_answer",
    ],
    "reference_answer": [
        "reference_answer",
        "reference",
        "ground_truth",
        "expected_answer",
        "true_answer",
        "target",
        "verified_answer",
    ],
    "source_information": [
        "source_information",
        "source_document",
        "context",
        "document",
        "source",
        "reference_context",
    ],
}


class BatchEvaluationService:
    """Manages CSV batch upload validation, multi-agent evaluation execution, and metrics aggregation."""

    def __init__(
        self,
        orchestrator: Optional[EvaluationOrchestrator] = None,
        db: Optional[SubmissionDB] = None,
    ):
        self.orchestrator = orchestrator or evaluation_orchestrator
        self.db = db or db_instance

    @staticmethod
    def clean_header_name(header: str) -> str:
        """Strip BOM, quotes, whitespace, and normalize spaces/hyphens to underscores."""
        if not header:
            return ""
        h = str(header).strip()
        h = h.lstrip("\ufeff").strip()
        h = h.strip("\"'").strip()
        h = h.lower()
        h = re.sub(r"[\s\-]+", "_", h)
        return h

    def detect_delimiter(self, sample_text: str) -> str:
        """Auto-detect CSV delimiter (comma, semicolon, tab)."""
        if not sample_text:
            return ","
        first_line = sample_text.strip().split("\n")[0] if sample_text else ""
        if ";" in first_line and "," not in first_line:
            return ";"
        if "\t" in first_line and "," not in first_line:
            return "\t"
        try:
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(sample_text[:2048])
            if dialect.delimiter in (",", ";", "\t"):
                return dialect.delimiter
        except Exception:
            pass
        return ","

    def decode_csv_content(self, raw_bytes: bytes) -> str:
        """Decode raw CSV bytes safely using multiple encoding fallbacks and normalize BOM."""
        encodings = ["utf-8-sig", "utf-8", "latin-1", "cp1252"]
        decoded = ""
        for enc in encodings:
            try:
                decoded = raw_bytes.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        if not decoded:
            decoded = raw_bytes.decode("utf-8", errors="replace")
        # Strip leading UTF-8 BOM if present as a character
        return decoded.lstrip("\ufeff")

    def resolve_headers(self, headers: List[str]) -> Tuple[Dict[str, str], List[str]]:
        """Map CSV column headers to canonical field names using alias lookup."""
        normalized_map: Dict[str, str] = {}
        missing_required: List[str] = []

        cleaned_headers = [self.clean_header_name(h) for h in headers]

        for canonical, aliases in COLUMN_ALIASES.items():
            matched_orig = None
            for alias in aliases:
                target = alias.lower()
                for idx, ch in enumerate(cleaned_headers):
                    if ch == target:
                        matched_orig = headers[idx]
                        break
                if matched_orig is not None:
                    break
            if matched_orig is not None:
                normalized_map[canonical] = matched_orig
            elif canonical in ("question", "ai_response"):
                missing_required.append(canonical)

        return normalized_map, missing_required

    def parse_and_validate_csv(
        self, content_str: str
    ) -> Tuple[List[Dict[str, Any]], List[str], List[InvalidRowDetail], Dict[str, str]]:
        """Parse CSV rows, validate required fields, and capture structured malformed row errors."""
        validation_errors: List[str] = []
        invalid_rows: List[InvalidRowDetail] = []
        valid_rows: List[Dict[str, Any]] = []
        col_map: Dict[str, str] = {}

        clean_content = (content_str or "").lstrip("\ufeff").strip()
        if not clean_content:
            err = "CSV file is completely empty."
            validation_errors.append(err)
            invalid_rows.append(InvalidRowDetail(row_number=1, error="Empty File", reason=err))
            return valid_rows, validation_errors, invalid_rows, col_map

        delim = self.detect_delimiter(clean_content)
        f = io.StringIO(clean_content)
        try:
            reader = csv.reader(f, delimiter=delim)
            header_row = next(reader, None)
        except Exception as e:
            err = f"Unable to parse CSV structure: {str(e)}"
            validation_errors.append(err)
            invalid_rows.append(InvalidRowDetail(row_number=1, error="Malformed CSV", reason=err))
            return valid_rows, validation_errors, invalid_rows, col_map

        if not header_row:
            err = "CSV file contains no header row."
            validation_errors.append(err)
            invalid_rows.append(InvalidRowDetail(row_number=1, error="Missing Header", reason=err))
            return valid_rows, validation_errors, invalid_rows, col_map

        header_row = [h.strip() for h in header_row if h is not None]
        col_map, missing_required = self.resolve_headers(header_row)
        if missing_required:
            err = (
                f"Missing required CSV column(s): {', '.join(missing_required)}. "
                f"Supported headers: {', '.join(COLUMN_ALIASES['question'][:3])} and "
                f"{', '.join(COLUMN_ALIASES['ai_response'][:3])}."
            )
            validation_errors.append(err)
            invalid_rows.append(
                InvalidRowDetail(
                    row_number=1,
                    error="Missing required columns",
                    reason=f"Required columns missing: {', '.join(missing_required)}",
                )
            )
            return valid_rows, validation_errors, invalid_rows, col_map

        q_col = col_map["question"]
        ans_col = col_map["ai_response"]
        ref_col = col_map.get("reference_answer")
        src_col = col_map.get("source_information")

        # Map indices safely
        header_indices = {h: i for i, h in enumerate(header_row)}
        q_idx = header_indices[q_col]
        ans_idx = header_indices[ans_col]
        ref_idx = header_indices.get(ref_col) if ref_col else None
        src_idx = header_indices.get(src_col) if src_col else None

        f.seek(0)
        dict_reader = csv.reader(f, delimiter=delim)
        next(dict_reader, None)  # Skip header

        row_num = 1
        for row in dict_reader:
            row_num += 1
            if not row or not any(cell.strip() for cell in row):
                # Ignore pure empty rows silently
                continue

            # Check if row has enough columns
            max_needed = max(q_idx, ans_idx)
            if len(row) <= max_needed:
                err_msg = f"Row {row_num}: Malformed row has fewer columns than required."
                validation_errors.append(err_msg)
                invalid_rows.append(
                    InvalidRowDetail(
                        row_number=row_num,
                        error="Malformed row",
                        reason=f"Row has {len(row)} columns; expected at least {max_needed + 1}.",
                    )
                )
                continue

            q_val = row[q_idx].strip() if q_idx < len(row) else ""
            ans_val = row[ans_idx].strip() if ans_idx < len(row) else ""
            ref_val = row[ref_idx].strip() if ref_idx is not None and ref_idx < len(row) and row[ref_idx].strip() else None
            src_val = row[src_idx].strip() if src_idx is not None and src_idx < len(row) and row[src_idx].strip() else None

            if not q_val and not ans_val:
                err_msg = f"Row {row_num}: Both question and AI response are empty."
                validation_errors.append(err_msg)
                invalid_rows.append(
                    InvalidRowDetail(
                        row_number=row_num,
                        error="Empty question and response",
                        reason="Both question and AI response cells are empty.",
                    )
                )
                continue
            if not q_val:
                err_msg = f"Row {row_num}: Missing question."
                validation_errors.append(err_msg)
                invalid_rows.append(
                    InvalidRowDetail(
                        row_number=row_num,
                        error="Missing question",
                        reason="The question column is empty.",
                    )
                )
                continue
            if not ans_val:
                err_msg = f"Row {row_num}: Missing AI response."
                validation_errors.append(err_msg)
                invalid_rows.append(
                    InvalidRowDetail(
                        row_number=row_num,
                        error="Missing AI response",
                        reason="The AI response column is empty.",
                    )
                )
                continue

            valid_rows.append({
                "record_id": len(valid_rows) + 1,
                "row_number": row_num,
                "question": q_val,
                "ai_response": ans_val,
                "reference_answer": ref_val,
                "source_information": src_val,
            })

        return valid_rows, validation_errors, invalid_rows, col_map

    def validate_csv_preview(
        self, raw_bytes: bytes, filename: str = "batch_upload.csv"
    ) -> BatchValidationPreview:
        """Pre-validate CSV content, resolve aliases, and return preview without executing."""
        content_str = self.decode_csv_content(raw_bytes)
        valid_rows, validation_errors, invalid_rows, col_map = self.parse_and_validate_csv(content_str)

        missing_required: List[str] = []
        if "question" not in col_map:
            missing_required.append("question")
        if "ai_response" not in col_map:
            missing_required.append("ai_response")

        is_valid = len(missing_required) == 0 and len(valid_rows) > 0
        preview_rows = valid_rows[:5]
        total_rows = len(valid_rows) + len(invalid_rows)

        err_msg: Optional[str] = None
        if missing_required:
            err_msg = f"Missing required CSV column(s): {', '.join(missing_required)}"
        elif len(valid_rows) == 0:
            err_msg = "No valid data rows found in CSV."

        return BatchValidationPreview(
            is_valid=is_valid,
            filename=filename,
            total_rows=total_rows,
            valid_rows_count=len(valid_rows),
            invalid_rows_count=len(invalid_rows),
            detected_columns=col_map,
            missing_required_columns=missing_required,
            preview_rows=preview_rows,
            invalid_rows=invalid_rows,
            error_message=err_msg,
        )


    def execute_batch(
        self,
        raw_bytes: bytes,
        filename: str = "batch_upload.csv",
        dataset_filter: Optional[str] = None,
        top_k: int = 5,
    ) -> BatchEvaluationResult:
        """Process complete batch evaluation job: parse CSV, run pipeline, compute stats, and store."""
        batch_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()

        # Step 1: Decode and Parse CSV
        content_str = self.decode_csv_content(raw_bytes)
        valid_rows, validation_errors, invalid_rows, col_map = self.parse_and_validate_csv(content_str)

        total_records = len(valid_rows) + len(validation_errors)

        # Create initial batch job record
        self.db.create_batch_job(
            batch_id=batch_id,
            filename=filename,
            total_records=total_records,
            processed_records=0,
            status="processing",
        )

        records: List[BatchRecord] = []
        pass_count = 0
        needs_improvement_count = 0
        fail_count = 0
        acc_scores: List[int] = []
        rel_scores: List[int] = []
        comp_scores: List[int] = []
        overall_scores: List[int] = []
        hallucination_flags = 0

        # Step 2: Execute complete evaluation pipeline for each valid row
        for idx, row in enumerate(valid_rows):
            record_id = idx + 1
            q = row["question"]
            ans = row["ai_response"]
            ref = row["reference_answer"]
            src = row["source_information"]

            try:
                eval_res = self.orchestrator.evaluate_response(
                    question=q,
                    ai_response=ans,
                    reference_answer=ref,
                    source_document=src,
                    dataset_filter=dataset_filter,
                    top_k=top_k,
                )

                acc = eval_res["accuracy"]
                rel = eval_res["relevance"]
                hal = eval_res["hallucination"]
                comp = eval_res["completeness"]
                overall = eval_res["overall"]
                v_details = eval_res.get("verdict_details", overall)

                score_val = overall.get("overall_score", 0)
                verdict_val = overall.get("verdict", "NEEDS IMPROVEMENT")

                acc_s = acc.get("score")
                rel_s = rel.get("score")
                comp_s = comp.get("score")
                hal_risk = hal.get("risk_level", "LOW")
                hal_status = hal.get("hallucination_status", "NONE")

                # Accumulate stats
                if verdict_val == "PASS":
                    pass_count += 1
                elif verdict_val in ("NEEDS IMPROVEMENT", "REVIEW"):
                    needs_improvement_count += 1
                else:
                    fail_count += 1

                if acc_s is not None:
                    acc_scores.append(acc_s)
                if rel_s is not None:
                    rel_scores.append(rel_s)
                if comp_s is not None:
                    comp_scores.append(comp_s)
                if score_val is not None:
                    overall_scores.append(score_val)

                if hal_risk in ("MEDIUM", "HIGH") or hal_status in ("PARTIAL", "HIGH"):
                    hallucination_flags += 1

                # Save individual submission to SQLite with batch_id
                sub = self.db.create_submission(
                    question=q,
                    ai_response=ans,
                    reference_answer=ref,
                    source_document=src,
                    retrieved_evidence=eval_res.get("evidence", []),
                    status="completed",
                    overall_score=score_val,
                    verdict=verdict_val,
                    relevance_score=rel_s,
                    accuracy_score=acc_s,
                    hallucination_risk=hal_risk,
                    completeness_score=comp_s,
                    verdict_details=v_details,
                    batch_id=batch_id,
                    evaluation_result=eval_res,
                )

                records.append(
                    BatchRecord(
                        record_id=record_id,
                        submission_id=sub["id"],
                        question=q,
                        ai_response=ans,
                        reference_answer=ref,
                        source_information=src,
                        status="success",
                        accuracy_score=acc_s,
                        relevance_score=rel_s,
                        completeness_score=comp_s,
                        completeness_status=comp.get("status"),
                        hallucination_risk=hal_risk,
                        hallucination_status=hal_status,
                        overall_score=score_val,
                        verdict=verdict_val,
                        evaluation=eval_res,
                    )
                )

            except Exception as exc:
                logger.error(f"Error evaluating batch row {record_id}: {exc}", exc_info=True)
                fail_count += 1
                records.append(
                    BatchRecord(
                        record_id=record_id,
                        question=q,
                        ai_response=ans,
                        reference_answer=ref,
                        source_information=src,
                        status="error",
                        error=f"Evaluation failed: {str(exc)}",
                        verdict="FAIL",
                    )
                )

        successful_evals = len([r for r in records if r.status == "success"])
        failed_evals = len([r for r in records if r.status == "error"])

        # Step 3: Compute aggregate statistics
        stats = BatchSummaryStats(
            total_records=total_records,
            successful_evaluations=successful_evals,
            failed_evaluations=failed_evals,
            pass_count=pass_count,
            needs_improvement_count=needs_improvement_count,
            fail_count=fail_count,
            average_accuracy=round(sum(acc_scores) / len(acc_scores), 2) if acc_scores else None,
            average_relevance=round(sum(rel_scores) / len(rel_scores), 2) if rel_scores else None,
            average_completeness=round(sum(comp_scores) / len(comp_scores), 2) if comp_scores else None,
            hallucination_flag_frequency=(
                round(hallucination_flags / successful_evals, 3) if successful_evals > 0 else 0.0
            ),
            average_overall_score=round(sum(overall_scores) / len(overall_scores), 1) if overall_scores else None,
        )

        # Update batch job in SQLite
        self.db.update_batch_job(
            batch_id=batch_id,
            processed_records=len(records),
            status="completed",
            stats=stats.model_dump(),
        )

        return BatchEvaluationResult(
            success=True,
            batch_id=batch_id,
            filename=filename,
            total_records=total_records,
            valid_records_count=len(valid_rows),
            invalid_records_count=len(validation_errors),
            validation_errors=validation_errors,
            invalid_rows=invalid_rows,
            stats=stats,
            records=records,
            created_at=created_at,
        )

    def get_batch_result(self, batch_id: str) -> Optional[BatchEvaluationResult]:
        """Retrieve completed batch result by ID including individual records."""
        job = self.db.get_batch_job(batch_id)
        if not job:
            return None

        # Fetch all submissions tied to this batch
        subs = self.db.list_submissions(limit=1000, batch_id=batch_id)
        records: List[BatchRecord] = []

        for idx, s in enumerate(subs):
            sub_full = self.db.get_submission(s["submission_id"])
            eval_data = sub_full.get("evaluation_result") if sub_full else None
            comp_data = eval_data.get("completeness", {}) if eval_data else {}
            hal_data = eval_data.get("hallucination", {}) if eval_data else {}

            records.append(
                BatchRecord(
                    record_id=idx + 1,
                    submission_id=s["submission_id"],
                    question=s["question"],
                    ai_response=sub_full.get("ai_response", "") if sub_full else s.get("ai_response_snippet", ""),
                    reference_answer=sub_full.get("reference_answer") if sub_full else None,
                    source_information=sub_full.get("source_document") if sub_full else None,
                    status="success",
                    accuracy_score=s.get("accuracy_score"),
                    relevance_score=s.get("relevance_score"),
                    completeness_score=s.get("completeness_score"),
                    completeness_status=comp_data.get("status"),
                    hallucination_risk=s.get("hallucination_risk"),
                    hallucination_status=hal_data.get("hallucination_status"),
                    overall_score=s.get("overall_score"),
                    verdict=s.get("verdict"),
                    evaluation=eval_data,
                )
            )

        stats_dict = job.get("stats") or {}
        stats = BatchSummaryStats(
            total_records=job.get("total_records", len(records)),
            successful_evaluations=stats_dict.get("successful_evaluations", len(records)),
            failed_evaluations=stats_dict.get("failed_evaluations", 0),
            pass_count=stats_dict.get("pass_count", 0),
            needs_improvement_count=stats_dict.get("needs_improvement_count", 0),
            fail_count=stats_dict.get("fail_count", 0),
            average_accuracy=stats_dict.get("average_accuracy"),
            average_relevance=stats_dict.get("average_relevance"),
            average_completeness=stats_dict.get("average_completeness"),
            hallucination_flag_frequency=stats_dict.get("hallucination_flag_frequency", 0.0),
            average_overall_score=stats_dict.get("average_overall_score"),
        )

        return BatchEvaluationResult(
            success=True,
            batch_id=batch_id,
            filename=job.get("filename", "batch.csv"),
            total_records=job.get("total_records", len(records)),
            valid_records_count=len(records),
            invalid_records_count=0,
            validation_errors=[],
            stats=stats,
            records=records,
            created_at=job.get("created_at", ""),
        )


# Global singleton instance
batch_evaluation_service = BatchEvaluationService()

clean_header_name = BatchEvaluationService.clean_header_name
detect_delimiter = batch_evaluation_service.detect_delimiter
decode_csv_content = batch_evaluation_service.decode_csv_content
parse_and_validate_csv = batch_evaluation_service.parse_and_validate_csv
