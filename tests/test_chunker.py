"""Tests for TextCleaner and DocumentChunker."""

import pytest
from knowledge_base.preprocessing.cleaner import TextCleaner
from knowledge_base.preprocessing.chunker import DocumentChunker


def test_text_cleaner_whitespace():
    raw = "This   is   a   test.\n\n\n\nNew paragraph with \r\n line breaks."
    cleaned = TextCleaner.clean_text(raw)
    assert "  " not in cleaned
    assert "\n\n\n" not in cleaned
    assert "\r" not in cleaned


def test_chunker_short_text():
    chunker = DocumentChunker(chunk_size=500, chunk_overlap=50)
    text = "Short factual evidence sentence."
    chunks = chunker.chunk_document(text, doc_id="doc_1", metadata={"dataset_name": "TruthfulQA"})

    assert len(chunks) == 1
    assert chunks[0]["chunk_id"] == "doc_1_c0"
    assert chunks[0]["text"] == text
    assert chunks[0]["metadata"]["dataset_name"] == "TruthfulQA"
    assert chunks[0]["metadata"]["chunk_index"] == 0
    assert chunks[0]["metadata"]["total_chunks"] == 1


def test_chunker_long_text():
    chunker = DocumentChunker(chunk_size=100, chunk_overlap=20)
    long_text = "This is a long passage designed to verify that the chunker splits sentences accurately. " * 5
    chunks = chunker.chunk_document(long_text, doc_id="doc_long", metadata={"topic": "Physics"})

    assert len(chunks) > 1
    for idx, c in enumerate(chunks):
        assert c["chunk_id"] == f"doc_long_c{idx}"
        assert c["metadata"]["chunk_index"] == idx
        assert c["metadata"]["total_chunks"] == len(chunks)
        assert c["metadata"]["topic"] == "Physics"
