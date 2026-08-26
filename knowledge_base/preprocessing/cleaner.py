"""Text cleaning and normalization utilities for knowledge base ingestion."""

import re
import unicodedata


class TextCleaner:
    """Provides consistent text normalization and cleaning routines."""

    @staticmethod
    def normalize_whitespace(text: str) -> str:
        """Replace consecutive whitespace/newlines with standardized spacing."""
        if not text:
            return ""
        # Normalize carriage returns and tabs
        text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\t", " ")
        # Collapse multiple horizontal spaces
        text = re.sub(r"[ ]{2,}", " ", text)
        # Collapse excessive newlines (max 2 consecutive)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    @staticmethod
    def clean_text(text: str) -> str:
        """Complete cleaning pipeline: unicode normalization, control character removal, whitespace standardization."""
        if not text:
            return ""

        # NFKC Unicode normalization
        text = unicodedata.normalize("NFKC", text)

        # Remove unprintable/control characters except standard newlines
        text = "".join(ch for ch in text if ch == "\n" or not unicodedata.category(ch).startswith("C"))

        # Normalize whitespace
        text = TextCleaner.normalize_whitespace(text)
        return text
