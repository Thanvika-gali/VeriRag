import React from 'react';
import { ArrowRight, Brain, Search, GitCompare, CheckCircle2, ShieldAlert, Sparkles, Database } from 'lucide-react';

export default function VerificationPipeline({ loading }) {
  const standardSteps = [
    { num: '01', title: 'AI Answer', desc: 'Query & generated response', status: 'ready' },
    { num: '02', title: 'Claim Analysis', desc: 'Semantic extraction', status: 'ready' },
    { num: '03', title: 'Evidence Search', desc: 'Reference knowledge lookup', status: 'active', badge: 'Active' },
    { num: '04', title: 'Evidence Check', desc: 'Grounding cross-check', status: 'upcoming', badge: 'Upcoming' },
    { num: '05', title: 'Trust Verdict', desc: 'Comprehensive consensus', status: 'upcoming', badge: 'Upcoming' },
  ];

  if (loading) {
    return (
      <div className="pipeline-container active-loading">
        <div className="pipeline-loading-header">
          <div className="pipeline-spinner-pulse" />
          <div>
            <div className="pipeline-loading-title">Searching for supporting evidence...</div>
            <div className="pipeline-loading-subtitle">
              Querying reference knowledge base & calculating match strength
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="pipeline-container static-concept">
      <div className="pipeline-label-row">
        <span className="pipeline-pill">VERIFICATION PIPELINE</span>
        <span className="pipeline-hint">How PROOFRAG cross-examines answers against trusted reference data</span>
      </div>
      <div className="pipeline-flow">
        {standardSteps.map((step, idx) => (
          <React.Fragment key={idx}>
            <div className={`flow-node ${step.status === 'active' ? 'highlight-node' : step.status === 'upcoming' ? 'upcoming-node' : ''}`}>
              <div className="flow-step-top">
                <span className="flow-step-num">{step.num}</span>
                {step.badge && (
                  <span className={`flow-badge ${step.status === 'active' ? 'active-badge' : 'upcoming-badge'}`}>
                    {step.badge}
                  </span>
                )}
              </div>
              <div className="flow-title">{step.title}</div>
              <div className="flow-sub">{step.desc}</div>
            </div>
            {idx < standardSteps.length - 1 && (
              <div className="flow-connector">
                <ArrowRight size={14} />
              </div>
            )}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}
