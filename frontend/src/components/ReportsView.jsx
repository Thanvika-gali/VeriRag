import React from 'react';
import { FileText, Download, Printer, ArrowRight, ShieldCheck } from 'lucide-react';

export default function ReportsView({ currentEvaluation, historyList = [], onSelectSubmission, onNewEvaluation }) {
  const evalItem = currentEvaluation || (historyList.length > 0 ? historyList[0] : null);

  const handleDownloadJSON = () => {
    if (!evalItem) return;
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(evalItem, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute("download", `verirag_report_${evalItem.submission_id || 'eval'}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  const handlePrint = () => {
    window.print();
  };

  if (!evalItem) {
    return (
      <div className="ink-card empty-state-box">
        <FileText size={40} className="empty-icon" />
        <h3 className="empty-heading">No evaluation selected for report</h3>
        <p className="empty-sub">
          Evaluate an AI response or select a past submission from History to generate and export an executive verification report.
        </p>
        <button
          type="button"
          className="btn-primary"
          style={{ marginTop: '12px' }}
          onClick={onNewEvaluation}
        >
          Evaluate a Response
        </button>
      </div>
    );
  }

  const accuracy = evalItem.accuracy || {};
  const relevance = evalItem.relevance || {};
  const hallucination = evalItem.hallucination || {};
  const evidence = evalItem.retrieved_evidence || [];

  return (
    <div className="reports-container">
      {/* Top Action Bar */}
      <div className="ink-card" style={{ padding: '16px 24px', marginBottom: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>
              Report Document
            </span>
            <div style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              PROOFRAG Evaluation Summary — ID: {evalItem.submission_id ? evalItem.submission_id.slice(0, 8) : 'Current'}
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <button
              type="button"
              className="btn-secondary"
              onClick={handleDownloadJSON}
            >
              <Download size={14} />
              <span>Export JSON</span>
            </button>
            <button
              type="button"
              className="btn-primary"
              onClick={handlePrint}
            >
              <Printer size={14} />
              <span>Print / Save PDF</span>
            </button>
          </div>
        </div>
      </div>

      {/* Printable Report Sheet */}
      <div
        className="ink-card"
        style={{
          backgroundColor: 'var(--bg-surface)',
          padding: '36px',
          border: '1px solid var(--border-color)',
        }}
      >
        <div style={{ borderBottom: '2px solid var(--text-primary)', paddingBottom: '16px', marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h1 style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--text-primary)' }}>
              VERIRAG AUDIT REPORT
            </h1>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
              AI Response Validation & Evidence Platform
            </p>
          </div>
          <div style={{ textAlign: 'right', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            <div>Date: {evalItem.created_at ? evalItem.created_at.slice(0, 10) : 'Recent'}</div>
            <div>Evaluation ID: {evalItem.submission_id || 'N/A'}</div>
          </div>
        </div>

        {/* Executive Verdict Block */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
            gap: '16px',
            backgroundColor: 'var(--bg-surface-subtle)',
            padding: '20px',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--border-subtle)',
            marginBottom: '28px',
          }}
        >
          <div>
            <span style={{ fontSize: '0.72rem', textTransform: 'uppercase', fontWeight: 700, color: 'var(--text-muted)' }}>
              Overall Score
            </span>
            <div style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--text-primary)' }}>
              {evalItem.overall_score || 0} / 100
            </div>
          </div>

          <div>
            <span style={{ fontSize: '0.72rem', textTransform: 'uppercase', fontWeight: 700, color: 'var(--text-muted)' }}>
              Final Verdict
            </span>
            <div style={{ fontSize: '1.3rem', fontWeight: 800, marginTop: '4px' }}>
              {evalItem.verdict || 'REVIEW'}
            </div>
          </div>

          <div>
            <span style={{ fontSize: '0.72rem', textTransform: 'uppercase', fontWeight: 700, color: 'var(--text-muted)' }}>
              Accuracy Score
            </span>
            <div style={{ fontSize: '1.3rem', fontWeight: 700, marginTop: '4px' }}>
              {accuracy.score || evalItem.accuracy_score || 0} / 5
            </div>
          </div>

          <div>
            <span style={{ fontSize: '0.72rem', textTransform: 'uppercase', fontWeight: 700, color: 'var(--text-muted)' }}>
              Relevance Score
            </span>
            <div style={{ fontSize: '1.3rem', fontWeight: 700, marginTop: '4px' }}>
              {relevance.score || evalItem.relevance_score || 0} / 5
            </div>
          </div>

          <div>
            <span style={{ fontSize: '0.72rem', textTransform: 'uppercase', fontWeight: 700, color: 'var(--text-muted)' }}>
              Hallucination Risk
            </span>
            <div style={{ fontSize: '1.3rem', fontWeight: 700, marginTop: '4px' }}>
              {hallucination.risk_level || evalItem.hallucination_risk || 'LOW'}
            </div>
          </div>
        </div>

        {/* Inquiry Content */}
        <div style={{ marginBottom: '24px' }}>
          <h3 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '8px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '4px' }}>
            Inquiry & Submitted Response
          </h3>
          <div style={{ marginBottom: '12px' }}>
            <span style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-muted)' }}>QUESTION:</span>
            <p style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-primary)', marginTop: '2px' }}>
              {evalItem.question}
            </p>
          </div>
          <div>
            <span style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-muted)' }}>AI ANSWER:</span>
            <p style={{ fontSize: '0.88rem', color: 'var(--text-primary)', marginTop: '2px', lineHeight: 1.45 }}>
              {evalItem.ai_response}
            </p>
          </div>
        </div>

        {/* Reasoning and Findings */}
        <div style={{ marginBottom: '24px' }}>
          <h3 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '8px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '4px' }}>
            Findings & Justifications
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.84rem' }}>
            <div><strong>Verdict Reasoning: </strong>{evalItem.verdict_reasoning || 'Based on multi-agent synthesis.'}</div>
            <div><strong>Accuracy Reasoning: </strong>{accuracy.reasoning || 'Evaluated against reference knowledge.'}</div>
            <div><strong>Relevance Reasoning: </strong>{relevance.reasoning || 'Evaluated against question intent.'}</div>
            <div><strong>Hallucination Summary: </strong>{hallucination.summary || 'Analyzed claim-by-claim.'}</div>
          </div>
        </div>

        {/* Evidence Sources */}
        <div>
          <h3 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '8px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '4px' }}>
            Retrieved Evidence ({evidence.length} sources)
          </h3>
          {evidence.length === 0 ? (
            <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>No reference evidence chunks logged.</p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {evidence.slice(0, 3).map((e, idx) => (
                <div key={idx} style={{ padding: '10px 14px', backgroundColor: 'var(--bg-surface-subtle)', borderRadius: 'var(--radius-sm)', fontSize: '0.82rem' }}>
                  <div style={{ fontWeight: 700, color: 'var(--text-primary)', marginBottom: '4px' }}>
                    #{idx + 1} [{e.dataset_name || 'Knowledge Base'}] — Match Strength: {Math.round((e.similarity_score || 0) * 100)}%
                  </div>
                  <div style={{ fontStyle: 'italic', color: 'var(--text-secondary)' }}>"{e.text}"</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
