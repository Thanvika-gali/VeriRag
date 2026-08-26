"""Configurable document chunker with metadata preservation."""

import os
from typing import Any, Dict, List, Optional
from langchain_text_splitters import RecursiveCharacterTextSplitter
from knowledge_base.preprocessing.cleaner import TextCleaner


DEFAULT_CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))
DEFAULT_CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))


class DocumentChunker:
    """Splits documents into overlapping chunks while preserving rich parent metadata."""

    def __init__(
        self,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
        separators: Optional[List[str]] = None,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", ". ", "? ", "! ", " ", ""]
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=self.separators,
            length_function=len,
        )

    def chunk_document(
        self,
        text: str,
        doc_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Clean and chunk a single text document, attaching chunk-specific metadata."""
        cleaned_text = TextCleaner.clean_text(text)
        if not cleaned_text:
            return []

        # If text is shorter than chunk size, return single chunk
        if len(cleaned_text) <= self.chunk_size:
            raw_chunks = [cleaned_text]
        else:
            raw_chunks = self.splitter.split_text(cleaned_text)

        base_meta = metadata or {}
        chunk_records: List[Dict[str, Any]] = []

        total_chunks = len(raw_chunks)
        for idx, chunk_text in enumerate(raw_chunks):
            chunk_id = f"{doc_id}_c{idx}"
            chunk_meta = {
                **base_meta,
                "doc_id": doc_id,
                "chunk_id": chunk_id,
                "chunk_index": idx,
                "total_chunks": total_chunks,
                "char_length": len(chunk_text),
            }
            chunk_records.append({
                "chunk_id": chunk_id,
                "text": chunk_text,
                "metadata": chunk_meta,
            })

        return chunk_records

    def chunk_batch(
        self,
        documents: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Chunk a batch of document dictionaries: [{"doc_id": ..., "text": ..., "metadata": ...}]."""
        all_chunks: List[Dict[str, Any]] = []
        for doc in documents:
            doc_id = str(doc.get("doc_id", "doc_unknown"))
            text = str(doc.get("text", ""))
            meta = doc.get("metadata", {})
            chunks = self.chunk_document(text, doc_id=doc_id, metadata=meta)
            all_chunks.extend(chunks)
        return all_chunks


# Global singleton instance
chunker = DocumentChunker()
