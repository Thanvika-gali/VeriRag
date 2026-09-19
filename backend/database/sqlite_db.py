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


# Global singleton instance for easy import
db_instance = SubmissionDB()
