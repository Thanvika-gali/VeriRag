import React, { useState, useEffect } from 'react';
import {
  Database,
  Search,
  Layers,
  ChevronDown,
  ChevronUp,
  AlertCircle,
  RefreshCw,
  SlidersHorizontal,
  ExternalLink,
  CheckCircle2,
  FileText,
  HelpCircle,
  Sparkles,
} from 'lucide-react';

const SUGGESTED_QUERIES = [
  'watermelon seeds swallowed',
  'what happens if you eat watermelon seeds',
  'photosynthesis carbon dioxide water',
  'Great Wall of China moon',
  'Which NFL team represented the AFC at Super Bowl 50?',
  'completely unrelated xyz query 12345',
];

export default function EvidenceLibraryView({ systemHealth }) {
  const [searchQuery, setSearchQuery] = useState('watermelon seeds swallowed');
  const [datasetFilter, setDatasetFilter] = useState('All');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchError, setSearchError] = useState(null);
  const [hasSearched, setHasSearched] = useState(false);
  const [expandedId, setExpandedId] = useState(null);
  const [metaStats, setMetaStats] = useState({
    totalChunks: systemHealth?.total_indexed_chunks || 543,
    embeddingModel: systemHealth?.embedding_model || 'all-MiniLM-L6-v2',
    embeddingDimension: 384,
  });

  // Fetch live stats and trigger initial search
  useEffect(() => {
    fetchStats();
    handleSearch('watermelon seeds swallowed', datasetFilter);
  }, []);

  const fetchStats = async () => {
    try {
      const res = await fetch('/api/knowledge-base/stats');
      if (res.ok) {
        const data = await res.json();
        setMetaStats({
          totalChunks: data.total_indexed_chunks ?? 543,
          embeddingModel: data.embedding_model || 'all-MiniLM-L6-v2',
          embeddingDimension: 384,
        });
      }
    } catch (err) {
      console.warn('[EvidenceLibrary] Stats load warning:', err);
    }
  };

  const handleSearch = async (queryText = searchQuery, filterOverride = datasetFilter) => {
    const q = (queryText !== undefined ? queryText : searchQuery).trim();
    if (!q) return;

    setLoading(true);
    setSearchError(null);
    setHasSearched(true);

    try {
      const params = new URLSearchParams({
        q,
        limit: '10',
      });
      if (filterOverride && filterOverride !== 'All') {
        params.append('dataset', filterOverride);
      }

      const res = await fetch(`/api/evidence/search?${params.toString()}`);
      if (!res.ok) {
        throw new Error(`Server returned HTTP ${res.status}`);
      }

      const data = await res.json();
      setResults(data.results || []);
      if (data.embedding_dimension || data.total_indexed_chunks) {
        setMetaStats((prev) => ({
          ...prev,
          embeddingDimension: data.embedding_dimension || prev.embeddingDimension,
          embeddingModel: data.embedding_model || prev.embeddingModel,
          totalChunks: data.total_indexed_chunks !== undefined ? data.total_indexed_chunks : prev.totalChunks,
        }));
      }
    } catch (err) {
      console.error('[EvidenceLibrary] Search error:', err);
      setSearchError('Unable to search the evidence library. Please try again.');
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const onChipClick = (term) => {
    setSearchQuery(term);
    handleSearch(term, datasetFilter);
  };

  const handleFilterChange = (newFilter) => {
    setDatasetFilter(newFilter);
    handleSearch(searchQuery, newFilter);
  };

  return (
    <div className="evidence-library-container">
      {/* Header & Search Bar Card */}
      <div className="ink-card">
        <div className="ink-card-header">
          <div className="card-title-block">
            <div className="card-icon-wrap">
              <Database size={18} />
            </div>
            <div>
              <h2 className="card-heading">Evidence Library</h2>
              <p className="card-subtext">
                Query and inspect {metaStats.embeddingDimension}-dimensional vector embeddings and reference chunks indexed in ChromaDB
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div className="telemetry-chip">
              <Database size={12} style={{ color: 'var(--accent-primary)' }} />
              <span>Indexed:</span>
              <strong style={{ color: 'var(--text-primary)' }}>
                {metaStats.totalChunks} chunks
              </strong>
            </div>
            <div className="telemetry-chip">
              <span>Model:</span>
              <strong style={{ color: 'var(--text-primary)' }}>
                {metaStats.embeddingModel} ({metaStats.embeddingDimension}d)
              </strong>
            </div>
          </div>
        </div>

        {/* Search Input Controls */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSearch();
          }}
          style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', marginBottom: '16px' }}
        >
          <div style={{ position: 'relative', flex: 1, minWidth: '280px' }}>
            <Search
              size={16}
              style={{
                position: 'absolute',
                left: '14px',
                top: '50%',
                transform: 'translateY(-50%)',
                color: 'var(--text-muted)',
                pointerEvents: 'none',
              }}
            />
            <input
              type="text"
              id="evidence-search-input"
              className="ink-input"
              style={{ paddingLeft: '38px' }}
              placeholder="Search reference chunks (e.g. watermelon seeds, photosynthesis)..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          <div style={{ display: 'flex', gap: '8px' }}>
            <select
              id="evidence-filter-select"
              className="ink-select"
              style={{ width: 'auto', minWidth: '170px' }}
              value={datasetFilter}
              onChange={(e) => handleFilterChange(e.target.value)}
            >
              <option value="All">All Datasets</option>
              <option value="TruthfulQA">TruthfulQA</option>
              <option value="SQuAD">SQuAD</option>
              <option value="Custom">Custom Documents</option>
            </select>

            <button
              type="submit"
              id="evidence-search-btn"
              className="btn-primary"
              disabled={loading}
              style={{ minWidth: '130px' }}
            >
              {loading ? (
                <>
                  <RefreshCw size={15} className="spin" />
                  <span>Searching...</span>
                </>
              ) : (
                <>
                  <Search size={15} />
                  <span>Search Index</span>
                </>
              )}
            </button>
          </div>
        </form>

        {/* Suggested Queries */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
            Suggested Queries:
          </span>
          {SUGGESTED_QUERIES.map((sq, idx) => (
            <button
              key={idx}
              type="button"
              className={`preset-chip ${searchQuery === sq ? 'active' : ''}`}
              style={{ fontSize: '0.75rem', padding: '4px 10px' }}
              onClick={() => onChipClick(sq)}
            >
              {sq}
            </button>
          ))}
        </div>
      </div>

      {/* Results Section */}
      <div className="ink-card">
        <div className="ink-card-header">
          <div className="card-title-block">
            <Layers size={17} style={{ color: 'var(--accent-primary)' }} />
            <h3 className="card-heading">
              Retrieved Reference Chunks ({results.length})
            </h3>
          </div>

          {results.length > 0 && (
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Filtered by: <strong>{datasetFilter === 'All' ? 'All Datasets' : datasetFilter}</strong>
            </div>
          )}
        </div>

        {/* 1. Loading State */}
        {loading ? (
          <div className="empty-state-box" style={{ padding: '40px 20px' }}>
            <div className="loading-spinner" />
            <h4 style={{ fontSize: '1.05rem', fontWeight: 600, marginTop: '16px', color: 'var(--text-primary)' }}>
              Searching reference knowledge...
            </h4>
            <p className="empty-sub" style={{ marginTop: '6px' }}>
              Generating 384-dimensional query embedding and querying ChromaDB index...
            </p>
          </div>
        ) : searchError ? (
          /* 2. Error State */
          <div
            className="empty-state-box"
            style={{
              padding: '36px 20px',
              backgroundColor: 'var(--status-fail-bg)',
              border: '1px solid var(--status-fail-border)',
              borderRadius: 'var(--radius-md)',
            }}
          >
            <AlertCircle size={36} style={{ color: 'var(--status-fail-text)', marginBottom: '12px' }} />
            <h4 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--status-fail-text)' }}>
              Search Error
            </h4>
            <p style={{ fontSize: '0.88rem', color: 'var(--status-fail-text)', marginTop: '4px', maxWidth: '460px' }}>
              {searchError}
            </p>
            <button
              type="button"
              className="btn-secondary"
              style={{ marginTop: '16px' }}
              onClick={() => handleSearch()}
            >
              <RefreshCw size={13} />
              <span>Retry Search</span>
            </button>
          </div>
        ) : results.length === 0 && hasSearched ? (
          /* 3. Empty Results State */
          <div className="empty-state-box" style={{ padding: '40px 20px' }}>
            <Database size={36} className="empty-icon" style={{ opacity: 0.5 }} />
            <h4 className="empty-heading">No relevant reference chunks found.</h4>
            <p className="empty-sub">
              Try a broader query or select All Datasets.
            </p>
            {datasetFilter !== 'All' && (
              <button
                type="button"
                className="btn-secondary"
                style={{ marginTop: '14px' }}
                onClick={() => handleFilterChange('All')}
              >
                <span>Switch to All Datasets</span>
              </button>
            )}
          </div>
        ) : (
          /* 4. Results List */
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {results.map((item, idx) => {
              const simPercent = Math.round((item.similarity_score || 0) * 1000) / 10;
              const isExpanded = expandedId === (item.chunk_id || idx);
              const tier = item.match_tier || (item.similarity_score >= 0.65 ? 'Strong' : item.similarity_score >= 0.50 ? 'Moderate' : 'Weak');
              const relevanceClass = item.relevance_classification || (tier === 'Strong' ? 'DIRECTLY RELEVANT' : tier === 'Moderate' ? 'RELATED BUT NOT SUFFICIENT' : 'WEAK');

              // Color determination for relevance classification
              let relStyle = {
                bg: 'var(--status-neutral-bg)',
                text: 'var(--status-neutral-text)',
                border: 'var(--status-neutral-border)',
              };
              if (relevanceClass === 'DIRECTLY RELEVANT') {
                relStyle = {
                  bg: 'var(--status-pass-bg)',
                  text: 'var(--status-pass-text)',
                  border: 'var(--status-pass-border)',
                };
              } else if (relevanceClass === 'RELATED BUT NOT SUFFICIENT') {
                relStyle = {
                  bg: 'var(--status-review-bg)',
                  text: 'var(--status-review-text)',
                  border: 'var(--status-review-border)',
                };
              } else if (relevanceClass === 'IRRELEVANT') {
                relStyle = {
                  bg: 'var(--status-fail-bg)',
                  text: 'var(--status-fail-text)',
                  border: 'var(--status-fail-border)',
                };
              }

              return (
                <div
                  key={item.chunk_id || idx}
                  className="evidence-chunk-card"
                  style={{
                    padding: '20px',
                    backgroundColor: 'var(--bg-surface-subtle)',
                    borderRadius: 'var(--radius-md)',
                    border: '1.5px solid var(--border-color)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '12px',
                    transition: 'border-color 0.15s ease',
                  }}
                >
                  {/* Top Metadata Row */}
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      flexWrap: 'wrap',
                      gap: '8px',
                      paddingBottom: '10px',
                      borderBottom: '1px solid var(--border-subtle)',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                      <span
                        style={{
                          fontSize: '0.78rem',
                          fontWeight: 800,
                          color: 'var(--text-primary)',
                          backgroundColor: 'var(--border-subtle)',
                          padding: '3px 8px',
                          borderRadius: 'var(--radius-sm)',
                        }}
                      >
                        #{idx + 1}
                      </span>

                      <span
                        style={{
                          fontSize: '0.8rem',
                          fontWeight: 700,
                          color: 'var(--accent-primary)',
                          backgroundColor: 'var(--accent-light)',
                          padding: '3px 10px',
                          borderRadius: 'var(--radius-sm)',
                          border: '1px solid var(--border-subtle)',
                        }}
                      >
                        {item.dataset_name || 'Knowledge Base'}
                      </span>

                      <span
                        style={{
                          fontSize: '0.74rem',
                          fontWeight: 700,
                          textTransform: 'uppercase',
                          letterSpacing: '0.03em',
                          padding: '3px 8px',
                          borderRadius: 'var(--radius-sm)',
                          backgroundColor: tier === 'Strong' ? 'var(--status-pass-bg)' : tier === 'Moderate' ? 'var(--status-review-bg)' : 'var(--bg-surface-muted)',
                          color: tier === 'Strong' ? 'var(--status-pass-text)' : tier === 'Moderate' ? 'var(--status-review-text)' : 'var(--text-muted)',
                          border: `1px solid ${tier === 'Strong' ? 'var(--status-pass-border)' : tier === 'Moderate' ? 'var(--status-review-border)' : 'var(--border-subtle)'}`,
                        }}
                      >
                        {tier} Match
                      </span>

                      <span
                        style={{
                          fontSize: '0.72rem',
                          fontWeight: 700,
                          letterSpacing: '0.04em',
                          padding: '3px 8px',
                          borderRadius: 'var(--radius-sm)',
                          backgroundColor: relStyle.bg,
                          color: relStyle.text,
                          border: `1px solid ${relStyle.border}`,
                        }}
                      >
                        {relevanceClass}
                      </span>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                      <span
                        style={{
                          fontFamily: 'var(--font-mono)',
                          fontSize: '0.78rem',
                          color: 'var(--text-secondary)',
                        }}
                        title="HNSW Cosine Distance"
                      >
                        Dist: {Number(item.distance || 0).toFixed(4)}
                      </span>
                      <span
                        style={{
                          fontSize: '0.86rem',
                          fontWeight: 700,
                          color: 'var(--text-primary)',
                        }}
                      >
                        Match Strength: <strong>{simPercent}%</strong>
                      </span>
                    </div>
                  </div>

                  {/* Question (if present) */}
                  {item.question && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                      <span style={{ fontSize: '0.72rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text-muted)' }}>
                        Question:
                      </span>
                      <p style={{ fontSize: '0.94rem', fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>
                        {item.question}
                      </p>
                    </div>
                  )}

                  {/* Reference Answer (if present) */}
                  {item.answer && (
                    <div
                      style={{
                        padding: '10px 14px',
                        backgroundColor: 'var(--bg-surface)',
                        borderRadius: 'var(--radius-sm)',
                        border: '1px solid var(--border-subtle)',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '4px',
                      }}
                    >
                      <span style={{ fontSize: '0.72rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--accent-primary)' }}>
                        Reference Answer:
                      </span>
                      <p style={{ fontSize: '0.88rem', color: 'var(--text-primary)', margin: 0, lineHeight: 1.5 }}>
                        {item.answer}
                      </p>
                    </div>
                  )}

                  {/* Passage / Raw Text Content */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <span style={{ fontSize: '0.72rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text-muted)' }}>
                      Indexed Context / Passage:
                    </span>
                    <p
                      style={{
                        fontSize: '0.86rem',
                        color: 'var(--text-secondary)',
                        lineHeight: 1.55,
                        margin: 0,
                        backgroundColor: 'var(--bg-surface)',
                        padding: '12px',
                        borderRadius: 'var(--radius-sm)',
                        border: '1px solid var(--border-subtle)',
                        whiteSpace: 'pre-wrap',
                      }}
                    >
                      {item.text}
                    </p>
                  </div>

                  {/* Expandable Details Button */}
                  <div>
                    <button
                      type="button"
                      id={`details-toggle-${idx}`}
                      onClick={() => setExpandedId(isExpanded ? null : (item.chunk_id || idx))}
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '6px',
                        background: 'none',
                        border: 'none',
                        cursor: 'pointer',
                        fontSize: '0.78rem',
                        fontWeight: 600,
                        color: 'var(--accent-primary)',
                        padding: '4px 0',
                      }}
                    >
                      <span>{isExpanded ? 'Hide Details' : 'Details'}</span>
                      {isExpanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
                    </button>
                  </div>

                  {/* Expanded Metadata Details Panel */}
                  {isExpanded && (
                    <div
                      style={{
                        padding: '16px',
                        backgroundColor: 'var(--bg-surface)',
                        borderRadius: 'var(--radius-sm)',
                        fontSize: '0.8rem',
                        border: '1px solid var(--border-color)',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '8px',
                      }}
                    >
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '8px' }}>
                        <div>
                          <strong style={{ color: 'var(--text-muted)', fontSize: '0.72rem', textTransform: 'uppercase' }}>Dataset:</strong>
                          <div style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{item.dataset_name}</div>
                        </div>
                        <div>
                          <strong style={{ color: 'var(--text-muted)', fontSize: '0.72rem', textTransform: 'uppercase' }}>Chunk ID:</strong>
                          <div style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>{item.chunk_id}</div>
                        </div>
                        <div>
                          <strong style={{ color: 'var(--text-muted)', fontSize: '0.72rem', textTransform: 'uppercase' }}>Match Strength:</strong>
                          <div style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{item.similarity_score} ({simPercent}%)</div>
                        </div>
                        <div>
                          <strong style={{ color: 'var(--text-muted)', fontSize: '0.72rem', textTransform: 'uppercase' }}>Distance:</strong>
                          <div style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>{item.distance}</div>
                        </div>
                      </div>

                      {item.question && (
                        <div>
                          <strong style={{ color: 'var(--text-muted)', fontSize: '0.72rem', textTransform: 'uppercase' }}>Question:</strong>
                          <div style={{ color: 'var(--text-primary)' }}>{item.question}</div>
                        </div>
                      )}

                      {item.answer && (
                        <div>
                          <strong style={{ color: 'var(--text-muted)', fontSize: '0.72rem', textTransform: 'uppercase' }}>Answer:</strong>
                          <div style={{ color: 'var(--text-primary)' }}>{item.answer}</div>
                        </div>
                      )}

                      {item.metadata && Object.keys(item.metadata).length > 0 && (
                        <div style={{ marginTop: '6px' }}>
                          <strong style={{ color: 'var(--text-muted)', fontSize: '0.72rem', textTransform: 'uppercase' }}>Metadata:</strong>
                          <pre
                            style={{
                              margin: '6px 0 0',
                              padding: '10px',
                              backgroundColor: 'var(--bg-surface-subtle)',
                              borderRadius: 'var(--radius-sm)',
                              fontFamily: 'var(--font-mono)',
                              fontSize: '0.74rem',
                              whiteSpace: 'pre-wrap',
                              color: 'var(--text-secondary)',
                              border: '1px solid var(--border-subtle)',
                              maxHeight: '220px',
                              overflowY: 'auto',
                            }}
                          >
                            {JSON.stringify(item.metadata, null, 2)}
                          </pre>
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
    </div>
  );
}
