"""Reproducible Knowledge Base Build & Vector Indexing Script for VeriRAG."""

import argparse
import logging
import os
import sys
import time
from typing import List

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.rag.vector_store import VectorStoreManager
from knowledge_base.embeddings.embedder import EmbeddingGenerator
from knowledge_base.ingestion.ingest_squad import SQuADIngester
from knowledge_base.ingestion.ingest_truthfulqa import TruthfulQAIngester
from knowledge_base.preprocessing.chunker import DocumentChunker


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("build_kb")


def build_knowledge_base(
    truthfulqa_samples: int = 200,
    squad_samples: int = 300,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
    batch_size: int = 64,
    persist_dir: str = "chromadb_data",
) -> None:
    """Ingest, clean, chunk, embed, and index TruthfulQA + SQuAD datasets into ChromaDB."""
    start_time = time.time()
    logger.info("=== Starting VeriRAG Knowledge Base Build ===")
    logger.info(f"Target Persist Dir: {persist_dir}")
    logger.info(f"Chunk Config: size={chunk_size}, overlap={chunk_overlap}")

    # Step 1: Ingest TruthfulQA
    logger.info(f"Step 1/5: Ingesting TruthfulQA ({truthfulqa_samples} samples)...")
    truthfulqa_docs = TruthfulQAIngester.load(split="validation", max_samples=truthfulqa_samples)

    # Step 2: Ingest SQuAD
    logger.info(f"Step 2/5: Ingesting SQuAD ({squad_samples} samples)...")
    squad_docs = SQuADIngester.load(split="validation", max_samples=squad_samples)

    all_docs = truthfulqa_docs + squad_docs
    logger.info(f"Total raw documents loaded: {len(all_docs)}")

    # Step 3: Chunking
    logger.info("Step 3/5: Chunking documents with metadata preservation...")
    chunker = DocumentChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    all_chunks = chunker.chunk_batch(all_docs)
    logger.info(f"Generated {len(all_chunks)} total chunks.")

    if not all_chunks:
        logger.warning("No chunks generated. Exiting build.")
        return

    # Step 4: Embedding generation & Vector Store Indexing
    logger.info("Step 4/5: Initializing local embedding generator & ChromaDB...")
    embedder = EmbeddingGenerator()
    store = VectorStoreManager(persist_dir=persist_dir)

    chunk_ids = [c["chunk_id"] for c in all_chunks]
    chunk_texts = [c["text"] for c in all_chunks]
    chunk_metas = [c["metadata"] for c in all_chunks]

    logger.info(f"Step 5/5: Generating embeddings & indexing in batches of {batch_size}...")
    total_indexed = 0
    for i in range(0, len(all_chunks), batch_size):
        batch_ids = chunk_ids[i : i + batch_size]
        batch_texts = chunk_texts[i : i + batch_size]
        batch_metas = chunk_metas[i : i + batch_size]

        batch_embeddings = embedder.embed_batch(batch_texts, batch_size=batch_size)
        store.add_chunks(
            ids=batch_ids,
            documents=batch_texts,
            metadatas=batch_metas,
            embeddings=batch_embeddings,
        )
        total_indexed += len(batch_ids)
        logger.info(f"Indexed {total_indexed}/{len(all_chunks)} chunks...")

    elapsed = round(time.time() - start_time, 2)
    final_count = store.count()
    logger.info(f"=== Knowledge Base Build Complete in {elapsed}s! Total indexed chunks: {final_count} ===")


def main():
    parser = argparse.ArgumentParser(description="Build and index VeriRAG Reference Knowledge Base.")
    parser.add_argument("--tqa-samples", type=int, default=200, help="Number of TruthfulQA samples to ingest.")
    parser.add_argument("--squad-samples", type=int, default=300, help="Number of SQuAD samples to ingest.")
    parser.add_argument("--max-samples", type=int, default=None, help="Set equal max samples for both datasets.")
    parser.add_argument("--chunk-size", type=int, default=500, help="Character chunk size.")
    parser.add_argument("--chunk-overlap", type=int, default=50, help="Character chunk overlap.")
    parser.add_argument("--batch-size", type=int, default=64, help="Embedding generation batch size.")
    parser.add_argument("--persist-dir", type=str, default="chromadb_data", help="ChromaDB storage path.")

    args = parser.parse_args()

    tqa_s = args.max_samples if args.max_samples is not None else args.tqa_samples
    squad_s = args.max_samples if args.max_samples is not None else args.squad_samples

    build_knowledge_base(
        truthfulqa_samples=tqa_s,
        squad_samples=squad_s,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        batch_size=args.batch_size,
        persist_dir=args.persist_dir,
    )


if __name__ == "__main__":
    main()
