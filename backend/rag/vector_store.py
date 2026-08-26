"""ChromaDB Vector Store management for VeriRAG."""

import os
from typing import Any, Dict, List, Optional
import chromadb
from chromadb.config import Settings


DEFAULT_PERSIST_DIR = os.getenv("CHROMADB_PERSIST_DIR", "chromadb_data")
DEFAULT_COLLECTION_NAME = "verirag_knowledge_base"


class VectorStoreManager:
    """Manages local ChromaDB vector store initialization, indexing, and collection querying."""

    def __init__(
        self,
        persist_dir: str = DEFAULT_PERSIST_DIR,
        collection_name: str = DEFAULT_COLLECTION_NAME,
    ):
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self._client: Optional[chromadb.PersistentClient] = None
        self._collection = None

    @property
    def client(self) -> chromadb.PersistentClient:
        """Lazy-initialize ChromaDB persistent client."""
        if self._client is None:
            os.makedirs(self.persist_dir, exist_ok=True)
            self._client = chromadb.PersistentClient(
                path=self.persist_dir,
                settings=Settings(anonymized_telemetry=False, is_persistent=True),
            )
        return self._client

    @property
    def collection(self):
        """Lazy-initialize or get the default collection."""
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    def add_chunks(
        self,
        ids: List[str],
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        embeddings: Optional[List[List[float]]] = None,
    ) -> int:
        """Index chunks and metadata into the ChromaDB collection."""
        if not ids or not documents:
            return 0

        # Sanitize metadata values (ChromaDB requires str, int, float, or bool)
        clean_metadatas = []
        for meta in metadatas:
            clean_m = {}
            for k, v in meta.items():
                if v is None:
                    continue
                if isinstance(v, (str, int, float, bool)):
                    clean_m[k] = v
                else:
                    clean_m[k] = str(v)
            clean_metadatas.append(clean_m)

        if embeddings is not None:
            self.collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=clean_metadatas,
                embeddings=embeddings,
            )
        else:
            self.collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=clean_metadatas,
            )

        return len(ids)

    def query(
        self,
        query_text: Optional[str] = None,
        query_embedding: Optional[List[float]] = None,
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Perform semantic similarity search against the indexed collection."""
        total_count = self.count()
        if total_count == 0:
            return []

        fetch_k = min(n_results, total_count)

        query_params: Dict[str, Any] = {
            "n_results": fetch_k,
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            query_params["where"] = where

        if query_embedding is not None:
            query_params["query_embeddings"] = [query_embedding]
        elif query_text is not None:
            query_params["query_texts"] = [query_text]
        else:
            raise ValueError("Either query_text or query_embedding must be provided.")

        results = self.collection.query(**query_params)

        formatted_results: List[Dict[str, Any]] = []
        if not results or not results.get("ids") or not results["ids"][0]:
            return formatted_results

        ids = results["ids"][0]
        docs = results["documents"][0] if results.get("documents") else []
        metas = results["metadatas"][0] if results.get("metadatas") else []
        distances = results["distances"][0] if results.get("distances") else []

        for i in range(len(ids)):
            raw_dist = distances[i] if i < len(distances) else 0.0
            # For cosine space in ChromaDB, distance is 1 - cosine_similarity
            # Therefore similarity score = max(0.0, 1.0 - raw_dist)
            similarity = max(0.0, min(1.0, 1.0 - float(raw_dist)))

            meta = metas[i] if i < len(metas) else {}
            formatted_results.append({
                "chunk_id": ids[i],
                "text": docs[i] if i < len(docs) else "",
                "dataset_name": meta.get("dataset_name", "Unknown"),
                "similarity_score": round(similarity, 4),
                "distance": round(float(raw_dist), 4),
                "metadata": meta,
            })

        return formatted_results

    def count(self) -> int:
        """Return the number of items in the collection."""
        try:
            return self.collection.count()
        except Exception:
            return 0


# Global singleton instance
vector_store = VectorStoreManager()
