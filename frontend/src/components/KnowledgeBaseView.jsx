import React, { useState, useEffect } from 'react';
import { Database, Layers, CheckCircle2, ShieldCheck, RefreshCw, Info } from 'lucide-react';

export default function KnowledgeBaseView({ systemHealth }) {
  const [kbStats, setKbStats] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/knowledge-base/stats');
      if (res.ok) {
        const data = await res.json();
        setKbStats(data);
      }
    } catch (err) {
      console.warn('Failed to load KB stats:', err);
    } finally {
      setLoading(false);
    }
  };

  const totalChunks = kbStats?.total_indexed_chunks || systemHealth?.total_indexed_chunks || 0;
  const datasets = kbStats?.datasets || [
    {
      name: 'TruthfulQA',
      chunks: Math.floor(totalChunks * 0.4),
      status: 'Active & Indexed',
      source_type: 'Adversarial Benchmark / Misconceptions',
      description: 'Reference assertions testing whether answers replicate common false assertions and myths.',
    },
    {
      name: 'SQuAD',
      chunks: Math.ceil(totalChunks * 0.6),
      status: 'Active & Indexed',
      source_type: 'Encyclopedic Knowledge / Wikipedia',
      description: 'Factual passages extracted from high-quality encyclopedic articles.',
    },
    {
      name: 'Custom Documents',
      chunks: 0,
      status: 'Supported via Runtime Upload',
      source_type: 'User-provided TXT, PDF, MD',
      description: 'Dynamic reference documents parsed and analyzed during evaluation submissions.',
    },
  ];

  return (
    <div className="knowledge-base-container">
      {/* Intro Header */}
      <div className="ink-card">
        <div className="ink-card-header">
          <div className="card-title-block">
            <div className="card-icon-wrap">
              <Database size={18} />
            </div>
            <div>
              <h2 className="card-heading">Reference Knowledge Base</h2>
              <p className="card-subtext">
                Reference information used to retrieve evidence for response evaluation
              </p>
            </div>
          </div>

          <button
            type="button"
            className="btn-secondary"
            onClick={fetchStats}
            title="Refresh Knowledge Base Status"
          >
            <RefreshCw size={13} className={loading ? 'spin' : ''} />
            <span>Refresh</span>
          </button>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px', marginTop: '12px' }}>
          <div style={{ padding: '16px', backgroundColor: 'var(--bg-surface-subtle)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
              Total Indexed Chunks
            </span>
            <div style={{ fontSize: '1.8rem', fontWeight: 700, color: 'var(--text-primary)', marginTop: '4px' }}>
              {totalChunks}
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Persistent ChromaDB collection</span>
          </div>

          <div style={{ padding: '16px', backgroundColor: 'var(--bg-surface-subtle)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
              Embedding Model
            </span>
            <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--accent-primary)', marginTop: '6px' }}>
              all-MiniLM-L6-v2
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>384-dimensional dense vectors</span>
          </div>

          <div style={{ padding: '16px', backgroundColor: 'var(--bg-surface-subtle)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
              Vector Storage
            </span>
            <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--text-primary)', marginTop: '6px' }}>
              ChromaDB Local
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Cosine distance index</span>
          </div>
        </div>
      </div>

      {/* Dataset Cards */}
      <div className="ink-card">
        <h3 className="card-heading" style={{ marginBottom: '16px' }}>Indexed Reference Datasets</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {datasets.map((ds, idx) => (
            <div
              key={idx}
              style={{
                padding: '18px',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-md)',
                backgroundColor: 'var(--bg-surface-subtle)',
                display: 'flex',
                alignItems: 'flex-start',
                justifyContent: 'space-between',
                flexWrap: 'wrap',
                gap: '12px',
              }}
            >
              <div style={{ maxWidth: '600px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
                  <span style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                    {ds.name}
                  </span>
                  <span
                    style={{
                      fontSize: '0.72rem',
                      fontWeight: 600,
                      backgroundColor: 'var(--status-pass-bg)',
                      color: 'var(--status-pass-text)',
                      padding: '2px 8px',
                      borderRadius: '4px',
                      border: '1px solid var(--status-pass-border)',
                    }}
                  >
                    {ds.status}
                  </span>
                </div>
                <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', lineHeight: 1.45 }}>
                  {ds.description}
                </p>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px', display: 'block' }}>
                  Type: {ds.source_type}
                </span>
              </div>

              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '1.3rem', fontWeight: 700, color: 'var(--accent-primary)' }}>
                  {ds.chunks}
                </div>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Indexed Chunks</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
