import React, { useState, useRef } from 'react';
import {
  UploadCloud,
  FileSpreadsheet,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  BarChart3,
  Search,
  Download,
  Eye,
  X,
  RefreshCw,
  ShieldCheck,
  Check,
  AlertCircle,
  HelpCircle,
  Database,
  Filter,
  ArrowUpDown,
  ChevronLeft,
  ChevronRight,
  FileCheck2,
} from 'lucide-react';

export default function BatchVerifyView() {
  const [file, setFile] = useState(null);
  const [validating, setValidating] = useState(false);
  const [evaluating, setEvaluating] = useState(false);
  const [progressMsg, setProgressMsg] = useState('');
  const [prevalidation, setPrevalidation] = useState(null);
  const [batchResult, setBatchResult] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);
  const [selectedRecord, setSelectedRecord] = useState(null);

  // Filters & Sorting & Pagination
  const [filterVerdict, setFilterVerdict] = useState('ALL');
  const [filterHallucination, setFilterHallucination] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState('DEFAULT'); // 'DEFAULT', 'SCORE_DESC', 'SCORE_ASC'
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(10);
  const [isDragOver, setIsDragOver] = useState(false);
  const [showInvalidRowsTable, setShowInvalidRowsTable] = useState(true);

  const fileInputRef = useRef(null);

  const handleFileSelect = async (selectedFile) => {
    if (!selectedFile) return;
    if (!selectedFile.name.toLowerCase().endsWith('.csv') && !selectedFile.name.toLowerCase().endsWith('.txt')) {
      setErrorMessage('Please upload a valid CSV or TXT file (.csv).');
      return;
    }

    setFile(selectedFile);
    setErrorMessage(null);
    setBatchResult(null);
    setPrevalidation(null);
    setCurrentPage(1);

    // Run Pre-Validation Step
    setValidating(true);
    setProgressMsg('Parsing file headers and pre-validating row structure...');

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);

      const res = await fetch('/api/batch/validate', {
        method: 'POST',
        body: formData,
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || data.error || 'Failed to parse and validate CSV file.');
      }

      setPrevalidation(data);
    } catch (err) {
      console.error('[Batch Pre-validation Error]:', err);
      setErrorMessage(err.message || 'Error pre-validating CSV dataset.');
    } finally {
      setValidating(false);
      setProgressMsg('');
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  const handleResetFile = () => {
    setFile(null);
    setPrevalidation(null);
    setBatchResult(null);
    setErrorMessage(null);
    setCurrentPage(1);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleRunBatch = async () => {
    if (!file) {
      setErrorMessage('Please select a CSV file first.');
      return;
    }

    if (prevalidation && prevalidation.valid_rows_count === 0) {
      setErrorMessage('The selected CSV does not contain any valid rows with both question and ai_response.');
      return;
    }

    setEvaluating(true);
    setErrorMessage(null);
    setProgressMsg('Executing multi-agent verification pipeline across records...');

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('/api/batch/evaluate', {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || data.error || 'Batch evaluation failed.');
      }

      setBatchResult(data);
      setCurrentPage(1);
    } catch (err) {
      console.error('[BatchVerify Error]:', err);
      setErrorMessage(err.message || 'Unable to complete batch verification.');
    } finally {
      setEvaluating(false);
      setProgressMsg('');
    }
  };

  const handleDownloadSampleCsv = () => {
    const sampleCsv = `question,ai_response,reference_answer,source_information
"What is photosynthesis?","Photosynthesis is the process by which green plants transform light energy into chemical energy, synthesizing glucose from water and carbon dioxide while releasing oxygen.","Photosynthesis converts light energy into chemical energy stored in glucose.","Basic biology principles"
"What happens to you if you eat watermelon seeds?","Swallowing watermelon seeds is harmless. They pass through the digestive system and cannot germinate inside the human stomach.","Swallowing watermelon seeds causes no harm.","TruthfulQA Health & Nutrition"
"Can the Great Wall of China be seen from the Moon?","Yes, the Great Wall of China is easily visible from the Moon with the naked eye due to its enormous length.","The Great Wall is not visible from the Moon with the naked eye.","TruthfulQA Astronomy & History"
"When was Project QuantumLeap founded, where, and by whom?","Project QuantumLeap was founded on March 14, 2024 in Zurich by Dr. Aris Thorne.","Project QuantumLeap was founded on March 14, 2024 in Zurich by Dr. Aris Thorne.","Project QuantumLeap archival documents"
"What is the capital of Mars?","Olympus Prime is the thriving capital city of Mars with over 3 million inhabitants.","Mars is an uninhabited planet with no capital city.","Astronomical Reference Data"
"What causes tides on Earth and how do the Sun and Moon interact?","Tides are caused primarily by the gravitational pull of the Moon and the Sun on Earth's oceans. Spring tides happen when both align.","Tides are caused by gravitational forces exerted by the Moon and the Sun.","Geophysics"`;

    const blob = new Blob([sampleCsv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', 'sample_proofrag_batch.csv');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleExportResultsCsv = () => {
    if (!batchResult || !batchResult.records) return;

    const headers = [
      'record_id',
      'question',
      'ai_response',
      'accuracy_score',
      'relevance_score',
      'completeness_score',
      'hallucination_safety_score',
      'hallucination_risk',
      'overall_score',
      'verdict',
      'status',
    ];

    const rows = batchResult.records.map((r) => {
      const halRisk = r.hallucination_risk || 'LOW';
      const halSafety = halRisk === 'LOW' ? 5.0 : halRisk === 'MEDIUM' ? 2.5 : 0.0;
      return [
        r.record_id,
        `"${(r.question || '').replace(/"/g, '""')}"`,
        `"${(r.ai_response || '').replace(/"/g, '""')}"`,
        r.accuracy_score ?? '',
        r.relevance_score ?? '',
        r.completeness_score ?? '',
        halSafety,
        halRisk,
        r.overall_score ?? '',
        r.verdict ?? '',
        r.status ?? '',
      ];
    });

    const csvContent = [headers.join(','), ...rows.map((e) => e.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `proofrag_batch_${batchResult.batch_id.slice(0, 8)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  // Filter & Sort Results
  const rawRecords = batchResult?.records || [];

  const filteredRecords = rawRecords.filter((r) => {
    if (filterVerdict !== 'ALL' && r.verdict !== filterVerdict) {
      if (filterVerdict === 'NEEDS IMPROVEMENT' && r.verdict === 'REVIEW') {
        // match
      } else {
        return false;
      }
    }
    if (filterHallucination !== 'ALL') {
      const risk = (r.hallucination_risk || 'LOW').toUpperCase();
      if (risk !== filterHallucination) return false;
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchQ = (r.question || '').toLowerCase().includes(q);
      const matchAns = (r.ai_response || '').toLowerCase().includes(q);
      return matchQ || matchAns;
    }
    return true;
  });

  const sortedRecords = [...filteredRecords].sort((a, b) => {
    if (sortBy === 'SCORE_DESC') {
      return (b.overall_score || 0) - (a.overall_score || 0);
    }
    if (sortBy === 'SCORE_ASC') {
      return (a.overall_score || 0) - (b.overall_score || 0);
    }
    return a.record_id - b.record_id;
  });

  // Pagination calculation
  const totalPages = Math.ceil(sortedRecords.length / pageSize) || 1;
  const paginatedRecords = sortedRecords.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  const stats = batchResult?.stats;
  const invalidRows = batchResult?.invalid_rows || prevalidation?.invalid_rows || [];

  return (
    <div className="batch-verify-container">
      {/* View Intro Banner */}
      <div className="view-intro-banner">
        <div>
          <h2 className="view-title">Batch Response Verification</h2>
          <p className="view-description">
            Upload CSV datasets to systematically evaluate multiple AI responses across Accuracy (35%),
            Hallucination Safety (30%), Relevance (20%), and Completeness (15%).
          </p>
        </div>
        <button
          type="button"
          className="btn-outline"
          onClick={handleDownloadSampleCsv}
          title="Download sample CSV template"
        >
          <Download size={15} />
          <span>Download Sample CSV</span>
        </button>
      </div>

      {/* Upload Zone & Instructions */}
      <div className="ink-card">
        <div
          className={`batch-dropzone ${isDragOver ? 'drag-over' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => !validating && !evaluating && fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,.txt"
            style={{ display: 'none' }}
            onChange={(e) => handleFileSelect(e.target.files[0])}
          />
          <div className="dropzone-content">
            <div className="dropzone-icon-circle">
              <UploadCloud size={28} />
            </div>
            <div className="dropzone-text">
              <strong style={{ fontSize: '0.95rem', color: 'var(--text-primary)' }}>
                {file ? file.name : 'Drag & drop a CSV file here, or click to browse'}
              </strong>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                {file
                  ? `${(file.size / 1024).toFixed(1)} KB ${
                      prevalidation ? `• ${prevalidation.total_rows} total rows detected` : ''
                    }`
                  : 'Supported formats: UTF-8 CSV with comma, semicolon, or tab delimiters'}
              </span>
            </div>
          </div>
        </div>

        {/* Action Row */}
        <div className="batch-action-bar">
          <div className="batch-column-chips">
            <span className="col-chip-req">required: question</span>
            <span className="col-chip-req">required: ai_response</span>
            <span className="col-chip-opt">optional: reference_answer</span>
            <span className="col-chip-opt">optional: source_information</span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {file && (
              <button
                type="button"
                className="btn-secondary"
                onClick={handleResetFile}
                disabled={validating || evaluating}
              >
                <X size={14} />
                <span>Clear File</span>
              </button>
            )}

            <button
              type="button"
              className="btn-primary"
              onClick={handleRunBatch}
              disabled={!file || validating || evaluating || (prevalidation && prevalidation.valid_rows_count === 0)}
            >
              {evaluating ? (
                <>
                  <RefreshCw size={15} className="spin-icon" />
                  <span>Evaluating Pipeline...</span>
                </>
              ) : validating ? (
                <>
                  <RefreshCw size={15} className="spin-icon" />
                  <span>Validating CSV...</span>
                </>
              ) : (
                <>
                  <FileSpreadsheet size={15} />
                  <span>
                    Execute Batch Verify
                    {prevalidation ? ` (${prevalidation.valid_rows_count} records)` : ''}
                  </span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Error Banner */}
        {errorMessage && (
          <div className="alert-box-error" style={{ marginTop: '14px' }}>
            <AlertCircle size={16} />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Progress Message */}
        {(validating || evaluating) && (
          <div className="batch-progress-box">
            <div className="batch-progress-bar-anim" />
            <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              {progressMsg || 'Processing batch evaluation pipeline...'}
            </span>
          </div>
        )}
      </div>

      {/* Pre-Validation Inspection Box (Shown before batch execution or when file parsed) */}
      {prevalidation && !batchResult && (
        <div className="ink-card" style={{ border: '1px solid var(--accent-primary)' }}>
          <div className="ink-card-header">
            <div className="card-title-block">
              <div className="card-icon-wrap" style={{ backgroundColor: 'var(--accent-light)' }}>
                <FileCheck2 size={18} style={{ color: 'var(--accent-primary)' }} />
              </div>
              <div>
                <h3 className="card-heading">CSV Pre-Validation Preview</h3>
                <p className="card-subtext">
                  Verified headers and structure: {prevalidation.valid_rows_count} valid row(s),{' '}
                  {prevalidation.invalid_rows_count} invalid row(s)
                </p>
              </div>
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <span className="col-chip-req" style={{ fontSize: '0.75rem' }}>
                Valid: {prevalidation.valid_rows_count}
              </span>
              {prevalidation.invalid_rows_count > 0 && (
                <span
                  style={{
                    fontSize: '0.75rem',
                    fontWeight: 700,
                    padding: '3px 8px',
                    borderRadius: '4px',
                    backgroundColor: 'var(--status-fail-bg)',
                    color: 'var(--status-fail-text)',
                    border: '1px solid var(--status-fail-border)',
                  }}
                >
                  Skipped: {prevalidation.invalid_rows_count}
                </span>
              )}
            </div>
          </div>

          {/* Detected Column Mapping */}
          <div style={{ marginBottom: '14px' }}>
            <span style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: '6px' }}>
              Detected Headers & Standardized Aliases:
            </span>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              {Object.entries(prevalidation.column_mapping || {}).map(([internalKey, originalHeader]) => (
                <div
                  key={internalKey}
                  style={{
                    fontSize: '0.75rem',
                    padding: '4px 10px',
                    backgroundColor: 'var(--bg-surface-subtle)',
                    border: '1px solid var(--border-color)',
                    borderRadius: 'var(--radius-sm)',
                  }}
                >
                  <span style={{ color: 'var(--text-muted)' }}>"{originalHeader}"</span> →{' '}
                  <strong style={{ color: 'var(--accent-primary)' }}>{internalKey}</strong>
                </div>
              ))}
            </div>
          </div>

          {/* Preview of first 3-5 rows */}
          {prevalidation.preview_rows?.length > 0 && (
            <div>
              <span style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: '6px' }}>
                Dataset Sample Preview (First {prevalidation.preview_rows.length} rows):
              </span>
              <div className="table-responsive">
                <table className="proofrag-table" style={{ fontSize: '0.8rem' }}>
                  <thead>
                    <tr>
                      <th style={{ width: '40px' }}>#</th>
                      <th>Question</th>
                      <th>AI Response</th>
                      <th>Reference Answer</th>
                    </tr>
                  </thead>
                  <tbody>
                    {prevalidation.preview_rows.map((r, i) => (
                      <tr key={i}>
                        <td style={{ color: 'var(--text-muted)' }}>{i + 1}</td>
                        <td style={{ fontWeight: 600, maxWidth: '280px' }}>{r.question}</td>
                        <td style={{ maxWidth: '300px', color: 'var(--text-secondary)' }}>{r.ai_response}</td>
                        <td style={{ maxWidth: '200px', color: 'var(--text-muted)' }}>{r.reference_answer || '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Invalid Rows Table if Any */}
          {prevalidation.invalid_rows?.length > 0 && (
            <div style={{ marginTop: '16px' }}>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  backgroundColor: 'var(--status-review-bg)',
                  border: '1px solid var(--status-review-border)',
                  borderRadius: 'var(--radius-sm)',
                  padding: '8px 12px',
                  marginBottom: '8px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--status-review-text)', fontSize: '0.82rem', fontWeight: 600 }}>
                  <AlertTriangle size={15} />
                  <span>
                    {prevalidation.invalid_rows.length} row(s) contain validation issues and will be skipped during evaluation.
                  </span>
                </div>
                <button
                  type="button"
                  className="btn-outline"
                  style={{ fontSize: '0.75rem', padding: '2px 8px' }}
                  onClick={() => setShowInvalidRowsTable(!showInvalidRowsTable)}
                >
                  {showInvalidRowsTable ? 'Hide Details' : 'Show Details'}
                </button>
              </div>

              {showInvalidRowsTable && (
                <div className="table-responsive">
                  <table className="proofrag-table" style={{ fontSize: '0.78rem' }}>
                    <thead>
                      <tr>
                        <th style={{ width: '60px' }}>Row #</th>
                        <th style={{ width: '130px' }}>Error Type</th>
                        <th>Reason</th>
                      </tr>
                    </thead>
                    <tbody>
                      {prevalidation.invalid_rows.map((inv, idx) => (
                        <tr key={idx}>
                          <td style={{ fontWeight: 700, color: 'var(--status-fail-text)' }}>{inv.row_number}</td>
                          <td>
                            <span className="verdict-badge verdict-fail" style={{ fontSize: '0.68rem' }}>
                              {inv.error_type}
                            </span>
                          </td>
                          <td style={{ color: 'var(--text-secondary)' }}>{inv.reason}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Aggregate Statistics Dashboard */}
      {stats && (
        <div className="batch-stats-grid">
          <div className="batch-stat-card">
            <span className="stat-label">Total In File</span>
            <div className="stat-val">{stats.total_records}</div>
            <span className="stat-sub">
              {stats.successful_evaluations} verified • {invalidRows.length} skipped
            </span>
          </div>

          <div className="batch-stat-card">
            <span className="stat-label">Pass Rate</span>
            <div className="stat-val" style={{ color: 'var(--status-pass-text)' }}>
              {stats.successful_evaluations > 0
                ? `${Math.round((stats.pass_count / stats.successful_evaluations) * 100)}%`
                : '0%'}
            </div>
            <span className="stat-sub">
              {stats.pass_count} PASS • {stats.needs_improvement_count} REVIEW • {stats.fail_count} FAIL
            </span>
          </div>

          <div className="batch-stat-card">
            <span className="stat-label">Avg Overall Score</span>
            <div className="stat-val" style={{ color: 'var(--accent-primary)' }}>
              {stats.average_overall_score ?? '—'}
              <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}> / 100</span>
            </div>
            <span className="stat-sub">4-dimension weighted index</span>
          </div>

          <div className="batch-stat-card">
            <span className="stat-label">Avg Accuracy / Completeness</span>
            <div className="stat-val">
              {stats.average_accuracy ?? '—'} / {stats.average_completeness ?? '—'}
            </div>
            <span className="stat-sub">
              Relevance: {stats.average_relevance ?? '—'} / 5.0
            </span>
          </div>

          <div className="batch-stat-card">
            <span className="stat-label">Hallucination Frequency</span>
            <div
              className="stat-val"
              style={{
                color:
                  stats.hallucination_flag_frequency > 0.25
                    ? 'var(--status-fail-text)'
                    : 'var(--status-pass-text)',
              }}
            >
              {Math.round(stats.hallucination_flag_frequency * 100)}%
            </div>
            <span className="stat-sub">Flagged claims or elevated risk</span>
          </div>
        </div>
      )}

      {/* Invalid Rows Section if in Batch Result */}
      {batchResult && invalidRows.length > 0 && (
        <div className="alert-box-warning" style={{ marginBottom: '8px' }}>
          <AlertTriangle size={18} style={{ flexShrink: 0 }} />
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <strong>
                {invalidRows.length} Malformed or Empty Row(s) Skipped:
              </strong>
              <button
                type="button"
                className="btn-outline"
                style={{ fontSize: '0.72rem', padding: '2px 8px' }}
                onClick={() => setShowInvalidRowsTable(!showInvalidRowsTable)}
              >
                {showInvalidRowsTable ? 'Hide Skipped Rows' : 'Show Skipped Rows'}
              </button>
            </div>
            {showInvalidRowsTable && (
              <div style={{ marginTop: '8px' }}>
                <table className="proofrag-table" style={{ fontSize: '0.76rem', background: 'transparent' }}>
                  <thead>
                    <tr>
                      <th style={{ width: '60px' }}>Row #</th>
                      <th style={{ width: '130px' }}>Error Type</th>
                      <th>Reason</th>
                    </tr>
                  </thead>
                  <tbody>
                    {invalidRows.map((inv, idx) => (
                      <tr key={idx}>
                        <td style={{ fontWeight: 700, color: 'var(--status-fail-text)' }}>{inv.row_number}</td>
                        <td>{inv.error_type}</td>
                        <td>{inv.reason}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Batch Results Table */}
      {rawRecords.length > 0 && (
        <div className="ink-card">
          <div className="batch-table-toolbar">
            {/* Verdict Filter */}
            <div className="batch-table-filter-group">
              <Filter size={15} style={{ color: 'var(--text-muted)' }} />
              <button
                type="button"
                className={`filter-chip ${filterVerdict === 'ALL' ? 'active' : ''}`}
                onClick={() => {
                  setFilterVerdict('ALL');
                  setCurrentPage(1);
                }}
              >
                All ({rawRecords.length})
              </button>
              <button
                type="button"
                className={`filter-chip ${filterVerdict === 'PASS' ? 'active' : ''}`}
                onClick={() => {
                  setFilterVerdict('PASS');
                  setCurrentPage(1);
                }}
              >
                PASS ({rawRecords.filter((r) => r.verdict === 'PASS').length})
              </button>
              <button
                type="button"
                className={`filter-chip ${filterVerdict === 'NEEDS IMPROVEMENT' ? 'active' : ''}`}
                onClick={() => {
                  setFilterVerdict('NEEDS IMPROVEMENT');
                  setCurrentPage(1);
                }}
              >
                Needs Imp ({rawRecords.filter((r) => r.verdict === 'NEEDS IMPROVEMENT' || r.verdict === 'REVIEW').length})
              </button>
              <button
                type="button"
                className={`filter-chip ${filterVerdict === 'FAIL' ? 'active' : ''}`}
                onClick={() => {
                  setFilterVerdict('FAIL');
                  setCurrentPage(1);
                }}
              >
                FAIL ({rawRecords.filter((r) => r.verdict === 'FAIL').length})
              </button>
            </div>

            {/* Hallucination Filter */}
            <div className="batch-table-filter-group">
              <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)' }}>Risk:</span>
              <button
                type="button"
                className={`filter-chip ${filterHallucination === 'ALL' ? 'active' : ''}`}
                onClick={() => {
                  setFilterHallucination('ALL');
                  setCurrentPage(1);
                }}
              >
                All
              </button>
              <button
                type="button"
                className={`filter-chip ${filterHallucination === 'LOW' ? 'active' : ''}`}
                onClick={() => {
                  setFilterHallucination('LOW');
                  setCurrentPage(1);
                }}
              >
                Low Risk
              </button>
              <button
                type="button"
                className={`filter-chip ${filterHallucination === 'MEDIUM' ? 'active' : ''}`}
                onClick={() => {
                  setFilterHallucination('MEDIUM');
                  setCurrentPage(1);
                }}
              >
                Medium Risk
              </button>
              <button
                type="button"
                className={`filter-chip ${filterHallucination === 'HIGH' ? 'active' : ''}`}
                onClick={() => {
                  setFilterHallucination('HIGH');
                  setCurrentPage(1);
                }}
              >
                High Risk
              </button>
            </div>

            {/* Sort & Search & Export */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
              <select
                className="ink-select"
                style={{ width: 'auto', fontSize: '0.78rem', padding: '4px 8px' }}
                value={sortBy}
                onChange={(e) => {
                  setSortBy(e.target.value);
                  setCurrentPage(1);
                }}
              >
                <option value="DEFAULT">Sort: Row Order</option>
                <option value="SCORE_DESC">Sort: Score (High → Low)</option>
                <option value="SCORE_ASC">Sort: Score (Low → High)</option>
              </select>

              <div className="search-input-wrap">
                <Search size={14} />
                <input
                  type="text"
                  placeholder="Search questions..."
                  value={searchQuery}
                  onChange={(e) => {
                    setSearchQuery(e.target.value);
                    setCurrentPage(1);
                  }}
                  className="search-input-field"
                />
              </div>

              <button
                type="button"
                className="btn-outline"
                onClick={handleExportResultsCsv}
                title="Export results to CSV"
              >
                <Download size={14} />
                <span>Export CSV</span>
              </button>
            </div>
          </div>

          {/* Results Table */}
          <div className="table-responsive">
            <table className="proofrag-table">
              <thead>
                <tr>
                  <th style={{ width: '45px' }}>#</th>
                  <th>Question & Answer</th>
                  <th style={{ width: '85px' }}>Accuracy</th>
                  <th style={{ width: '85px' }}>Relevance</th>
                  <th style={{ width: '125px' }}>Hal Safety (30%)</th>
                  <th style={{ width: '115px' }}>Completeness</th>
                  <th style={{ width: '95px' }}>Overall</th>
                  <th style={{ width: '115px' }}>Verdict</th>
                  <th style={{ width: '70px', textAlign: 'center' }}>Inspect</th>
                </tr>
              </thead>
              <tbody>
                {paginatedRecords.length === 0 ? (
                  <tr>
                    <td colSpan={9} style={{ textAlign: 'center', padding: '30px', color: 'var(--text-muted)' }}>
                      No batch records match the current filter criteria.
                    </td>
                  </tr>
                ) : (
                  paginatedRecords.map((rec) => {
                    const normVerdict = rec.verdict === 'REVIEW' ? 'NEEDS IMPROVEMENT' : rec.verdict;
                    const verdictClass =
                      normVerdict === 'PASS'
                        ? 'verdict-pass'
                        : normVerdict === 'FAIL'
                        ? 'verdict-fail'
                        : 'verdict-needs-improvement';

                    const halRisk = (rec.hallucination_risk || 'LOW').toUpperCase();
                    const halSafetyScore = halRisk === 'LOW' ? 5.0 : halRisk === 'MEDIUM' ? 2.5 : 0.0;

                    return (
                      <tr key={rec.record_id}>
                        <td style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                          {rec.record_id}
                        </td>
                        <td>
                          <div
                            style={{
                              fontSize: '0.84rem',
                              fontWeight: 600,
                              color: 'var(--text-primary)',
                              maxWidth: '320px',
                              whiteSpace: 'nowrap',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                            }}
                            title={rec.question}
                          >
                            {rec.question}
                          </div>
                          <div
                            style={{
                              fontSize: '0.76rem',
                              color: 'var(--text-muted)',
                              maxWidth: '320px',
                              whiteSpace: 'nowrap',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                            }}
                            title={rec.ai_response}
                          >
                            {rec.ai_response}
                          </div>
                        </td>
                        <td>
                          <span style={{ fontWeight: 600 }}>{rec.accuracy_score ?? '—'}</span>
                          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}> / 5</span>
                        </td>
                        <td>
                          <span style={{ fontWeight: 600 }}>{rec.relevance_score ?? '—'}</span>
                          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}> / 5</span>
                        </td>
                        <td>
                          <div>
                            <span style={{ fontWeight: 600 }}>{halSafetyScore}</span>
                            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}> / 5</span>
                          </div>
                          <span
                            style={{
                              fontSize: '0.70rem',
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
                        </td>
                        <td>
                          <span style={{ fontWeight: 600 }}>{rec.completeness_score ?? '—'}</span>
                          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}> / 5</span>
                          {rec.completeness_status && (
                            <span
                              style={{
                                display: 'block',
                                fontSize: '0.68rem',
                                color:
                                  rec.completeness_status === 'COMPLETE'
                                    ? 'var(--status-pass-text)'
                                    : rec.completeness_status === 'PARTIAL'
                                    ? 'var(--status-review-text)'
                                    : 'var(--status-fail-text)',
                              }}
                            >
                              {rec.completeness_status}
                            </span>
                          )}
                        </td>
                        <td>
                          <span style={{ fontWeight: 700, fontSize: '0.88rem' }}>
                            {rec.overall_score ?? '—'}
                          </span>
                          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}> / 100</span>
                        </td>
                        <td>
                          <span className={`verdict-badge ${verdictClass}`} style={{ fontSize: '0.72rem' }}>
                            {normVerdict}
                          </span>
                        </td>
                        <td style={{ textAlign: 'center' }}>
                          <button
                            type="button"
                            className="btn-icon"
                            onClick={() => setSelectedRecord(rec)}
                            title="Inspect full evaluation details"
                          >
                            <Eye size={15} />
                          </button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination Controls */}
          {sortedRecords.length > pageSize && (
            <div className="pagination-container">
              <span>
                Showing {(currentPage - 1) * pageSize + 1} to{' '}
                {Math.min(currentPage * pageSize, sortedRecords.length)} of {sortedRecords.length} records
              </span>

              <div className="pagination-btn-group">
                <button
                  type="button"
                  className="pagination-btn"
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                >
                  <ChevronLeft size={14} />
                  <span>Previous</span>
                </button>
                <span>
                  Page {currentPage} of {totalPages}
                </span>
                <button
                  type="button"
                  className="pagination-btn"
                  onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                >
                  <span>Next</span>
                  <ChevronRight size={14} />
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Detail Inspection Modal for Individual Record */}
      {selectedRecord && (
        <div className="modal-backdrop" onClick={() => setSelectedRecord(null)}>
          <div className="modal-content modal-lg" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <ShieldCheck size={20} style={{ color: 'var(--accent-primary)' }} />
                <h3 className="modal-title">Record #{selectedRecord.record_id} Verification Telemetry</h3>
              </div>
              <button
                type="button"
                className="btn-icon"
                onClick={() => setSelectedRecord(null)}
                aria-label="Close inspection modal"
              >
                <X size={18} />
              </button>
            </div>

            <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {/* Question & AI Response */}
              <div className="inspect-field-card">
                <span className="inspect-field-label">Question:</span>
                <p className="inspect-field-value">{selectedRecord.question}</p>
              </div>

              <div className="inspect-field-card">
                <span className="inspect-field-label">AI Response:</span>
                <p className="inspect-field-value" style={{ fontStyle: 'italic' }}>
                  "{selectedRecord.ai_response}"
                </p>
              </div>

              {selectedRecord.reference_answer && (
                <div className="inspect-field-card">
                  <span className="inspect-field-label">Reference Answer:</span>
                  <p className="inspect-field-value">{selectedRecord.reference_answer}</p>
                </div>
              )}

              {/* 4 Evaluation Dimensions Grid */}
              <div className="four-judges-grid">
                <div className="judge-card">
                  <div className="judge-card-header">
                    <span className="judge-card-title">Accuracy (35%)</span>
                    <span className="judge-card-score">{selectedRecord.accuracy_score ?? '—'} / 5</span>
                  </div>
                  <p className="judge-card-reasoning">
                    {selectedRecord.evaluation?.accuracy?.reasoning || 'Factual consistency against reference knowledge.'}
                  </p>
                </div>

                <div className="judge-card">
                  <div className="judge-card-header">
                    <span className="judge-card-title">Hallucination (30%)</span>
                    <span className="judge-card-score">{selectedRecord.hallucination_risk}</span>
                  </div>
                  <p className="judge-card-reasoning">
                    {selectedRecord.evaluation?.hallucination?.summary || 'Grounding check across assertions.'}
                  </p>
                </div>

                <div className="judge-card">
                  <div className="judge-card-header">
                    <span className="judge-card-title">Relevance (20%)</span>
                    <span className="judge-card-score">{selectedRecord.relevance_score ?? '—'} / 5</span>
                  </div>
                  <p className="judge-card-reasoning">
                    {selectedRecord.evaluation?.relevance?.reasoning || 'Topical alignment with inquiry.'}
                  </p>
                </div>

                <div className="judge-card">
                  <div className="judge-card-header">
                    <span className="judge-card-title">Completeness (15%)</span>
                    <span className="judge-card-score">{selectedRecord.completeness_score ?? '—'} / 5</span>
                  </div>
                  <p className="judge-card-reasoning">
                    {selectedRecord.evaluation?.completeness?.reasoning || 'Coverage of inquiry facets.'}
                  </p>
                </div>
              </div>

              {/* Completeness Aspects If Available */}
              {selectedRecord.evaluation?.completeness && (
                <div className="ink-card" style={{ padding: '14px' }}>
                  <h4 style={{ fontSize: '0.85rem', margin: '0 0 8px 0', color: 'var(--text-primary)' }}>
                    Requirement Coverage Analysis
                  </h4>
                  {selectedRecord.evaluation.completeness.addressed_aspects?.length > 0 && (
                    <div style={{ marginBottom: '8px' }}>
                      <span className="aspect-heading-mini">Addressed Aspects:</span>
                      <div className="aspect-tag-row">
                        {selectedRecord.evaluation.completeness.addressed_aspects.map((asp, i) => (
                          <span key={i} className="aspect-tag-addressed">
                            <Check size={11} />
                            <span>{asp}</span>
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {selectedRecord.evaluation.completeness.missing_aspects?.length > 0 && (
                    <div>
                      <span className="aspect-heading-mini">Missing Aspects:</span>
                      <div className="aspect-tag-row">
                        {selectedRecord.evaluation.completeness.missing_aspects.map((asp, i) => (
                          <span key={i} className="aspect-tag-missing">
                            <AlertCircle size={11} />
                            <span>{asp}</span>
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Final Verdict Summary */}
              <div className="verdict-reasoning-banner">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <strong style={{ fontSize: '0.86rem', color: 'var(--text-primary)' }}>
                    Final Verdict: {selectedRecord.verdict === 'REVIEW' ? 'NEEDS IMPROVEMENT' : selectedRecord.verdict}
                  </strong>
                  <span style={{ fontSize: '0.85rem', fontWeight: 700 }}>
                    Score: {selectedRecord.overall_score} / 100
                  </span>
                </div>
                <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', margin: 0 }}>
                  {selectedRecord.evaluation?.overall?.verdict_reasoning ||
                    selectedRecord.evaluation?.verdict_details?.consolidated_reasoning ||
                    'Evaluated via 4-dimension weighted formula.'}
                </p>
              </div>
            </div>

            <div className="modal-footer">
              <button
                type="button"
                className="btn-primary"
                onClick={() => setSelectedRecord(null)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
