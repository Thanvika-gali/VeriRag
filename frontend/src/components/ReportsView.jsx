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

  const accuracy = evalItem.accuracy || (evalItem.evaluation_result ? evalItem.evaluation_result.accuracy : {}) || {};
  const relevance = evalItem.relevance || (evalItem.evaluation_result ? evalItem.evaluation_result.relevance : {}) || {};
  const hallucination = evalItem.hallucination || (evalItem.evaluation_result ? evalItem.evaluation_result.hallucination : {}) || {};
  const completeness = evalItem.completeness || (evalItem.evaluation_result ? evalItem.evaluation_result.completeness : {}) || {};
  const evidence = evalItem.retrieved_evidence || (evalItem.evaluation_result ? evalItem.evaluation_result.retrieved_evidence : []) || [];
  const verdictDetails = evalItem.verdict_details || (evalItem.evaluation_result ? evalItem.evaluation_result.verdict_details : {}) || {};

  const majorStrengths = verdictDetails.major_strengths || [];
  const majorIssues = verdictDetails.major_issues || [];
  const criticalOverrideApplied = verdictDetails.critical_override_applied || evalItem.critical_override_applied || verdictDetails.critical_issues_detected;
  const criticalOverrideReason = verdictDetails.critical_override_reason || evalItem.critical_override_reason || '';
  const flaggedClaims = hallucination.flagged_claims || [];
  const missingAspects = completeness.missing_aspects || [];
  const addressedAspects = completeness.addressed_aspects || [];

  const accScore = accuracy.score !== undefined ? accuracy.score : (evalItem.accuracy_score ?? 0);
  const relScore = relevance.score !== undefined ? relevance.score : (evalItem.relevance_score ?? 0);
  const compScore = completeness.score !== undefined ? completeness.score : (evalItem.completeness_score ?? 0);
  const halRisk = hallucination.risk_level || evalItem.hallucination_risk || 'LOW';

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
              PROOFRAG AUDIT REPORT
            </h1>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
              Evidence-Grounded AI Response Verification & Evaluation Engine
            </p>
          </div>
          <div style={{ textAlign: 'right', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            <div>Date: {evalItem.created_at ? evalItem.created_at.slice(0, 10) : 'Recent'}</div>
            <div>Evaluation ID: {evalItem.submission_id || 'N/A'}</div>
          </div>
        </div>

        {/* Critical Override Alert if Triggered */}
        {criticalOverrideApplied && (
          <div
            style={{
              backgroundColor: 'var(--status-fail-bg)',
              border: '1px solid var(--status-fail-border)',
              borderRadius: 'var(--radius-sm)',
              padding: '12px 16px',
              marginBottom: '20px',
              color: 'var(--status-fail-text)',
            }}
          >
            <strong style={{ fontSize: '0.86rem', display: 'block', marginBottom: '2px' }}>
              CRITICAL OVERRIDE: TRIGGERED
            </strong>
            <span style={{ fontSize: '0.82rem' }}>
              {criticalOverrideReason || 'A critical issue (severe contradiction or low accuracy) forced a non-passing verdict.'}
            </span>
          </div>
        )}

        {/* Executive Verdict Block: All 4 M3 Dimensions */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
            gap: '14px',
            backgroundColor: 'var(--bg-surface-subtle)',
            padding: '20px',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--border-subtle)',
            marginBottom: '28px',
          }}
        >
          <div>
            <span style={{ fontSize: '0.7rem', textTransform: 'uppercase', fontWeight: 700, color: 'var(--text-muted)' }}>
              1. Accuracy (35%)
            </span>
            <div style={{ fontSize: '1.3rem', fontWeight: 700, marginTop: '4px' }}>
              {accScore} / 5
            </div>
          </div>

          <div>
            <span style={{ fontSize: '0.7rem', textTransform: 'uppercase', fontWeight: 700, color: 'var(--text-muted)' }}>
              2. Relevance (20%)
            </span>
            <div style={{ fontSize: '1.3rem', fontWeight: 700, marginTop: '4px' }}>
              {relScore} / 5
            </div>
          </div>

          <div>
            <span style={{ fontSize: '0.7rem', textTransform: 'uppercase', fontWeight: 700, color: 'var(--text-muted)' }}>
              3. Hallucination (30%)
            </span>
            <div
              style={{
                fontSize: '1.15rem',
                fontWeight: 700,
                marginTop: '4px',
                color:
                  halRisk === 'HIGH'
                    ? 'var(--status-fail-text)'
                    : halRisk === 'MEDIUM'
                    ? 'var(--status-review-text)'
                    : 'var(--status-pass-text)',
              }}
            >
              {halRisk} RISK
            </div>
          </div>

          <div>
            <span style={{ fontSize: '0.7rem', textTransform: 'uppercase', fontWeight: 700, color: 'var(--text-muted)' }}>
              4. Completeness (15%)
            </span>
            <div style={{ fontSize: '1.3rem', fontWeight: 700, marginTop: '4px' }}>
              {compScore} / 5
            </div>
          </div>

          <div style={{ borderLeft: '1px solid var(--border-subtle)', paddingLeft: '14px' }}>
            <span style={{ fontSize: '0.7rem', textTransform: 'uppercase', fontWeight: 700, color: 'var(--text-muted)' }}>
              Overall Score
            </span>
            <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--text-primary)', marginTop: '2px' }}>
              {evalItem.overall_score || 0} / 100
            </div>
          </div>

          <div>
            <span style={{ fontSize: '0.7rem', textTransform: 'uppercase', fontWeight: 700, color: 'var(--text-muted)' }}>
              Final Verdict
            </span>
            <div style={{ fontSize: '1.25rem', fontWeight: 800, marginTop: '4px' }}>
              {evalItem.verdict || 'NEEDS IMPROVEMENT'}
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

        {/* Major Strengths & Issues */}
        {(majorStrengths.length > 0 || majorIssues.length > 0) && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px', marginBottom: '24px' }}>
            <div style={{ padding: '14px', backgroundColor: 'var(--status-pass-bg)', border: '1px solid var(--status-pass-border)', borderRadius: 'var(--radius-sm)' }}>
              <strong style={{ fontSize: '0.82rem', color: 'var(--status-pass-text)', display: 'block', marginBottom: '6px' }}>
                Major Strengths
              </strong>
              {majorStrengths.length > 0 ? (
                <ul style={{ margin: '0 0 0 16px', fontSize: '0.82rem', color: 'var(--status-pass-text)' }}>
                  {majorStrengths.map((s, i) => (
                    <li key={i}>{s}</li>
                  ))}
                </ul>
              ) : (
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>None recorded.</span>
              )}
            </div>

            <div style={{ padding: '14px', backgroundColor: 'var(--status-fail-bg)', border: '1px solid var(--status-fail-border)', borderRadius: 'var(--radius-sm)' }}>
              <strong style={{ fontSize: '0.82rem', color: 'var(--status-fail-text)', display: 'block', marginBottom: '6px' }}>
                Major Issues & Critical Flags
              </strong>
              {majorIssues.length > 0 ? (
                <ul style={{ margin: '0 0 0 16px', fontSize: '0.82rem', color: 'var(--status-fail-text)' }}>
                  {majorIssues.map((issue, i) => (
                    <li key={i}>{issue}</li>
                  ))}
                </ul>
              ) : (
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>No critical issues detected.</span>
              )}
            </div>
          </div>
        )}

        {/* Claim-Level Grounding Findings */}
        {flaggedClaims.length > 0 && (
          <div style={{ marginBottom: '24px' }}>
            <h3 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '8px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '4px' }}>
              Claim-Level Grounding Breakdown ({flaggedClaims.length} Claims)
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {flaggedClaims.map((c, idx) => (
                <div key={idx} style={{ padding: '10px 14px', backgroundColor: 'var(--bg-surface-subtle)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)', fontSize: '0.82rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                    <span style={{ fontWeight: 700 }}>Claim {idx + 1}: "{c.claim}"</span>
                    <span
                      style={{
                        fontWeight: 700,
                        fontSize: '0.72rem',
                        textTransform: 'uppercase',
                        color:
                          c.status === 'SUPPORTED'
                            ? 'var(--status-pass-text)'
                            : c.status === 'CONTRADICTED'
                            ? 'var(--status-fail-text)'
                            : 'var(--status-review-text)',
                      }}
                    >
                      {c.status}
                    </span>
                  </div>
                  {c.reasoning && <div style={{ color: 'var(--text-secondary)' }}>Reason: {c.reasoning}</div>}
                  {c.evidence && <div style={{ color: 'var(--text-muted)', fontStyle: 'italic', marginTop: '2px' }}>Evidence: "{c.evidence}"</div>}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Completeness Aspects */}
        {(missingAspects.length > 0 || addressedAspects.length > 0) && (
          <div style={{ marginBottom: '24px' }}>
            <h3 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '8px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '4px' }}>
              Completeness Coverage Analysis
            </h3>
            <div style={{ fontSize: '0.82rem' }}>
              {addressedAspects.length > 0 && (
                <div style={{ marginBottom: '6px' }}>
                  <strong>Addressed Aspects: </strong>
                  <span>{addressedAspects.join('; ')}</span>
                </div>
              )}
              {missingAspects.length > 0 && (
                <div style={{ color: 'var(--status-fail-text)' }}>
                  <strong>Missing / Omitted Aspects: </strong>
                  <span>{missingAspects.join('; ')}</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Reasoning and Findings */}
        <div style={{ marginBottom: '24px' }}>
          <h3 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '8px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '4px' }}>
            Agent Reasoning & Justifications
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.84rem' }}>
            <div><strong>Consolidated Verdict: </strong>{evalItem.verdict_reasoning || 'Based on 4-dimension multi-agent synthesis.'}</div>
            <div><strong>Accuracy Reasoning: </strong>{accuracy.reasoning || 'Evaluated against reference knowledge.'}</div>
            <div><strong>Relevance Reasoning: </strong>{relevance.reasoning || 'Evaluated against question intent.'}</div>
            <div><strong>Hallucination Summary: </strong>{hallucination.summary || 'Analyzed claim-by-claim.'}</div>
            <div><strong>Completeness Reasoning: </strong>{completeness.reasoning || 'Coverage evaluated across question requirements.'}</div>
          </div>
        </div>

        {/* Evidence Sources */}
        <div>
          <h3 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '8px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '4px' }}>
            Evidence Used ({evidence.length} sources)
          </h3>
          {evidence.length === 0 ? (
            <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>No reference evidence chunks logged.</p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {evidence.slice(0, 4).map((e, idx) => (
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
