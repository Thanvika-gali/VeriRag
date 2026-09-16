import React from 'react';
import { X, Settings, Database, Cpu, ShieldCheck } from 'lucide-react';

export default function SettingsModal({ isOpen, onClose, systemHealth, theme, onToggleTheme }) {
  if (!isOpen) return null;

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(74, 74, 74, 0.45)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 100,
        padding: '20px',
      }}
      onClick={onClose}
    >
      <div
        className="ink-card"
        style={{
          width: '100%',
          maxWidth: '520px',
          padding: '24px',
          boxShadow: 'var(--shadow-lg)',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Settings size={18} style={{ color: 'var(--accent-primary)' }} />
            <h3 style={{ fontSize: '1.05rem', fontWeight: 700 }}>PROOFRAG Settings & Telemetry</h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}
          >
            <X size={18} />
          </button>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', fontSize: '0.85rem' }}>
          <div style={{ padding: '10px 14px', backgroundColor: 'var(--bg-surface-subtle)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>Interface Theme</div>
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', marginTop: '2px' }}>
                Current: {theme === 'dark' ? 'Dark Palette' : 'Ink Wash Light Palette'}
              </div>
            </div>
            {onToggleTheme && (
              <button
                type="button"
                className="btn-secondary"
                onClick={onToggleTheme}
                style={{ fontSize: '0.78rem', padding: '6px 12px' }}
              >
                Switch to {theme === 'dark' ? 'Light' : 'Dark'}
              </button>
            )}
          </div>

          <div style={{ padding: '10px 14px', backgroundColor: 'var(--bg-surface-subtle)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
            <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>Evaluation Engine Mode</div>
            <div style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', marginTop: '2px' }}>
              Multi-Agent Orchestrator: Relevance Judge + Accuracy Judge + Hallucination Detector
            </div>
          </div>

          <div style={{ padding: '10px 14px', backgroundColor: 'var(--bg-surface-subtle)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
            <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>Embedding Model</div>
            <div style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', marginTop: '2px' }}>
              {systemHealth?.embedding_model || 'all-MiniLM-L6-v2'} (384-dimensional dense vectors)
            </div>
          </div>

          <div style={{ padding: '10px 14px', backgroundColor: 'var(--bg-surface-subtle)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
            <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>Database Storage</div>
            <div style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', marginTop: '2px' }}>
              SQLite (<code>submissions.db</code>) & ChromaDB (<code>chromadb_data/</code>)
            </div>
          </div>

          <div style={{ padding: '10px 14px', backgroundColor: 'var(--bg-surface-subtle)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
            <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>Indexed Knowledge Chunks</div>
            <div style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', marginTop: '2px' }}>
              {systemHealth?.total_indexed_chunks || 0} chunks (TruthfulQA + SQuAD + Canonical Benchmarks)
            </div>
          </div>
        </div>

        <div style={{ marginTop: '20px', textAlign: 'right' }}>
          <button type="button" className="btn-secondary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
