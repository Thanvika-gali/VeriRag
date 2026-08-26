"""Hugging Face SQuAD dataset ingestion module."""

import logging
from typing import Any, Dict, List, Optional
from datasets import load_dataset
from knowledge_base.preprocessing.cleaner import TextCleaner


logger = logging.getLogger(__name__)


class SQuADIngester:
    """Ingests, parses, and standardizes the SQuAD benchmark dataset from Hugging Face."""

    DATASET_NAME = "rajpurkar/squad"
    FALLBACK_NAME = "squad"

    @classmethod
    def load(cls, split: str = "validation", max_samples: Optional[int] = None) -> List[Dict[str, Any]]:
        """Load SQuAD from Hugging Face and convert into standardized documents."""
        logger.info(f"Loading SQuAD ({split} split)...")
        try:
            ds = load_dataset(cls.DATASET_NAME, split=split)
        except Exception:
            logger.info(f"Falling back to legacy dataset identifier: {cls.FALLBACK_NAME}")
            ds = load_dataset(cls.FALLBACK_NAME, split=split)

        if max_samples and max_samples > 0:
            ds = ds.select(range(min(max_samples, len(ds))))

        documents: List[Dict[str, Any]] = []
        for idx, row in enumerate(ds):
            raw_id = row.get("id") or f"squad_{idx}"
            title = TextCleaner.clean_text(row.get("title") or "General")
            context = TextCleaner.clean_text(row.get("context") or "")
            question = TextCleaner.clean_text(row.get("question") or "")

            answers_dict = row.get("answers") or {}
            answer_texts = answers_dict.get("text") or []
            first_answer = TextCleaner.clean_text(answer_texts[0]) if answer_texts else ""

            # Standardized evidence representation: Topic Title + Context + Ground Truth Q&A
            evidence_parts = []
            if title and title != "General":
                evidence_parts.append(f"Topic: {title}")
            if context:
                evidence_parts.append(f"Context: {context}")
            if question and first_answer:
                evidence_parts.append(f"Reference Q&A: {question} -> {first_answer}")

            full_text = "\n".join(evidence_parts) if evidence_parts else context
            doc_id = f"squad_{raw_id}"

            documents.append({
                "doc_id": doc_id,
                "text": full_text,
                "metadata": {
                    "dataset_name": "SQuAD",
                    "question_id": raw_id,
                    "title": title,
                    "question": question,
                    "answer": first_answer,
                    "source": f"SQuAD v1.1 - {title}",
                },
            })

        logger.info(f"Ingested {len(documents)} standardized documents from SQuAD.")
        return documents
