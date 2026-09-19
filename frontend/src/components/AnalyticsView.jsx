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
  const passCount = analytics.pass_count || 0;
  const reviewCount = analytics.review_count || 0;
  const failCount = analytics.fail_count || 0;
  const passRate = total > 0 ? Math.round((passCount / total) * 100) : 0;
  const reviewRate = total > 0 ? Math.round((reviewCount / total) * 100) : 0;
  const failRate = total > 0 ? Math.round((failCount / total) * 100) : 0;

  const halFlagCount = analytics.hallucination_flag_count || 0;
  const halFrequency = analytics.hallucination_frequency !== undefined && analytics.hallucination_frequency !== null
    ? Math.round(analytics.hallucination_frequency * 100)
    : (total > 0 ? Math.round((halFlagCount / total) * 100) : 0);

  const avgAcc = analytics.average_accuracy !== null && analytics.average_accuracy !== undefined ? analytics.average_accuracy : 0;
  const avgRel = analytics.average_relevance !== null && analytics.average_relevance !== undefined ? analytics.average_relevance : 0;
  const avgComp = analytics.average_completeness !== null && analytics.average_completeness !== undefined ? analytics.average_completeness : 0;
  const avgHalSafety = analytics.average_hallucination_safety !== null && analytics.average_hallucination_safety !== undefined ? analytics.average_hallucination_safety : 0;
  const avgOverall = analytics.average_overall_score !== null && analytics.average_overall_score !== undefined ? analytics.average_overall_score : 0;

  return (
    <div className="analytics-container">
      {/* Top summary metrics */}
      <div className="metrics-grid">
        <div className="stat-card">
          <span className="stat-title">Pass Rate</span>
          <div className="stat-value" style={{ color: 'var(--status-pass-text)' }}>
            {passRate}%
          </div>
          <div className="stat-desc">{passCount} of {total} evaluations passed</div>
        </div>

        <div className="stat-card">
          <span className="stat-title">Needs Improvement</span>
          <div className="stat-value" style={{ color: 'var(--status-review-text)' }}>
            {reviewRate}%
          </div>
          <div className="stat-desc">{reviewCount} of {total} required review</div>
        </div>

        <div className="stat-card">
          <span className="stat-title">Fail Rate</span>
          <div className="stat-value" style={{ color: 'var(--status-fail-text)' }}>
            {failRate}%
          </div>
          <div className="stat-desc">{failCount} of {total} failed criteria</div>
        </div>

        <div className="stat-card">
          <span className="stat-title">Hallucination Frequency</span>
          <div className="stat-value" style={{ color: halFrequency > 25 ? 'var(--status-fail-text)' : 'var(--accent-primary)' }}>
            {halFrequency}%
          </div>
          <div className="stat-desc">{halFlagCount} of {total} flagged with elevated risk</div>
        </div>
      </div>

      {/* Aggregate Score Distribution: All 5 Dimensions */}
      <div className="ink-card">
        <div className="ink-card-header">
          <div className="card-title-block">
            <div className="card-icon-wrap">
              <TrendingUp size={16} />
            </div>
            <div>
              <h3 className="card-heading">Aggregate Verification Dimensions</h3>
              <p className="card-subtext">Real averages calculated from all {total} stored database submissions</p>
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Average Accuracy Bar */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px', fontSize: '0.85rem' }}>
              <span style={{ fontWeight: 600 }}>Average Accuracy (35% weight)</span>
              <span style={{ fontWeight: 700 }}>{avgAcc} / 5.0</span>
            </div>
            <div style={{ height: '10px', backgroundColor: 'var(--bg-surface-subtle)', borderRadius: '5px', overflow: 'hidden', border: '1px solid var(--border-subtle)' }}>
              <div
                style={{
                  height: '100%',
                  width: `${(avgAcc / 5) * 100}%`,
                  backgroundColor: 'var(--accent-primary)',
                }}
              />
            </div>
          </div>

          {/* Average Relevance Bar */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px', fontSize: '0.85rem' }}>
              <span style={{ fontWeight: 600 }}>Average Relevance (20% weight)</span>
              <span style={{ fontWeight: 700 }}>{avgRel} / 5.0</span>
            </div>
            <div style={{ height: '10px', backgroundColor: 'var(--bg-surface-subtle)', borderRadius: '5px', overflow: 'hidden', border: '1px solid var(--border-subtle)' }}>
              <div
                style={{
                  height: '100%',
                  width: `${(avgRel / 5) * 100}%`,
                  backgroundColor: '#6366f1',
                }}
              />
            </div>
          </div>

          {/* Average Hallucination Safety Bar */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px', fontSize: '0.85rem' }}>
              <span style={{ fontWeight: 600 }}>Average Hallucination Safety (30% weight)</span>
              <span style={{ fontWeight: 700 }}>{avgHalSafety} / 5.0</span>
            </div>
            <div style={{ height: '10px', backgroundColor: 'var(--bg-surface-subtle)', borderRadius: '5px', overflow: 'hidden', border: '1px solid var(--border-subtle)' }}>
              <div
                style={{
                  height: '100%',
                  width: `${(avgHalSafety / 5) * 100}%`,
                  backgroundColor: '#10b981',
                }}
              />
            </div>
          </div>

          {/* Average Completeness Bar */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px', fontSize: '0.85rem' }}>
              <span style={{ fontWeight: 600 }}>Average Completeness (15% weight)</span>
              <span style={{ fontWeight: 700 }}>{avgComp} / 5.0</span>
            </div>
            <div style={{ height: '10px', backgroundColor: 'var(--bg-surface-subtle)', borderRadius: '5px', overflow: 'hidden', border: '1px solid var(--border-subtle)' }}>
              <div
                style={{
                  height: '100%',
                  width: `${(avgComp / 5) * 100}%`,
                  backgroundColor: '#8b5cf6',
                }}
              />
            </div>
          </div>

          {/* Average Overall Score */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px', fontSize: '0.85rem' }}>
              <span style={{ fontWeight: 600 }}>Average Overall Score</span>
              <span style={{ fontWeight: 700 }}>{avgOverall} / 100</span>
            </div>
            <div style={{ height: '10px', backgroundColor: 'var(--bg-surface-subtle)', borderRadius: '5px', overflow: 'hidden', border: '1px solid var(--border-subtle)' }}>
              <div
                style={{
                  height: '100%',
                  width: `${Math.min(100, avgOverall)}%`,
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
