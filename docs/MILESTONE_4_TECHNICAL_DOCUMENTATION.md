# PROOFRAG / VeriRAG: Technical System Documentation
**Milestone 4 — Comprehensive System Architecture, Evaluation Engine & Operational Reference**

---

## 1. Problem Statement
Generative Large Language Models (LLMs) used in retrieval-augmented workflows frequently generate convincing yet erroneous responses. Critical failure modes include:
- **Hallucination**: Fabrication of plausible entities, dates, causal relations, or historical claims unsupported by authoritative context.
- **Factual Inaccuracy**: Stating information directly contradicting verified domain knowledge.
- **Topical Drift / Irrelevance**: Formulating coherent answers to questions different from what was actually asked.
- **Incompleteness**: Omitting critical sub-facets or constraints of multi-part prompts while projecting a false aura of completion.

Traditional evaluation approaches rely on monolithic end-to-end LLM judges or naive n-gram metrics (ROUGE, BLEU) that suffer from judge self-preference, non-determinism, and lack of atomic claim traceability. **PROOFRAG** solves this by decomposing evaluation across specialized autonomous judge agents backed by local semantic vector search, prioritized reference hierarchies, and explainable multi-metric verdict synthesis.

---

## 2. Objectives
1. **Multi-Dimensional Decomposition**: Evaluate AI responses independently across Relevance, Accuracy, Hallucination Safety, and Completeness.
2. **Prioritized Reference Grounding**: Ground evaluations on a strict hierarchy: User Ground Truth Reference > Uploaded Supporting Documents > Semantic Knowledge Base Chunks (ChromaDB).
3. **Claim-Level Atomic Verification**: Parse candidate answers into discrete atomic claims and verify each against dense embeddings and contradiction patterns.
4. **Transparent Explainability**: Provide granular justifications, verbatim supporting evidence quotes, and flagged claims for every score.
5. **Robust Batch Processing & Fault Isolation**: Evaluate hundreds of records concurrently with strict row-level isolation and CSV schema error resilience.
6. **Dynamic Analytics & Reporting**: Real-time aggregation of stored evaluation records without hardcoded statistics, complemented by professional multi-page PDF executive reports.

---

## 3. Overall Architecture
PROOFRAG follows a decoupled, three-tier architecture:

```
[ Frontend: React 18 + Vite + Tailwind/Modern UI ]
                 │
                 ▼  REST API (JSON & Binary Stream)
[ Backend: FastAPI + Pydantic v2 + SQLite + ChromaDB ]
                 │
                 ├── [ Evaluation Orchestrator ]
                 │       ├── Semantic Retriever (BAAI/bge-small-en-v1.5)
                 │       ├── Relevance Judge Agent
                 │       ├── Accuracy Judge Agent
                 │       ├── Hallucination Judge Agent
                 │       ├── Completeness Judge Agent
                 │       └── Verdict Agent (Weighted Synthesis & Critical Overrides)
                 │
                 ├── [ Storage Engine: SQLite (submissions.db) ]
                 └── [ PDF Reporting Engine: ReportLab 5.0 ]
```

---

## 4. Frontend Architecture
Built with **React 18** and **Vite**, featuring responsive dark/light themes, persistent state management, and real-time dashboard analytics:
- **`App.jsx`**: Central navigation router coordinating 6 core operational views:
  1. `VerifyView`: Interactive single-response verification.
  2. `BatchVerifyView`: CSV batch upload, progress tracking, and tabular results.
  3. `AnalyticsView`: Evaluation Scoring Dashboard with interactive filters, distribution charts, frequent issue tables, and drill-down records.
  4. `ReportsView`: Executive PDF generation and batch-level audit report downloads.
  5. `HistoryView`: Complete audit log of past evaluations with search and JSON inspect.
  6. `KnowledgeBaseView`: Knowledge source management, vector chunk browsing, and document ingestion.
- **Design Tokens**: Standardized CSS variables supporting seamless theme transitions, accessible contrast ratios, and glassmorphism cards.

---

## 5. Backend Architecture
Implemented using **FastAPI** (`backend/main.py`, `backend/api/endpoints.py`):
- **CORS Middleware**: Secure cross-origin resource sharing configured for local and containerized frontends.
- **Asynchronous Execution**: Thread-pool offloading for compute-heavy vector embedding and batch evaluation.
- **Dependency Injection**: Shared singleton instances for SQLite database helper, evaluation orchestrator, and PDF report generator.
- **Clean API Separation**: Modular routes for `/api/verify`, `/api/verify/batch`, `/api/dashboard/stats`, `/api/reports/pdf`, and `/api/knowledge`.

---

## 6. RAG Pipeline
The Retrieval-Augmented Generation pipeline (`knowledge_base/retrieval/`) provides multi-stage semantic grounding:
1. **Candidate Retrieval**: Dense vector similarity search via ChromaDB retrieving `top_k * 2` candidate chunks.
2. **Confidence Filtering**: Threshold filtering using `MINIMUM_EVIDENCE_THRESHOLD = 0.35` and `STRONG_MATCH_THRESHOLD = 0.50`.
3. **Context Construction**: Passages formatted and tagged with dataset metadata, preserved across downstream judges.

---

## 7. Reference Knowledge Base
Persisted in **ChromaDB** (`chromadb_data/`) using `BAAI/bge-small-en-v1.5` dense embeddings:
- **TruthfulQA Benchmark Knowledge**: Curated verified facts across science, health, history, and common misconceptions.
- **Ingestion Engine** (`knowledge_base/ingestion/`): Token-aware recursive text splitting with metadata tagging.
- **Custom Document Ingestion**: Supports `.txt` and `.md` document uploads dynamically integrated into evaluation candidate pools.

---

## 8. Evaluation Orchestrator
Coordinates the evaluation lifecycle (`evaluation/orchestrator.py`):
1. Normalizes and validates inputs.
2. Executes semantic evidence retrieval from the knowledge base.
3. Invokes the four specialized judge agents sequentially or in parallel.
4. Passes dimension outputs to the Verdict Agent for final synthesis.
5. Persists evaluation records and returns the structured JSON payload.

---

## 9. Relevance Judge
Evaluates whether the AI response addresses the inquiry or drifts into unrelated subjects (`evaluation/agents/relevance_judge.py`):
- **Scale (1–5)**:
  - `5`: Fully Relevant (Direct, focused answer).
  - `4`: Mostly Relevant (Addresses core with minor tangential remarks).
  - `3`: Partially Relevant (Mix of relevant statements and off-topic discussion).
  - `2`: Minimally Relevant (Tangential mention without answering the question).
  - `1`: Completely Irrelevant (Unrelated topic).
- **Technique**: Dense semantic similarity between question prompt and response, normalized for length and lexical grounding.

---

## 10. Accuracy Judge
Assesses factual consistency against prioritized reference evidence (`evaluation/agents/accuracy_judge.py`):
- **Scale (1–5)**:
  - `5`: Fully Correct (Factually consistent with verified facts).
  - `4`: Mostly Correct (Core facts accurate; minor imprecision).
  - `3`: Partially Correct (Mix of confirmed facts and unverified claims).
  - `2`: Mostly Incorrect (Central claim contradicts reference).
  - `1`: Completely Incorrect (Entirely contrary to verified facts).
- **Technique**: Atomic claim decomposition, negation pattern matching, distinctive entity replacement detection, and dense similarity thresholding.

---

## 11. Hallucination Judge
Detects ungrounded or fabricated claims (`evaluation/agents/hallucination_judge.py`):
- **Risk Tiers**:
  - `LOW`: All assertions grounded in verified evidence (0 unsupported claims).
  - `MEDIUM`: 1 unsupported claim or minor unverified assertion.
  - `HIGH`: Direct contradictions or multiple fabricated claims.
- **Technique**: Pronoun and anaphora contextualization, atomic claim verification, and citation extraction.

---

## 12. Completeness Judge
Measures requirement coverage against prompt sub-questions (`evaluation/agents/completeness_judge.py`):
- **Scale (1–5)**:
  - `5`: Fully Complete (All requirements thoroughly covered).
  - `4`: Mostly Complete (Core requirements covered; minor detail omitted).
  - `3`: Partially Complete (Important sub-questions left unanswered).
  - `2`: Substantially Incomplete (Only touches a minor facet).
  - `1`: Completely Incomplete (Fails to address core subject).
- **Technique**: Syntactic requirement decomposition, aspect-specific keyword grounding excluding shared query terms, and semantic synonym expansion.

---

## 13. Verdict Agent
Synthesizes dimensional assessments into a final actionable verdict (`evaluation/agents/verdict_agent.py`):
- **Verdicts**: `PASS`, `NEEDS IMPROVEMENT`, `FAIL`.
- **Weighted Formula**:
  $$\text{Score} = (\text{Accuracy} \times 0.35 + \text{Relevance} \times 0.25 + \text{Completeness} \times 0.20 + \text{Hallucination Safety} \times 0.20) \times 20$$
- **Safety Overrides**:
  - High Hallucination Risk $\rightarrow$ Verdict capped at `FAIL`.
  - Accuracy Score $\le 2$ $\rightarrow$ Verdict forced to `FAIL` regardless of high relevance or completeness.

---

## 14. Database & Storage Architecture
Single SQLite database (`submissions.db`) managing relational tables:
- **`submissions`**: Evaluation records storing query, response, reference, dimension scores, verdict, overall score, raw JSON details, batch ID, and timestamps.
- **`batch_jobs`**: Batch execution jobs, status, total records, pass/fail counts, and execution metrics.
- **`knowledge_sources`**: Registered document corpora and metadata.

---

## 15. Evaluation Scoring Dashboard (M4.1)
Dynamic analytics computed directly from SQLite records (`backend/database/sqlite_db.py` `get_dashboard_stats`):
- Total records evaluated and verdict breakdown (`PASS`, `NEEDS IMPROVEMENT`, `FAIL`).
- Average overall score and dimension averages (Accuracy, Relevance, Completeness, Hallucination Safety).
- Hallucination statistics: frequency percentage, flagged record count, and total unsupported claims.
- Completeness statistics: breakdown of complete, partial, and incomplete records with missing-aspect frequency.
- Distribution breakdowns: overall score tiers (90-100, 75-89, 50-74, 0-49) and 1–5 distribution per dimension.
- Interactive multi-dimensional filtering (Batch, Verdict, Score Range, Hallucination status).
- Drill-down record inspection table with instant search and snippet inspection.

---

## 16. Batch Evaluation Engine
High-throughput batch evaluation (`backend/api/endpoints.py` `/api/verify/batch`):
- Multipart CSV parsing with UTF-8 BOM, semicolon, and delimiter autodetection.
- Record validation isolating missing fields and malformed rows without crashing the batch.
- Real-time progress updates with aggregated batch metrics and error logging.

---

## 17. PDF Report Generation Service (M4.2)
Professional multi-page export service (`backend/services/pdf_report_service.py`) implemented via **ReportLab**:
- **Design Structure**:
  1. Header with title, report metadata, and generation timestamp.
  2. Executive Summary with overall health indicators.
  3. Key Performance Indicator (KPI) cards with Pass Rate and Average Scores.
  4. Dimensional Breakdown and Hallucination / Completeness audit tables.
  5. Multi-page per-record evaluation table with automatic cell wrapping.
  6. Detailed case study findings for flagged or problematic responses.
  7. Automated actionable improvement recommendations.
- **Technical Features**: Two-pass `NumberedCanvas` ("Page X of Y"), table auto-pagination, strict padding, and overflow prevention.

---

## 18. Scoring Methodology
| Dimension | Range | Weight | Description |
|---|---|---|---|
| **Accuracy** | 1–5 | 35% | Factual correctness vs authoritative reference. |
| **Relevance** | 1–5 | 25% | Topical alignment and query satisfaction. |
| **Completeness** | 1–5 | 20% | Coverage of all requirements and sub-aspects. |
| **Hallucination Safety** | 1–5 (derived) | 20% | Groundedness (Low=5, Medium=2.5, High=0). |
| **Overall Score** | 0–100 | 100% | Normalized weighted composite score. |

---

## 19. Verdict Thresholds
- **PASS**: Overall Score $\ge 75$, Accuracy $\ge 3$, Hallucination Risk = `LOW`.
- **NEEDS IMPROVEMENT**: Overall Score between $50$ and $74$, or minor completeness/relevance gaps.
- **FAIL**: Overall Score $< 50$, or Accuracy $\le 2$, or Hallucination Risk = `HIGH`.

---

## 20. API Endpoints
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/verify` | Run single response verification. |
| `POST` | `/api/verify/batch` | Upload and process CSV batch evaluation. |
| `GET` | `/api/dashboard/stats` | Retrieve dynamic dashboard statistics with filters. |
| `GET` | `/api/reports/pdf` | Download generated multi-page PDF evaluation report. |
| `GET` | `/api/reports/data` | Fetch structured JSON data for executive reporting. |
| `GET` | `/api/submissions` | List stored evaluation records with search & pagination. |
| `GET` | `/api/submissions/{id}` | Retrieve individual submission details. |
| `POST` | `/api/knowledge/upload` | Ingest supporting text/markdown documents into ChromaDB. |

---

## 21. Input/Output Models
- **`SingleVerificationRequest`**: `question` (str, req), `ai_response` (str, req), `reference_answer` (str, opt), `source_document` (str, opt).
- **`EvaluationResultResponse`**: `overall_score`, `verdict`, `dimension_scores`, `claims_breakdown`, `missing_aspects`, `evidence`.
- **`DashboardStatsResponse`**: Aggregated totals, percentages, distributions, frequent issues, and drill-down records.

---

## 22. CSV Format for Batch Evaluation
Standard CSV format with flexible column naming:
```csv
question,ai_response,reference_answer,source_document
"What is photosynthesis?","Photosynthesis converts light into chemical energy.","Outputs are glucose and oxygen.",""
"What causes tides?","Gravitational forces exerted by the Moon and Sun.","Tides are caused by gravitational pull of Moon/Sun.",""
```
Headers are case-insensitive and whitespace-tolerant.

---

## 23. Testing Methodology
Comprehensive 14-test validation suite (`tests/test_m4_validation_suite.py`) confirming:
1. `test_01`: Single evaluation pipeline end-to-end data flow.
2. `test_02`: Batch evaluation pipeline from CSV parse to dashboard persistence.
3. `test_03`: Correct response benchmark (high score, PASS verdict).
4. `test_04`: Irrelevant response benchmark (low relevance, appropriate verdict).
5. `test_05`: Incorrect response benchmark (low accuracy, unsupported claims).
6. `test_06`: Incomplete response benchmark (low completeness, missing aspects identified).
7. `test_07`: Hallucinated response benchmark (unsupported claim isolated, high risk).
8. `test_08`: Contradictory response benchmark (contradiction detected, penalty applied).
9. `test_09`: Evaluation without reference answer utilizing semantic RAG chunks.
10. `test_10`: Resilient invalid CSV handling (missing fields, empty rows).
11. `test_11`: Scoring consistency and reasoning correlation.
12. `test_12`: Critical regression check (Nitrogen/methane photosynthesis failure test).
13. `test_13`: Dashboard mathematical formula exactness ($Total = PASS + Review + FAIL$).
14. `test_14`: PDF report generation service output and byte validity.

---

## 24. Test Results
- **M4 Validation Suite**: 14/14 tests passed (100% pass rate).
- **Completeness Suite**: 10/10 tests passed.
- **Full Project Suite**: 110/110 tests passed without regression across M1, M2, and M3 modules.
- **Critical Photosynthesis Regression**: Stating nitrogen and methane for photosynthesis produces Accuracy Score 1 ("Completely Incorrect"), Overall Score 33, and Verdict `FAIL`.

---

## 25. Limitations
1. **Local Model Capacity**: Local sentence-transformers embeddings (`bge-small-en-v1.5`) rely on entity extraction heuristics when deep multi-hop reasoning is required without external LLM judges.
2. **Domain-Specific Ontologies**: Specialized medical or legal terms outside TruthfulQA require custom document ingestion into the knowledge base for optimal grounding.
3. **Execution Latency**: Full 4-dimension claim decomposition for long responses (500+ words) requires multiple embedding passes, scaling with claim count.

---

## 26. Future Scope
1. **Multi-Modal Validation**: Extending judges to verify image captions and chart interpretations against document figures.
2. **Streaming Judge Responses**: Token-by-token evaluation streaming over WebSockets for interactive chat applications.
3. **Automated Dynamic Prompt Correction**: Self-correcting AI agent loop that automatically rewrites responses failing evaluation to achieve a verified `PASS`.
