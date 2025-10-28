import { useState } from 'react';
import { Search, Loader, AlertCircle, BookOpen, FileText } from 'lucide-react';
import { queryGraph } from '../utils/api';

const QueryInterface = () => {
  const [question, setQuestion] = useState('');
  const [minConfidence, setMinConfidence] = useState(0.8);
  const [documentFilter, setDocumentFilter] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!question.trim()) {
      setError('Please enter a question');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await queryGraph(
        question,
        minConfidence,
        documentFilter || null
      );
      setResult(response);
    } catch (err) {
      console.error('Query error:', err);
      setError(err.response?.data?.error || err.message || 'Query failed');
    } finally {
      setLoading(false);
    }
  };

  const getKarakaColor = (karaka) => {
    const colors = {
      'KARTA': '#ef4444',      // red
      'KARMA': '#3b82f6',      // blue
      'SAMPRADANA': '#10b981', // green
      'KARANA': '#eab308',     // yellow
      'ADHIKARANA': '#a855f7', // purple
      'APADANA': '#f97316'     // orange
    };
    return colors[karaka] || '#6b7280';
  };

  const formatAnswerWithKarakas = (answer, karakas) => {
    if (!karakas) return answer;
    
    return (
      <div className="answer-text">
        {answer}
      </div>
    );
  };

  return (
    <div className="query-interface">
      <h2 className="section-title">
        <Search size={20} />
        Query Knowledge Graph
      </h2>

      <form onSubmit={handleSubmit} className="query-form">
        <div className="form-group">
          <label htmlFor="question">Natural Language Question</label>
          <textarea
            id="question"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="e.g., Who gave bow to Lakshmana?"
            disabled={loading}
            className="question-input"
            rows={3}
          />
        </div>

        <div className="form-row">
          <div className="form-group">
            <label htmlFor="confidence">Min Confidence</label>
            <input
              type="number"
              id="confidence"
              value={minConfidence}
              onChange={(e) => setMinConfidence(parseFloat(e.target.value))}
              min="0"
              max="1"
              step="0.1"
              disabled={loading}
              className="confidence-input"
            />
          </div>

          <div className="form-group">
            <label htmlFor="document-filter">Document Filter (optional)</label>
            <input
              type="text"
              id="document-filter"
              value={documentFilter}
              onChange={(e) => setDocumentFilter(e.target.value)}
              placeholder="doc_123"
              disabled={loading}
              className="document-filter-input"
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={loading || !question.trim()}
          className="query-button"
        >
          {loading ? (
            <>
              <Loader size={18} className="spinner" />
              Processing...
            </>
          ) : (
            <>
              <Search size={18} />
              Query
            </>
          )}
        </button>
      </form>

      {error && (
        <div className="status-message error">
          <AlertCircle size={18} />
          <div>{error}</div>
        </div>
      )}

      {result && (
        <div className="query-result">
          <div className="answer-section">
            <h3 className="result-title">
              <BookOpen size={18} />
              Answer
            </h3>
            {formatAnswerWithKarakas(result.answer, result.karakas)}
            
            {result.karakas && (
              <div className="karakas-info">
                <div className="karaka-label">Semantic Roles:</div>
                <div className="karaka-tags">
                  {result.karakas.target && (
                    <span 
                      className="karaka-tag"
                      style={{ backgroundColor: getKarakaColor(result.karakas.target) }}
                    >
                      Target: {result.karakas.target}
                    </span>
                  )}
                  {result.karakas.constraints && Object.entries(result.karakas.constraints).map(([role, entity]) => (
                    <span 
                      key={role}
                      className="karaka-tag"
                      style={{ backgroundColor: getKarakaColor(role) }}
                    >
                      {role}: {entity}
                    </span>
                  ))}
                </div>
              </div>
            )}
            
            {result.confidence !== undefined && (
              <div className="confidence-badge">
                Confidence: {(result.confidence * 100).toFixed(1)}%
              </div>
            )}
          </div>

          {result.sources && result.sources.length > 0 && (
            <div className="sources-section">
              <h3 className="result-title">
                <FileText size={18} />
                Sources ({result.sources.length})
              </h3>
              <div className="sources-list">
                {result.sources.map((source, index) => (
                  <div key={index} className="source-item">
                    <div className="source-header">
                      <span className="source-number">#{index + 1}</span>
                      <span className="source-confidence">
                        {(source.confidence * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div className="source-text">
                      "{source.text || source.line_text}"
                    </div>
                    <div className="source-meta">
                      <span>Line {source.line_number}</span>
                      {source.document_name && (
                        <>
                          <span className="separator">•</span>
                          <span>{source.document_name}</span>
                        </>
                      )}
                      {source.document_id && (
                        <>
                          <span className="separator">•</span>
                          <span className="doc-id">{source.document_id}</span>
                        </>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default QueryInterface;
