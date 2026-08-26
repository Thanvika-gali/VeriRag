"""Tests for SQLite SubmissionDB storage."""

import os
import pytest
from backend.database.sqlite_db import SubmissionDB


@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test_submissions.db"
    db = SubmissionDB(db_path=str(db_file))
    return db


def test_create_and_get_submission(temp_db):
    res = temp_db.create_submission(
        question="What is the boiling point of water at sea level?",
        ai_response="100 degrees Celsius or 212 degrees Fahrenheit.",
        reference_answer="100 C",
        retrieved_evidence=[
            {
                "chunk_id": "c1",
                "text": "Water boils at 100 degrees Celsius under standard atmospheric pressure.",
                "dataset_name": "SQuAD",
                "similarity_score": 0.95,
                "distance": 0.05,
                "metadata": {"title": "Water"},
            }
        ],
    )
    sub_id = res["id"]
    assert sub_id is not None

    fetched = temp_db.get_submission(sub_id)
    assert fetched is not None
    assert fetched["id"] == sub_id
    assert fetched["question"] == "What is the boiling point of water at sea level?"
    assert len(fetched["retrieved_evidence"]) == 1
    assert fetched["retrieved_evidence"][0]["dataset_name"] == "SQuAD"


def test_list_submissions(temp_db):
    temp_db.create_submission(question="Q1", ai_response="A1")
    temp_db.create_submission(question="Q2", ai_response="A2")

    items = temp_db.list_submissions(limit=10)
    assert len(items) == 2
    assert items[0]["question"] == "Q2"  # Newest first
