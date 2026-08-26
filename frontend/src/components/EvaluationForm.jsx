import React, { useState, useRef } from 'react';
import { Send, Upload, FileText, X, Sparkles } from 'lucide-react';

const SAMPLE_QUERIES = [
  {
    label: 'Great Wall of China (Misconception)',
    question: 'Can the Great Wall of China be seen from the Moon with the naked eye?',
    ai_response: 'Yes, the Great Wall of China is the only human-made object visible from the Moon with the naked eye.',
    reference_answer: 'No, the Great Wall of China cannot be seen from the Moon without optical aids.',
  },
  {
    label: 'Oxygen Discovery (Historical Fact)',
    question: 'Who discovered oxygen and in what year?',
    ai_response: 'Oxygen was discovered independently by Carl Wilhelm Scheele in 1772 and Joseph Priestley in 1774.',
    reference_answer: 'Joseph Priestley and Carl Wilhelm Scheele are credited with discovering oxygen in the 1770s.',
  },
  {
    label: 'Moon Landing — Historical Fact',
    question: 'When did Apollo 11 land on the Moon and who was the first person to walk on it?',
    ai_response: 'Apollo 11 landed on the Moon on July 20, 1969, and Neil Armstrong was the first person to walk on the lunar surface.',
    reference_answer: 'Apollo 11 landed on the Moon on July 20, 1969. Neil Armstrong became the first human to step onto the lunar surface.',
  }
];

export default function EvaluationForm({ onSubmit, loading }) {
  const [question, setQuestion] = useState('');
  const [aiResponse, setAiResponse] = useState('');
  const [referenceAnswer, setReferenceAnswer] = useState('');
  const [sourceDocText, setSourceDocText] = useState('');
  const [uploadedFile, setUploadedFile] = useState(null);
  const [topK, setTopK] = useState(5);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef(null);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!question.trim() || !aiResponse.trim()) {
      alert('Please fill in both the Question and the AI Generated Response fields.');
      return;
    }
    onSubmit({
      question: question.trim(),
      ai_response: aiResponse.trim(),
      reference_answer: referenceAnswer.trim() || null,
      source_document: sourceDocText.trim() || null,
      top_k: parseInt(topK, 10) || 5,
    });
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch('/api/upload-document', {
        method: 'POST',
        body: formData,
      });
      if (!res.ok) throw new Error('Upload failed');
      const data = await res.json();
      setUploadedFile({ name: data.filename, type: data.file_type, words: data.word_count });
      setSourceDocText(data.extracted_text);
    } catch (err) {
      alert('Failed to parse uploaded document: ' + err.message);
    } finally {
      setUploading(false);
    }
  };

  const removeUploadedFile = () => {
    setUploadedFile(null);
    setSourceDocText('');
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const loadSample = (sample) => {
    setQuestion(sample.question);
    setAiResponse(sample.ai_response);
    setReferenceAnswer(sample.reference_answer || '');
  };

  return (
    <div className="panel-card">
      <div className="panel-header">
        <h2>
          <Send size={18} color="#818CF8" />
          Evaluation Submission
        </h2>
        <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>* Required fields</span>
      </div>

      <div style={{ marginBottom: '1rem' }}>
        <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.4rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <Sparkles size={14} color="#818CF8" />
          Quick Test Examples:
        </div>
        <div className="example-chips">
          {SAMPLE_QUERIES.map((sample, idx) => (
            <button
              key={idx}
              type="button"
              className="chip-btn"
              onClick={() => loadSample(sample)}
            >
              {sample.label}
            </button>
          ))}
        </div>
      </div>

      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label className="form-label">
            Question <span className="required-star">*</span>
          </label>
          <input
            type="text"
            className="form-input"
            placeholder="e.g., Can the Great Wall of China be seen from the Moon?"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            required
          />
        </div>

        <div className="form-group">
          <label className="form-label">
            AI-Generated Response <span className="required-star">*</span>
            <span className="label-hint">Response to be grounded & checked</span>
          </label>
          <textarea
            className="form-textarea"
            placeholder="Paste the model's generated answer here..."
            value={aiResponse}
            onChange={(e) => setAiResponse(e.target.value)}
            rows={4}
            required
          />
        </div>

        <div className="form-group">
          <label className="form-label">
            Reference Answer <span className="label-hint">(Optional ground truth)</span>
          </label>
          <textarea
            className="form-textarea"
            placeholder="Optional verified answer..."
            value={referenceAnswer}
            onChange={(e) => setReferenceAnswer(e.target.value)}
            rows={2}
          />
        </div>

        <div className="form-group">
          <label className="form-label">
            Source Document <span className="label-hint">(Optional TXT / PDF upload or raw text)</span>
          </label>
          <textarea
            className="form-textarea"
            placeholder="Optional raw source text or upload a document below..."
            value={sourceDocText}
            onChange={(e) => setSourceDocText(e.target.value)}
            rows={2}
          />

          {!uploadedFile ? (
            <div
              className="file-upload-box"
              onClick={() => fileInputRef.current?.click()}
            >
              <Upload size={20} color="#818CF8" style={{ margin: '0 auto 0.3rem auto' }} />
              <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                {uploading ? 'Extracting text...' : 'Click to attach TXT or PDF document'}
              </div>
              <input
                ref={fileInputRef}
                type="file"
                accept=".txt,.pdf,.md"
                style={{ display: 'none' }}
                onChange={handleFileUpload}
              />
            </div>
          ) : (
            <div className="uploaded-file-info">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <FileText size={16} color="#818CF8" />
                <span><strong>{uploadedFile.name}</strong> ({uploadedFile.words} words extracted)</span>
              </div>
              <button
                type="button"
                onClick={removeUploadedFile}
                style={{ background: 'transparent', border: 'none', color: '#F43F5E', cursor: 'pointer' }}
              >
                <X size={16} />
              </button>
            </div>
          )}
        </div>

        <div className="form-group" style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <label className="form-label" style={{ margin: 0 }}>
            Retrieved Evidence Chunks (Top-K):
          </label>
          <select
            className="form-input"
            style={{ width: '90px', padding: '0.4rem 0.6rem' }}
            value={topK}
            onChange={(e) => setTopK(e.target.value)}
          >
            <option value="3">3</option>
            <option value="5">5</option>
            <option value="8">8</option>
            <option value="10">10</option>
          </select>
        </div>

        <button
          type="submit"
          className="btn-primary"
          disabled={loading || !question.trim() || !aiResponse.trim()}
        >
          {loading ? 'Retrieving Evidence...' : 'Retrieve & Validate Evidence'}
        </button>
      </form>
    </div>
  );
}
