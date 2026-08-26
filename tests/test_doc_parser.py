"""Tests for DocumentParser (TXT and PDF handling)."""

import pytest
from backend.services.doc_parser import DocumentParser


def test_extract_from_txt_string():
    raw_text = "  Hello   VeriRAG! \n\n Testing text extraction.  "
    extracted = DocumentParser.extract_from_txt(raw_text)
    assert extracted == "Hello   VeriRAG! \n\n Testing text extraction."


def test_extract_from_txt_bytes():
    raw_bytes = "Plain text content for evaluation.".encode("utf-8")
    extracted = DocumentParser.extract_from_txt(raw_bytes)
    assert extracted == "Plain text content for evaluation."


def test_parse_file_txt():
    content = "Sample context for grounding.".encode("utf-8")
    result = DocumentParser.parse_file("evidence.txt", content)
    assert result["filename"] == "evidence.txt"
    assert result["file_type"] == "txt"
    assert result["extracted_text"] == "Sample context for grounding."
    assert result["word_count"] == 4
    assert result["char_count"] == 29
