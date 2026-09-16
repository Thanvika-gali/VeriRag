import React from 'react';
import { BarChart3, PieChart, TrendingUp, AlertCircle, ShieldCheck } from 'lucide-react';

export default function AnalyticsView({ analytics, onNewEvaluation }) {
  const hasData = analytics && analytics.total_evaluations > 0;

  if (!hasData) {
    return (
      <div className="ink-card empty-state-box">
        <BarChart3 size={40} className="empty-icon" />
        <h3 className="empty-heading">Not enough evaluations to generate analytics</h3>
        <p className="empty-sub">
          Run evaluations through the platform to calculate real accuracy averages,
          hallucination rates, and pass/review distributions.
        </p>
        <button
          type="button"
          className="btn-primary"
          style={{ marginTop: '12px' }}
          onClick={onNewEvaluation}
        >
          Evaluate an AI Response
        </button>
      </div>
    );
  }

  const total = analytics.total_evaluations;
  const passRate = Math.round((analytics.pass_count / total) * 100);
  const reviewRate = Math.round((analytics.review_count / total) * 100);
  const failRate = Math.round((analytics.fail_count / total) * 100);
  const hallucinationRate = Math.round((analytics.hallucination_flag_count / total) * 100);

  return (
    <div className="analytics-container">
      {/* Top summary metrics */}
      <div className="metrics-grid">
        <div className="stat-card">
          <span className="stat-title">Pass Rate</span>
          <div className="stat-value" style={{ color: 'var(--status-pass-text)' }}>
            {passRate}%
          </div>
          <div className="stat-desc">{analytics.pass_count} of {total} evaluations passed</div>
        </div>

        <div className="stat-card">
          <span className="stat-title">Review Rate</span>
          <div className="stat-value" style={{ color: 'var(--status-review-text)' }}>
            {reviewRate}%
          </div>
          <div className="stat-desc">{analytics.review_count} of {total} required review</div>
        </div>

        <div className="stat-card">
          <span className="stat-title">Fail Rate</span>
          <div className="stat-value" style={{ color: 'var(--status-fail-text)' }}>
            {failRate}%
          </div>
          <div className="stat-desc">{analytics.fail_count} of {total} failed criteria</div>
        </div>

        <div className="stat-card">
          <span className="stat-title">Hallucination Rate</span>
          <div className="stat-value" style={{ color: 'var(--accent-primary)' }}>
            {hallucinationRate}%
          </div>
          <div className="stat-desc">{analytics.hallucination_flag_count} responses with flagged claims</div>
        </div>
      </div>

      {/* Aggregate Score Distribution */}
      <div className="ink-card">
        <div className="ink-card-header">
          <div className="card-title-block">
            <div className="card-icon-wrap">
              <TrendingUp size={16} />
            </div>
            <div>
              <h3 className="card-heading">Aggregate Verification Dimensions</h3>
              <p className="card-subtext">Real averages calculated from all stored database submissions</p>
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Average Accuracy Bar */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px', fontSize: '0.85rem' }}>
              <span style={{ fontWeight: 600 }}>Average Factual Accuracy</span>
              <span style={{ fontWeight: 700 }}>{analytics.average_accuracy || 0} / 5.0</span>
            </div>
            <div style={{ height: '10px', backgroundColor: 'var(--bg-surface-subtle)', borderRadius: '5px', overflow: 'hidden', border: '1px solid var(--border-subtle)' }}>
              <div
                style={{
                  height: '100%',
                  width: `${((analytics.average_accuracy || 0) / 5) * 100}%`,
                  backgroundColor: 'var(--accent-primary)',
                }}
              />
            </div>
          </div>

          {/* Average Relevance Bar */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px', fontSize: '0.85rem' }}>
              <span style={{ fontWeight: 600 }}>Average Topical Relevance</span>
              <span style={{ fontWeight: 700 }}>{analytics.average_relevance || 0} / 5.0</span>
            </div>
            <div style={{ height: '10px', backgroundColor: 'var(--bg-surface-subtle)', borderRadius: '5px', overflow: 'hidden', border: '1px solid var(--border-subtle)' }}>
              <div
                style={{
                  height: '100%',
                  width: `${((analytics.average_relevance || 0) / 5) * 100}%`,
                  backgroundColor: 'var(--accent-hover)',
                }}
              />
            </div>
          </div>

          {/* Average Overall Score */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px', fontSize: '0.85rem' }}>
              <span style={{ fontWeight: 600 }}>Average Overall Score</span>
              <span style={{ fontWeight: 700 }}>{analytics.average_overall_score || 0} / 100</span>
            </div>
            <div style={{ height: '10px', backgroundColor: 'var(--bg-surface-subtle)', borderRadius: '5px', overflow: 'hidden', border: '1px solid var(--border-subtle)' }}>
              <div
                style={{
                  height: '100%',
                  width: `${analytics.average_overall_score || 0}%`,
                  backgroundColor: 'var(--text-primary)',
                }}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
