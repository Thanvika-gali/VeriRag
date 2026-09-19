import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import DashboardView from './components/DashboardView';
import EvaluationForm from './components/EvaluationForm';
import EvaluationResultView from './components/EvaluationResultView';
import HistoryView from './components/HistoryView';
import EvidenceLibraryView from './components/EvidenceLibraryView';
import KnowledgeBaseView from './components/KnowledgeBaseView';
import AnalyticsView from './components/AnalyticsView';
import ReportsView from './components/ReportsView';
import SystemStatusView from './components/SystemStatusView';
import SettingsModal from './components/SettingsModal';
import BatchVerifyView from './components/BatchVerifyView';
import { Database, ShieldCheck, Cpu, Moon, Sun } from 'lucide-react';

export default function App() {
  const [activePage, setActivePage] = useState('verify');
  const [loading, setLoading] = useState(false);
  const [currentEvaluation, setCurrentEvaluation] = useState(null);
  const [systemHealth, setSystemHealth] = useState(null);
  const [historyList, setHistoryList] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [analytics, setAnalytics] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  // Theme state with localStorage persistence
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('proofRagTheme') || 'light';
  });

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('proofRagTheme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'light' ? 'dark' : 'light'));
  };

  useEffect(() => {
    fetchHealth();
    fetchHistory();
    fetchAnalytics();
  }, []);

  const fetchHealth = async () => {
    try {
      const res = await fetch('/api/health');
      if (res.ok) {
        const data = await res.json();
        setSystemHealth(data);
      }
    } catch (err) {
      console.warn('[PROOFRAG] Health check warning:', err);
    }
  };

  const fetchHistory = async () => {
    setHistoryLoading(true);
    try {
      const res = await fetch('/api/submissions?limit=50');
      if (res.ok) {
        const data = await res.json();
        setHistoryList(Array.isArray(data) ? data : []);
      }
    } catch (err) {
      console.warn('[PROOFRAG] History fetch warning:', err);
    } finally {
      setHistoryLoading(false);
    }
  };

  const fetchAnalytics = async () => {
    try {
      const res = await fetch('/api/analytics');
      if (res.ok) {
        const data = await res.json();
        setAnalytics(data);
      }
    } catch (err) {
      console.warn('[PROOFRAG] Analytics fetch warning:', err);
    }
  };

  const handleEvaluate = async (formData) => {
    setLoading(true);
    setErrorMessage(null);

    try {
      const res = await fetch('/api/submissions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });

      const contentType = res.headers.get('content-type');

      if (!res.ok) {
        let errMsg = 'Unable to verify response. Please check that the backend is running.';
        if (contentType && contentType.includes('application/json')) {
          try {
            const errData = await res.json();
            errMsg = errData.error || errData.detail || errMsg;
          } catch {
            // fallback
          }
        }
        throw new Error(errMsg);
      }

      const data = await res.json();
      setCurrentEvaluation(data);
      fetchHistory();
      fetchAnalytics();
      fetchHealth();
    } catch (err) {
      console.error('[PROOFRAG Error]:', err);
      const userMsg =
        err.message && !err.message.includes('Traceback')
          ? err.message
          : 'Unable to verify response. Please verify backend connectivity.';
      setErrorMessage(userMsg);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectSubmission = async (submissionId) => {
    setLoading(true);
    setErrorMessage(null);

    try {
      const res = await fetch(`/api/submissions/${submissionId}`);
      if (!res.ok) {
        throw new Error('Unable to retrieve submission record.');
      }
      const data = await res.json();
      setCurrentEvaluation(data);
      setActivePage('verify');
    } catch (err) {
      setErrorMessage(err.message || 'Unable to load submission details.');
    } finally {
      setLoading(false);
    }
  };

  const pageTitles = {
    verify: 'Verify Response',
    evaluate: 'Verify Response',
    dashboard: 'Verify Response',
    'batch-verify': 'Batch Verify',
    history: 'Evaluation History',
    'evidence-library': 'Evidence Library',
    'data-sources': 'Data Sources',
    'knowledge-base': 'Data Sources',
    insights: 'Verification Insights',
    analytics: 'Verification Insights',
    reports: 'Audit Reports',
    'system-status': 'System Status',
    architecture: 'System Status',
  };

  return (
    <div className="app-container" data-theme={theme}>
      {/* Left Navigation Sidebar */}
      <Sidebar
        activePage={activePage}
        setActivePage={setActivePage}
        historyCount={historyList.length}
        onOpenSettings={() => setIsSettingsOpen(true)}
      />

      {/* Main App Canvas */}
      <div className="main-wrapper">
        {/* Top Header Bar */}
        <header className="topbar">
          <div className="topbar-page-info">
            <h1 className="topbar-title">{pageTitles[activePage] || 'PROOFRAG'}</h1>
          </div>

          <div className="topbar-meta-row">
            {/* Light / Dark Mode Toggle */}
            <button
              type="button"
              id="theme-toggle-btn"
              className="theme-toggle-btn"
              onClick={toggleTheme}
              title={`Switch to ${theme === 'light' ? 'Dark' : 'Light'} Mode (Current: ${theme === 'light' ? 'Light' : 'Dark'})`}
              aria-label={`Switch to ${theme === 'light' ? 'Dark' : 'Light'} Mode`}
            >
              {theme === 'light' ? (
                <>
                  <Moon size={14} />
                  <span className="theme-toggle-label">Dark</span>
                </>
              ) : (
                <>
                  <Sun size={14} />
                  <span className="theme-toggle-label">Light</span>
                </>
              )}
            </button>

            <div className="telemetry-chip">
              <span className="status-dot-green" />
              <span>Model:</span>
              <strong style={{ color: 'var(--text-primary)' }}>
                {systemHealth?.embedding_model || 'all-MiniLM-L6-v2'}
              </strong>
            </div>

            <div className="telemetry-chip">
              <Database size={13} style={{ color: 'var(--accent-primary)' }} />
              <span>Chunks:</span>
              <strong style={{ color: 'var(--text-primary)' }}>
                {systemHealth?.total_indexed_chunks !== undefined ? systemHealth.total_indexed_chunks : '—'}
              </strong>
            </div>
          </div>
        </header>

        {/* Dynamic Body Content */}
        <main className="content-body">
          {(activePage === 'verify' || activePage === 'evaluate' || activePage === 'dashboard') && (
            <div className="evaluate-layout-grid">
              <section aria-label="Input Form Column">
                <EvaluationForm
                  onSubmit={handleEvaluate}
                  loading={loading}
                  errorMessage={errorMessage}
                  onClearError={() => setErrorMessage(null)}
                />
              </section>

              <section aria-label="Evaluation Results Column">
                <EvaluationResultView
                  evaluation={currentEvaluation}
                  onBackToForm={() => setCurrentEvaluation(null)}
                />
              </section>
            </div>
          )}

          {activePage === 'batch-verify' && (
            <BatchVerifyView />
          )}

          {activePage === 'history' && (
            <HistoryView
              historyList={historyList}
              loading={historyLoading}
              onSelectSubmission={handleSelectSubmission}
              onRefresh={fetchHistory}
            />
          )}

          {activePage === 'evidence-library' && (
            <EvidenceLibraryView systemHealth={systemHealth} />
          )}

          {(activePage === 'data-sources' || activePage === 'knowledge-base') && (
            <KnowledgeBaseView systemHealth={systemHealth} />
          )}

          {(activePage === 'insights' || activePage === 'analytics') && (
            <AnalyticsView
              analytics={analytics}
              onNewEvaluation={() => setActivePage('verify')}
            />
          )}

          {activePage === 'reports' && (
            <ReportsView
              currentEvaluation={currentEvaluation}
              historyList={historyList}
              onSelectSubmission={handleSelectSubmission}
              onNewEvaluation={() => setActivePage('verify')}
            />
          )}

          {(activePage === 'system-status' || activePage === 'architecture') && (
            <SystemStatusView
              systemHealth={systemHealth}
              onRefreshHealth={fetchHealth}
            />
          )}
        </main>
      </div>

      {/* Settings Modal */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        systemHealth={systemHealth}
        theme={theme}
        onToggleTheme={toggleTheme}
      />
    </div>
  );
}
