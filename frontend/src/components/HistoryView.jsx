import React, { useState } from 'react';
import { History, Search, ArrowRight, Layers, Calendar, RefreshCw } from 'lucide-react';

export default function HistoryView({
  historyList = [],
  loading = false,
  onSelectSubmission,
  onRefresh,
}) {
  const [searchQuery, setSearchQuery] = useState('');

  const filtered = historyList.filter((item) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      (item.question && item.question.toLowerCase().includes(q)) ||
      (item.ai_response_snippet && item.ai_response_snippet.toLowerCase().includes(q))
    );
  });

  return (
    <div className="ink-card">
      <div className="ink-card-header">
        <div className="card-title-block">
          <div className="card-icon-wrap">
            <History size={18} />
          </div>
          <div>
            <h2 className="card-heading">Evaluation History</h2>
            <p className="card-subtext">Past AI response validations stored in SQLite database</p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ position: 'relative', width: '220px' }}>
            <Search size={14} style={{ position: 'absolute', left: 10, top: 12, color: 'var(--text-muted)' }} />
            <input
              type="text"
              className="ink-input"
              style={{ paddingLeft: '32px', fontSize: '0.82rem', padding: '8px 10px 8px 30px' }}
              placeholder="Search evaluations..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          <button
            type="button"
            className="btn-secondary"
            onClick={onRefresh}
            title="Refresh History"
          >
            <RefreshCw size={13} className={loading ? 'spin' : ''} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {loading ? (
        <div className="empty-state-box">
          <div className="loading-spinner" style={{ width: 32, height: 32 }} />
          <p className="empty-sub">Loading evaluation records...</p>
        </div>
      ) : filtered.length === 0 ? (
        <div className="empty-state-box">
          <History size={40} className="empty-icon" />
          <h3 className="empty-heading">No evaluations yet</h3>
          <p className="empty-sub">
            {searchQuery
              ? 'No evaluations matched your search criteria.'
              : 'Previous evaluations processed by PROOFRAG will appear here.'}
          </p>
        </div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table className="ink-table">
            <thead>
              <tr>
                <th>Question</th>
                <th>Overall</th>
                <th>Accuracy</th>
                <th>Relevance</th>
                <th>Hallucination</th>
                <th>Completeness</th>
                <th>Verdict</th>
                <th>Date</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((item) => {
                const verdictClass =
                  item.verdict === 'PASS'
                    ? 'verdict-pass'
                    : item.verdict === 'FAIL'
                    ? 'verdict-fail'
                    : 'verdict-review';

                return (
                  <tr
                    key={item.submission_id}
                    onClick={() => onSelectSubmission(item.submission_id)}
                  >
                    <td style={{ maxWidth: '260px' }}>
                      <div style={{ fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {item.question}
                      </div>
                      <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {item.ai_response_snippet}
                      </div>
                    </td>
                    <td>
                      <span style={{ fontWeight: 700, fontSize: '0.95rem' }}>
                        {item.overall_score !== null && item.overall_score !== undefined
                          ? `${item.overall_score}/100`
                          : '—'}
                      </span>
                    </td>
                    <td>{item.accuracy_score ? `${item.accuracy_score}/5` : '—'}</td>
                    <td>{item.relevance_score ? `${item.relevance_score}/5` : '—'}</td>
                    <td>
                      <span style={{ fontSize: '0.8rem', fontWeight: 600 }}>
                        {item.hallucination_risk || 'LOW'}
                      </span>
                    </td>
                    <td>{item.completeness_score ? `${item.completeness_score}/5` : '—'}</td>
                    <td>
                      <span className={`verdict-badge ${verdictClass}`}>
                        {item.verdict || 'REVIEW'}
                      </span>
                    </td>
                    <td style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                      {item.created_at ? item.created_at.slice(0, 16).replace('T', ' ') : 'Recent'}
                    </td>
                    <td>
                      <button
                        type="button"
                        className="btn-secondary"
                        style={{ padding: '4px 10px', fontSize: '0.78rem' }}
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectSubmission(item.submission_id);
                        }}
                      >
                        <span>Inspect</span>
                        <ArrowRight size={12} />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
