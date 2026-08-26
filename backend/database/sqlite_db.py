"""SQLite Database storage for VeriRAG evaluation submissions."""

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


DEFAULT_DB_PATH = os.getenv("SQLITE_DB_PATH", "submissions.db")


class SubmissionDB:
    """Manages SQLite storage for evaluation submissions and evidence results."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self.init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Create a database connection with Row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        """Initialize submissions table schema if not already existing."""
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

    def create_submission(
        self,
        question: str,
        ai_response: str,
        reference_answer: Optional[str] = None,
        source_document: Optional[str] = None,
        retrieved_evidence: Optional[List[Dict[str, Any]]] = None,
        status: str = "completed",
        submission_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Save a new evaluation submission into SQLite."""
        sub_id = submission_id or str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        evidence_json = json.dumps(retrieved_evidence or [])

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO submissions (
                    id, question, ai_response, reference_answer, source_document,
                    status, retrieved_evidence_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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

        return {
            "id": row["id"],
            "question": row["question"],
            "ai_response": row["ai_response"],
            "reference_answer": row["reference_answer"],
            "source_document": row["source_document"],
            "status": row["status"],
            "retrieved_evidence": evidence_list,
            "created_at": row["created_at"],
        }

    def list_submissions(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """List past evaluation submissions with pagination."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, question, ai_response, retrieved_evidence_json, created_at
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
                "created_at": r["created_at"],
            })
        return results


# Global singleton instance for easy import
db_instance = SubmissionDB()
