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
  Check,
  AlertCircle,
  Award,
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
          relevance, claim-level hallucination detection, and completeness.
        </p>
      </div>
    );
  }

  const {
    question,
    ai_response,
    overall_score = 0,
    verdict = 'NEEDS IMPROVEMENT',
    verdict_reasoning = '',
    relevance = {},
    accuracy = {},
    hallucination = {},
    completeness = {},
    verdict_details = {},
    retrieved_evidence = [],
    additional_matches = [],
    candidate_count = 0,
    match_status = 'moderate',
    top_similarity = 0.0,
  } = evaluation;

  const totalCandidates = candidate_count || (retrieved_evidence.length + additional_matches.length);

  const normalizedVerdict = verdict === 'REVIEW' ? 'NEEDS IMPROVEMENT' : verdict;
  const verdictClass =
    normalizedVerdict === 'PASS'
      ? 'verdict-pass'
      : normalizedVerdict === 'FAIL'
      ? 'verdict-fail'
      : 'verdict-needs-improvement';

  const halRisk = hallucination.risk_level || 'LOW';
  const halStatus = hallucination.hallucination_status || 'NONE';
  const flaggedClaims = hallucination.flagged_claims || [];

  const compScore = completeness.score || 0;
  const compStatus = completeness.status || (compScore >= 4 ? 'COMPLETE' : compScore === 3 ? 'PARTIAL' : 'INCOMPLETE');
  const compAddressed = completeness.addressed_aspects || [];
  const compMissing = completeness.missing_aspects || [];

  // Weighted contributions from verdict_details or defaults
  const contributions = verdict_details.weighted_contributions || {
    accuracy: Math.round(((accuracy.score || 0) / 5) * 35),
    hallucination: halStatus === 'NONE' ? 30 : halStatus === 'PARTIAL' ? 15 : 0,
    relevance: Math.round(((relevance.score || 0) / 5) * 20),
    completeness: Math.round((compScore / 5) * 15),
  };

  const majorStrengths = verdict_details.major_strengths || [];
  const majorIssues = verdict_details.major_issues || [];
  const consolidatedReasoning =
    verdict_details.consolidated_reasoning || verdict_reasoning || 'Evaluated across four verification dimensions.';

  const isCriticalOverride =
    Boolean(
      evaluation.critical_override_applied ||
      verdict_details.critical_override_applied ||
      evaluation.overall?.critical_override_applied
    );

  const criticalOverrideReason =
    evaluation.critical_override_reason ||
    verdict_details.critical_override_reason ||
    evaluation.overall?.critical_override_reason ||
    'Severe factual contradiction or safety failure triggered an automatic FAIL override.';

  const halSafetyScore =
    hallucination.safety_score != null
      ? hallucination.safety_score
      : halRisk === 'LOW' || halStatus === 'NONE'
      ? 5.0
      : halRisk === 'MEDIUM' || halStatus === 'PARTIAL'
      ? 2.5
      : 0.0;

  const toggleChunk = (id) => {
    setExpandedChunkId(expandedChunkId === id ? null : id);
  };

  return (
    <div className="result-view-container">
      {/* Critical Override Alert Banner if triggered */}
      {isCriticalOverride && (
        <div
          className="critical-override-banner"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            backgroundColor: 'var(--status-fail-bg)',
            border: '1.5px solid var(--status-fail-border)',
            borderRadius: 'var(--radius-md)',
            padding: '14px 18px',
            marginBottom: '16px',
            boxShadow: '0 2px 8px rgba(239, 68, 68, 0.12)',
          }}
        >
          <AlertTriangle size={22} style={{ color: 'var(--status-fail-text)', flexShrink: 0 }} />
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <strong
                style={{
                  fontSize: '0.88rem',
                  color: 'var(--status-fail-text)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.04em',
                }}
              >
                Critical Override: TRIGGERED
              </strong>
              <span className="verdict-badge verdict-fail" style={{ fontSize: '0.68rem', padding: '2px 6px' }}>
                FAIL ENFORCED
              </span>
            </div>
            <p style={{ fontSize: '0.84rem', color: 'var(--status-fail-text)', margin: '4px 0 0 0', lineHeight: 1.4 }}>
              {criticalOverrideReason}
            </p>
          </div>
        </div>
      )}

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
              4-Dimension Weighted Verification Index
            </span>
          </div>
        </div>

        <div className="result-verdict-group">
          <div className="verdict-item-box">
            <span className="score-title-text">Final Verdict</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span className={`verdict-badge ${verdictClass}`}>
                {normalizedVerdict}
              </span>
              {isCriticalOverride && (
                <span
                  className="verdict-badge verdict-fail"
                  style={{ fontSize: '0.65rem', padding: '2px 6px' }}
                  title="Override applied: contradiction or high risk forces FAIL"
                >
                  OVERRIDE
                </span>
              )}
            </div>
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
              {halRisk} RISK
            </span>
          </div>
        </div>
      </div>

      {/* Four Major Evaluation Cards: Accuracy, Relevance, Hallucination, Completeness */}
      <div className="four-judges-grid">
        {/* Accuracy Card */}
        <div className="judge-card">
          <div className="judge-card-header">
            <span className="judge-card-title">Accuracy (35%)</span>
            <span className="judge-card-score">{accuracy.score || 0} / 5</span>
          </div>
          <span className="judge-card-label">{accuracy.label || 'Evaluated'}</span>
          <p className="judge-card-reasoning">
            {accuracy.reasoning || 'Factual consistency verified against reference knowledge.'}
          </p>
          {accuracy.supporting_evidence && accuracy.supporting_evidence.length > 0 && (
            <div className="judge-card-evidence-snippet">
              <strong>Key Reference: </strong>
              <span>"{accuracy.supporting_evidence[0].slice(0, 140)}..."</span>
            </div>
          )}
        </div>

        {/* Hallucination Safety Card */}
        <div className="judge-card">
          <div className="judge-card-header">
            <span className="judge-card-title">Hallucination Safety (30%)</span>
            <span
              className="judge-card-score"
              style={{
                fontSize: '1.0rem',
                color:
                  halRisk === 'HIGH'
                    ? 'var(--status-fail-text)'
                    : halRisk === 'MEDIUM'
                    ? 'var(--status-review-text)'
                    : 'var(--status-pass-text)',
              }}
            >
              {halSafetyScore} / 5
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
            <span
              style={{
                fontSize: '0.74rem',
                fontWeight: 700,
                padding: '2px 8px',
                borderRadius: 'var(--radius-sm)',
                backgroundColor:
                  halRisk === 'HIGH'
                    ? 'var(--status-fail-bg)'
                    : halRisk === 'MEDIUM'
                    ? 'var(--status-review-bg)'
                    : 'var(--status-pass-bg)',
                color:
                  halRisk === 'HIGH'
                    ? 'var(--status-fail-text)'
                    : halRisk === 'MEDIUM'
                    ? 'var(--status-review-text)'
                    : 'var(--status-pass-text)',
              }}
            >
              {halRisk} RISK • {halStatus}
            </span>
            <span style={{ fontSize: '0.74rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
              Weight: <strong>{contributions.hallucination ?? 0} / 30 pts</strong>
            </span>
          </div>
          <p className="judge-card-reasoning">
            {hallucination.summary || 'Assertion-level grounding check complete.'}
          </p>
          <div
            style={{
              marginTop: '8px',
              padding: '6px 8px',
              backgroundColor: 'var(--bg-surface)',
              borderRadius: 'var(--radius-sm)',
              fontSize: '0.7rem',
              color: 'var(--text-muted)',
              border: '1px solid var(--border-subtle)',
            }}
          >
            Safety Conversion: LOW = 5/5 (30 pts) • MEDIUM = 2.5/5 (15 pts) • HIGH = 0/5 (0 pts)
          </div>
        </div>

        {/* Relevance Card */}
        <div className="judge-card">
          <div className="judge-card-header">
            <span className="judge-card-title">Relevance (20%)</span>
            <span className="judge-card-score">{relevance.score || 0} / 5</span>
          </div>
          <span className="judge-card-label">{relevance.label || 'Evaluated'}</span>
          <p className="judge-card-reasoning">
            {relevance.reasoning || 'Topical alignment with the submitted question.'}
          </p>
        </div>

        {/* Completeness Card (Milestone 3) */}
        <div className="judge-card">
          <div className="judge-card-header">
            <span className="judge-card-title">Completeness (15%)</span>
            <span className="judge-card-score">{compScore} / 5</span>
          </div>
          <span
            className="judge-card-label"
            style={{
              color:
                compStatus === 'COMPLETE'
                  ? 'var(--status-pass-text)'
                  : compStatus === 'PARTIAL'
                  ? 'var(--status-review-text)'
                  : 'var(--status-fail-text)',
            }}
          >
            Status: {compStatus}
          </span>
          <p className="judge-card-reasoning">
            {completeness.reasoning || 'Coverage of identified question requirements and sub-questions.'}
          </p>

          {/* Addressed / Missing Aspects Pills */}
          <div className="aspects-summary-box">
            {compAddressed.length > 0 && (
              <div style={{ marginBottom: '6px' }}>
                <span className="aspect-heading-mini">Addressed ({compAddressed.length}):</span>
                <div className="aspect-tag-row">
                  {compAddressed.map((asp, i) => (
                    <span key={i} className="aspect-tag-addressed">
                      <Check size={11} />
                      <span>{asp}</span>
                    </span>
                  ))}
                </div>
              </div>
            )}

            {compMissing.length > 0 && (
              <div>
                <span className="aspect-heading-mini">Missing ({compMissing.length}):</span>
                <div className="aspect-tag-row">
                  {compMissing.map((asp, i) => (
                    <span key={i} className="aspect-tag-missing">
                      <AlertCircle size={11} />
                      <span>{asp}</span>
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Verdict Synthesis & Weighted Breakdown (Milestone 3) */}
      <div className="ink-card">
        <div className="ink-card-header">
          <div className="card-title-block">
            <div className="card-icon-wrap">
              <Sparkles size={16} />
            </div>
            <div>
              <h3 className="card-heading">Verdict Synthesis & Weighted Breakdown</h3>
              <p className="card-subtext">Multi-agent aggregation formula: 35% Acc + 30% Hal + 20% Rel + 15% Comp</p>
            </div>
          </div>
          <span className={`verdict-badge ${verdictClass}`}>{normalizedVerdict}</span>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Consolidated Reasoning Banner */}
          <div className="verdict-reasoning-banner">
            <strong style={{ fontSize: '0.86rem', color: 'var(--text-primary)', display: 'block', marginBottom: '6px' }}>
              Consolidated Verdict Justification:
            </strong>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5, margin: 0 }}>
              {consolidatedReasoning}
            </p>
          </div>

          {/* Weighted Contribution Progress Bars */}
          <div className="contributions-grid">
            <div className="contrib-item">
              <div className="contrib-header">
                <span>Accuracy (35% wt)</span>
                <strong>{contributions.accuracy ?? 0} pts</strong>
              </div>
              <div className="contrib-bar-track">
                <div
                  className="contrib-bar-fill"
                  style={{ width: `${Math.min(100, ((contributions.accuracy || 0) / 35) * 100)}%`, backgroundColor: 'var(--accent-primary)' }}
                />
              </div>
            </div>

            <div className="contrib-item">
              <div className="contrib-header">
                <span>Hallucination Safety (30% wt)</span>
                <strong>{contributions.hallucination ?? 0} pts</strong>
              </div>
              <div className="contrib-bar-track">
                <div
                  className="contrib-bar-fill"
                  style={{ width: `${Math.min(100, ((contributions.hallucination || 0) / 30) * 100)}%`, backgroundColor: '#10b981' }}
                />
              </div>
            </div>

            <div className="contrib-item">
              <div className="contrib-header">
                <span>Relevance (20% wt)</span>
                <strong>{contributions.relevance ?? 0} pts</strong>
              </div>
              <div className="contrib-bar-track">
                <div
                  className="contrib-bar-fill"
                  style={{ width: `${Math.min(100, ((contributions.relevance || 0) / 20) * 100)}%`, backgroundColor: '#6366f1' }}
                />
              </div>
            </div>

            <div className="contrib-item">
              <div className="contrib-header">
                <span>Completeness (15% wt)</span>
                <strong>{contributions.completeness ?? 0} pts</strong>
              </div>
              <div className="contrib-bar-track">
                <div
                  className="contrib-bar-fill"
                  style={{ width: `${Math.min(100, ((contributions.completeness || 0) / 15) * 100)}%`, backgroundColor: '#8b5cf6' }}
                />
              </div>
            </div>
          </div>

          {/* Major Strengths & Issues Two-Column Layout */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '12px' }}>
            {/* Major Strengths */}
            <div className="strengths-box">
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
                <CheckCircle2 size={15} style={{ color: 'var(--status-pass-text)' }} />
                <span style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                  Major Strengths
                </span>
              </div>
              {majorStrengths.length > 0 ? (
                <ul className="strength-list">
                  {majorStrengths.map((item, i) => (
                    <li key={i}>{item}</li>
                  ))}
                </ul>
              ) : (
                <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>No notable strengths recorded.</p>
              )}
            </div>

            {/* Major Issues */}
            <div className="issues-box">
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
                <AlertTriangle size={15} style={{ color: 'var(--status-fail-text)' }} />
                <span style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                  Major Issues & Critical Alerts
                </span>
              </div>
              {majorIssues.length > 0 ? (
                <ul className="issue-list">
                  {majorIssues.map((item, i) => (
                    <li key={i}>{item}</li>
                  ))}
                </ul>
              ) : (
                <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>No critical issues or contradictions detected.</p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Claim-Level Grounding Breakdown */}
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
            <span>Technical Verification Details & 4-Dimension Telemetry</span>
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
              <div className="tech-metric-label">Thresholds</div>
              <div className="tech-metric-val">Pass: 80 / Needs Imp: 60</div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                Configurable engineering thresholds
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
              <div className="tech-metric-label">Weighted Scoring Formula</div>
              <div className="tech-metric-val" style={{ fontSize: '0.76rem' }}>
                Acc (35%) + Hal (30%) + Rel (20%) + Comp (15%)
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                Normalized 4-dimension aggregation
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
