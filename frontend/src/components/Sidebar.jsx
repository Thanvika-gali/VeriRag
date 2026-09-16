import React from 'react';
import {
  ShieldCheck,
  History,
  Database,
  Layers,
  BarChart3,
  FileText,
  Activity,
  Settings,
} from 'lucide-react';

export default function Sidebar({ activePage, setActivePage, historyCount = 0, onOpenSettings }) {
  const navSections = [
    {
      category: 'VERIFY',
      items: [
        { id: 'verify', label: 'Verify Response', icon: ShieldCheck },
        { id: 'history', label: 'Evaluation History', icon: History, badge: historyCount > 0 ? historyCount : null },
      ],
    },
    {
      category: 'EVIDENCE',
      items: [
        { id: 'evidence-library', label: 'Evidence Library', icon: Database },
        { id: 'data-sources', label: 'Data Sources', icon: Layers },
      ],
    },
    {
      category: 'INSIGHTS',
      items: [
        { id: 'insights', label: 'Verification Insights', icon: BarChart3 },
        { id: 'reports', label: 'Reports', icon: FileText },
      ],
    },
    {
      category: 'SYSTEM',
      items: [
        { id: 'system-status', label: 'System Status', icon: Activity },
      ],
    },
  ];

  return (
    <aside className="sidebar" aria-label="Main Navigation">
      <div className="sidebar-header">
        <div className="brand-logo-badge" aria-hidden="true">
          PR
        </div>
        <div className="brand-info">
          <span className="brand-name">PROOFRAG</span>
          <span className="brand-subtext">AI RESPONSE VERIFICATION</span>
        </div>
      </div>

      <nav className="sidebar-nav">
        {navSections.map((section) => (
          <div key={section.category} style={{ marginBottom: '12px' }}>
            <div className="nav-category-label">{section.category}</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
              {section.items.map((item) => {
                const Icon = item.icon;
                const isActive = activePage === item.id;
                return (
                  <button
                    key={item.id}
                    id={`nav-${item.id}-btn`}
                    type="button"
                    className={`nav-link-btn ${isActive ? 'active' : ''}`}
                    onClick={() => setActivePage(item.id)}
                  >
                    <Icon size={17} />
                    <span>{item.label}</span>
                    {item.badge !== null && item.badge !== undefined && (
                      <span className="nav-badge-pill">{item.badge}</span>
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      <div className="sidebar-footer">
        <button
          type="button"
          id="nav-settings-btn"
          className="nav-link-btn"
          onClick={onOpenSettings}
        >
          <Settings size={17} />
          <span>Settings</span>
        </button>

        <div className="user-profile-badge">
          <div className="user-avatar">PR</div>
          <div className="user-details">
            <span className="user-name">PROOFRAG Evaluator</span>
            <span className="user-role">Verification Workspace</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
