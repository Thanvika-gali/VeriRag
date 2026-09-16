# PROOFRAG — AI Response Verification

> **Evidence-Grounded AI Response Verification & Multi-Agent Evaluation Platform**

---

## 1. Overview

**PROOFRAG** is an evidence-grounded AI evaluation platform designed to verify AI-generated answers against trusted reference knowledge bases (TruthfulQA, SQuAD, and custom documents). It moves beyond naive string similarity by utilizing dense semantic vectors (`all-MiniLM-L6-v2`), local persistent vector storage (`ChromaDB`), and a multi-agent judge pipeline that evaluates responses across three critical dimensions:

1. **Relevance Judge**: Calibrated 1–5 assessment of topical alignment with question-specific entity and action heuristics.
2. **Accuracy Judge**: Claim-level decomposition that penalizes mixed responses containing correct clauses combined with fabricated assertions ($\le 3/5$).
3. **Hallucination Detection Agent**: Assertion-level grounding assigning strict states (`SUPPORTED`, `UNSUPPORTED`, `CONTRADICTED`, `INSUFFICIENT_EVIDENCE`) and overall risk levels (`LOW`, `MEDIUM`, `HIGH`).
4. **Transparent Scoring & Verdict**: Linear multi-agent aggregation with rule-based verdict synthesis (`PASS`, `REVIEW`, `FAIL`).

---

## 2. Multi-Agent Evaluation Architecture

```
User Inquiry (Question + AI Response + Optional Reference Doc)
                         │
                         ▼
        ┌──────────────────────────────────┐
        │   RAG Candidate Pool Expansion   │
        │      (Top-10 Dual-Query RAG)     │
        └────────────────┬─────────────────┘
                         │
        ┌────────────────▼─────────────────┐
        │     Candidate Threshold Filter   │
        │  (Direct Evidence ≥ 0.50 & Entity│
        │   Matches vs. Excluded Matches)  │
        └───────┬──────────────────┬───────┘
                │                  │
         Direct Evidence    Additional Matches
                │
    ┌───────────┼──────────────────────────┐
    │           │                          │
    ▼           ▼                          ▼
┌─────────┐ ┌──────────────┐    ┌────────────────────┐
│Relevance│ │Accuracy Judge│    │Hallucination Agent │
│  Judge  │ │(Claim Decomp)│    │ (4 Grounding States)│
└────┬────┘ └──────┬───────┘    └─────────┬──────────┘
     │             │                      │
     └─────────────┼──────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────┐
│       Transparent Linear Score Synthesis     │
│ Overall = (Acc/5 * 0.40 + Rel/5 * 0.30       │
│           + Hal_Safety * 0.30) * 100         │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│         Rule-Based Final Verdict             │
│            PASS | REVIEW | FAIL              │
└──────────────────────────────────────────────┘
```

---

## 3. Evidence Candidate Filtering

To eliminate false-positive evidence grounding (such as watermelon seeds matching unrelated fruit passages like pomegranates or chewing gum):

- **Candidate Pool Expansion**: Retrieves the top-10 candidate chunks combining inquiry terms and joint answer embeddings.
- **Strict Relevance Filter**:
  - **Strong Match ($\ge 0.65$)**: Anchors direct evidence if it shares core discriminating entities with the inquiry.
  - **Moderate Match ($0.50 - 0.64$)**: Only counted as direct evidence if it explicitly contains the primary topic nouns.
  - **Contextual / Excluded ($< 0.50$)**: Separated cleanly into the collapsible **Additional Retrieved Matches** pool and excluded from primary evidence used.

---

## 4. Calibrated Multi-Agent Judges

### Relevance Judge (1–5)
- **5 (Completely Relevant)**: Thoroughly answers the inquiry with direct topical focus.
- **4 (Mostly Relevant)**: Relevant core response with minor extraneous context.
- **3 (Partially Relevant)**: Touches on the general subject but misses the direct question.
- **2 (Mostly Irrelevant)**: Weak lexical overlap; largely off-topic.
- **1 (Completely Irrelevant)**: Total topic mismatch (e.g., Photosynthesis vs. Elephants).

### Accuracy Judge (1–5)
- **5 (Fully Accurate)**: All assertions fully grounded in reference evidence or ground truth.
- **4 (Largely Accurate)**: Core claims correct with non-critical nuances omitted.
- **3 (Partially Accurate / Mixed)**: Partially correct statements mixed with ungrounded or fabricated assertions (e.g. Napoleon discovering photosynthesis).
- **2 (Substantially Inaccurate)**: Multiple contradictions or fundamental misconceptions.
- **1 (Completely Inaccurate)**: Direct contradiction of verified facts.

### Hallucination Detection Agent
- **SUPPORTED**: Explicitly grounded in reference evidence chunks.
- **UNSUPPORTED**: Fabricated assertion lacking basis in verified evidence.
- **CONTRADICTED**: Directly conflicts with factual reference passages.
- **INSUFFICIENT_EVIDENCE**: Knowledge base lacks sufficient context for verified determination.

---

## 5. Distinctive 4-Tier Navigation & Design System

The PROOFRAG interface features a four-tier operational hierarchy:

1. **VERIFY**
   - **Verify Response**: Interactive inquiry input, document attachment, demo presets, real-time stage progress, and evaluation view.
   - **Evaluation History**: Comprehensive audit logs, search, verdict filters, and inspection.
2. **EVIDENCE**
   - **Evidence Library**: Semantic search across ChromaDB embeddings with similarity and distance inspection.
   - **Data Sources**: Collection metrics for TruthfulQA (435 chunks), SQuAD (108 chunks), and custom uploads.
3. **INSIGHTS**
   - **Verification Insights**: Pass/Review/Fail distributions, score averages, and hallucination frequency metrics.
   - **Reports**: Detailed audit reports and JSON export capabilities.
4. **SYSTEM**
   - **System Status**: Telemetry, live health pings, embedding model diagnostics, and threshold matrix.

### Theme Switcher
- **Ink Wash Light Palette**: `#FFFFE3` (Warm Cream background), `#4A4A4A` (Dark Charcoal), `#CBCBCB` (Borders), `#6D8196` (Muted Blue-Gray).
- **Dark Slate Palette**: `#141618` (Deep Background), `#1E2023` (Surfaces), `#EDEDEA` (Primary text), `#7E97AF` (Accents).
- Toggled via the top bar or settings modal and persisted across sessions in `localStorage`.

---

## 6. Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+

### 1. Backend Setup
```bash
# Clone and enter workspace
git clone https://github.com/Thanvika-gali/VeriRag.git
cd VeriRag

# Activate virtual environment
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Run FastAPI backend (port 8001)
python backend/main.py
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
# App will be accessible at http://localhost:5173
```

---

## 7. Running the Automated Validation Suite

PROOFRAG includes a 10-scenario automated benchmark suite covering basic science, TruthfulQA misconceptions, fabricated claims, and formula integrity:

```bash
python -m pytest tests/test_validation_suite.py -v
```

All 10 benchmark scenarios run deterministically with zero mocked evaluations.