"""SQLite Database storage for VeriRAG evaluation submissions."""

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

DEFAULT_DB_PATH = os.getenv("SQLITE_DB_PATH", "submissions.db")


class SubmissionDB:
    """Manages SQLite storage for evaluation submissions, evidence results, and agent metrics."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self.init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Create a database connection with Row factory."""
        conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        """Initialize submissions table schema and migrate missing columns non-destructively."""
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
        evaluation_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Save a new evaluation submission into SQLite with full agent metrics."""
        sub_id = submission_id or str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        evidence_json = json.dumps(retrieved_evidence or [])
        eval_json = json.dumps(evaluation_result) if evaluation_result else None

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO submissions (
                    id, question, ai_response, reference_answer, source_document,
                    status, retrieved_evidence_json, created_at,
                    overall_score, verdict, relevance_score, accuracy_score,
                    hallucination_risk, evaluation_result_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            "evaluation_result": eval_result,
            "created_at": row["created_at"],
        }

    def list_submissions(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """List past evaluation submissions with pagination."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, question, ai_response, retrieved_evidence_json,
                       overall_score, verdict, relevance_score, accuracy_score,
                       hallucination_risk, created_at
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
                "hallucination_risk": r["hallucination_risk"] if "hallucination_risk" in r.keys() else None,
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
                    "average_overall_score": None,
                    "pass_count": 0,
                    "review_count": 0,
                    "fail_count": 0,
                    "hallucination_flag_count": 0,
                    "has_data": False,
                }

            cursor.execute("SELECT AVG(accuracy_score) FROM submissions WHERE accuracy_score IS NOT NULL")
            avg_acc = cursor.fetchone()[0]

            cursor.execute("SELECT AVG(relevance_score) FROM submissions WHERE relevance_score IS NOT NULL")
            avg_rel = cursor.fetchone()[0]

            cursor.execute("SELECT AVG(overall_score) FROM submissions WHERE overall_score IS NOT NULL")
            avg_overall = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM submissions WHERE verdict = 'PASS'")
            pass_cnt = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM submissions WHERE verdict = 'REVIEW'")
            review_cnt = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM submissions WHERE verdict = 'FAIL'")
            fail_cnt = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM submissions WHERE hallucination_risk IN ('MEDIUM', 'HIGH')")
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

            return {
                "total_evaluations": total_count,
                "evidence_retrieved_count": evidence_total,
                "average_accuracy": round(float(avg_acc), 2) if avg_acc is not None else None,
                "average_relevance": round(float(avg_rel), 2) if avg_rel is not None else None,
                "average_overall_score": round(float(avg_overall), 1) if avg_overall is not None else None,
                "pass_count": pass_cnt,
                "review_count": review_cnt,
                "fail_count": fail_cnt,
                "hallucination_flag_count": hal_flags,
                "has_data": True,
            }


# Global singleton instance for easy import
db_instance = SubmissionDB()
