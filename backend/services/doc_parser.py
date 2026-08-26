"""Document parser supporting TXT and PDF text extraction."""

import io
from typing import Dict, Union
from pypdf import PdfReader


class DocumentParser:
    """Utility service for extracting clean text from uploaded or provided documents."""

    @staticmethod
    def extract_from_txt(file_content: Union[str, bytes]) -> str:
        """Extract clean text from plain text input."""
        if isinstance(file_content, bytes):
            # Try utf-8 first, fallback to latin-1
            try:
                text = file_content.decode("utf-8")
            except UnicodeDecodeError:
                text = file_content.decode("latin-1", errors="replace")
        else:
            text = str(file_content)

        return text.strip()

    @staticmethod
    def extract_from_pdf(file_bytes: bytes) -> str:
        """Extract clean text from PDF bytes using pypdf."""
        if not file_bytes:
            return ""

        stream = io.BytesIO(file_bytes)
        reader = PdfReader(stream)
        pages_text = []

        for page_idx, page in enumerate(reader.pages):
            page_content = page.extract_text()
            if page_content:
                pages_text.append(page_content.strip())

        return "\n\n".join(pages_text).strip()

    @classmethod
    def parse_file(cls, filename: str, content: bytes) -> Dict[str, Union[str, int]]:
        """Parse file according to its extension (txt or pdf)."""
        filename_lower = filename.lower()
        if filename_lower.endswith(".pdf"):
            extracted = cls.extract_from_pdf(content)
            file_type = "pdf"
        elif filename_lower.endswith(".txt") or filename_lower.endswith(".md") or filename_lower.endswith(".csv"):
            extracted = cls.extract_from_txt(content)
            file_type = "txt"
        else:
            # Fallback to UTF-8 text attempt
            extracted = cls.extract_from_txt(content)
            file_type = "generic_text"

        words = extracted.split()
        return {
            "filename": filename,
            "file_type": file_type,
            "extracted_text": extracted,
            "char_count": len(extracted),
            "word_count": len(words),
        }
