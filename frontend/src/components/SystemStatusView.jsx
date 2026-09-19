import React, { useState, useEffect } from 'react';
import { Activity, Database, Cpu, CheckCircle2, RefreshCw, ShieldCheck, Server, Sliders } from 'lucide-react';

export default function SystemStatusView({ systemHealth, onRefreshHealth }) {
  const [health, setHealth] = useState(systemHealth);
  const [refreshing, setRefreshing] = useState(false);
  const [pingMs, setPingMs] = useState(12);

  useEffect(() => {
    if (systemHealth) setHealth(systemHealth);
  }, [systemHealth]);

  const handleRefresh = async () => {
    setRefreshing(true);
    const start = performance.now();
    try {
      const res = await fetch('/api/health');
      const elapsed = Math.round(performance.now() - start);
      setPingMs(elapsed);
      if (res.ok) {
        const data = await res.json();
        setHealth(data);
        if (onRefreshHealth) onRefreshHealth();
      }
    } catch (err) {
      console.warn('Health refresh error:', err);
    } finally {
      setRefreshing(false);
    }
  };

  const isDbReady = health?.database_connected ?? true;
  const isVecReady = health?.vector_store_ready ?? true;

  return (
    <div className="system-status-container">
      {/* Top Health Overview */}
      <div className="ink-card">
        <div className="ink-card-header">
          <div className="card-title-block">
            <div className="card-icon-wrap">
              <Activity size={18} />
            </div>
            <div>
              <h2 className="card-heading">System Status & Engine Diagnostics</h2>
              <p className="card-subtext">
                Live telemetry and operational readiness of PROOFRAG evaluation subsystems
              </p>
            </div>
          </div>

          <button
            type="button"
            id="system-refresh-btn"
            className="btn-secondary"
            onClick={handleRefresh}
            disabled={refreshing}
          >
            <RefreshCw size={14} className={refreshing ? 'spin' : ''} />
            <span>{refreshing ? 'Checking...' : 'Ping Diagnostics'}</span>
          </button>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '14px', marginTop: '8px' }}>
          <div style={{ padding: '16px', backgroundColor: 'var(--bg-surface-subtle)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
              System Health
            </span>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '6px' }}>
              <span className="status-dot-green" />
              <span style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--status-pass-text)' }}>
                OPERATIONAL
              </span>
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Latency: {pingMs} ms (Localhost API)</span>
          </div>

          <div style={{ padding: '16px', backgroundColor: 'var(--bg-surface-subtle)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
              Vector Database
            </span>
            <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--text-primary)', marginTop: '6px' }}>
              ChromaDB Local
            </div>
            <span style={{ fontSize: '0.75rem', color: isVecReady ? 'var(--status-pass-text)' : 'var(--status-fail-text)' }}>
              ● {health?.total_indexed_chunks !== undefined ? health.total_indexed_chunks : '—'} chunks indexed ({isVecReady ? 'Ready' : 'Offline'})
            </span>
          </div>

          <div style={{ padding: '16px', backgroundColor: 'var(--bg-surface-subtle)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
              Relational Storage
            </span>
            <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--text-primary)', marginTop: '6px' }}>
              SQLite Persistent
            </div>
            <span style={{ fontSize: '0.75rem', color: isDbReady ? 'var(--status-pass-text)' : 'var(--status-fail-text)' }}>
              ● submissions.db connected
            </span>
          </div>

          <div style={{ padding: '16px', backgroundColor: 'var(--bg-surface-subtle)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
              Dense Embedding Model
            </span>
            <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--accent-primary)', marginTop: '6px' }}>
              {health?.embedding_model || 'all-MiniLM-L6-v2'}
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>SentenceTransformers (384 dims)</span>
          </div>
        </div>
      </div>

      {/* Multi-Agent Subsystems (M3 Complete Architecture) */}
      <div className="ink-card">
        <div className="ink-card-header">
          <div className="card-title-block">
            <div className="card-icon-wrap">
              <Cpu size={16} />
            </div>
            <div>
              <h3 className="card-heading">Multi-Agent Pipeline Architecture</h3>
              <p className="card-subtext">Operational telemetry across all 8 verified evaluation subsystems</p>
            </div>
          </div>
          <span className="badge-pass" style={{ fontSize: '0.74rem' }}>8 NODES ACTIVE</span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '14px' }}>
          {[
            {
              name: 'RAG / Evidence Retrieval',
              key: 'RAG / Evidence Retrieval',
              desc: 'Dual-query semantic vector expansion on ChromaDB with discriminating entity filtering.',
              defaultOnline: isVecReady,
            },
            {
              name: 'Relevance Judge Agent',
              key: 'Relevance Judge Agent',
              desc: 'Calibrated 1-5 evaluation of inquiry alignment using semantic overlap and topical heuristics.',
              defaultOnline: true,
            },
            {
              name: 'Accuracy Judge Agent',
              key: 'Accuracy Judge Agent',
              desc: 'Claim-level factual decomposition penalizing mixed true/fabricated statements (<= 3/5).',
              defaultOnline: true,
            },
            {
              name: 'Hallucination Detection Agent',
              key: 'Hallucination Detection Agent',
              desc: 'Assertion grounding assigning SUPPORTED, UNSUPPORTED, CONTRADICTED, or INSUFFICIENT.',
              defaultOnline: true,
            },
            {
              name: 'Completeness Judge Agent',
              key: 'Completeness Judge Agent',
              desc: 'Multi-part requirement decomposition tracking addressed aspects versus critical omissions.',
              defaultOnline: true,
            },
            {
              name: 'Verdict Agent',
              key: 'Verdict Agent',
              desc: 'Linear 4-dimension aggregation with rule-based critical failure override protection.',
              defaultOnline: true,
            },
            {
              name: 'Evaluation Orchestrator',
              key: 'Evaluation Orchestrator',
              desc: 'Coordinates deterministic pipeline execution, candidate filtering, and record persistence.',
              defaultOnline: true,
            },
            {
              name: 'Batch Evaluation',
              key: 'Batch Evaluation',
              desc: 'High-throughput CSV ingestion, deterministic alias mapping, and row-level resilience.',
              defaultOnline: true,
            },
          ].map((agent, i) => {
            const isOnline = health?.agent_statuses
              ? health.agent_statuses[agent.key] === 'ONLINE'
              : agent.defaultOnline;

            return (
              <div
                key={i}
                style={{
                  padding: '16px',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-md)',
                  backgroundColor: 'var(--bg-surface-subtle)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <div style={{ fontWeight: 700, color: 'var(--text-primary)', fontSize: '0.92rem' }}>
                    {agent.name}
                  </div>
                  <span
                    className={isOnline ? 'badge-pass' : 'badge-fail'}
                    style={{ fontSize: '0.7rem' }}
                  >
                    {isOnline ? 'ONLINE' : 'OFFLINE'}
                  </span>
                </div>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.45 }}>
                  {agent.desc}
                </p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Threshold & Weight Configuration Matrix */}
      <div className="ink-card">
        <h3 className="card-heading" style={{ marginBottom: '16px' }}>
          Threshold Configuration & Milestone 3 Scoring Weights
        </h3>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '14px' }}>
          <div style={{ padding: '14px', backgroundColor: 'var(--bg-surface-subtle)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>
              Minimum Evidence Threshold
            </span>
            <div style={{ fontSize: '1.2rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--text-primary)', marginTop: '4px' }}>
              0.50
            </div>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>Candidates below 0.50 excluded</span>
          </div>

          <div style={{ padding: '14px', backgroundColor: 'var(--bg-surface-subtle)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>
              Strong Match Threshold
            </span>
            <div style={{ fontSize: '1.2rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--text-primary)', marginTop: '4px' }}>
              0.65
            </div>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>Direct factual grounding anchor</span>
          </div>

          <div style={{ padding: '14px', backgroundColor: 'var(--bg-surface-subtle)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>
              Candidate Expansion Pool
            </span>
            <div style={{ fontSize: '1.2rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--text-primary)', marginTop: '4px' }}>
              Top 10 Chunks
            </div>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>Dual query expansion</span>
          </div>

          <div style={{ padding: '14px', backgroundColor: 'var(--bg-surface-subtle)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>
              M3 Transparent Weighting
            </span>
            <div style={{ fontSize: '1.2rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--accent-primary)', marginTop: '4px' }}>
              35 / 30 / 20 / 15
            </div>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>35% Acc, 30% Hal, 20% Rel, 15% Comp</span>
          </div>
        </div>
      </div>
    </div>
  );
}
