import React, { useState, useEffect } from 'react';
import {
  BarChart3,
  TrendingUp,
  Download,
  Filter,
  RefreshCw,
  FileCheck2,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  ShieldCheck,
  Flame,
  Layers,
  ArrowRight,
  Database,
  Search,
  Eye,
  Calendar,
  Sparkles,
  HelpCircle,
  FileText,
  ChevronRight,
  PieChart as PieChartIcon,
} from 'lucide-react';

export default function AnalyticsView({
  analytics: fallbackAnalytics,
  onSelectSubmission,
  onNavigatePage,
  onNewEvaluation,
}) {
  const [loading, setLoading] = useState(false);
  const [pdfExporting, setPdfExporting] = useState(false);
  const [statsData, setStatsData] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);

  // Filters
  const [selectedBatch, setSelectedBatch] = useState('ALL');
  const [selectedVerdict, setSelectedVerdict] = useState('ALL');
  const [selectedScoreRange, setSelectedScoreRange] = useState('ALL');
  const [selectedHallucination, setSelectedHallucination] = useState('ALL');
  const [activeScoreDistTab, setActiveScoreDistTab] = useState('overall'); // 'overall', 'accuracy', 'relevance', 'completeness'

  // Drilldown Search & Pagination
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 8;

  useEffect(() => {
    fetchDashboardStats();
  }, [selectedBatch, selectedVerdict, selectedScoreRange, selectedHallucination]);

  const fetchDashboardStats = async () => {
    setLoading(true);
    setErrorMessage(null);
    try {
      const params = new URLSearchParams();
      if (selectedBatch && selectedBatch !== 'ALL') params.append('batch_id', selectedBatch);
      if (selectedVerdict && selectedVerdict !== 'ALL') params.append('verdict', selectedVerdict);
      if (selectedHallucination && selectedHallucination !== 'ALL') params.append('hallucination_status', selectedHallucination);

      if (selectedScoreRange === '90-100') {
        params.append('score_min', '90');
        params.append('score_max', '100');
      } else if (selectedScoreRange === '75-89') {
        params.append('score_min', '75');
        params.append('score_max', '89');
      } else if (selectedScoreRange === '50-74') {
        params.append('score_min', '50');
        params.append('score_max', '74');
      } else if (selectedScoreRange === '0-49') {
        params.append('score_min', '0');
        params.append('score_max', '49');
      }

      const res = await fetch(`/api/dashboard/stats?${params.toString()}`);
      if (!res.ok) {
        throw new Error('Failed to load dashboard statistics from database.');
      }
      const data = await res.json();
      setStatsData(data);
      setCurrentPage(1);
    } catch (err) {
      console.error('[Dashboard fetch error]:', err);
      setErrorMessage(err.message || 'Error communicating with backend storage.');
    } finally {
      setLoading(false);
    }
  };

  const handleExportPDF = async () => {
    setPdfExporting(true);
    try {
      const params = new URLSearchParams();
      if (selectedBatch && selectedBatch !== 'ALL') {
        params.append('batch_id', selectedBatch);
      }
      const url = `/api/reports/pdf?${params.toString()}`;
      const res = await fetch(url);
      if (!res.ok) {
        throw new Error('PDF export failed on the server.');
      }
      const blob = await res.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = downloadUrl;
      const filename = selectedBatch && selectedBatch !== 'ALL'
        ? `proofrag_batch_${selectedBatch.slice(0, 8)}_report.pdf`
        : 'proofrag_evaluation_report.pdf';
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(downloadUrl);
    } catch (err) {
      alert(`Could not export PDF report: ${err.message}`);
    } finally {
      setPdfExporting(false);
    }
  };

  const handleResetFilters = () => {
    setSelectedBatch('ALL');
    setSelectedVerdict('ALL');
    setSelectedScoreRange('ALL');
    setSelectedHallucination('ALL');
    setSearchQuery('');
    setCurrentPage(1);
  };

  const handleFilterByVerdictClick = (verdictKey) => {
    if (selectedVerdict === verdictKey) {
      setSelectedVerdict('ALL');
    } else {
      setSelectedVerdict(verdictKey);
    }
  };

  const data = statsData || {};
  const hasData = data && data.total_evaluations > 0;

  const total = data.total_evaluations || 0;
  const verdicts = data.verdicts || { PASS: 0, 'NEEDS IMPROVEMENT': 0, FAIL: 0 };
  const verdictPcts = data.verdict_percentages || { PASS: 0, 'NEEDS IMPROVEMENT': 0, FAIL: 0 };
  const dimAvg = data.dimension_averages || {};
  const halStats = data.hallucination_stats || {};
  const compStats = data.completeness_stats || {};
  const distributions = data.score_distributions || {};
  const frequentIssues = data.frequent_issues || [];
  const batchTrends = data.batch_trends || [];
  const availableBatches = data.available_batches || [{ id: 'ALL', label: 'All Batches & Evaluations' }];
  const rawRecords = data.records || [];

  // Filter drilldown records by local search query if provided
  const filteredRecords = rawRecords.filter((rec) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      (rec.question && rec.question.toLowerCase().includes(q)) ||
      (rec.ai_response_snippet && rec.ai_response_snippet.toLowerCase().includes(q)) ||
      (rec.verdict && rec.verdict.toLowerCase().includes(q)) ||
      (rec.submission_id && rec.submission_id.toLowerCase().includes(q))
    );
  });

  const totalPages = Math.ceil(filteredRecords.length / pageSize) || 1;
  const paginatedRecords = filteredRecords.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  const avgOverall = data.average_overall_score !== null && data.average_overall_score !== undefined
    ? data.average_overall_score
    : 0;

  const avgAcc = dimAvg.accuracy !== null && dimAvg.accuracy !== undefined ? dimAvg.accuracy : 0;
  const avgRel = dimAvg.relevance !== null && dimAvg.relevance !== undefined ? dimAvg.relevance : 0;
  const avgComp = dimAvg.completeness !== null && dimAvg.completeness !== undefined ? dimAvg.completeness : 0;
  const avgHalSafety = dimAvg.hallucination_safety !== null && dimAvg.hallucination_safety !== undefined ? dimAvg.hallucination_safety : 0;

  return (
    <div className="analytics-container" style={{ display: 'flex', flexDirection: 'column', gap: '22px' }}>
      {/* Top Header & Controls */}
      <div className="ink-card" style={{ padding: '18px 24px', borderLeft: '4px solid var(--accent-primary)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '14px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 800, textTransform: 'uppercase', color: 'var(--accent-primary)', letterSpacing: '0.05em' }}>
                Milestone 4 — Real-Time Evaluation Dashboard
              </span>
              {loading && <RefreshCw size={13} className="spin-icon" style={{ color: 'var(--text-muted)' }} />}
            </div>
            <h2 style={{ fontSize: '1.35rem', fontWeight: 800, color: 'var(--text-primary)', margin: '4px 0 2px 0' }}>
              Evaluation Scoring & Quality Analytics
            </h2>
            <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', margin: 0 }}>
              Calculated dynamically from real stored evaluation records in the SQLite archive.
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
            <button
              type="button"
              id="refresh-dashboard-btn"
              className="btn-secondary"
              onClick={fetchDashboardStats}
              disabled={loading}
              title="Refresh statistics from database"
            >
              <RefreshCw size={14} className={loading ? 'spin-icon' : ''} />
              <span>Refresh</span>
            </button>

            <button
              type="button"
              id="export-pdf-report-btn"
              className="btn-primary"
              onClick={handleExportPDF}
              disabled={pdfExporting || total === 0}
              style={{ backgroundColor: '#0f172a', borderColor: '#0f172a' }}
              title="Download professional PDF evaluation audit report"
            >
              <Download size={14} />
              <span>{pdfExporting ? 'Generating PDF...' : 'Export Evaluation Report (PDF)'}</span>
            </button>
          </div>
        </div>

        {/* Dynamic Filter Bar */}
        <div
          style={{
            marginTop: '16px',
            paddingTop: '16px',
            borderTop: '1px solid var(--border-subtle)',
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
            gap: '12px',
            alignItems: 'end',
          }}
        >
          {/* Batch Selector */}
          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '5px' }}>
              FILTER BY BATCH
            </label>
            <select
              id="filter-batch-select"
              className="form-input"
              value={selectedBatch}
              onChange={(e) => setSelectedBatch(e.target.value)}
              style={{ fontSize: '0.82rem', padding: '7px 10px' }}
            >
              {availableBatches.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.label}
                </option>
              ))}
            </select>
          </div>

          {/* Verdict Filter */}
          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '5px' }}>
              VERDICT
            </label>
            <select
              id="filter-verdict-select"
              className="form-input"
              value={selectedVerdict}
              onChange={(e) => setSelectedVerdict(e.target.value)}
              style={{ fontSize: '0.82rem', padding: '7px 10px' }}
            >
              <option value="ALL">All Verdicts</option>
              <option value="PASS">PASS Only</option>
              <option value="NEEDS IMPROVEMENT">NEEDS IMPROVEMENT Only</option>
              <option value="FAIL">FAIL Only</option>
            </select>
          </div>

          {/* Score Range Filter */}
          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '5px' }}>
              SCORE RANGE
            </label>
            <select
              id="filter-score-select"
              className="form-input"
              value={selectedScoreRange}
              onChange={(e) => setSelectedScoreRange(e.target.value)}
              style={{ fontSize: '0.82rem', padding: '7px 10px' }}
            >
              <option value="ALL">All Scores (0 - 100)</option>
              <option value="90-100">90 – 100 (Exemplary)</option>
              <option value="75-89">75 – 89 (Passing)</option>
              <option value="50-74">50 – 74 (Borderline)</option>
              <option value="0-49">0 – 49 (Failing)</option>
            </select>
          </div>

          {/* Hallucination Filter */}
          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '5px' }}>
              HALLUCINATION RISK
            </label>
            <select
              id="filter-hal-select"
              className="form-input"
              value={selectedHallucination}
              onChange={(e) => setSelectedHallucination(e.target.value)}
              style={{ fontSize: '0.82rem', padding: '7px 10px' }}
            >
              <option value="ALL">All Responses</option>
              <option value="FLAGGED">Flagged Risk (Medium/High)</option>
              <option value="SAFE">Grounded / Safe (Low)</option>
            </select>
          </div>

          {/* Reset Filters */}
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              type="button"
              className="btn-secondary"
              onClick={handleResetFilters}
              style={{ height: '36px', fontSize: '0.8rem', padding: '0 14px', width: '100%' }}
            >
              <Filter size={13} />
              <span>Reset Filters</span>
            </button>
          </div>
        </div>

        {/* Active Filter Indicators */}
        {(selectedBatch !== 'ALL' || selectedVerdict !== 'ALL' || selectedScoreRange !== 'ALL' || selectedHallucination !== 'ALL') && (
          <div style={{ marginTop: '12px', display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', fontSize: '0.78rem' }}>
            <span style={{ color: 'var(--text-muted)', fontWeight: 600 }}>Active Filters:</span>
            {selectedBatch !== 'ALL' && (
              <span className="telemetry-chip">Batch: {selectedBatch.slice(0, 10)}</span>
            )}
            {selectedVerdict !== 'ALL' && (
              <span className="telemetry-chip">Verdict: {selectedVerdict}</span>
            )}
            {selectedScoreRange !== 'ALL' && (
              <span className="telemetry-chip">Score: {selectedScoreRange}</span>
            )}
            {selectedHallucination !== 'ALL' && (
              <span className="telemetry-chip">Hallucination: {selectedHallucination}</span>
            )}
            <span style={{ color: 'var(--accent-primary)', fontWeight: 700, marginLeft: '4px' }}>
              ({total} matching records)
            </span>
          </div>
        )}
      </div>

      {!hasData ? (
        <div className="ink-card empty-state-box" style={{ padding: '48px 24px' }}>
          <BarChart3 size={44} className="empty-icon" />
          <h3 className="empty-heading">No evaluation records match this query</h3>
          <p className="empty-sub">
            Adjust your filters or execute single / batch evaluations to populate real stored validation statistics.
          </p>
          <div style={{ display: 'flex', gap: '10px', marginTop: '14px' }}>
            <button type="button" className="btn-secondary" onClick={handleResetFilters}>
              Reset Filters
            </button>
            <button type="button" className="btn-primary" onClick={onNewEvaluation}>
              Evaluate Response
            </button>
          </div>
        </div>
      ) : (
        <>
          {/* 1. High-Level KPI Stat Cards */}
          <div className="metrics-grid">
            <div className="stat-card" style={{ borderTop: '3px solid var(--accent-primary)' }}>
              <div className="stat-card-top">
                <span className="stat-title">Total Evaluated</span>
                <FileCheck2 size={18} className="stat-icon" />
              </div>
              <div className="stat-value">{total}</div>
              <div className="stat-desc">Filtered evaluation records stored</div>
            </div>

            <div
              className="stat-card"
              style={{ borderTop: '3px solid var(--status-pass-text)', cursor: 'pointer' }}
              onClick={() => handleFilterByVerdictClick('PASS')}
              title="Click to filter by PASS verdict"
            >
              <div className="stat-card-top">
                <span className="stat-title">PASS Verdicts</span>
                <CheckCircle2 size={18} style={{ color: 'var(--status-pass-text)' }} />
              </div>
              <div className="stat-value" style={{ color: 'var(--status-pass-text)' }}>
                {verdicts.PASS || 0}
                <span style={{ fontSize: '0.85rem', fontWeight: 600, marginLeft: '6px' }}>
                  ({verdictPcts.PASS || 0}%)
                </span>
              </div>
              <div className="stat-desc">Passed all critical quality criteria</div>
            </div>

            <div
              className="stat-card"
              style={{ borderTop: '3px solid var(--status-review-text)', cursor: 'pointer' }}
              onClick={() => handleFilterByVerdictClick('NEEDS IMPROVEMENT')}
              title="Click to filter by NEEDS IMPROVEMENT verdict"
            >
              <div className="stat-card-top">
                <span className="stat-title">Needs Improvement</span>
                <AlertTriangle size={18} style={{ color: 'var(--status-review-text)' }} />
              </div>
              <div className="stat-value" style={{ color: 'var(--status-review-text)' }}>
                {verdicts['NEEDS IMPROVEMENT'] || 0}
                <span style={{ fontSize: '0.85rem', fontWeight: 600, marginLeft: '6px' }}>
                  ({verdictPcts['NEEDS IMPROVEMENT'] || 0}%)
                </span>
              </div>
              <div className="stat-desc">Substantive revisions or review recommended</div>
            </div>

            <div
              className="stat-card"
              style={{ borderTop: '3px solid var(--status-fail-text)', cursor: 'pointer' }}
              onClick={() => handleFilterByVerdictClick('FAIL')}
              title="Click to filter by FAIL verdict"
            >
              <div className="stat-card-top">
                <span className="stat-title">FAIL Verdicts</span>
                <XCircle size={18} style={{ color: 'var(--status-fail-text)' }} />
              </div>
              <div className="stat-value" style={{ color: 'var(--status-fail-text)' }}>
                {verdicts.FAIL || 0}
                <span style={{ fontSize: '0.85rem', fontWeight: 600, marginLeft: '6px' }}>
                  ({verdictPcts.FAIL || 0}%)
                </span>
              </div>
              <div className="stat-desc">Severe contradiction or factual errors</div>
            </div>

            <div className="stat-card" style={{ borderTop: '3px solid #3b82f6' }}>
              <div className="stat-card-top">
                <span className="stat-title">Mean Overall Score</span>
                <TrendingUp size={18} style={{ color: '#3b82f6' }} />
              </div>
              <div className="stat-value">
                {avgOverall}
                <span style={{ fontSize: '0.8rem', fontWeight: 500, color: 'var(--text-muted)', marginLeft: '4px' }}>
                  / 100
                </span>
              </div>
              <div className="stat-desc">4-dimension weighted score average</div>
            </div>
          </div>

          {/* 2. Visual Distributions: Verdict Distribution & Dimension Comparison */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '20px' }}>
            {/* Verdict Distribution Card */}
            <div className="ink-card" style={{ display: 'flex', flexDirection: 'column' }}>
              <div className="ink-card-header">
                <div className="card-title-block">
                  <div className="card-icon-wrap">
                    <PieChartIcon size={16} />
                  </div>
                  <div>
                    <h3 className="card-heading">Verdict Distribution</h3>
                    <p className="card-subtext">Click any bar segment to drill down into records</p>
                  </div>
                </div>
              </div>

              {/* Stacked Progress Bar */}
              <div style={{ margin: '14px 0 20px 0' }}>
                <div
                  style={{
                    height: '24px',
                    borderRadius: '8px',
                    display: 'flex',
                    overflow: 'hidden',
                    border: '1px solid var(--border-color)',
                  }}
                >
                  <div
                    style={{
                      width: `${verdictPcts.PASS || 0}%`,
                      backgroundColor: '#22c55e',
                      transition: 'width 0.4s ease',
                      cursor: 'pointer',
                    }}
                    onClick={() => handleFilterByVerdictClick('PASS')}
                    title={`PASS: ${verdicts.PASS || 0} (${verdictPcts.PASS || 0}%)`}
                  />
                  <div
                    style={{
                      width: `${verdictPcts['NEEDS IMPROVEMENT'] || 0}%`,
                      backgroundColor: '#f59e0b',
                      transition: 'width 0.4s ease',
                      cursor: 'pointer',
                    }}
                    onClick={() => handleFilterByVerdictClick('NEEDS IMPROVEMENT')}
                    title={`NEEDS IMPROVEMENT: ${verdicts['NEEDS IMPROVEMENT'] || 0} (${verdictPcts['NEEDS IMPROVEMENT'] || 0}%)`}
                  />
                  <div
                    style={{
                      width: `${verdictPcts.FAIL || 0}%`,
                      backgroundColor: '#ef4444',
                      transition: 'width 0.4s ease',
                      cursor: 'pointer',
                    }}
                    onClick={() => handleFilterByVerdictClick('FAIL')}
                    title={`FAIL: ${verdicts.FAIL || 0} (${verdictPcts.FAIL || 0}%)`}
                  />
                </div>
              </div>

              {/* Legend & Count Details */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '8px 12px',
                    backgroundColor: 'var(--bg-surface-subtle)',
                    borderRadius: 'var(--radius-sm)',
                    cursor: 'pointer',
                  }}
                  onClick={() => handleFilterByVerdictClick('PASS')}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ width: '12px', height: '12px', borderRadius: '3px', backgroundColor: '#22c55e' }} />
                    <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>PASS</span>
                  </div>
                  <div style={{ fontSize: '0.85rem' }}>
                    <strong>{verdicts.PASS || 0}</strong> <span style={{ color: 'var(--text-muted)' }}>({verdictPcts.PASS || 0}%)</span>
                  </div>
                </div>

                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '8px 12px',
                    backgroundColor: 'var(--bg-surface-subtle)',
                    borderRadius: 'var(--radius-sm)',
                    cursor: 'pointer',
                  }}
                  onClick={() => handleFilterByVerdictClick('NEEDS IMPROVEMENT')}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ width: '12px', height: '12px', borderRadius: '3px', backgroundColor: '#f59e0b' }} />
                    <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>NEEDS IMPROVEMENT</span>
                  </div>
                  <div style={{ fontSize: '0.85rem' }}>
                    <strong>{verdicts['NEEDS IMPROVEMENT'] || 0}</strong> <span style={{ color: 'var(--text-muted)' }}>({verdictPcts['NEEDS IMPROVEMENT'] || 0}%)</span>
                  </div>
                </div>

                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '8px 12px',
                    backgroundColor: 'var(--bg-surface-subtle)',
                    borderRadius: 'var(--radius-sm)',
                    cursor: 'pointer',
                  }}
                  onClick={() => handleFilterByVerdictClick('FAIL')}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ width: '12px', height: '12px', borderRadius: '3px', backgroundColor: '#ef4444' }} />
                    <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>FAIL</span>
                  </div>
                  <div style={{ fontSize: '0.85rem' }}>
                    <strong>{verdicts.FAIL || 0}</strong> <span style={{ color: 'var(--text-muted)' }}>({verdictPcts.FAIL || 0}%)</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Dimension Comparison Card */}
            <div className="ink-card" style={{ display: 'flex', flexDirection: 'column' }}>
              <div className="ink-card-header">
                <div className="card-title-block">
                  <div className="card-icon-wrap">
                    <TrendingUp size={16} />
                  </div>
                  <div>
                    <h3 className="card-heading">Dimension Comparison</h3>
                    <p className="card-subtext">Average performance across 4 calibrated evaluation dimensions</p>
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginTop: '8px' }}>
                {/* Accuracy */}
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '5px', fontSize: '0.83rem' }}>
                    <span style={{ fontWeight: 600 }}>
                      Accuracy <span style={{ color: 'var(--text-muted)', fontSize: '0.78rem' }}>(35% weight)</span>
                    </span>
                    <strong style={{ color: 'var(--text-primary)' }}>{avgAcc} / 5.0</strong>
                  </div>
                  <div style={{ height: '8px', backgroundColor: 'var(--bg-surface-subtle)', borderRadius: '4px', overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: `${(avgAcc / 5) * 100}%`, backgroundColor: 'var(--accent-primary)' }} />
                  </div>
                </div>

                {/* Hallucination Safety */}
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '5px', fontSize: '0.83rem' }}>
                    <span style={{ fontWeight: 600 }}>
                      Hallucination Safety <span style={{ color: 'var(--text-muted)', fontSize: '0.78rem' }}>(30% weight)</span>
                    </span>
                    <strong style={{ color: 'var(--text-primary)' }}>{avgHalSafety} / 5.0</strong>
                  </div>
                  <div style={{ height: '8px', backgroundColor: 'var(--bg-surface-subtle)', borderRadius: '4px', overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: `${(avgHalSafety / 5) * 100}%`, backgroundColor: '#10b981' }} />
                  </div>
                </div>

                {/* Relevance */}
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '5px', fontSize: '0.83rem' }}>
                    <span style={{ fontWeight: 600 }}>
                      Relevance <span style={{ color: 'var(--text-muted)', fontSize: '0.78rem' }}>(20% weight)</span>
                    </span>
                    <strong style={{ color: 'var(--text-primary)' }}>{avgRel} / 5.0</strong>
                  </div>
                  <div style={{ height: '8px', backgroundColor: 'var(--bg-surface-subtle)', borderRadius: '4px', overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: `${(avgRel / 5) * 100}%`, backgroundColor: '#6366f1' }} />
                  </div>
                </div>

                {/* Completeness */}
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '5px', fontSize: '0.83rem' }}>
                    <span style={{ fontWeight: 600 }}>
                      Completeness <span style={{ color: 'var(--text-muted)', fontSize: '0.78rem' }}>(15% weight)</span>
                    </span>
                    <strong style={{ color: 'var(--text-primary)' }}>{avgComp} / 5.0</strong>
                  </div>
                  <div style={{ height: '8px', backgroundColor: 'var(--bg-surface-subtle)', borderRadius: '4px', overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: `${(avgComp / 5) * 100}%`, backgroundColor: '#8b5cf6' }} />
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* 3. Deep Dive: Hallucination & Completeness Statistics */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '20px' }}>
            {/* Hallucination Statistics */}
            <div className="ink-card">
              <div className="ink-card-header">
                <div className="card-title-block">
                  <div className="card-icon-wrap" style={{ backgroundColor: 'var(--status-fail-bg)', color: 'var(--status-fail-text)' }}>
                    <Flame size={16} />
                  </div>
                  <div>
                    <h3 className="card-heading">Hallucination Analysis</h3>
                    <p className="card-subtext">Detection of ungrounded or contradicted assertions</p>
                  </div>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px', margin: '14px 0' }}>
                <div style={{ padding: '12px', backgroundColor: 'var(--bg-surface-subtle)', borderRadius: 'var(--radius-sm)', textAlign: 'center' }}>
                  <div style={{ fontSize: '1.4rem', fontWeight: 800, color: halStats.frequency_percentage > 25 ? 'var(--status-fail-text)' : 'var(--text-primary)' }}>
                    {halStats.frequency_percentage || 0}%
                  </div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600 }}>FREQUENCY</div>
                </div>

                <div style={{ padding: '12px', backgroundColor: 'var(--bg-surface-subtle)', borderRadius: 'var(--radius-sm)', textAlign: 'center' }}>
                  <div style={{ fontSize: '1.4rem', fontWeight: 800, color: halStats.flagged_count > 0 ? 'var(--status-review-text)' : 'var(--text-primary)' }}>
                    {halStats.flagged_count || 0}
                  </div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600 }}>FLAGGED RESPONSES</div>
                </div>

                <div style={{ padding: '12px', backgroundColor: 'var(--bg-surface-subtle)', borderRadius: 'var(--radius-sm)', textAlign: 'center' }}>
                  <div style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--text-primary)' }}>
                    {halStats.unsupported_claims_count || 0}
                  </div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600 }}>UNGROUNDED CLAIMS</div>
                </div>
              </div>

              {/* Risk Level Breakdown */}
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                  <span>Low Risk (Grounded):</span>
                  <strong>{halStats.risk_breakdown?.LOW || 0}</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                  <span>Medium Risk (Partially Ungrounded):</span>
                  <strong style={{ color: 'var(--status-review-text)' }}>{halStats.risk_breakdown?.MEDIUM || 0}</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span>High Risk (Severely Contradicted):</span>
                  <strong style={{ color: 'var(--status-fail-text)' }}>{halStats.risk_breakdown?.HIGH || 0}</strong>
                </div>
              </div>
            </div>

            {/* Completeness Statistics */}
            <div className="ink-card">
              <div className="ink-card-header">
                <div className="card-title-block">
                  <div className="card-icon-wrap" style={{ backgroundColor: '#ede9fe', color: '#6d28d9' }}>
                    <Layers size={16} />
                  </div>
                  <div>
                    <h3 className="card-heading">Completeness Analysis</h3>
                    <p className="card-subtext">Coverage of question requirements and omitted details</p>
                  </div>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px', margin: '14px 0' }}>
                <div style={{ padding: '12px', backgroundColor: 'var(--bg-surface-subtle)', borderRadius: 'var(--radius-sm)', textAlign: 'center' }}>
                  <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#15803d' }}>
                    {compStats.complete_count || 0}
                  </div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600 }}>COMPLETE (4-5)</div>
                </div>

                <div style={{ padding: '12px', backgroundColor: 'var(--bg-surface-subtle)', borderRadius: 'var(--radius-sm)', textAlign: 'center' }}>
                  <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#b45309' }}>
                    {compStats.partially_complete_count || 0}
                  </div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600 }}>PARTIAL (3)</div>
                </div>

                <div style={{ padding: '12px', backgroundColor: 'var(--bg-surface-subtle)', borderRadius: 'var(--radius-sm)', textAlign: 'center' }}>
                  <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#b91c1c' }}>
                    {compStats.incomplete_count || 0}
                  </div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600 }}>INCOMPLETE (1-2)</div>
                </div>
              </div>

              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                  <span>Missing Aspect Frequency:</span>
                  <strong>{compStats.missing_aspect_frequency || 0}%</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span>Total Omitted Requirements Identified:</span>
                  <strong>{compStats.total_missing_aspects || 0} facets</strong>
                </div>
              </div>
            </div>
          </div>

          {/* 4. Score Distributions */}
          <div className="ink-card">
            <div className="ink-card-header">
              <div className="card-title-block">
                <div className="card-icon-wrap">
                  <BarChart3 size={16} />
                </div>
                <div>
                  <h3 className="card-heading">Score Distributions</h3>
                  <p className="card-subtext">Spread of overall scores and dimension-specific ratings</p>
                </div>
              </div>

              {/* Dimension Switcher Tabs */}
              <div style={{ display: 'flex', gap: '6px' }}>
                {['overall', 'accuracy', 'relevance', 'completeness'].map((tab) => (
                  <button
                    key={tab}
                    type="button"
                    className={`btn-secondary ${activeScoreDistTab === tab ? 'active' : ''}`}
                    style={{
                      padding: '4px 10px',
                      fontSize: '0.75rem',
                      textTransform: 'capitalize',
                      borderColor: activeScoreDistTab === tab ? 'var(--accent-primary)' : 'var(--border-color)',
                      backgroundColor: activeScoreDistTab === tab ? 'var(--bg-surface-subtle)' : 'transparent',
                    }}
                    onClick={() => setActiveScoreDistTab(tab)}
                  >
                    {tab}
                  </button>
                ))}
              </div>
            </div>

            {/* Distribution Bar Chart */}
            <div style={{ marginTop: '14px' }}>
              {activeScoreDistTab === 'overall' && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px' }}>
                  {Object.entries(distributions.overall || {}).map(([tier, count]) => {
                    const pct = total > 0 ? Math.round((count / total) * 100) : 0;
                    return (
                      <div
                        key={tier}
                        style={{
                          padding: '12px',
                          backgroundColor: 'var(--bg-surface-subtle)',
                          borderRadius: 'var(--radius-sm)',
                          border: '1px solid var(--border-subtle)',
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '6px' }}>
                          <span style={{ fontWeight: 700 }}>Score {tier}</span>
                          <span style={{ color: 'var(--text-muted)' }}>{count} ({pct}%)</span>
                        </div>
                        <div style={{ height: '6px', backgroundColor: 'var(--border-color)', borderRadius: '3px', overflow: 'hidden' }}>
                          <div style={{ height: '100%', width: `${pct}%`, backgroundColor: tier === '90-100' ? '#22c55e' : tier === '75-89' ? '#3b82f6' : tier === '50-74' ? '#f59e0b' : '#ef4444' }} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              {activeScoreDistTab !== 'overall' && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '10px' }}>
                  {[1, 2, 3, 4, 5].map((star) => {
                    const count = (distributions[activeScoreDistTab] && distributions[activeScoreDistTab][String(star)]) || 0;
                    const pct = total > 0 ? Math.round((count / total) * 100) : 0;
                    return (
                      <div
                        key={star}
                        style={{
                          padding: '10px',
                          backgroundColor: 'var(--bg-surface-subtle)',
                          borderRadius: 'var(--radius-sm)',
                          border: '1px solid var(--border-subtle)',
                          textAlign: 'center',
                        }}
                      >
                        <div style={{ fontSize: '0.9rem', fontWeight: 800 }}>{star} / 5</div>
                        <div style={{ fontSize: '1.1rem', fontWeight: 800, margin: '4px 0', color: 'var(--text-primary)' }}>
                          {count}
                        </div>
                        <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>{pct}%</div>
                        <div style={{ height: '4px', backgroundColor: 'var(--border-color)', borderRadius: '2px', overflow: 'hidden', marginTop: '6px' }}>
                          <div style={{ height: '100%', width: `${pct}%`, backgroundColor: star >= 4 ? '#22c55e' : star === 3 ? '#f59e0b' : '#ef4444' }} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {/* 5. Most Frequent Evaluation Issues */}
          <div className="ink-card">
            <div className="ink-card-header">
              <div className="card-title-block">
                <div className="card-icon-wrap" style={{ backgroundColor: 'var(--status-review-bg)', color: 'var(--status-review-text)' }}>
                  <AlertTriangle size={16} />
                </div>
                <div>
                  <h3 className="card-heading">Most Frequent Evaluation Issues</h3>
                  <p className="card-subtext">Common factual errors, omissions, and verification gaps across responses</p>
                </div>
              </div>
            </div>

            <div style={{ overflowX: 'auto', marginTop: '10px' }}>
              <table className="ink-table">
                <thead>
                  <tr>
                    <th>Issue Type</th>
                    <th>Category</th>
                    <th>Affected Records</th>
                    <th>Frequency</th>
                    <th>Description</th>
                  </tr>
                </thead>
                <tbody>
                  {frequentIssues.map((issue) => (
                    <tr key={issue.issue_type}>
                      <td style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{issue.issue_type}</td>
                      <td>
                        <span className="telemetry-chip" style={{ fontSize: '0.72rem' }}>
                          {issue.category}
                        </span>
                      </td>
                      <td style={{ fontWeight: 700 }}>{issue.count}</td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ fontWeight: 600 }}>{issue.percentage}%</span>
                          <div style={{ width: '60px', height: '6px', backgroundColor: 'var(--bg-surface-subtle)', borderRadius: '3px', overflow: 'hidden' }}>
                            <div
                              style={{
                                height: '100%',
                                width: `${Math.min(100, issue.percentage)}%`,
                                backgroundColor: issue.percentage > 20 ? 'var(--status-fail-text)' : 'var(--status-review-text)',
                              }}
                            />
                          </div>
                        </div>
                      </td>
                      <td style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{issue.description}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* 6. Batch Quality Trends & Batch-Level Summary */}
          {batchTrends.length > 0 && (
            <div className="ink-card">
              <div className="ink-card-header">
                <div className="card-title-block">
                  <div className="card-icon-wrap">
                    <Calendar size={16} />
                  </div>
                  <div>
                    <h3 className="card-heading">Quality Trends Across Evaluation Batches</h3>
                    <p className="card-subtext">Historical comparison across {batchTrends.length} executed batch verification jobs</p>
                  </div>
                </div>
              </div>

              <div style={{ overflowX: 'auto', marginTop: '10px' }}>
                <table className="ink-table">
                  <thead>
                    <tr>
                      <th>Batch File</th>
                      <th>Date</th>
                      <th>Records</th>
                      <th>Pass Rate</th>
                      <th>Mean Score</th>
                      <th>Accuracy</th>
                      <th>Hallucination Freq</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {batchTrends.map((bt) => (
                      <tr key={bt.batch_id}>
                        <td style={{ fontWeight: 600, maxWidth: '200px' }}>
                          <div style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                            {bt.filename}
                          </div>
                        </td>
                        <td style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                          {bt.created_at ? bt.created_at.slice(0, 10) : 'Recent'}
                        </td>
                        <td>{bt.total_records}</td>
                        <td>
                          <span style={{ fontWeight: 700, color: bt.pass_rate >= 70 ? 'var(--status-pass-text)' : bt.pass_rate >= 50 ? 'var(--status-review-text)' : 'var(--status-fail-text)' }}>
                            {bt.pass_rate}%
                          </span>
                        </td>
                        <td>
                          <strong>{bt.average_overall_score ?? '—'}</strong> / 100
                        </td>
                        <td>{bt.average_accuracy ?? '—'} / 5.0</td>
                        <td>
                          <span style={{ color: bt.hallucination_frequency > 20 ? 'var(--status-fail-text)' : 'inherit' }}>
                            {bt.hallucination_frequency}%
                          </span>
                        </td>
                        <td>
                          <button
                            type="button"
                            className="btn-secondary"
                            style={{ padding: '4px 10px', fontSize: '0.76rem' }}
                            onClick={() => setSelectedBatch(bt.batch_id)}
                          >
                            <span>Filter Batch</span>
                            <ArrowRight size={11} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* 7. Interactive Drill-Down Table */}
          <div className="ink-card" id="drill-down-records-section">
            <div className="ink-card-header">
              <div className="card-title-block">
                <div className="card-icon-wrap">
                  <Search size={16} />
                </div>
                <div>
                  <h3 className="card-heading">Evaluated Records Drill-Down</h3>
                  <p className="card-subtext">
                    Showing {filteredRecords.length} matching evaluation submission(s). Click any record to inspect full audit details.
                  </p>
                </div>
              </div>

              {/* Local Search Input */}
              <div style={{ width: '220px' }}>
                <input
                  type="text"
                  className="form-input"
                  placeholder="Search questions or terms..."
                  value={searchQuery}
                  onChange={(e) => {
                    setSearchQuery(e.target.value);
                    setCurrentPage(1);
                  }}
                  style={{ fontSize: '0.8rem', padding: '6px 10px' }}
                />
              </div>
            </div>

            {paginatedRecords.length === 0 ? (
              <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.86rem' }}>
                No records match your active search terms.
              </div>
            ) : (
              <div style={{ overflowX: 'auto', marginTop: '10px' }}>
                <table className="ink-table">
                  <thead>
                    <tr>
                      <th>Question</th>
                      <th>Verdict</th>
                      <th>Score</th>
                      <th>Accuracy</th>
                      <th>Relevance</th>
                      <th>Completeness</th>
                      <th>Hal. Risk</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {paginatedRecords.map((item) => {
                      const verdictClass =
                        item.verdict === 'PASS'
                          ? 'verdict-pass'
                          : item.verdict === 'FAIL'
                          ? 'verdict-fail'
                          : 'verdict-review';

                      const halRisk = (item.hallucination_risk || 'LOW').toUpperCase();
                      const halColor =
                        halRisk === 'HIGH'
                          ? 'var(--status-fail-text)'
                          : halRisk === 'MEDIUM'
                          ? 'var(--status-review-text)'
                          : 'var(--status-pass-text)';

                      return (
                        <tr
                          key={item.submission_id}
                          style={{ cursor: 'pointer' }}
                          onClick={() => onSelectSubmission && onSelectSubmission(item.submission_id)}
                        >
                          <td style={{ maxWidth: '280px' }}>
                            <div style={{ fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                              {item.question}
                            </div>
                            <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginTop: '2px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                              {item.ai_response_snippet}
                            </div>
                          </td>
                          <td>
                            <span className={`verdict-badge ${verdictClass}`}>
                              {item.verdict || 'REVIEW'}
                            </span>
                          </td>
                          <td>
                            <strong style={{ fontSize: '0.9rem' }}>{item.overall_score ?? '—'}</strong> / 100
                          </td>
                          <td>{item.accuracy_score ? `${item.accuracy_score}/5` : '—'}</td>
                          <td>{item.relevance_score ? `${item.relevance_score}/5` : '—'}</td>
                          <td>{item.completeness_score ? `${item.completeness_score}/5` : '—'}</td>
                          <td>
                            <span style={{ fontWeight: 700, fontSize: '0.78rem', color: halColor }}>
                              {halRisk}
                            </span>
                          </td>
                          <td>
                            <button
                              type="button"
                              className="btn-secondary"
                              style={{ padding: '4px 8px', fontSize: '0.74rem' }}
                              onClick={(e) => {
                                e.stopPropagation();
                                if (onSelectSubmission) onSelectSubmission(item.submission_id);
                              }}
                            >
                              <Eye size={12} />
                              <span>View</span>
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>

                {/* Pagination Controls */}
                {totalPages > 1 && (
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      marginTop: '14px',
                      paddingTop: '12px',
                      borderTop: '1px solid var(--border-subtle)',
                      fontSize: '0.8rem',
                    }}
                  >
                    <span style={{ color: 'var(--text-muted)' }}>
                      Page {currentPage} of {totalPages} ({filteredRecords.length} records)
                    </span>
                    <div style={{ display: 'flex', gap: '6px' }}>
                      <button
                        type="button"
                        className="btn-secondary"
                        style={{ padding: '4px 10px', fontSize: '0.76rem' }}
                        disabled={currentPage === 1}
                        onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                      >
                        Previous
                      </button>
                      <button
                        type="button"
                        className="btn-secondary"
                        style={{ padding: '4px 10px', fontSize: '0.76rem' }}
                        disabled={currentPage >= totalPages}
                        onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                      >
                        Next
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
