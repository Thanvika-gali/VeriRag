"""SQLite Database storage for VeriRAG evaluation submissions."""

import json
import os
from pathlib import Path
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Anchor path to project root (parent of backend/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_env_db = os.getenv("SQLITE_DB_PATH", "submissions.db")
_db_path = Path(_env_db)
if not _db_path.is_absolute():
    _db_path = PROJECT_ROOT / _db_path
DEFAULT_DB_PATH = str(_db_path)


class SubmissionDB:
    """Manages SQLite storage for evaluation submissions, evidence results, and agent metrics."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path:
            p = Path(db_path)
            self.db_path = str(p if p.is_absolute() else PROJECT_ROOT / p)
        else:
            self.db_path = DEFAULT_DB_PATH
        self.init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Create a database connection with Row factory."""
        conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        """Initialize submissions and batch_jobs table schemas and migrate missing columns non-destructively."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS submissions (
                    id TEXT PRIMARY KEY,
                    question TEXT NOT NULL,
                    ai_response TEXT NOT NULL,
                    reference_answer TEXT,
                    source_document TEXT,
                    status TEXT NOT NULL,
                    retrieved_evidence_json TEXT,
                    created_at TEXT NOT NULL
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS batch_jobs (
                    id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    total_records INTEGER NOT NULL,
                    processed_records INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    stats_json TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            conn.commit()

            # Non-destructive schema migrations for evaluation attributes
            cursor.execute("PRAGMA table_info(submissions)")
            existing_cols = {row["name"] for row in cursor.fetchall()}

            migrations = [
                ("overall_score", "INTEGER"),
                ("verdict", "TEXT"),
                ("relevance_score", "INTEGER"),
                ("accuracy_score", "INTEGER"),
                ("hallucination_risk", "TEXT"),
                ("evaluation_result_json", "TEXT"),
                ("completeness_score", "INTEGER"),
                ("verdict_details_json", "TEXT"),
                ("batch_id", "TEXT"),
            ]

            for col_name, col_type in migrations:
                if col_name not in existing_cols:
                    cursor.execute(f"ALTER TABLE submissions ADD COLUMN {col_name} {col_type}")

            conn.commit()

    def create_submission(
        self,
        question: str,
        ai_response: str,
        reference_answer: Optional[str] = None,
        source_document: Optional[str] = None,
        retrieved_evidence: Optional[List[Dict[str, Any]]] = None,
        status: str = "completed",
        submission_id: Optional[str] = None,
        overall_score: Optional[int] = None,
        verdict: Optional[str] = None,
        relevance_score: Optional[int] = None,
        accuracy_score: Optional[int] = None,
        hallucination_risk: Optional[str] = None,
        completeness_score: Optional[int] = None,
        verdict_details: Optional[Dict[str, Any]] = None,
        batch_id: Optional[str] = None,
        evaluation_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Save a new evaluation submission into SQLite with full agent metrics."""
        sub_id = submission_id or str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        evidence_json = json.dumps(retrieved_evidence or [])
        eval_json = json.dumps(evaluation_result) if evaluation_result else None
        verdict_details_json = json.dumps(verdict_details) if verdict_details else None

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO submissions (
                    id, question, ai_response, reference_answer, source_document,
                    status, retrieved_evidence_json, created_at,
                    overall_score, verdict, relevance_score, accuracy_score,
                    hallucination_risk, completeness_score, verdict_details_json,
                    batch_id, evaluation_result_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sub_id,
                    question,
                    ai_response,
                    reference_answer,
                    source_document,
                    status,
                    evidence_json,
                    created_at,
                    overall_score,
                    verdict,
                    relevance_score,
                    accuracy_score,
                    hallucination_risk,
                    completeness_score,
                    verdict_details_json,
                    batch_id,
                    eval_json,
                ),
            )
            conn.commit()

        return {
            "id": sub_id,
            "question": question,
            "ai_response": ai_response,
            "reference_answer": reference_answer,
            "source_document": source_document,
            "status": status,
            "retrieved_evidence": retrieved_evidence or [],
            "overall_score": overall_score,
            "verdict": verdict,
            "relevance_score": relevance_score,
            "accuracy_score": accuracy_score,
            "hallucination_risk": hallucination_risk,
            "completeness_score": completeness_score,
            "verdict_details": verdict_details,
            "batch_id": batch_id,
            "evaluation_result": evaluation_result,
            "created_at": created_at,
        }

    def get_submission(self, submission_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific submission by its UUID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM submissions WHERE id = ?", (submission_id,))
            row = cursor.fetchone()

        if not row:
            return None

        evidence_list = []
        if row["retrieved_evidence_json"]:
            try:
                evidence_list = json.loads(row["retrieved_evidence_json"])
            except Exception:
                evidence_list = []

        eval_result = None
        if "evaluation_result_json" in row.keys() and row["evaluation_result_json"]:
            try:
                eval_result = json.loads(row["evaluation_result_json"])
            except Exception:
                eval_result = None

        verdict_details = None
        if "verdict_details_json" in row.keys() and row["verdict_details_json"]:
            try:
                verdict_details = json.loads(row["verdict_details_json"])
            except Exception:
                verdict_details = None

        return {
            "id": row["id"],
            "question": row["question"],
            "ai_response": row["ai_response"],
            "reference_answer": row["reference_answer"],
            "source_document": row["source_document"],
            "status": row["status"],
            "retrieved_evidence": evidence_list,
            "overall_score": row["overall_score"] if "overall_score" in row.keys() else None,
            "verdict": row["verdict"] if "verdict" in row.keys() else None,
            "relevance_score": row["relevance_score"] if "relevance_score" in row.keys() else None,
            "accuracy_score": row["accuracy_score"] if "accuracy_score" in row.keys() else None,
            "hallucination_risk": row["hallucination_risk"] if "hallucination_risk" in row.keys() else None,
            "completeness_score": row["completeness_score"] if "completeness_score" in row.keys() else None,
            "verdict_details": verdict_details,
            "batch_id": row["batch_id"] if "batch_id" in row.keys() else None,
            "evaluation_result": eval_result,
            "created_at": row["created_at"],
        }

    def list_submissions(
        self, limit: int = 50, offset: int = 0, batch_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List past evaluation submissions with pagination."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if batch_id:
                cursor.execute(
                    """
                    SELECT id, question, ai_response, retrieved_evidence_json,
                           overall_score, verdict, relevance_score, accuracy_score,
                           completeness_score, hallucination_risk, batch_id, created_at
                    FROM submissions
                    WHERE batch_id = ?
                    ORDER BY created_at ASC
                    LIMIT ? OFFSET ?
                    """,
                    (batch_id, limit, offset),
                )
            else:
                cursor.execute(
                    """
                    SELECT id, question, ai_response, retrieved_evidence_json,
                           overall_score, verdict, relevance_score, accuracy_score,
                           completeness_score, hallucination_risk, batch_id, created_at
                    FROM submissions
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (limit, offset),
                )
            rows = cursor.fetchall()

        results = []
        for r in rows:
            evidence_count = 0
            if r["retrieved_evidence_json"]:
                try:
                    evidence_count = len(json.loads(r["retrieved_evidence_json"]))
                except Exception:
                    evidence_count = 0

            snippet = r["ai_response"][:100] + ("..." if len(r["ai_response"]) > 100 else "")
            results.append({
                "submission_id": r["id"],
                "question": r["question"],
                "ai_response_snippet": snippet,
                "evidence_count": evidence_count,
                "overall_score": r["overall_score"] if "overall_score" in r.keys() else None,
                "verdict": r["verdict"] if "verdict" in r.keys() else None,
                "relevance_score": r["relevance_score"] if "relevance_score" in r.keys() else None,
                "accuracy_score": r["accuracy_score"] if "accuracy_score" in r.keys() else None,
                "completeness_score": r["completeness_score"] if "completeness_score" in r.keys() else None,
                "hallucination_risk": r["hallucination_risk"] if "hallucination_risk" in r.keys() else None,
                "batch_id": r["batch_id"] if "batch_id" in r.keys() else None,
                "created_at": r["created_at"],
            })
        return results

    # --------------------------------------------------------------------------
    # Batch Job Storage Methods
    # --------------------------------------------------------------------------

    def create_batch_job(
        self,
        batch_id: str,
        filename: str,
        total_records: int,
        processed_records: int = 0,
        status: str = "processing",
        stats: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Save a new batch job record into SQLite."""
        created_at = datetime.now(timezone.utc).isoformat()
        stats_json = json.dumps(stats) if stats else None

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO batch_jobs (
                    id, filename, total_records, processed_records, status, stats_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (batch_id, filename, total_records, processed_records, status, stats_json, created_at),
            )
            conn.commit()

        return {
            "id": batch_id,
            "filename": filename,
            "total_records": total_records,
            "processed_records": processed_records,
            "status": status,
            "stats": stats,
            "created_at": created_at,
        }

    def update_batch_job(
        self,
        batch_id: str,
        processed_records: int,
        status: str,
        stats: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Update batch job status and statistics."""
        stats_json = json.dumps(stats) if stats else None
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE batch_jobs
                SET processed_records = ?, status = ?, stats_json = ?
                WHERE id = ?
                """,
                (processed_records, status, stats_json, batch_id),
            )
            conn.commit()

    def get_batch_job(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve batch job information by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM batch_jobs WHERE id = ?", (batch_id,))
            row = cursor.fetchone()

        if not row:
            return None

        stats = None
        if row["stats_json"]:
            try:
                stats = json.loads(row["stats_json"])
            except Exception:
                stats = None

        return {
            "batch_id": row["id"],
            "filename": row["filename"],
            "total_records": row["total_records"],
            "processed_records": row["processed_records"],
            "status": row["status"],
            "stats": stats,
            "created_at": row["created_at"],
        }

    def list_batch_jobs(self, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """List past batch evaluation jobs."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, filename, total_records, processed_records, status, stats_json, created_at
                FROM batch_jobs
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            )
            rows = cursor.fetchall()

        results = []
        for r in rows:
            stats = None
            if r["stats_json"]:
                try:
                    stats = json.loads(r["stats_json"])
                except Exception:
                    stats = None
            results.append({
                "batch_id": r["id"],
                "filename": r["filename"],
                "total_records": r["total_records"],
                "processed_records": r["processed_records"],
                "status": r["status"],
                "stats": stats,
                "created_at": r["created_at"],
            })
        return results

    def get_analytics(self) -> Dict[str, Any]:
        """Compute aggregate evaluation metrics from real database records."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM submissions")
            total_count = cursor.fetchone()[0]

            if total_count == 0:
                return {
                    "total_evaluations": 0,
                    "evidence_retrieved_count": 0,
                    "average_accuracy": None,
                    "average_relevance": None,
                    "average_completeness": None,
                    "average_hallucination_safety": None,
                    "average_overall_score": None,
                    "pass_count": 0,
                    "review_count": 0,
                    "fail_count": 0,
                    "hallucination_flag_count": 0,
                    "hallucination_frequency": 0.0,
                    "has_data": False,
                }

            cursor.execute("SELECT AVG(accuracy_score) FROM submissions WHERE accuracy_score IS NOT NULL")
            avg_acc = cursor.fetchone()[0]

            cursor.execute("SELECT AVG(relevance_score) FROM submissions WHERE relevance_score IS NOT NULL")
            avg_rel = cursor.fetchone()[0]

            cursor.execute("SELECT AVG(completeness_score) FROM submissions WHERE completeness_score IS NOT NULL")
            avg_comp = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT AVG(
                    CASE
                        WHEN UPPER(hallucination_risk) = 'LOW' THEN 5.0
                        WHEN UPPER(hallucination_risk) = 'MEDIUM' THEN 2.5
                        WHEN UPPER(hallucination_risk) = 'HIGH' THEN 0.0
                        ELSE 5.0
                    END
                )
                FROM submissions WHERE hallucination_risk IS NOT NULL
                """
            )
            avg_hal_safety = cursor.fetchone()[0]

            cursor.execute("SELECT AVG(overall_score) FROM submissions WHERE overall_score IS NOT NULL")
            avg_overall = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM submissions WHERE verdict = 'PASS'")
            pass_cnt = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM submissions WHERE verdict IN ('REVIEW', 'NEEDS IMPROVEMENT')")
            review_cnt = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM submissions WHERE verdict = 'FAIL'")
            fail_cnt = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM submissions WHERE UPPER(hallucination_risk) IN ('MEDIUM', 'HIGH')")
            hal_flags = cursor.fetchone()[0]

            # Calculate total evidence chunks retrieved across all submissions
            cursor.execute("SELECT retrieved_evidence_json FROM submissions")
            all_evidence_rows = cursor.fetchall()
            evidence_total = 0
            for row in all_evidence_rows:
                if row[0]:
                    try:
                        evidence_total += len(json.loads(row[0]))
                    except Exception:
                        pass

            hal_freq = round(hal_flags / total_count, 3) if total_count > 0 else 0.0

            return {
                "total_evaluations": total_count,
                "evidence_retrieved_count": evidence_total,
                "average_accuracy": round(float(avg_acc), 2) if avg_acc is not None else None,
                "average_relevance": round(float(avg_rel), 2) if avg_rel is not None else None,
                "average_completeness": round(float(avg_comp), 2) if avg_comp is not None else None,
                "average_hallucination_safety": round(float(avg_hal_safety), 2) if avg_hal_safety is not None else None,
                "average_overall_score": round(float(avg_overall), 1) if avg_overall is not None else None,
                "pass_count": pass_cnt,
                "review_count": review_cnt,
                "fail_count": fail_cnt,
                "hallucination_flag_count": hal_flags,
                "hallucination_frequency": hal_freq,
                "has_data": True,
            }

    def get_dashboard_stats(
        self,
        batch_id: Optional[str] = None,
        verdict: Optional[str] = None,
        score_min: Optional[int] = None,
        score_max: Optional[int] = None,
        hallucination_status: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit_records: int = 100,
    ) -> Dict[str, Any]:
        """Compute real, verified dashboard analytics and distribution metrics directly from stored evaluations."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 1. Fetch available batch list for dropdown filter
            cursor.execute("SELECT id, filename, total_records, created_at FROM batch_jobs ORDER BY created_at DESC")
            batch_job_rows = cursor.fetchall()

            # Check if there are single (non-batch) evaluations
            cursor.execute("SELECT COUNT(*) FROM submissions WHERE batch_id IS NULL OR batch_id = ''")
            single_eval_count = cursor.fetchone()[0]

            available_batches = [{"id": "ALL", "label": "All Batches & Evaluations"}]
            if single_eval_count > 0:
                available_batches.append({"id": "SINGLE", "label": f"Single Evaluations ({single_eval_count})"})

            for bj in batch_job_rows:
                lbl = f"{bj['filename']} ({bj['total_records']} records) — {bj['created_at'][:10]}"
                available_batches.append({"id": bj["id"], "label": lbl})

            # 2. Build dynamic filter query
            conditions: List[str] = []
            params: List[Any] = []

            if batch_id and batch_id.upper() != "ALL":
                if batch_id.upper() in ("SINGLE", "MANUAL"):
                    conditions.append("(batch_id IS NULL OR batch_id = '')")
                else:
                    conditions.append("batch_id = ?")
                    params.append(batch_id)

            if verdict and verdict.upper() != "ALL":
                v_clean = verdict.upper().strip()
                if v_clean in ("NEEDS IMPROVEMENT", "REVIEW"):
                    conditions.append("verdict IN ('NEEDS IMPROVEMENT', 'REVIEW')")
                elif v_clean in ("PASS", "FAIL"):
                    conditions.append("verdict = ?")
                    params.append(v_clean)

            if score_min is not None:
                conditions.append("overall_score >= ?")
                params.append(score_min)

            if score_max is not None:
                conditions.append("overall_score <= ?")
                params.append(score_max)

            if hallucination_status and hallucination_status.upper() != "ALL":
                h_clean = hallucination_status.upper().strip()
                if h_clean in ("FLAGGED", "RISK", "HIGH", "MEDIUM"):
                    conditions.append("UPPER(hallucination_risk) IN ('MEDIUM', 'HIGH')")
                elif h_clean in ("SAFE", "LOW", "CLEAN"):
                    conditions.append("UPPER(hallucination_risk) = 'LOW'")

            if start_date:
                conditions.append("created_at >= ?")
                params.append(start_date)

            if end_date:
                conditions.append("created_at <= ?")
                params.append(end_date)

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            # Fetch matching submissions
            query = f"""
                SELECT id, question, ai_response, reference_answer, source_document,
                       overall_score, verdict, relevance_score, accuracy_score,
                       completeness_score, hallucination_risk, batch_id, created_at,
                       evaluation_result_json, verdict_details_json, retrieved_evidence_json
                FROM submissions
                {where_clause}
                ORDER BY created_at DESC
            """
            cursor.execute(query, params)
            matching_rows = cursor.fetchall()

            total_records = len(matching_rows)
            if total_records == 0:
                return {
                    "total_evaluations": 0,
                    "verdicts": {"PASS": 0, "NEEDS IMPROVEMENT": 0, "FAIL": 0},
                    "verdict_percentages": {"PASS": 0.0, "NEEDS IMPROVEMENT": 0.0, "FAIL": 0.0},
                    "average_overall_score": None,
                    "dimension_averages": {
                        "accuracy": None,
                        "relevance": None,
                        "completeness": None,
                        "hallucination_safety": None,
                    },
                    "hallucination_stats": {
                        "flagged_count": 0,
                        "frequency_percentage": 0.0,
                        "unsupported_claims_count": 0,
                        "risk_breakdown": {"LOW": 0, "MEDIUM": 0, "HIGH": 0},
                    },
                    "completeness_stats": {
                        "complete_count": 0,
                        "partially_complete_count": 0,
                        "incomplete_count": 0,
                        "missing_aspect_frequency": 0.0,
                        "total_missing_aspects": 0,
                    },
                    "score_distributions": {
                        "overall": {"90-100": 0, "75-89": 0, "50-74": 0, "0-49": 0},
                        "accuracy": {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0},
                        "relevance": {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0},
                        "completeness": {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0},
                    },
                    "frequent_issues": [],
                    "batch_trends": [],
                    "available_batches": available_batches,
                    "filtered_records_count": 0,
                    "records": [],
                    "has_data": False,
                }

            # Helper to normalize verdict for any legacy records
            def _normalize_verdict(row) -> str:
                v = (row["verdict"] or "").upper().strip()
                if v == "PASS":
                    return "PASS"
                if v == "FAIL":
                    return "FAIL"
                if v in ("NEEDS IMPROVEMENT", "REVIEW"):
                    return "NEEDS IMPROVEMENT"
                ov = row["overall_score"]
                if ov is not None:
                    if ov >= 75:
                        return "PASS"
                    elif ov < 50:
                        return "FAIL"
                    else:
                        return "NEEDS IMPROVEMENT"
                return "NEEDS IMPROVEMENT"

            # Verdict Counts & Percentages
            pass_cnt = sum(1 for r in matching_rows if _normalize_verdict(r) == "PASS")
            review_cnt = sum(1 for r in matching_rows if _normalize_verdict(r) == "NEEDS IMPROVEMENT")
            fail_cnt = sum(1 for r in matching_rows if _normalize_verdict(r) == "FAIL")

            pass_pct = round((pass_cnt / total_records) * 100, 1)
            review_pct = round((review_cnt / total_records) * 100, 1)
            fail_pct = round((fail_cnt / total_records) * 100, 1)

            # Dimension Averages
            acc_scores = [r["accuracy_score"] for r in matching_rows if r["accuracy_score"] is not None]
            rel_scores = [r["relevance_score"] for r in matching_rows if r["relevance_score"] is not None]
            comp_scores = [r["completeness_score"] for r in matching_rows if r["completeness_score"] is not None]
            overall_scores = [r["overall_score"] for r in matching_rows if r["overall_score"] is not None]

            avg_acc = round(sum(acc_scores) / len(acc_scores), 2) if acc_scores else None
            avg_rel = round(sum(rel_scores) / len(rel_scores), 2) if rel_scores else None
            avg_comp = round(sum(comp_scores) / len(comp_scores), 2) if comp_scores else None
            avg_overall = round(sum(overall_scores) / len(overall_scores), 1) if overall_scores else None

            # Hallucination Safety Score: LOW -> 5.0, MEDIUM -> 2.5, HIGH -> 0.0
            hal_safety_vals = []
            for r in matching_rows:
                h_risk = (r["hallucination_risk"] or "LOW").upper()
                if h_risk == "LOW":
                    hal_safety_vals.append(5.0)
                elif h_risk == "MEDIUM":
                    hal_safety_vals.append(2.5)
                elif h_risk == "HIGH":
                    hal_safety_vals.append(0.0)
                else:
                    hal_safety_vals.append(5.0)
            avg_hal_safety = round(sum(hal_safety_vals) / len(hal_safety_vals), 2) if hal_safety_vals else None

            # Hallucination Statistics
            flagged_cnt = sum(1 for r in matching_rows if (r["hallucination_risk"] or "").upper() in ("MEDIUM", "HIGH"))
            hal_freq_pct = round((flagged_cnt / total_records) * 100, 1)

            risk_low = sum(1 for r in matching_rows if (r["hallucination_risk"] or "LOW").upper() == "LOW")
            risk_med = sum(1 for r in matching_rows if (r["hallucination_risk"] or "").upper() == "MEDIUM")
            risk_high = sum(1 for r in matching_rows if (r["hallucination_risk"] or "").upper() == "HIGH")

            total_unsupported_claims = 0
            records_with_unsupported_claims = 0

            # Completeness Breakdown
            comp_complete = sum(1 for r in matching_rows if r["completeness_score"] is not None and r["completeness_score"] >= 4)
            comp_partial = sum(1 for r in matching_rows if r["completeness_score"] == 3)
            comp_incomplete = sum(1 for r in matching_rows if r["completeness_score"] is not None and r["completeness_score"] <= 2)

            total_missing_aspects = 0
            records_with_missing_aspects = 0

            drill_down_records = []

            for r in matching_rows:
                r_id = r["id"]
                eval_json = r["evaluation_result_json"]
                c_flagged = 0
                c_missing = 0

                if eval_json:
                    try:
                        parsed = json.loads(eval_json)
                        hal_obj = parsed.get("hallucination", {})
                        claims = hal_obj.get("flagged_claims", [])
                        c_flagged = len(claims)
                        total_unsupported_claims += c_flagged
                        if c_flagged > 0:
                            records_with_unsupported_claims += 1

                        comp_obj = parsed.get("completeness", {})
                        missing_list = comp_obj.get("missing_aspects", [])
                        c_missing = len(missing_list)
                        total_missing_aspects += c_missing
                        if c_missing > 0:
                            records_with_missing_aspects += 1
                    except Exception:
                        pass

                if len(drill_down_records) < limit_records:
                    snippet = r["ai_response"][:120] + ("..." if len(r["ai_response"]) > 120 else "")
                    drill_down_records.append({
                        "submission_id": r["id"],
                        "question": r["question"],
                        "ai_response_snippet": snippet,
                        "overall_score": r["overall_score"],
                        "verdict": r["verdict"],
                        "accuracy_score": r["accuracy_score"],
                        "relevance_score": r["relevance_score"],
                        "completeness_score": r["completeness_score"],
                        "hallucination_risk": r["hallucination_risk"],
                        "batch_id": r["batch_id"],
                        "created_at": r["created_at"],
                        "flagged_claims_count": c_flagged,
                        "missing_aspects_count": c_missing,
                    })

            missing_aspect_freq = round((records_with_missing_aspects / total_records) * 100, 1)

            # Score Distributions
            dist_overall = {"90-100": 0, "75-89": 0, "50-74": 0, "0-49": 0}
            for sc in overall_scores:
                if sc >= 90:
                    dist_overall["90-100"] += 1
                elif sc >= 75:
                    dist_overall["75-89"] += 1
                elif sc >= 50:
                    dist_overall["50-74"] += 1
                else:
                    dist_overall["0-49"] += 1

            dist_acc = {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
            for sc in acc_scores:
                key = str(max(1, min(5, sc)))
                dist_acc[key] += 1

            dist_rel = {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
            for sc in rel_scores:
                key = str(max(1, min(5, sc)))
                dist_rel[key] += 1

            dist_comp = {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
            for sc in comp_scores:
                key = str(max(1, min(5, sc)))
                dist_comp[key] += 1

            # Most Frequent Issues
            low_acc_count = sum(1 for sc in acc_scores if sc <= 2)
            low_rel_count = sum(1 for sc in rel_scores if sc <= 2)
            low_comp_count = sum(1 for sc in comp_scores if sc <= 2)

            frequent_issues = [
                {
                    "issue_type": "Low Accuracy",
                    "category": "Factual Error",
                    "count": low_acc_count,
                    "percentage": round((low_acc_count / total_records) * 100, 1),
                    "description": "Responses with accuracy score <= 2 due to factual contradictions or inaccurate claims.",
                },
                {
                    "issue_type": "Hallucination Detected",
                    "category": "Ungrounded Claim",
                    "count": flagged_cnt,
                    "percentage": hal_freq_pct,
                    "description": "Responses flagged with medium or high hallucination risk containing ungrounded assertions.",
                },
                {
                    "issue_type": "Low Completeness",
                    "category": "Omission",
                    "count": low_comp_count,
                    "percentage": round((low_comp_count / total_records) * 100, 1),
                    "description": "Responses scoring <= 2 on completeness with essential question aspects missing.",
                },
                {
                    "issue_type": "Unsupported Claims",
                    "category": "Evidence Gap",
                    "count": records_with_unsupported_claims,
                    "percentage": round((records_with_unsupported_claims / total_records) * 100, 1),
                    "description": f"Specific atomic assertions lacking reference verification ({total_unsupported_claims} claims across dataset).",
                },
                {
                    "issue_type": "Low Relevance",
                    "category": "Topic Drift",
                    "count": low_rel_count,
                    "percentage": round((low_rel_count / total_records) * 100, 1),
                    "description": "Responses failing to focus on the submitted user inquiry (relevance <= 2).",
                },
            ]

            # 3. Batch Quality Trends across all recorded batches
            cursor.execute("SELECT id, filename, total_records, created_at FROM batch_jobs ORDER BY created_at ASC")
            all_bj_rows = cursor.fetchall()
            batch_trends = []

            for bj in all_bj_rows:
                b_id = bj["id"]
                cursor.execute(
                    """
                    SELECT overall_score, verdict, accuracy_score, relevance_score, completeness_score, hallucination_risk
                    FROM submissions
                    WHERE batch_id = ?
                    """,
                    (b_id,),
                )
                b_sub_rows = cursor.fetchall()
                if not b_sub_rows:
                    continue

                b_tot = len(b_sub_rows)
                b_pass = sum(1 for r in b_sub_rows if r["verdict"] == "PASS")
                b_rev = sum(1 for r in b_sub_rows if r["verdict"] in ("NEEDS IMPROVEMENT", "REVIEW"))
                b_fail = sum(1 for r in b_sub_rows if r["verdict"] == "FAIL")
                b_pass_rate = round((b_pass / b_tot) * 100, 1)

                b_sc = [r["overall_score"] for r in b_sub_rows if r["overall_score"] is not None]
                b_acc = [r["accuracy_score"] for r in b_sub_rows if r["accuracy_score"] is not None]
                b_rel = [r["relevance_score"] for r in b_sub_rows if r["relevance_score"] is not None]
                b_comp = [r["completeness_score"] for r in b_sub_rows if r["completeness_score"] is not None]

                b_hal_cnt = sum(1 for r in b_sub_rows if (r["hallucination_risk"] or "").upper() in ("MEDIUM", "HIGH"))
                b_hal_freq = round((b_hal_cnt / b_tot) * 100, 1)

                b_hal_safety = []
                for r in b_sub_rows:
                    hr = (r["hallucination_risk"] or "LOW").upper()
                    b_hal_safety.append(5.0 if hr == "LOW" else 2.5 if hr == "MEDIUM" else 0.0)

                batch_trends.append({
                    "batch_id": b_id,
                    "filename": bj["filename"],
                    "created_at": bj["created_at"],
                    "total_records": b_tot,
                    "pass_count": b_pass,
                    "review_count": b_rev,
                    "fail_count": b_fail,
                    "pass_rate": b_pass_rate,
                    "average_overall_score": round(sum(b_sc) / len(b_sc), 1) if b_sc else None,
                    "average_accuracy": round(sum(b_acc) / len(b_acc), 2) if b_acc else None,
                    "average_relevance": round(sum(b_rel) / len(b_rel), 2) if b_rel else None,
                    "average_completeness": round(sum(b_comp) / len(b_comp), 2) if b_comp else None,
                    "average_hallucination_safety": round(sum(b_hal_safety) / len(b_hal_safety), 2) if b_hal_safety else None,
                    "hallucination_flag_count": b_hal_cnt,
                    "hallucination_frequency": b_hal_freq,
                })

            return {
                "total_evaluations": total_records,
                "verdicts": {
                    "PASS": pass_cnt,
                    "NEEDS IMPROVEMENT": review_cnt,
                    "FAIL": fail_cnt,
                },
                "verdict_percentages": {
                    "PASS": pass_pct,
                    "NEEDS IMPROVEMENT": review_pct,
                    "FAIL": fail_pct,
                },
                "average_overall_score": avg_overall,
                "dimension_averages": {
                    "accuracy": avg_acc,
                    "relevance": avg_rel,
                    "completeness": avg_comp,
                    "hallucination_safety": avg_hal_safety,
                },
                "hallucination_stats": {
                    "flagged_count": flagged_cnt,
                    "frequency_percentage": hal_freq_pct,
                    "unsupported_claims_count": total_unsupported_claims,
                    "risk_breakdown": {
                        "LOW": risk_low,
                        "MEDIUM": risk_med,
                        "HIGH": risk_high,
                    },
                },
                "completeness_stats": {
                    "complete_count": comp_complete,
                    "partially_complete_count": comp_partial,
                    "incomplete_count": comp_incomplete,
                    "missing_aspect_frequency": missing_aspect_freq,
                    "total_missing_aspects": total_missing_aspects,
                },
                "score_distributions": {
                    "overall": dist_overall,
                    "accuracy": dist_acc,
                    "relevance": dist_rel,
                    "completeness": dist_comp,
                },
                "frequent_issues": frequent_issues,
                "batch_trends": batch_trends,
                "available_batches": available_batches,
                "filtered_records_count": total_records,
                "records": drill_down_records,
                "has_data": True,
            }

    def get_evaluations_for_report(
        self,
        batch_id: Optional[str] = None,
        submission_id: Optional[str] = None,
        limit: int = 500,
    ) -> Dict[str, Any]:
        """Fetch complete evaluation data and aggregated stats formatted for report generation."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            if submission_id:
                cursor.execute(
                    """
                    SELECT id, question, ai_response, reference_answer, source_document,
                           overall_score, verdict, relevance_score, accuracy_score,
                           completeness_score, hallucination_risk, batch_id, created_at,
                           evaluation_result_json, verdict_details_json, retrieved_evidence_json
                    FROM submissions
                    WHERE id = ?
                    """,
                    (submission_id,),
                )
                rows = cursor.fetchall()
                report_mode = "Single Response Audit"
                batch_info = None
            elif batch_id and batch_id.upper() not in ("ALL", "NONE", ""):
                cursor.execute(
                    """
                    SELECT id, question, ai_response, reference_answer, source_document,
                           overall_score, verdict, relevance_score, accuracy_score,
                           completeness_score, hallucination_risk, batch_id, created_at,
                           evaluation_result_json, verdict_details_json, retrieved_evidence_json
                    FROM submissions
                    WHERE batch_id = ?
                    ORDER BY created_at ASC
                    LIMIT ?
                    """,
                    (batch_id, limit),
                )
                rows = cursor.fetchall()
                report_mode = "Batch Verification Report"
                cursor.execute("SELECT * FROM batch_jobs WHERE id = ?", (batch_id,))
                b_row = cursor.fetchone()
                batch_info = dict(b_row) if b_row else None
            else:
                cursor.execute(
                    """
                    SELECT id, question, ai_response, reference_answer, source_document,
                           overall_score, verdict, relevance_score, accuracy_score,
                           completeness_score, hallucination_risk, batch_id, created_at,
                           evaluation_result_json, verdict_details_json, retrieved_evidence_json
                    FROM submissions
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (limit,),
                )
                rows = cursor.fetchall()
                report_mode = "Comprehensive System Verification Report"
                batch_info = None

            evaluations = []
            for r in rows:
                eval_data = {}
                if r["evaluation_result_json"]:
                    try:
                        eval_data = json.loads(r["evaluation_result_json"])
                    except Exception:
                        eval_data = {}

                verdict_details = {}
                if r["verdict_details_json"]:
                    try:
                        verdict_details = json.loads(r["verdict_details_json"])
                    except Exception:
                        verdict_details = {}

                evidence = []
                if r["retrieved_evidence_json"]:
                    try:
                        evidence = json.loads(r["retrieved_evidence_json"])
                    except Exception:
                        evidence = []

                evaluations.append({
                    "id": r["id"],
                    "question": r["question"],
                    "ai_response": r["ai_response"],
                    "reference_answer": r["reference_answer"],
                    "source_document": r["source_document"],
                    "overall_score": r["overall_score"] if r["overall_score"] is not None else 0,
                    "verdict": r["verdict"] or "NEEDS IMPROVEMENT",
                    "accuracy_score": r["accuracy_score"],
                    "relevance_score": r["relevance_score"],
                    "completeness_score": r["completeness_score"],
                    "hallucination_risk": r["hallucination_risk"] or "LOW",
                    "batch_id": r["batch_id"],
                    "created_at": r["created_at"],
                    "evaluation_result": eval_data,
                    "verdict_details": verdict_details,
                    "retrieved_evidence": evidence,
                })

            stats = self.get_dashboard_stats(batch_id=batch_id) if not submission_id else None

            return {
                "report_mode": report_mode,
                "batch_id": batch_id,
                "batch_info": batch_info,
                "submission_id": submission_id,
                "total_records": len(evaluations),
                "evaluations": evaluations,
                "stats": stats,
            }


# Global singleton instance for easy import
db_instance = SubmissionDB()

