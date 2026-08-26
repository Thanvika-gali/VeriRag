import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import EvaluationForm from './components/EvaluationForm';
import EvidenceViewer from './components/EvidenceViewer';
import { History, Search, CheckCircle, RefreshCw } from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState('evaluate'); // 'evaluate' | 'history'
  const [loading, setLoading] = useState(false);
  const [currentResult, setCurrentResult] = useState(null);
  const [systemHealth, setSystemHealth] = useState(null);
  const [historyList, setHistoryList] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  // Fetch health on mount
  useEffect(() => {
    fetchHealth();
  }, []);

  const fetchHealth = async () => {
    try {
      const res = await fetch('/api/health');
      if (res.ok) {
        const data = await res.json();
        setSystemHealth(data);
      }
    } catch (err) {
      console.error('Health check error:', err);
    }
  };

  const fetchHistory = async () => {
    setHistoryLoading(true);
    try {
      const res = await fetch('/api/submissions?limit=30');
      if (res.ok) {
        const data = await res.json();
        setHistoryList(data);
      }
    } catch (err) {
      console.error('History fetch error:', err);
    } finally {
      setHistoryLoading(false);
    }
  };

  const handleEvaluate = async (formData) => {
    setLoading(true);
    try {
      const res = await fetch('/api/submissions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Evaluation request failed');
      }

      const data = await res.json();
      setCurrentResult(data);
      fetchHealth(); // refresh indexed counts if updated
    } catch (err) {
      alert('Error during evaluation: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectHistoryItem = async (submissionId) => {
    setLoading(true);
    setActiveTab('evaluate');
    try {
      const res = await fetch(`/api/submissions/${submissionId}`);
      if (res.ok) {
        const data = await res.json();
        setCurrentResult(data);
      }
    } catch (err) {
      alert('Failed to load submission: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-container">
      <Header systemHealth={systemHealth} />

      {/* M1 Information Banner */}
      <div className="m1-notice-banner">
        <div className="notice-content">
          <span className="notice-badge">Milestone 1</span>
          <span>
            Semantic Evidence Retrieval & Ingestion Pipeline: Ingests TruthfulQA and SQuAD benchmarks into ChromaDB and retrieves relevant evidence for grounded AI response evaluation.
          </span>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button
            onClick={() => { setActiveTab('evaluate'); }}
            className="chip-btn"
            style={{
              background: activeTab === 'evaluate' ? 'var(--accent-primary)' : 'rgba(255,255,255,0.05)',
              color: activeTab === 'evaluate' ? '#FFF' : 'var(--text-secondary)'
            }}
          >
            <Search size={14} style={{ display: 'inline', marginRight: '4px', verticalAlign: 'text-bottom' }} />
            Single Submission
          </button>
          <button
            onClick={() => { setActiveTab('history'); fetchHistory(); }}
            className="chip-btn"
            style={{
              background: activeTab === 'history' ? 'var(--accent-primary)' : 'rgba(255,255,255,0.05)',
              color: activeTab === 'history' ? '#FFF' : 'var(--text-secondary)'
            }}
          >
            <History size={14} style={{ display: 'inline', marginRight: '4px', verticalAlign: 'text-bottom' }} />
            History ({historyList.length})
          </button>
        </div>
      </div>

      {activeTab === 'evaluate' ? (
        <main className="main-grid">
          <EvaluationForm onSubmit={handleEvaluate} loading={loading} />
          <EvidenceViewer result={currentResult} loading={loading} />
        </main>
      ) : (
        <div className="panel-card">
          <div className="panel-header">
            <h2>
              <History size={18} color="#818CF8" />
              Submission History (SQLite Storage)
            </h2>
            <button
              onClick={fetchHistory}
              className="chip-btn"
              style={{ display: 'flex', alignItems: 'center', gap: '4px' }}
            >
              <RefreshCw size={12} />
              Refresh
            </button>
          </div>

          {historyLoading ? (
            <p style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>Loading history...</p>
          ) : historyList.length === 0 ? (
            <div className="empty-state">
              <p>No evaluation submissions stored yet.</p>
            </div>
          ) : (
            <div>
              {historyList.map((item) => (
                <div
                  key={item.submission_id}
                  className="history-item"
                  onClick={() => handleSelectHistoryItem(item.submission_id)}
                >
                  <div>
                    <div className="history-q">{item.question}</div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
                      AI Response: {item.ai_response_snippet}
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <span className="dataset-tag tag-squad" style={{ marginRight: '0.5rem' }}>
                      {item.evidence_count} Chunks
                    </span>
                    <span className="history-meta">{item.created_at.slice(0, 10)}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
