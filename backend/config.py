"""Central configuration for PROOFRAG evaluation and retrieval parameters.

Defines configurable thresholds, candidate pool sizes, and scoring weights.
All similarity and distance conversions are mathematically grounded:
For ChromaDB cosine space: distance d = 1 - cos(theta), so similarity = 1.0 - d.
"""

import os
from pathlib import Path

# Project root directory (parent of backend/)
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

# Persistent Storage Paths (anchored to project root)
_env_chroma = os.getenv("CHROMADB_PERSIST_DIR", "chromadb_data")
_chroma_path = Path(_env_chroma)
CHROMADB_PERSIST_PATH: str = str(_chroma_path if _chroma_path.is_absolute() else PROJECT_ROOT / _chroma_path)

_env_db = os.getenv("SQLITE_DB_PATH", "submissions.db")
_db_path = Path(_env_db)
SQLITE_DB_PATH: str = str(_db_path if _db_path.is_absolute() else PROJECT_ROOT / _db_path)

# ==============================================================================
# RAG Retrieval & Evidence Filtering Thresholds
# ==============================================================================
# Note: These are engineering thresholds calibrated against benchmark validation cases,
# not scientifically absolute constants.
STRONG_MATCH_THRESHOLD: float = float(os.getenv("STRONG_MATCH_THRESHOLD", "0.65"))
MODERATE_MATCH_THRESHOLD: float = float(os.getenv("MODERATE_MATCH_THRESHOLD", "0.50"))
MINIMUM_EVIDENCE_THRESHOLD: float = float(os.getenv("MINIMUM_EVIDENCE_THRESHOLD", "0.50"))

# Number of nearest neighbors to retrieve from ChromaDB for the candidate pool before filtering
CANDIDATE_POOL_SIZE: int = int(os.getenv("CANDIDATE_POOL_SIZE", "10"))

# Maximum number of filtered supporting evidence chunks to pass to judges
MAX_EVIDENCE_USED: int = int(os.getenv("MAX_EVIDENCE_USED", "5"))

# ==============================================================================
# Evaluation Scoring Weights & Verdict Thresholds (Milestone 3)
# ==============================================================================
# Configurable engineering weighting for 4-dimension overall score aggregation:
# Accuracy: 35%, Hallucination: 30%, Relevance: 20%, Completeness: 15%
WEIGHT_ACCURACY: float = float(os.getenv("WEIGHT_ACCURACY", "0.35"))
WEIGHT_HALLUCINATION: float = float(os.getenv("WEIGHT_HALLUCINATION", "0.30"))
WEIGHT_RELEVANCE: float = float(os.getenv("WEIGHT_RELEVANCE", "0.20"))
WEIGHT_COMPLETENESS: float = float(os.getenv("WEIGHT_COMPLETENESS", "0.15"))

# Configurable verdict classification thresholds
VERDICT_PASS_THRESHOLD: int = int(os.getenv("VERDICT_PASS_THRESHOLD", "80"))
VERDICT_NEEDS_IMPROVEMENT_THRESHOLD: int = int(os.getenv("VERDICT_NEEDS_IMPROVEMENT_THRESHOLD", "60"))

# Product Branding
PRODUCT_NAME: str = "PROOFRAG"
PRODUCT_SUBTITLE: str = "AI RESPONSE VERIFICATION"

