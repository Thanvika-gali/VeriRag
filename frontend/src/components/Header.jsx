import React from 'react';
import { ShieldCheck, Database, Cpu } from 'lucide-react';

export default function Header({ systemHealth }) {
  return (
    <header className="header">
      <div className="header-brand">
        <div className="header-logo">
          <ShieldCheck size={28} color="#FFFFFF" />
        </div>
        <div className="header-titles">
          <h1>VeriRAG</h1>
          <p>Evidence-Grounded AI Response Validation System with Hallucination Detection Assistance</p>
        </div>
      </div>
      <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
        <div className="header-status-badge">
          <span className="status-dot"></span>
          <span>M1: Evidence Grounding Active</span>
        </div>
        <div className="header-status-badge" style={{ background: 'rgba(16, 185, 129, 0.1)', borderColor: 'rgba(16, 185, 129, 0.3)', color: '#34D399' }}>
          <Database size={14} />
          <span>{systemHealth ? `${systemHealth.total_indexed_chunks} Indexed Chunks` : 'Connecting to ChromaDB...'}</span>
        </div>
      </div>
    </header>
  );
}
