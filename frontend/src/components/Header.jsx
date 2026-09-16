import React from 'react';
import { ShieldCheck, Database, Sparkles, History } from 'lucide-react';

export default function Header({ systemHealth, activeTab, setActiveTab, historyCount }) {
  return (
    <header className="lab-header">
      <div className="lab-header-top">
        <div className="brand-lockup">
          <div className="brand-orb">
            <ShieldCheck size={28} className="brand-orb-icon" />
            <div className="orb-pulse-ring" />
          </div>
          <div className="brand-text">
            <div className="brand-badge-row">
              <span className="brand-name">PROOFRAG</span>
              <span className="brand-tag">AI RESPONSE VERIFICATION</span>
            </div>
            <h1 className="hero-question">Check whether an AI answer is supported by reliable evidence.</h1>
            <p className="hero-subtext">Find supporting evidence from trusted benchmark and reference data</p>
          </div>
        </div>

        <div className="header-controls">
          <div className="telemetry-bar">
            <div className="telemetry-item">
              <span className="telemetry-indicator online" />
              <span className="telemetry-label">Engine:</span>
              <span className="telemetry-val">all-MiniLM-L6-v2</span>
            </div>
            <div className="telemetry-item">
              <Database size={13} className="telemetry-icon" />
              <span className="telemetry-label">Knowledge Base:</span>
              <span className="telemetry-val">
                {systemHealth ? `${systemHealth.total_indexed_chunks} chunks` : 'Connecting...'}
              </span>
            </div>
          </div>

          <div className="nav-toggle-group">
            <button
              type="button"
              id="tab-verify-btn"
              onClick={() => setActiveTab('evaluate')}
              className={`nav-btn ${activeTab === 'evaluate' ? 'active' : ''}`}
            >
              <Sparkles size={14} />
              <span>Check Answer</span>
            </button>
            <button
              type="button"
              id="tab-archive-btn"
              onClick={() => setActiveTab('history')}
              className={`nav-btn ${activeTab === 'history' ? 'active' : ''}`}
            >
              <History size={14} />
              <span>Archive ({historyCount})</span>
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
