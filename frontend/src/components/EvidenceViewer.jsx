import React from 'react';
import { BookOpen, Layers, CheckCircle2, AlertCircle, Info, Cpu, Database, Search, Hash } from 'lucide-react';

export default function EvidenceViewer({ result, loading }) {
  if (loading) {
    return (
      <div className="panel-card">
        <div className="panel-header">
          <h2>
            <Layers size={18} color="#818CF8" />
            Retrieved Grounding Evidence
          </h2>
        </div>
        <div className="empty-state">
          <div className="status-dot" style={{ width: '16px', height: '16px', margin: '0 auto 1rem auto' }}></div>
          <p style={{ color: 'var(--text-primary)', fontWeight: 500 }}>Generating Query Embeddings & Querying ChromaDB...</p>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
            Matching question and response against TruthfulQA & SQuAD index.
          </p>
        </div>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="panel-card">
        <div className="panel-header">
          <h2>
            <Layers size={18} color="#818CF8" />
            Retrieved Grounding Evidence
          </h2>
        </div>
        <div className="empty-state">
          <BookOpen size={48} className="empty-icon" />
          <p style={{ fontWeight: 500, color: 'var(--text-secondary)' }}>No Submission Evaluated Yet</p>
          <p style={{ fontSize: '0.85rem', marginTop: '0.5rem' }}>
            Submit a question and AI response to perform semantic vector search across the Reference Knowledge Base.
          </p>
        </div>
      </div>
    );
  }

  const { submission_id, retrieved_evidence, created_at } = result;

  return (
    <div className="panel-card">
      <div className="panel-header">
        <h2>
          <Layers size={18} color="#818CF8" />
          Retrieved Grounding Evidence ({retrieved_evidence.length} Chunks)
        </h2>
        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
          ID: {submission_id.slice(0, 8)}...
        </span>
      </div>

      {/* Notice box indicating M1 scope */}
      <div style={{
        background: 'rgba(99, 102, 241, 0.08)',
        border: '1px solid rgba(99, 102, 241, 0.25)',
        borderRadius: 'var(--radius-md)',
        padding: '0.75rem 1rem',
        marginBottom: '1rem',
        fontSize: '0.82rem',
        color: '#C7D2FE',
        display: 'flex',
        alignItems: 'flex-start',
        gap: '0.6rem',
      }}>
        <Info size={16} style={{ flexShrink: 0, marginTop: '2px', color: '#818CF8' }} />
        <div>
          <strong>Milestone 1 Grounding Phase:</strong> Verified reference chunks retrieved below. 
          Automated judge agents (Accuracy, Relevance, Hallucination Detection, Completeness, Verdict) are designated for Milestone 2.
        </div>
      </div>

      {/* Retrieval Summary Section */}
      <div style={{
        background: 'rgba(15, 23, 42, 0.75)',
        border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--radius-md)',
        padding: '0.85rem 1rem',
        marginBottom: '1.25rem',
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
        gap: '0.75rem',
      }}>
        <div>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Status</div>
          <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#34D399', display: 'flex', alignItems: 'center', gap: '4px', marginTop: '2px' }}>
            <CheckCircle2 size={13} /> Completed
          </div>
        </div>
        <div>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Retrieved</div>
          <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#F9FAFB', marginTop: '2px' }}>
            {retrieved_evidence.length} Chunks
          </div>
        </div>
        <div>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Embedding Model</div>
          <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#A78BFA', marginTop: '2px' }}>
            all-MiniLM-L6-v2
          </div>
        </div>
        <div>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Vector Store</div>
          <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#818CF8', marginTop: '2px' }}>
            ChromaDB
          </div>
        </div>
        <div>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Search Method</div>
          <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#38BDF8', marginTop: '2px' }}>
            Dense Cosine
          </div>
        </div>
      </div>

      {retrieved_evidence.length === 0 ? (
        <div className="empty-state">
          <AlertCircle size={36} color="#F59E0B" className="empty-icon" />
          <p style={{ color: 'var(--text-secondary)' }}>No matching reference evidence found.</p>
          <p style={{ fontSize: '0.8rem', marginTop: '0.3rem' }}>
            Ensure the knowledge base has been built via <code>python knowledge_base/build_kb.py</code>.
          </p>
        </div>
      ) : (
        <div className="evidence-list">
          {retrieved_evidence.map((item, idx) => {
            const isTruthfulQA = (item.dataset_name || '').toLowerCase().includes('truthful');
            const isSQuAD = (item.dataset_name || '').toLowerCase().includes('squad');

            return (
              <div key={item.chunk_id || idx} className="evidence-card">
                <div className="evidence-header">
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span style={{
                      fontSize: '0.78rem',
                      fontWeight: 700,
                      background: 'rgba(99, 102, 241, 0.2)',
                      color: '#C7D2FE',
                      padding: '0.15rem 0.45rem',
                      borderRadius: '4px'
                    }}>
                      Evidence #{idx + 1}
                    </span>
                    <span className={`dataset-tag ${isTruthfulQA ? 'tag-truthfulqa' : isSQuAD ? 'tag-squad' : 'tag-custom'}`}>
                      {item.dataset_name || 'Knowledge Base'}
                    </span>
                  </div>
                  <div className="score-badge">
                    <span style={{ color: 'var(--text-muted)' }}>Sim:</span>
                    <strong style={{ color: item.similarity_score > 0.5 ? '#34D399' : '#FBBF24' }}>
                      {(item.similarity_score * 100).toFixed(1)}%
                    </strong>
                    <span style={{ color: 'var(--text-muted)', fontSize: '0.72rem' }}>
                      (dist: {item.distance.toFixed(3)})
                    </span>
                  </div>
                </div>

                <div className="evidence-body">
                  {item.text}
                </div>

                <div className="evidence-meta-footer" style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem' }}>
                    <span><strong>Chunk ID:</strong> {item.chunk_id}</span>
                    {item.metadata?.doc_id && <span><strong>Doc ID:</strong> {item.metadata.doc_id}</span>}
                    {item.metadata?.question_id && <span><strong>Question ID:</strong> {item.metadata.question_id}</span>}
                  </div>
                  {(item.metadata?.category || item.metadata?.title || item.metadata?.source) && (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', color: '#94A3B8' }}>
                      {item.metadata?.category && <span><strong>Category:</strong> {item.metadata.category}</span>}
                      {item.metadata?.title && <span><strong>Topic/Title:</strong> {item.metadata.title}</span>}
                      {item.metadata?.source && (
                        <span><strong>Source:</strong> {item.metadata.source}</span>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
