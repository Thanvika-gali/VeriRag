"""Central configuration for PROOFRAG evaluation and retrieval parameters.

Defines configurable thresholds, candidate pool sizes, and scoring weights.
All similarity and distance conversions are mathematically grounded:
For ChromaDB cosine space: distance d = 1 - cos(theta), so similarity = 1.0 - d.
"""

import os

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
# Evaluation Scoring Weights
# ==============================================================================
# Transparent engineering weighting for overall score aggregation
WEIGHT_ACCURACY: float = float(os.getenv("WEIGHT_ACCURACY", "0.40"))
WEIGHT_RELEVANCE: float = float(os.getenv("WEIGHT_RELEVANCE", "0.30"))
WEIGHT_HALLUCINATION: float = float(os.getenv("WEIGHT_HALLUCINATION", "0.30"))

# Product Branding
PRODUCT_NAME: str = "PROOFRAG"
PRODUCT_SUBTITLE: str = "AI RESPONSE VERIFICATION"
