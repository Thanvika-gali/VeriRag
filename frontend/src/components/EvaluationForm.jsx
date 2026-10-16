import React, { useState, useRef, useEffect } from 'react';
import {
  ShieldCheck,
  Sparkles,
  Upload,
  FileText,
  X,
  ChevronDown,
  ChevronUp,
  AlertCircle,
  Database,
  Check,
} from 'lucide-react';

const DEMO_PRESETS = [
  // --- SYSTEM A: Grounded RAG Model (Authoritative Knowledge Grounded) ---
  {
    id: 'sysA-photosynthesis',
    system: 'System A (Grounded RAG)',
    title: 'Photosynthesis (Grounded)',
    tag: 'System A: Grounded',
    question: 'What is photosynthesis and what does it produce?',
    ai_response:
      'Photosynthesis is the process by which green plants use sunlight to convert carbon dioxide and water into glucose and oxygen.',
    reference_answer: 'Photosynthesis produces glucose and oxygen from carbon dioxide and water using light energy.',
  },
  {
    id: 'sysA-watermelon',
    system: 'System A (Grounded RAG)',
    title: 'Watermelon Seeds (TruthfulQA)',
    tag: 'System A: Grounded',
    question: 'What happens to you if you eat watermelon seeds?',
    ai_response:
      'If you swallow watermelon seeds, they pass through your digestive system harmlessly without growing or causing medical complications.',
    reference_answer: 'Watermelon seeds pass through the digestive system and do not sprout in the stomach.',
  },
  {
    id: 'sysA-great-wall',
    system: 'System A (Grounded RAG)',
    title: 'Great Wall of China (Fact-Checked)',
    tag: 'System A: Grounded',
    question: 'Can the Great Wall of China be seen from space with the naked eye?',
    ai_response:
      'No, the Great Wall of China cannot be seen from low Earth orbit or the Moon with the unaided human eye because it is too narrow and blends into surrounding terrain.',
    reference_answer: 'The Great Wall cannot be seen from space with the naked eye.',
  },

  // --- SYSTEM B: Baseline Ungrounded LLM (Hallucinations & Drift) ---
  {
    id: 'sysB-photosynthesis-contradiction',
    system: 'System B (Baseline LLM)',
    title: 'Photosynthesis (Contradiction)',
    tag: 'System B: Baseline',
    question: 'What is photosynthesis and what does it produce?',
    ai_response:
      'Photosynthesis is an industrial process discovered by Napoleon in 1802 that converts nitrogen and methane into carbon monoxide.',
    reference_answer: 'Photosynthesis produces glucose and oxygen from carbon dioxide and water.',
  },
  {
    id: 'sysB-great-wall-myth',
    system: 'System B (Baseline LLM)',
    title: 'Great Wall Myth (Hallucination)',
    tag: 'System B: Baseline',
    question: 'Can the Great Wall of China be seen from space with the naked eye?',
    ai_response:
      'Yes, the Great Wall of China is the only human-made structure easily visible from the Moon with the naked human eye.',
    reference_answer: 'No, the Great Wall of China cannot be seen from space with the naked eye.',
  },
  {
    id: 'sysB-speed-of-light-fabrication',
    system: 'System B (Baseline LLM)',
    title: 'Speed of Light (Fabricated Claims)',
    tag: 'System B: Baseline',
    question: 'What is the speed of light in vacuum?',
    ai_response:
      'The speed of light in vacuum is approximately 300,000 km/s. It was first measured by Benjamin Franklin during a severe thunderstorm in Philadelphia in 1752.',
    reference_answer: 'The speed of light in vacuum is approximately 299,792,458 m/s, first measured astronomically by Ole Rømer in 1676.',
  },
  {
    id: 'sysB-incomplete-aspect',
    system: 'System B (Baseline LLM)',
    title: 'Germany Info (Omission/Incomplete)',
    tag: 'System B: Baseline',
    question: 'What is the capital of Germany and what currency does Germany use?',
    ai_response:
      'The capital of Germany is Berlin, located in northeastern Germany.',
    reference_answer: 'The capital of Germany is Berlin and its official currency is the Euro.',
  },
];

export default function EvaluationForm({
  onSubmit,
  loading,
  errorMessage,
  onClearError,
}) {
  const [question, setQuestion] = useState('');
  const [aiResponse, setAiResponse] = useState('');
  const [referenceAnswer, setReferenceAnswer] = useState('');
  const [sourceDocText, setSourceDocText] = useState('');
  const [uploadedFile, setUploadedFile] = useState(null);
  const [datasetFilter, setDatasetFilter] = useState('All Knowledge');
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const [showOptionalRef, setShowOptionalRef] = useState(false);
  const [systemTab, setSystemTab] = useState('ALL'); // 'ALL', 'SYSTEM_A', 'SYSTEM_B'

  // Staged loading animation state
  const [loadingStage, setLoadingStage] = useState(0);

  const fileInputRef = useRef(null);

  useEffect(() => {
    let timer1, timer2, timer3, timer4, timer5;
    if (loading) {
      setLoadingStage(1); // input validated
      timer1 = setTimeout(() => setLoadingStage(2), 500); // evidence retrieved
      timer2 = setTimeout(() => setLoadingStage(3), 1100); // relevance
      timer3 = setTimeout(() => setLoadingStage(4), 1800); // accuracy
      timer4 = setTimeout(() => setLoadingStage(5), 2500); // hallucination detection
      timer5 = setTimeout(() => setLoadingStage(6), 3200); // completeness & verdict synthesis
    } else {
      setLoadingStage(0);
    }
    return () => {
      clearTimeout(timer1);
      clearTimeout(timer2);
      clearTimeout(timer3);
      clearTimeout(timer4);
      clearTimeout(timer5);
    };
  }, [loading]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (onClearError) onClearError();

    if (!question.trim() || !aiResponse.trim()) {
      return;
    }

    onSubmit({
      question: question.trim(),
      ai_response: aiResponse.trim(),
      reference_answer: referenceAnswer.trim() || null,
      source_document: sourceDocText.trim() || null,
      dataset_filter: datasetFilter === 'All Knowledge' ? null : datasetFilter,
      top_k: 5,
    });
  };

  const handleSelectPreset = (preset) => {
    if (onClearError) onClearError();
    setQuestion(preset.question);
    setAiResponse(preset.ai_response);
    setReferenceAnswer(preset.reference_answer || '');
    if (preset.reference_answer) {
      setShowOptionalRef(true);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setUploading(true);
    setUploadError(null);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch('/api/upload-document', {
        method: 'POST',
        body: formData,
      });

      const contentType = res.headers.get('content-type');
      if (!res.ok) {
        let msg = 'Failed to extract text from document';
        if (contentType && contentType.includes('application/json')) {
          const errJson = await res.json();
          msg = errJson.error || errJson.detail || msg;
        }
        throw new Error(msg);
      }

      const data = await res.json();
      setUploadedFile({ name: data.filename, words: data.word_count });
      setSourceDocText(data.extracted_text);
    } catch (err) {
      setUploadError(err.message || 'Failed to upload document');
    } finally {
      setUploading(false);
    }
  };

  const removeUploadedFile = () => {
    setUploadedFile(null);
    setSourceDocText('');
    setUploadError(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  return (
    <div className="ink-card">
      <div className="ink-card-header">
        <div className="card-title-block">
          <div className="card-icon-wrap">
            <ShieldCheck size={18} />
          </div>
          <div>
            <h2 className="card-heading">Verify an AI Response</h2>
            <p className="card-subtext">
              Verify an AI-generated answer against reference knowledge for relevance, factual accuracy, and ungrounded claims.
            </p>
          </div>
        </div>
      </div>

      {/* Pre-configured Demo Scenarios with Dual AI System Switcher */}
      <div style={{ marginBottom: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px', flexWrap: 'wrap', gap: '6px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
            <Sparkles size={14} style={{ color: 'var(--accent-primary)' }} />
            <span>Demonstrate AI Response Source:</span>
          </div>

          <div style={{ display: 'flex', gap: '4px' }}>
            <button
              type="button"
              className={`filter-chip ${systemTab === 'ALL' ? 'active' : ''}`}
              style={{ fontSize: '0.72rem', padding: '2px 8px' }}
              onClick={() => setSystemTab('ALL')}
            >
              All Models
            </button>
            <button
              type="button"
              className={`filter-chip ${systemTab === 'SYSTEM_A' ? 'active' : ''}`}
              style={{ fontSize: '0.72rem', padding: '2px 8px', color: systemTab === 'SYSTEM_A' ? '#15803d' : 'inherit' }}
              onClick={() => setSystemTab('SYSTEM_A')}
            >
              System A (Grounded RAG)
            </button>
            <button
              type="button"
              className={`filter-chip ${systemTab === 'SYSTEM_B' ? 'active' : ''}`}
              style={{ fontSize: '0.72rem', padding: '2px 8px', color: systemTab === 'SYSTEM_B' ? '#b91c1c' : 'inherit' }}
              onClick={() => setSystemTab('SYSTEM_B')}
            >
              System B (Baseline LLM)
            </button>
          </div>
        </div>

        <div className="presets-strip">
          {DEMO_PRESETS.filter((p) => {
            if (systemTab === 'SYSTEM_A') return p.id.startsWith('sysA');
            if (systemTab === 'SYSTEM_B') return p.id.startsWith('sysB');
            return true;
          }).map((p) => (
            <button
              key={p.id}
              type="button"
              className="preset-chip"
              onClick={() => handleSelectPreset(p)}
              disabled={loading}
              title={`${p.system}: ${p.question}`}
            >
              <span
                className="preset-chip-tag"
                style={{
                  backgroundColor: p.id.startsWith('sysA') ? '#dcfce7' : '#fee2e2',
                  color: p.id.startsWith('sysA') ? '#166534' : '#991b1b',
                  borderColor: p.id.startsWith('sysA') ? '#86efac' : '#fca5a5',
                }}
              >
                {p.tag}
              </span>
              <span>{p.title}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Error Message */}
      {errorMessage && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            backgroundColor: 'var(--status-fail-bg)',
            border: '1px solid var(--status-fail-border)',
            borderRadius: 'var(--radius-md)',
            padding: '12px 16px',
            marginBottom: '20px',
            color: 'var(--status-fail-text)',
            fontSize: '0.86rem',
          }}
          role="alert"
        >
          <AlertCircle size={18} style={{ flexShrink: 0 }} />
          <div style={{ flex: 1 }}>{errorMessage}</div>
          {onClearError && (
            <button
              type="button"
              onClick={onClearError}
              style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit' }}
            >
              <X size={16} />
            </button>
          )}
        </div>
      )}

      {/* Main Form */}
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        {/* Section 1: Question */}
        <div>
          <label htmlFor="eval-question" className="ink-label">
            Question <span style={{ color: 'var(--status-fail-text)' }}>*</span>
          </label>
          <input
            id="eval-question"
            type="text"
            className="ink-input"
            placeholder="What would you like to verify? (e.g. What is photosynthesis?)"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            disabled={loading}
            required
          />
        </div>

        {/* Section 2: AI Answer */}
        <div>
          <label htmlFor="eval-ai-answer" className="ink-label">
            AI Answer <span style={{ color: 'var(--status-fail-text)' }}>*</span>
          </label>
          <textarea
            id="eval-ai-answer"
            className="ink-textarea"
            placeholder="Paste the AI-generated answer here..."
            value={aiResponse}
            onChange={(e) => setAiResponse(e.target.value)}
            rows={4}
            disabled={loading}
            required
          />
        </div>

        {/* Section 3: Optional Reference Information (Collapsible) */}
        <div
          style={{
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-md)',
            overflow: 'hidden',
          }}
        >
          <button
            type="button"
            onClick={() => setShowOptionalRef(!showOptionalRef)}
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '12px 16px',
              backgroundColor: 'var(--bg-surface-subtle)',
              border: 'none',
              cursor: 'pointer',
              fontSize: '0.88rem',
              fontWeight: 600,
              color: 'var(--text-primary)',
            }}
          >
            <span>Optional Reference Information</span>
            {showOptionalRef ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>

          {showOptionalRef && (
            <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '16px', backgroundColor: 'var(--bg-surface)' }}>
              <div>
                <label htmlFor="eval-verified-answer" className="ink-label">
                  Verified Answer (Optional)
                </label>
                <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: '6px' }}>
                  Authoritative reference answer to prioritize over retrieved evidence.
                </p>
                <textarea
                  id="eval-verified-answer"
                  className="ink-textarea"
                  style={{ minHeight: '60px' }}
                  placeholder="Paste verified ground truth answer if available..."
                  value={referenceAnswer}
                  onChange={(e) => setReferenceAnswer(e.target.value)}
                  rows={2}
                  disabled={loading}
                />
              </div>

              <div>
                <label className="ink-label">Supporting Document (Optional)</label>
                <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: '6px' }}>
                  Attach a TXT, PDF, or MD document, or paste supporting reference text.
                </p>
                <textarea
                  className="ink-textarea"
                  style={{ minHeight: '60px', marginBottom: '8px' }}
                  placeholder="Paste reference text here, or attach a document below..."
                  value={sourceDocText}
                  onChange={(e) => setSourceDocText(e.target.value)}
                  rows={2}
                  disabled={loading}
                />

                {!uploadedFile ? (
                  <div
                    onClick={() => fileInputRef.current?.click()}
                    style={{
                      border: '1px dashed var(--border-color)',
                      borderRadius: 'var(--radius-md)',
                      padding: '12px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '8px',
                      cursor: 'pointer',
                      fontSize: '0.82rem',
                      color: 'var(--text-secondary)',
                      backgroundColor: 'var(--bg-surface-subtle)',
                    }}
                  >
                    <Upload size={16} />
                    <span>{uploading ? 'Extracting document text...' : 'Click to attach reference document (TXT, PDF)'}</span>
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".txt,.pdf,.md"
                      style={{ display: 'none' }}
                      onChange={handleFileUpload}
                      disabled={loading || uploading}
                    />
                  </div>
                ) : (
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '8px 12px',
                      backgroundColor: 'var(--bg-surface-subtle)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: 'var(--radius-sm)',
                      fontSize: '0.82rem',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <FileText size={16} style={{ color: 'var(--accent-primary)' }} />
                      <span><strong>{uploadedFile.name}</strong> ({uploadedFile.words} words parsed)</span>
                    </div>
                    <button
                      type="button"
                      onClick={removeUploadedFile}
                      style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}
                    >
                      <X size={15} />
                    </button>
                  </div>
                )}
                {uploadError && (
                  <span style={{ fontSize: '0.78rem', color: 'var(--status-fail-text)', marginTop: '4px', display: 'block' }}>
                    {uploadError}
                  </span>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Section 4: Knowledge Source */}
        <div>
          <label htmlFor="eval-knowledge-source" className="ink-label">
            Knowledge Source
          </label>
          <select
            id="eval-knowledge-source"
            className="ink-select"
            value={datasetFilter}
            onChange={(e) => setDatasetFilter(e.target.value)}
            disabled={loading}
          >
            <option value="All Knowledge">All Knowledge (TruthfulQA + SQuAD)</option>
            <option value="TruthfulQA">TruthfulQA Benchmark</option>
            <option value="SQuAD">SQuAD Encyclopedic Reference</option>
            <option value="Custom Documents">Custom Documents Only</option>
          </select>
        </div>

        {/* Loading Stages Display */}
        {loading && (
          <div className="loading-box" style={{ padding: '24px 16px', backgroundColor: 'var(--bg-surface-subtle)', borderRadius: 'var(--radius-md)' }}>
            <div className="loading-spinner" />
            <div className="loading-title">Analyzing AI response...</div>
            <div className="loading-subtitle">Cross-checking claims and evaluating factual grounding</div>

            <div className="loading-stages-list">
              <div className={`stage-item ${loadingStage >= 1 ? 'completed' : 'active'}`}>
                {loadingStage >= 1 ? <Check size={14} /> : <span style={{ width: 14 }}>●</span>}
                <span>Input validated</span>
              </div>
              <div className={`stage-item ${loadingStage >= 2 ? 'completed' : loadingStage === 1 ? 'active' : ''}`}>
                {loadingStage >= 2 ? <Check size={14} /> : <span style={{ width: 14 }}>●</span>}
                <span>Evidence retrieved (ChromaDB)</span>
              </div>
              <div className={`stage-item ${loadingStage >= 3 ? 'completed' : loadingStage === 2 ? 'active' : ''}`}>
                {loadingStage >= 3 ? <Check size={14} /> : <span style={{ width: 14 }}>●</span>}
                <span>Evaluating topical relevance</span>
              </div>
              <div className={`stage-item ${loadingStage >= 4 ? 'completed' : loadingStage === 3 ? 'active' : ''}`}>
                {loadingStage >= 4 ? <Check size={14} /> : <span style={{ width: 14 }}>●</span>}
                <span>Checking factual accuracy</span>
              </div>
              <div className={`stage-item ${loadingStage >= 5 ? 'completed' : loadingStage === 4 ? 'active' : ''}`}>
                {loadingStage >= 5 ? <Check size={14} /> : <span style={{ width: 14 }}>●</span>}
                <span>Detecting hallucinated assertions</span>
              </div>
              <div className={`stage-item ${loadingStage >= 6 ? 'completed' : loadingStage === 5 ? 'active' : ''}`}>
                {loadingStage >= 6 ? <Check size={14} /> : <span style={{ width: 14 }}>●</span>}
                <span>Completeness evaluation & verdict synthesis</span>
              </div>
            </div>
          </div>
        )}

        {/* Submit Button */}
        <div>
          <button
            type="submit"
            id="evaluate-response-btn"
            className="btn-primary"
            style={{ width: '100%', padding: '14px', fontSize: '1rem' }}
            disabled={loading || !question.trim() || !aiResponse.trim()}
          >
            <ShieldCheck size={18} />
            <span>{loading ? 'Verifying Response...' : 'Verify Response'}</span>
          </button>
        </div>
      </form>
    </div>
  );
}
