import React from 'react';
import { Cpu, ArrowDown, Database, ShieldCheck, CheckCircle2, Layers, GitCompare, Sparkles } from 'lucide-react';

export default function ArchitectureView() {
  const steps = [
    {
      title: '1. Frontend (React + Vite)',
      desc: 'Minimalist Ink Wash UI captures User Question, AI Answer, optional Verified Answer and Supporting Documents.',
      icon: Layers,
    },
    {
      title: '2. FastAPI Backend & Validation',
      desc: 'REST API validates payloads, parses multi-format documents (PDF/TXT), and orchestrates asynchronous evaluation.',
      icon: Cpu,
    },
    {
      title: '3. Evaluation Orchestrator',
      desc: 'Coordinates dual-query candidate expansion, manages agent dependencies, and synchronizes scoring logic.',
      icon: Sparkles,
    },
    {
      title: '4. RAG Retrieval & Vector Search',
      desc: 'Dense embeddings generated with all-MiniLM-L6-v2; dual-query cosine search across ChromaDB vector store.',
      icon: Database,
    },
    {
      title: '5. Evidence Tiering & Filtering',
      desc: 'Threshold-based relevance filtering (Strong >=70%, Moderate 50-69%, Weak <50%) isolates verified evidence.',
      icon: GitCompare,
    },
    {
      title: '6. Parallel Multi-Agent Judges',
      desc: 'Relevance Judge Agent (1-5), Accuracy Judge Agent (1-5), and Hallucination Detection Agent (Claim Decomposition).',
      icon: ShieldCheck,
    },
    {
      title: '7. Transparent Score Aggregation',
      desc: 'Weighted engineering aggregation: 40% Accuracy, 30% Relevance, 30% Hallucination Safety -> 0-100 Score.',
      icon: CheckCircle2,
    },
    {
      title: '8. Rule-Based Final Verdict & SQLite Storage',
      desc: 'Deterministic determination of PASS, REVIEW, or FAIL persisted into SQLite with full audit metrics.',
      icon: Database,
    },
  ];

  return (
    <div className="architecture-container">
      <div className="ink-card">
        <div className="ink-card-header">
          <div className="card-title-block">
            <div className="card-icon-wrap">
              <Cpu size={18} />
            </div>
            <div>
              <h2 className="card-heading">System Architecture & Pipeline Flow</h2>
              <p className="card-subtext">
                Evidence-grounded response evaluation engine architecture
              </p>
            </div>
          </div>
        </div>

        <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', marginBottom: '24px', lineHeight: 1.5 }}>
          PROOFRAG operates as an end-to-end evidence evaluation platform. Responses are broken down into
          atomic assertions, cross-referenced against dense vector representations of verified reference knowledge,
          and evaluated through specialized judge agents before synthesizing a final audit verdict.
        </p>

        {/* Visual Pipeline Stack */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px' }}>
          {steps.map((step, idx) => {
            const Icon = step.icon;
            return (
              <React.Fragment key={idx}>
                <div
                  style={{
                    width: '100%',
                    maxWidth: '680px',
                    padding: '16px 20px',
                    backgroundColor: 'var(--bg-surface-subtle)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: 'var(--radius-md)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '16px',
                    boxShadow: 'var(--shadow-sm)',
                  }}
                >
                  <div
                    style={{
                      width: '40px',
                      height: '40px',
                      borderRadius: 'var(--radius-md)',
                      backgroundColor: 'var(--accent-light)',
                      color: 'var(--accent-primary)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                    }}
                  >
                    <Icon size={20} />
                  </div>
                  <div>
                    <div style={{ fontSize: '0.92rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                      {step.title}
                    </div>
                    <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: '2px', lineHeight: 1.4 }}>
                      {step.desc}
                    </div>
                  </div>
                </div>

                {idx < steps.length - 1 && (
                  <ArrowDown size={18} style={{ color: 'var(--accent-primary)', margin: '2px 0' }} />
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>
    </div>
  );
}
