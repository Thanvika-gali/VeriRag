"""Semantic retrieval and candidate evidence filtering service for PROOFRAG."""

import logging
from typing import Any, Dict, List, Optional
from backend.config import (
    CANDIDATE_POOL_SIZE,
    MAX_EVIDENCE_USED,
    MINIMUM_EVIDENCE_THRESHOLD,
    MODERATE_MATCH_THRESHOLD,
    STRONG_MATCH_THRESHOLD,
)
from backend.rag.vector_store import VectorStoreManager, vector_store
from knowledge_base.embeddings.embedder import EmbeddingGenerator, embedder

logger = logging.getLogger("proofrag.retriever")


class EvidenceRetriever:
    """Orchestrates query embedding generation, candidate pooling, and relevance filtering."""

    def __init__(
        self,
        store: Optional[VectorStoreManager] = None,
        generator: Optional[EmbeddingGenerator] = None,
    ):
        self.store = store or vector_store
        self.generator = generator or embedder

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        dataset_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve top-K evidence chunks matching the query string."""
        if not query or not query.strip():
            return []

        clean_query = query.strip()
        query_vector = self.generator.embed_text(clean_query)

        where_clause = None
        if dataset_filter and dataset_filter.lower() not in ("all", "all knowledge", "all sources", "none"):
            where_clause = {"dataset_name": dataset_filter}

        fetch_k = min(self.store.count(), max(top_k * 2, 10)) if self.store.count() > 0 else top_k
        candidates = self.store.query(
            query_embedding=query_vector,
            n_results=fetch_k,
            where=where_clause,
        )

        candidates.sort(key=lambda x: x.get("similarity_score", 0.0), reverse=True)
        return candidates[:top_k]

    def retrieve_and_filter_candidates(
        self,
        question: str,
        ai_response: str,
        candidate_pool_size: int = CANDIDATE_POOL_SIZE,
        dataset_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute true RAG candidate pooling followed by relevance filtering.

        1. Retrieves a broad candidate pool from ChromaDB via dual-query expansion.
        2. Applies calibrated thresholds to separate direct supporting evidence from weak/peripheral candidates.
        3. Excludes weak or off-subject matches from 'Evidence Used'.
        """
        q_clean = (question or "").strip()
        ans_clean = (ai_response or "").strip()

        if not q_clean and not ans_clean:
            return {
                "relevant_evidence": [],
                "additional_matches": [],
                "candidate_count": 0,
                "relevant_count": 0,
                "top_similarity": 0.0,
                "has_sufficient_evidence": False,
            }

        where_clause = None
        if dataset_filter and dataset_filter.lower() not in ("all", "all knowledge", "all sources", "none"):
            where_clause = {"dataset_name": dataset_filter}

        total_docs = self.store.count()
        pool_size = min(total_docs, max(candidate_pool_size, 10)) if total_docs > 0 else candidate_pool_size

        # Candidate pool dictionary keyed by chunk_id
        candidate_pool: Dict[str, Dict[str, Any]] = {}

        # 1. Question query
        if q_clean:
            q_emb = self.generator.embed_text(q_clean)
            q_matches = self.store.query(
                query_embedding=q_emb,
                n_results=pool_size,
                where=where_clause,
            )
            for m in q_matches:
                cid = m["chunk_id"]
                candidate_pool[cid] = m

        # 2. Joint query (Question + AI response)
        joint_query = f"{q_clean} {ans_clean}".strip()
        if joint_query and joint_query != q_clean:
            joint_emb = self.generator.embed_text(joint_query)
            joint_matches = self.store.query(
                query_embedding=joint_emb,
                n_results=pool_size,
                where=where_clause,
            )
            for m in joint_matches:
                cid = m["chunk_id"]
                if cid in candidate_pool:
                    if m.get("similarity_score", 0.0) > candidate_pool[cid].get("similarity_score", 0.0):
                        candidate_pool[cid] = m
                else:
                    candidate_pool[cid] = m

        # Sort all retrieved candidates by highest similarity score
        ranked_candidates = list(candidate_pool.values())
        ranked_candidates.sort(key=lambda x: x.get("similarity_score", 0.0), reverse=True)

        # Separate candidates into relevant_evidence vs additional_matches
        relevant_evidence: List[Dict[str, Any]] = []
        additional_matches: List[Dict[str, Any]] = []

        # Extract key discriminating nouns/entities from query (excluding generic action words)
        generic_words = {
            "what", "is", "are", "was", "were", "the", "a", "an", "and", "or", "in", "of", "to", "for",
            "on", "with", "at", "by", "from", "can", "you", "does", "did", "how", "why", "who", "which",
            "happen", "happens", "happening", "between", "eating", "eat", "eats", "when", "into", "over"
        }
        discriminating_terms = [
            w.strip("?,.!;:\"'()").lower() for w in q_clean.split()
            if len(w) > 3 and w.lower() not in generic_words
        ]

        top_similarity = ranked_candidates[0].get("similarity_score", 0.0) if ranked_candidates else 0.0

        for item in ranked_candidates:
            sim = float(item.get("similarity_score", 0.0))
            text_lower = item.get("text", "").lower()

            # Assign match tier
            if sim >= STRONG_MATCH_THRESHOLD:
                item["match_tier"] = "strong"
            elif sim >= MODERATE_MATCH_THRESHOLD:
                item["match_tier"] = "moderate"
            else:
                item["match_tier"] = "weak"

            # Strict relevance filter:
            # - Strong match (>= 0.65) is direct evidence if it doesn't contradict discriminating terms
            # - Moderate match (0.50 - 0.64) is only direct evidence if it specifically mentions the key subject terms
            # - Anything below 0.50 or lacking key subject entities is excluded as an additional/contextual match
            is_direct_evidence = False
            if sim >= STRONG_MATCH_THRESHOLD:
                if discriminating_terms:
                    # Require at least one key subject term for high-confidence direct grounding
                    if any(term in text_lower for term in discriminating_terms):
                        is_direct_evidence = True
                    elif sim >= 0.75:
                        is_direct_evidence = True
                else:
                    is_direct_evidence = True
            elif sim >= MINIMUM_EVIDENCE_THRESHOLD:
                # Moderate candidate: only count as direct evidence if it contains the primary topic nouns
                if discriminating_terms and all(term in text_lower for term in discriminating_terms[:2]):
                    is_direct_evidence = True

            if is_direct_evidence and len(relevant_evidence) < MAX_EVIDENCE_USED:
                relevant_evidence.append(item)
            else:
                additional_matches.append(item)

        logger.info(
            f"[Evidence Pipeline] Query: '{q_clean[:50]}' | Candidates: {len(ranked_candidates)} "
            f"-> Filtered Relevant: {len(relevant_evidence)} | Excluded Additional: {len(additional_matches)}"
        )

        return {
            "relevant_evidence": relevant_evidence,
            "additional_matches": additional_matches,
            "candidate_count": len(ranked_candidates),
            "relevant_count": len(relevant_evidence),
            "top_similarity": round(top_similarity, 4),
            "has_sufficient_evidence": len(relevant_evidence) > 0 and top_similarity >= MINIMUM_EVIDENCE_THRESHOLD,
        }

    def retrieve_grounded_evidence(
        self,
        question: str,
        ai_response: str,
        top_k: int = 5,
        dataset_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve filtered relevant evidence list (backward-compatible method)."""
        filtered = self.retrieve_and_filter_candidates(
            question=question,
            ai_response=ai_response,
            candidate_pool_size=max(top_k * 2, 10),
            dataset_filter=dataset_filter,
        )
        return filtered["relevant_evidence"][:top_k]


# Global singleton instance
retriever = EvidenceRetriever()
