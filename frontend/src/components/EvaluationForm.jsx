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
