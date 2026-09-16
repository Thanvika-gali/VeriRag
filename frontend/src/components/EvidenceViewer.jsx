import React, { useState } from 'react';
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Database,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  FileSearch,
  Sparkles,
  Info,
  HelpCircle,
} from 'lucide-react';

export default function EvidenceViewer({ evaluation, loading, backendError }) {
  const [expandedChunkId, setExpandedChunkId] = useState(null);

  const toggleChunk = (id) => {
    setExpandedChunkId(expandedChunkId === id ? null : id);
  };

  // STATE 7: Backend unavailable
  if (backendError) {
    return (
      <div className="lab-card evidence-empty-card error-state">
        <div className="empty-icon-wrap error-icon">
          <XCircle size={36} />
        </div>
        <h3 className="empty-title">Unable to connect to PROOFRAG</h3>
        <p className="empty-desc">
          Please make sure the backend is running and try again.
        </p>
      </div>
    );
  }

  // STATE 2: Loading
  if (loading) {
    return (
      <div className="lab-card evidence-empty-card loading-state">
        <div className="radar-spinner" />
        <h3 className="empty-title">Searching for supporting evidence...</h3>
        <p className="empty-desc">
          Querying reference knowledge base and measuring match strength against benchmark data.
        </p>
      </div>
    );
  }

  // STATE 1: No submission
  if (!evaluation) {
    return (
      <div className="lab-card evidence-empty-card">
        <div className="empty-icon-wrap">
          <FileSearch size={36} />
        </div>
        <h3 className="empty-title">Ready to check an AI answer</h3>
        <p className="empty-desc">
          Enter a question and an AI-generated answer, or select one of the benchmark examples above to retrieve grounded reference evidence.
        </p>
      </div>
    );
  }

  const {
    question,
    ai_response,
    retrieved_evidence = [],
    match_status = 'moderate',
    match_label = 'Some supporting evidence found',
    match_message = '',
    top_similarity = 0.0,
  } = evaluation;

  // Determine top status banner configuration
  const getStatusConfig = () => {
    if (!retrieved_evidence || retrieved_evidence.length === 0) {
      return {
        badgeClass: 'status-none',
        title: 'No strong supporting evidence found',
        desc: 'No matching reference evidence was found in the reference knowledge base.',
        icon: <XCircle size={18} />,
        isWeak: true,
      };
    }

    if (match_status === 'strong' || top_similarity >= 0.70) {
      return {
        badgeClass: 'status-strong',
        title: 'Strong evidence found',
        desc: match_message || 'High-confidence supporting evidence was retrieved from reference knowledge.',
        icon: <CheckCircle2 size={18} />,
        isWeak: false,
      };
    }

    if (match_status === 'moderate' || top_similarity >= 0.50) {
      return {
        badgeClass: 'status-moderate',
        title: 'Some supporting evidence found',
        desc: match_message || 'Moderate supporting evidence was found matching the inquiry.',
        icon: <AlertTriangle size={18} />,
        isWeak: false,
      };
    }

    return {
      badgeClass: 'status-weak',
      title: 'Limited evidence found',
      desc: 'Current reference data does not contain strong supporting evidence for this question.',
      icon: <XCircle size={18} />,
      isWeak: true,
    };
  };

  const statusCfg = getStatusConfig();

  return (
    <div className="lab-card evidence-viewer-card">
      <div className="card-top-bar">
        <div className="card-title-group">
          <div className="title-icon-badge cyan">
            <Sparkles size={18} />
          </div>
          <div>
            <h2 className="card-main-title">Evidence Analysis</h2>
            <p className="card-subtitle">
              {retrieved_evidence.length} {retrieved_evidence.length === 1 ? 'source' : 'sources'} retrieved from reference knowledge
            </p>
          </div>
        </div>

        <div className={`evidence-status-pill ${statusCfg.badgeClass}`}>
          {statusCfg.icon}
          <span>{statusCfg.title}</span>
        </div>
      </div>

      {/* Honest Status Explanation Banner */}
      <div className={`status-explanation-banner ${statusCfg.badgeClass}`}>
        <div className="status-explanation-header">
          <strong>{statusCfg.title}</strong>
          {top_similarity > 0 && (
            <span className="status-top-sim">Peak Match: {Math.round(top_similarity * 100)}%</span>
          )}
        </div>
        <p className="status-explanation-body">{statusCfg.desc}</p>
        {statusCfg.isWeak && retrieved_evidence.length > 0 && (
          <div className="status-weak-warning">
            <Info size={14} />
            <span>
              The closest retrieved sources below have low similarity and may discuss unrelated topics rather than confirming or refuting the claim.
            </span>
          </div>
        )}
      </div>

      {/* Question & AI Answer Summary */}
      <div className="query-summary-box">
        <div className="query-summary-item">
          <span className="summary-label">Question:</span>
          <span className="summary-text">{question}</span>
        </div>
        <div className="query-summary-item">
          <span className="summary-label">AI Answer:</span>
          <span className="summary-text ai-answer">{ai_response}</span>
        </div>
      </div>

      {/* Section Header */}
      <div className="evidence-section-header">
        <span className="evidence-header-title">
          {statusCfg.isWeak ? 'Closest Retrieved Sources (Low Confidence)' : 'Evidence Found'}
        </span>
        <span className="evidence-count-tag">
          {retrieved_evidence.length} Available
        </span>
      </div>

      {/* Evidence Cards */}
      {retrieved_evidence.length === 0 ? (
        <div className="no-evidence-box">
          <XCircle size={22} className="no-evidence-icon" />
          <p>No reference evidence could be retrieved for this query.</p>
        </div>
      ) : (
        <div className="evidence-cards-stack">
          {retrieved_evidence.map((item, idx) => {
            const sim = typeof item.similarity === 'number' ? item.similarity : (item.similarity_score || 0.0);
            const simPercent = Math.min(100, Math.max(0, Math.round(sim * 100)));
            const isExpanded = expandedChunkId === item.chunk_id;
            const tier = item.match_tier || (sim >= 0.70 ? 'strong' : sim >= 0.50 ? 'moderate' : 'weak');

            const tierBadge =
              tier === 'strong' ? { label: 'Strong Match', css: 'tier-strong' } :
              tier === 'moderate' ? { label: 'Moderate Match', css: 'tier-moderate' } :
              { label: 'Weak Match', css: 'tier-weak' };

            return (
              <div key={item.chunk_id || idx} className={`evidence-card ${tierBadge.css}`}>
                <div className="evidence-card-header">
                  <div className="evidence-card-meta">
                    <span className="evidence-rank-num">#{idx + 1}</span>
                    <span className="evidence-source-pill">
                      <Database size={12} />
                      <span>{item.dataset_name || item.source || 'Reference Data'}</span>
                    </span>
                    <span className={`evidence-tier-pill ${tierBadge.css}`}>
                      {tierBadge.label}
                    </span>
                  </div>

                  <div className="evidence-score-badge">
                    <span className="score-label">MATCH STRENGTH</span>
                    <span className="score-val">{simPercent}%</span>
                  </div>
                </div>

                {/* Visual Match Strength Bar */}
                <div className="similarity-meter-track">
                  <div
                    className={`similarity-meter-fill ${tier}`}
                    style={{ width: `${Math.max(6, simPercent)}%` }}
                  />
                </div>

                {/* Evidence Text Snippet */}
                <div className="evidence-text-content">
                  <p className="evidence-text-quote">
                    "{item.text}"
                  </p>
                </div>

                {/* Source details if present */}
                {item.metadata?.source && (
                  <div className="evidence-source-link-row">
                    <span className="source-link-label">Source reference:</span>
                    <span className="source-link-val">{item.metadata.source}</span>
                  </div>
                )}

                {/* Expandable Technical Details */}
                <button
                  type="button"
                  className="evidence-expand-btn"
                  onClick={() => toggleChunk(item.chunk_id)}
                >
                  <span>Technical Vector Details</span>
                  {isExpanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
                </button>

                {isExpanded && (
                  <div className="evidence-tech-drawer">
                    <div className="tech-prop-row">
                      <span className="prop-name">Chunk ID:</span>
                      <span className="prop-val mono">{item.chunk_id}</span>
                    </div>
                    <div className="tech-prop-row">
                      <span className="prop-name">Cosine Distance:</span>
                      <span className="prop-val mono">{(item.distance || 0).toFixed(4)}</span>
                    </div>
                    {item.metadata?.question && (
                      <div className="tech-prop-row">
                        <span className="prop-name">Indexed Question:</span>
                        <span className="prop-val">{item.metadata.question}</span>
                      </div>
                    )}
                    {item.metadata?.best_answer && (
                      <div className="tech-prop-row">
                        <span className="prop-name">Ground Truth Answer:</span>
                        <span className="prop-val">{item.metadata.best_answer}</span>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
