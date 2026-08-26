"""Hugging Face TruthfulQA dataset ingestion module."""

import logging
from typing import Any, Dict, List, Optional
from datasets import load_dataset
from knowledge_base.preprocessing.cleaner import TextCleaner


logger = logging.getLogger(__name__)


class TruthfulQAIngester:
    """Ingests, parses, and standardizes the TruthfulQA benchmark dataset from Hugging Face."""

    DATASET_NAME = "truthfulqa/truthful_qa"
    FALLBACK_NAME = "truthful_qa"

    @classmethod
    def load(cls, split: str = "validation", max_samples: Optional[int] = None) -> List[Dict[str, Any]]:
        """Load TruthfulQA from Hugging Face and convert into standardized documents."""
        logger.info(f"Loading TruthfulQA ({split} split)...")
        try:
            ds = load_dataset(cls.DATASET_NAME, "generation", split=split)
        except Exception:
            logger.info(f"Falling back to legacy dataset identifier: {cls.FALLBACK_NAME}")
            ds = load_dataset(cls.FALLBACK_NAME, "generation", split=split)

        if max_samples and max_samples > 0:
            ds = ds.select(range(min(max_samples, len(ds))))

        documents: List[Dict[str, Any]] = []
        for idx, row in enumerate(ds):
            question = TextCleaner.clean_text(row.get("Question") or row.get("question") or "")
            best_answer = TextCleaner.clean_text(row.get("Best Answer") or row.get("best_answer") or "")
            category = TextCleaner.clean_text(row.get("Category") or row.get("category") or "General")
            source = TextCleaner.clean_text(row.get("Source") or row.get("source") or "")

            correct_answers = row.get("Correct Answers") or row.get("correct_answers") or []
            correct_text_list = [TextCleaner.clean_text(ans) for ans in correct_answers if ans]

            # Build grounded reference context text
            evidence_parts = [
                f"Question: {question}",
                f"Best Verified Answer: {best_answer}",
            ]
            if correct_text_list and correct_text_list != [best_answer]:
                additional_facts = "; ".join(correct_text_list[:3])
                evidence_parts.append(f"Additional Truthful Information: {additional_facts}")

            full_text = "\n".join(evidence_parts)
            doc_id = f"truthfulqa_{idx:05d}"

            documents.append({
                "doc_id": doc_id,
                "text": full_text,
                "metadata": {
                    "dataset_name": "TruthfulQA",
                    "question_id": f"tqa_{idx}",
                    "question": question,
                    "best_answer": best_answer,
                    "category": category,
                    "source": source,
                },
            })

        logger.info(f"Ingested {len(documents)} standardized documents from TruthfulQA.")
        return documents
