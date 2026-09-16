import React, { useState } from 'react';
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  HelpCircle,
  Database,
  ChevronDown,
  ChevronUp,
  Sparkles,
  Info,
  ShieldCheck,
  Cpu,
  Layers,
} from 'lucide-react';

export default function EvaluationResultView({ evaluation, onBackToForm }) {
  const [expandedChunkId, setExpandedChunkId] = useState(null);
  const [showTechDetails, setShowTechDetails] = useState(false);
  const [showAdditionalMatches, setShowAdditionalMatches] = useState(false);

  if (!evaluation) {
    return (
      <div className="ink-card empty-state-box">
        <ShieldCheck size={40} className="empty-icon" />
        <h3 className="empty-heading">Ready to Verify</h3>
        <p className="empty-sub">
          Submit a question and an AI-generated answer to inspect factual grounding,
          relevance, and claim-level hallucination detection.
        </p>
      </div>
    );
  }

  const {
    question,
    ai_response,
    overall_score = 0,
    verdict = 'REVIEW',
    verdict_reasoning = '',
    relevance = {},
    accuracy = {},
    hallucination = {},
    retrieved_evidence = [],
    additional_matches = [],
    candidate_count = 0,
    match_status = 'moderate',
    top_similarity = 0.0,
  } = evaluation;

  const totalCandidates = candidate_count || (retrieved_evidence.length + additional_matches.length);

  const verdictClass =
    verdict === 'PASS'
      ? 'verdict-pass'
      : verdict === 'FAIL'
      ? 'verdict-fail'
      : 'verdict-review';

  const halRisk = hallucination.risk_level || 'LOW';
  const halStatus = hallucination.hallucination_status || 'NONE';

  const flaggedClaims = hallucination.flagged_claims || [];

  const toggleChunk = (id) => {
    setExpandedChunkId(expandedChunkId === id ? null : id);
  };

  return (
    <div className="result-view-container">
      {/* Top Banner: Score, Verdict, and Hallucination Risk */}
      <div className="result-header-banner">
        <div className="score-overview-group">
          <div className="score-number-box">
            <span className="score-big">{overall_score}</span>
            <span className="score-denom">/ 100</span>
          </div>
          <div className="score-label-col">
            <span className="score-title-text">Overall Score</span>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Weighted verification index
            </span>
          </div>
        </div>

        <div className="result-verdict-group">
          <div className="verdict-item-box">
            <span className="score-title-text">Verdict</span>
            <span className={`verdict-badge ${verdictClass}`}>
              {verdict}
            </span>
          </div>

          <div className="verdict-item-box">
            <span className="score-title-text">Hallucination Risk</span>
            <span
              style={{
                fontSize: '0.82rem',
                fontWeight: 700,
                color:
                  halRisk === 'HIGH'
                    ? 'var(--status-fail-text)'
                    : halRisk === 'MEDIUM'
                    ? 'var(--status-review-text)'
                    : 'var(--status-pass-text)',
              }}
            >
              {halRisk}
            </span>
          </div>
        </div>
      </div>

      {/* Three Major Evaluation Cards: Accuracy, Relevance, Hallucination */}
      <div className="three-judges-grid">
        {/* Accuracy Card */}
        <div className="judge-card">
          <div className="judge-card-header">
            <span className="judge-card-title">Accuracy</span>
            <span className="judge-card-score">{accuracy.score || 0} / 5</span>
          </div>
          <span className="judge-card-label">{accuracy.label || 'Evaluated'}</span>
          <p className="judge-card-reasoning">
            {accuracy.reasoning || 'Factual consistency verified against reference knowledge.'}
          </p>
        </div>

        {/* Relevance Card */}
        <div className="judge-card">
          <div className="judge-card-header">
            <span className="judge-card-title">Relevance</span>
            <span className="judge-card-score">{relevance.score || 0} / 5</span>
          </div>
          <span className="judge-card-label">{relevance.label || 'Evaluated'}</span>
          <p className="judge-card-reasoning">
            {relevance.reasoning || 'Topical alignment with the submitted question.'}
          </p>
        </div>

        {/* Hallucination Check Card */}
        <div className="judge-card">
          <div className="judge-card-header">
            <span className="judge-card-title">Hallucination Check</span>
            <span
              className="judge-card-score"
              style={{
                fontSize: '1rem',
                color:
                  halRisk === 'HIGH'
                    ? 'var(--status-fail-text)'
                    : halRisk === 'MEDIUM'
                    ? 'var(--status-review-text)'
                    : 'var(--status-pass-text)',
              }}
            >
              {halRisk} RISK
            </span>
          </div>
          <span className="judge-card-label">Status: {halStatus}</span>
          <p className="judge-card-reasoning">
            {hallucination.summary || 'Assertion-level grounding check complete.'}
          </p>
        </div>
      </div>

      {/* Why did VeriRAG reach this result? */}
      <div className="ink-card">
        <div className="ink-card-header">
          <div className="card-title-block">
            <div className="card-icon-wrap">
              <Sparkles size={16} />
            </div>
            <div>
              <h3 className="card-heading">Why did PROOFRAG reach this result?</h3>
              <p className="card-subtext">Synthesized reasoning from evaluation judge agents</p>
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {verdict_reasoning && (
            <div style={{ padding: '12px 14px', backgroundColor: 'var(--bg-surface-subtle)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
              <strong style={{ fontSize: '0.85rem', color: 'var(--text-primary)', display: 'block', marginBottom: '4px' }}>
                Verdict Determination:
              </strong>
              <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                {verdict_reasoning}
              </span>
            </div>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '12px' }}>
            <div style={{ padding: '10px 12px', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)' }}>
              <span style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
                Accuracy Justification:
              </span>
              <p style={{ fontSize: '0.82rem', color: 'var(--text-primary)', marginTop: '4px' }}>
                {accuracy.reasoning}
              </p>
            </div>

            <div style={{ padding: '10px 12px', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)' }}>
              <span style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
                Relevance Justification:
              </span>
              <p style={{ fontSize: '0.82rem', color: 'var(--text-primary)', marginTop: '4px' }}>
                {relevance.reasoning}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Claim-Level Hallucination Breakdown */}
      <div className="ink-card">
        <div className="ink-card-header">
          <div className="card-title-block">
            <div className="card-icon-wrap">
              <CheckCircle2 size={16} />
            </div>
            <div>
              <h3 className="card-heading">Claim-Level Grounding Analysis</h3>
              <p className="card-subtext">Individual factual statements decomposed from the AI response</p>
            </div>
          </div>
          <span style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
            {flaggedClaims.length} {flaggedClaims.length === 1 ? 'Claim' : 'Claims'} Analyzed
          </span>
        </div>

        {flaggedClaims.length === 0 ? (
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            No individual claims extracted from response.
          </p>
        ) : (
          <div className="claims-stack">
            {flaggedClaims.map((claimItem, idx) => {
              const status = claimItem.status;
              const badgeClass =
                status === 'SUPPORTED'
                  ? 'claim-supported'
                  : status === 'UNSUPPORTED'
                  ? 'claim-unsupported'
                  : status === 'CONTRADICTED'
                  ? 'claim-contradicted'
                  : 'claim-insufficient';

              return (
                <div key={idx} className="claim-item-card">
                  <div className="claim-item-header">
                    <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)' }}>
                      Claim {idx + 1}
                    </span>
                    <span className={`claim-badge ${badgeClass}`}>
                      {status === 'INSUFFICIENT_EVIDENCE' ? 'Insufficient Evidence' : status}
                    </span>
                  </div>

                  <div className="claim-text">"{claimItem.claim}"</div>

                  {claimItem.reasoning && (
                    <div className="claim-reason-row">
                      <strong>Reason: </strong>
                      <span>{claimItem.reasoning}</span>
                    </div>
                  )}

                  {claimItem.evidence && (
                    <div className="claim-evidence-quote">
                      <strong>Evidence: </strong>
                      <span>"{claimItem.evidence}"</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Evidence Presentation */}
      <div className="ink-card">
        <div className="ink-card-header">
          <div className="card-title-block">
            <div className="card-icon-wrap">
              <Database size={16} />
            </div>
            <div>
              <h3 className="card-heading">Evidence Used</h3>
              <p className="card-subtext">
                Direct supporting passages meeting strict relevance criteria
              </p>
            </div>
          </div>
          <span style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--accent-primary)' }}>
            {retrieved_evidence.length} Relevant {retrieved_evidence.length === 1 ? 'Source' : 'Sources'}
          </span>
        </div>

        {retrieved_evidence.length === 0 ? (
          <div className="empty-state-box" style={{ padding: '24px' }}>
            <Info size={24} className="empty-icon" />
            <p className="empty-sub">No reference evidence chunks met the direct grounding threshold for this inquiry.</p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            {retrieved_evidence.map((item, idx) => {
              const simPercent = Math.round((item.similarity_score || item.similarity || 0) * 100);
              const isExpanded = expandedChunkId === (item.chunk_id || idx);
              const tier = item.match_tier || (simPercent >= 70 ? 'strong' : simPercent >= 50 ? 'moderate' : 'weak');

              return (
                <div
                  key={item.chunk_id || idx}
                  style={{
                    backgroundColor: 'var(--bg-surface-subtle)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: 'var(--radius-md)',
                    padding: '16px',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)' }}>
                        #{idx + 1}
                      </span>
                      <span style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-primary)', backgroundColor: 'var(--border-subtle)', padding: '2px 8px', borderRadius: '4px' }}>
                        {item.dataset_name || item.source || 'Knowledge Base'}
                      </span>
                      <span
                        style={{
                          fontSize: '0.72rem',
                          fontWeight: 700,
                          textTransform: 'uppercase',
                          color: tier === 'strong' ? 'var(--status-pass-text)' : tier === 'moderate' ? 'var(--status-review-text)' : 'var(--text-muted)',
                        }}
                      >
                        {tier === 'weak' ? 'Contextual Match' : `${tier} Match`}
                      </span>
                    </div>

                    <span style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                      Match Strength: {simPercent}%
                    </span>
                  </div>

                  <p style={{ fontSize: '0.85rem', color: 'var(--text-primary)', lineHeight: 1.45, fontStyle: 'italic', marginBottom: '8px' }}>
                    "{item.text}"
                  </p>

                  <button
                    type="button"
                    onClick={() => toggleChunk(item.chunk_id || idx)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                      background: 'none',
                      border: 'none',
                      cursor: 'pointer',
                      fontSize: '0.75rem',
                      fontWeight: 600,
                      color: 'var(--accent-primary)',
                      padding: '2px 0',
                    }}
                  >
                    <span>Details & Metadata</span>
                    {isExpanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                  </button>

                  {isExpanded && (
                    <div
                      style={{
                        marginTop: '10px',
                        padding: '10px',
                        backgroundColor: 'var(--bg-surface)',
                        borderRadius: 'var(--radius-sm)',
                        fontSize: '0.78rem',
                        fontFamily: 'var(--font-mono)',
                        border: '1px solid var(--border-subtle)',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '4px',
                      }}
                    >
                      <div><strong>Chunk ID:</strong> {item.chunk_id}</div>
                      <div><strong>Distance:</strong> {Number(item.distance || 0).toFixed(4)}</div>
                      <div><strong>Similarity:</strong> {Number(item.similarity_score || 0).toFixed(4)}</div>
                      {item.metadata?.question && <div><strong>Indexed Question:</strong> {item.metadata.question}</div>}
                      {item.metadata?.best_answer && <div><strong>Verified Answer:</strong> {item.metadata.best_answer}</div>}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* Additional Retrieved Matches (Excluded Candidates) */}
        {additional_matches.length > 0 && (
          <div className="additional-matches-section">
            <button
              type="button"
              className="additional-matches-toggle"
              onClick={() => setShowAdditionalMatches(!showAdditionalMatches)}
            >
              <Layers size={14} />
              <span>
                {showAdditionalMatches ? 'Hide' : 'Show'} Additional Retrieved Matches ({additional_matches.length} excluded candidates)
              </span>
              {showAdditionalMatches ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            </button>

            {showAdditionalMatches && (
              <div style={{ marginTop: '10px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                  These candidate passages were retrieved during initial vector expansion (top-10 pool) but excluded because they scored below the direct evidence threshold or lacked essential inquiry topics.
                </p>
                {additional_matches.map((item, idx) => (
                  <div
                    key={item.chunk_id || idx}
                    style={{
                      padding: '10px 12px',
                      backgroundColor: 'var(--bg-surface-subtle)',
                      borderRadius: 'var(--radius-sm)',
                      border: '1px solid var(--border-subtle)',
                      fontSize: '0.8rem',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                      <span style={{ fontWeight: 600, color: 'var(--text-secondary)' }}>
                        Candidate #{idx + 1} — {item.dataset_name || 'Knowledge Base'}
                      </span>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        Similarity: {Math.round((item.similarity_score || 0) * 100)}% (Dist: {Number(item.distance || 0).toFixed(4)})
                      </span>
                    </div>
                    <p style={{ color: 'var(--text-secondary)', fontStyle: 'italic' }}>"{item.text}"</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Expandable Technical Details Section */}
      <div className="tech-details-container">
        <button
          type="button"
          className="tech-details-toggle"
          onClick={() => setShowTechDetails(!showTechDetails)}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Cpu size={16} style={{ color: 'var(--accent-primary)' }} />
            <span>Technical Verification Details & RAG Telemetry</span>
          </div>
          {showTechDetails ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>

        {showTechDetails && (
          <div className="tech-details-content">
            <div className="tech-metric-card">
              <div className="tech-metric-label">Embedding Model</div>
              <div className="tech-metric-val">all-MiniLM-L6-v2</div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                384-dimensional dense semantic vectors
              </div>
            </div>

            <div className="tech-metric-card">
              <div className="tech-metric-label">Vector Store</div>
              <div className="tech-metric-val">ChromaDB</div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                Cosine space: dist = 1 - cos(θ)
              </div>
            </div>

            <div className="tech-metric-card">
              <div className="tech-metric-label">Top Similarity / Distance</div>
              <div className="tech-metric-val">
                {Number(top_similarity).toFixed(4)} / {retrieved_evidence[0]?.distance != null ? Number(retrieved_evidence[0].distance).toFixed(4) : 'N/A'}
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                Normalized confidence score
              </div>
            </div>

            <div className="tech-metric-card">
              <div className="tech-metric-label">Relevance Thresholds</div>
              <div className="tech-metric-val">0.50 min / 0.65 strong</div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                Strict topic entity verification applied
              </div>
            </div>

            <div className="tech-metric-card">
              <div className="tech-metric-label">Candidate Pool Filter</div>
              <div className="tech-metric-val">
                {totalCandidates} queried → {retrieved_evidence.length} used
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                {additional_matches.length} candidates excluded
              </div>
            </div>

            <div className="tech-metric-card">
              <div className="tech-metric-label">Overall Score Formula</div>
              <div className="tech-metric-val" style={{ fontSize: '0.78rem' }}>
                (Acc × 0.40 + Rel × 0.30 + Hal × 0.30) × 100
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                Transparent linear multi-agent weighting
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
