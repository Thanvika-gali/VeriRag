import React from 'react';
import {
  FileCheck,
  Database,
  CheckCircle,
  AlertTriangle,
  Flame,
  ArrowRight,
  PlusCircle,
  Clock,
  ShieldCheck,
} from 'lucide-react';

export default function DashboardView({
  analytics,
  recentSubmissions = [],
  onSelectSubmission,
  onNewEvaluation,
}) {
  const hasData = analytics && analytics.total_evaluations > 0;

  return (
    <div className="dashboard-container">
      {/* High-Level Metric Cards */}
      <div className="metrics-grid">
        <div className="stat-card">
          <div className="stat-card-top">
            <span className="stat-title">Total Evaluations</span>
            <FileCheck size={18} className="stat-icon" />
          </div>
          <div className="stat-value">{hasData ? analytics.total_evaluations : 0}</div>
          <div className="stat-desc">Evaluations processed by platform</div>
        </div>

        <div className="stat-card">
          <div className="stat-card-top">
            <span className="stat-title">Evidence Retrieved</span>
            <Database size={18} className="stat-icon" />
          </div>
          <div className="stat-value">{hasData ? analytics.evidence_retrieved_count : 0}</div>
          <div className="stat-desc">Chunks retrieved from knowledge base</div>
        </div>

        <div className="stat-card">
          <div className="stat-card-top">
            <span className="stat-title">Average Accuracy</span>
            <CheckCircle size={18} className="stat-icon" />
          </div>
          <div className="stat-value">
            {hasData && analytics.average_accuracy !== null
              ? `${analytics.average_accuracy} / 5`
              : '—'}
          </div>
          <div className="stat-desc">Factual consistency rating</div>
        </div>

        <div className="stat-card">
          <div className="stat-card-top">
            <span className="stat-title">Average Relevance</span>
            <AlertTriangle size={18} className="stat-icon" />
          </div>
          <div className="stat-value">
            {hasData && analytics.average_relevance !== null
              ? `${analytics.average_relevance} / 5`
              : '—'}
          </div>
          <div className="stat-desc">Topic alignment rating</div>
        </div>

        <div className="stat-card">
          <div className="stat-card-top">
            <span className="stat-title">Hallucination Flags</span>
            <Flame size={18} className="stat-icon" />
          </div>
          <div className="stat-value">{hasData ? analytics.hallucination_flag_count : 0}</div>
          <div className="stat-desc">Responses with ungrounded claims</div>
        </div>
      </div>

      {/* Quick Action & Recent Evaluations */}
      <div className="ink-card">
        <div className="ink-card-header">
          <div className="card-title-block">
            <div className="card-icon-wrap">
              <Clock size={16} />
            </div>
            <div>
              <h2 className="card-heading">Recent Evaluations</h2>
              <p className="card-subtext">Verified responses stored in SQLite archive</p>
            </div>
          </div>

          <button
            type="button"
            className="btn-primary"
            onClick={onNewEvaluation}
          >
            <PlusCircle size={16} />
            <span>Evaluate Response</span>
          </button>
        </div>

        {!hasData || recentSubmissions.length === 0 ? (
          <div className="empty-state-box">
            <ShieldCheck size={42} className="empty-icon" />
            <h3 className="empty-heading">No evaluations yet</h3>
            <p className="empty-sub">
              Evaluate your first AI-generated response to view factual verification scores,
              hallucination risk analysis, and retrieved evidence.
            </p>
            <button
              type="button"
              className="btn-primary"
              style={{ marginTop: '8px' }}
              onClick={onNewEvaluation}
            >
              Start First Evaluation
            </button>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="ink-table">
              <thead>
                <tr>
                  <th>Question</th>
                  <th>Status</th>
                  <th>Accuracy</th>
                  <th>Relevance</th>
                  <th>Hallucination Risk</th>
                  <th>Date</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {recentSubmissions.slice(0, 8).map((item) => {
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
                      <td style={{ fontWeight: 600, maxWidth: '280px' }}>
                        <div style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          {item.question}
                        </div>
                      </td>
                      <td>
                        <span className={`verdict-badge ${verdictClass}`}>
                          {item.verdict || 'REVIEW'}
                        </span>
                      </td>
                      <td>
                        {item.accuracy_score ? `${item.accuracy_score} / 5` : '—'}
                      </td>
                      <td>
                        {item.relevance_score ? `${item.relevance_score} / 5` : '—'}
                      </td>
                      <td>
                        <span style={{ fontSize: '0.82rem', fontWeight: 600 }}>
                          {item.hallucination_risk || 'LOW'}
                        </span>
                      </td>
                      <td style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                        {item.created_at ? item.created_at.slice(0, 10) : 'Recent'}
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
                          <span>View</span>
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
    </div>
  );
}
