import React, { useState } from 'react';
import { Signal } from '../api/types';
import { apiClient } from '../api/client';
import { Sparkles, Play, CheckCircle, AlertTriangle, ArrowRight, Layers, Cpu, ShieldAlert } from 'lucide-react';

const PRESETS = [
  {
    title: 'Geopolitical Shock',
    text: 'Military escalation in the Middle East threatens key oil shipping lanes; crude oil jumps 8.5% in global markets.',
    source: 'news' as const,
  },
  {
    title: 'Cybersecurity Attack',
    text: 'Microsoft discloses sophisticated zero-day cyberattack impacting internal cloud security and enterprise customers.',
    source: 'news' as const,
  },
  {
    title: 'Regulatory Investigation',
    text: 'Tesla faces escalating federal DOJ probe into automated driving claims; regulators weigh mandatory nationwide recall.',
    source: 'news' as const,
  },
  {
    title: 'Credit Event / Default',
    text: 'Major subprime auto lender initiates Chapter 11 bankruptcy filing as provisioning rises sharply across JPMorgan books.',
    source: 'news' as const,
  },
  {
    title: 'Favourable Tech Earnings',
    text: 'Apple beats quarterly earnings estimates on strong iPhone demand in Asia and announces record $110B share buyback.',
    source: 'news' as const,
  },
  {
    title: 'Social Media Panic Tweet',
    text: '$BA Boeing groundings continue after FAA warning, airline cancels thousands of flights over supplier component defects.',
    source: 'tweet' as const,
  },
];

interface Props {
  onForwardToStress?: (signal: Signal) => void;
}

export const NLPInteractiveSandbox: React.FC<Props> = ({ onForwardToStress }) => {
  const [inputText, setInputText] = useState(PRESETS[0].text);
  const [sourceType, setSourceType] = useState<'news' | 'tweet'>('news');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<Signal[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleRunAnalysis = async () => {
    if (!inputText.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.analyzeText(inputText, sourceType);
      setResults(data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Analysis failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="glass-card" style={{ marginBottom: '1.5rem' }}>
        <div className="card-header">
          <div>
            <div className="card-title">
              <Cpu size={20} style={{ color: '#3b82f6' }} />
              Interactive NLP & Signal Extraction Sandbox
            </div>
            <div className="card-subtitle">
              Input any arbitrary unstructured news headline, analyst note, or financial tweet to inspect full end-to-end processing.
            </div>
          </div>
        </div>

        {/* Preset chips */}
        <div style={{ marginBottom: '1.25rem' }}>
          <div style={{ fontSize: '0.8rem', color: '#9ca3af', marginBottom: '0.5rem', fontWeight: 600 }}>
            Quick Pre-loaded Scenarios:
          </div>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            {PRESETS.map((p, idx) => (
              <button
                key={idx}
                className="btn btn-secondary btn-sm"
                onClick={() => {
                  setInputText(p.text);
                  setSourceType(p.source);
                }}
              >
                {p.title}
              </button>
            ))}
          </div>
        </div>

        {/* Text Input Area */}
        <div className="form-group">
          <label className="form-label">Input Text</label>
          <textarea
            className="form-textarea"
            rows={3}
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder="Type or paste unstructured financial text here..."
          />
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
            <span style={{ fontSize: '0.85rem', color: '#9ca3af', fontWeight: 500 }}>Source Type:</span>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.85rem', cursor: 'pointer' }}>
              <input
                type="radio"
                name="source"
                checked={sourceType === 'news'}
                onChange={() => setSourceType('news')}
              />
              News Article (Reliability ~0.85)
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.85rem', cursor: 'pointer' }}>
              <input
                type="radio"
                name="source"
                checked={sourceType === 'tweet'}
                onChange={() => setSourceType('tweet')}
              />
              Social / Tweet (Reliability ~0.60)
            </label>
          </div>

          <button
            className="btn btn-primary"
            onClick={handleRunAnalysis}
            disabled={loading}
          >
            <Play size={16} />
            {loading ? 'Processing through Pipeline...' : 'Analyze Text'}
          </button>
        </div>

        {error && (
          <div style={{ marginTop: '1rem', padding: '0.75rem', background: 'rgba(239, 68, 68, 0.1)', color: '#f87171', borderRadius: '8px', border: '1px solid rgba(239, 68, 68, 0.3)' }}>
            {error}
          </div>
        )}
      </div>

      {/* Analysis Results */}
      {results && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {results.length === 0 ? (
            <div className="glass-card" style={{ textAlign: 'center', padding: '2rem' }}>
              <AlertTriangle size={32} style={{ color: '#f59e0b', margin: '0 auto 0.75rem' }} />
              <h3>No Relevant Financial Entities or Risk Signals Detected</h3>
              <p style={{ color: '#9ca3af', fontSize: '0.85rem', marginTop: '0.5rem' }}>
                The NLP relevance gating filter correctly identified that this text does not contain supported tickers or actionable financial risk events.
              </p>
            </div>
          ) : (
            results.map((signal, idx) => (
              <div key={idx} className="glass-card" style={{ borderLeft: '4px solid #3b82f6' }}>
                <div className="card-header">
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                      <span className="mono" style={{ fontSize: '1.3rem', fontWeight: 800, color: '#60a5fa' }}>
                        {signal.ticker}
                      </span>
                      <span style={{ fontSize: '1rem', color: '#e5e7eb', fontWeight: 600 }}>
                        {signal.company_name}
                      </span>
                      <span className="badge badge-neutral">{signal.sector}</span>
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span className={`badge badge-${signal.risk_level}`}>
                      Risk Level: {signal.risk_level.toUpperCase()}
                    </span>
                    {signal.triggers_stress_test && (
                      <span className="badge badge-critical">
                        <ShieldAlert size={12} /> Auto-Stress Trigger
                      </span>
                    )}
                  </div>
                </div>

                {/* 4 Step Pipeline Decomposition */}
                <div className="grid-3" style={{ marginBottom: '1.25rem' }}>
                  {/* Step 1: Entity & Event */}
                  <div style={{ background: '#111827', padding: '1rem', borderRadius: '8px' }}>
                    <div style={{ fontSize: '0.75rem', color: '#9ca3af', textTransform: 'uppercase', marginBottom: '0.5rem', fontWeight: 600 }}>
                      1. Entity & Event Classification
                    </div>
                    <div style={{ fontSize: '0.85rem', marginBottom: '0.25rem' }}>
                      <strong>Detected Event:</strong> <span style={{ color: '#60a5fa' }}>{signal.event_type}</span>
                    </div>
                    <div style={{ fontSize: '0.85rem', marginBottom: '0.25rem' }}>
                      <strong>Classifier Confidence:</strong> {(((signal.event_confidence ?? 0.85) * 100)).toFixed(0)}%
                    </div>
                    <div style={{ fontSize: '0.85rem' }}>
                      <strong>Event Severity Base:</strong> {signal.impact_breakdown?.event_weight ?? 'N/A'}/10
                    </div>
                  </div>

                  {/* Step 2: Sentiment Polarity */}
                  <div style={{ background: '#111827', padding: '1rem', borderRadius: '8px' }}>
                    <div style={{ fontSize: '0.75rem', color: '#9ca3af', textTransform: 'uppercase', marginBottom: '0.5rem', fontWeight: 600 }}>
                      2. FinBERT Sentiment Engine
                    </div>
                    <div style={{ fontSize: '0.85rem', marginBottom: '0.25rem' }}>
                      <strong>Sentiment:</strong>{' '}
                      <span
                        className={`badge ${
                          signal.sentiment_label === 'positive'
                            ? 'badge-positive'
                            : signal.sentiment_label === 'negative'
                            ? 'badge-negative'
                            : 'badge-neutral'
                        }`}
                      >
                        {signal.sentiment_label}
                      </span>
                    </div>
                    <div style={{ fontSize: '0.85rem', marginBottom: '0.25rem' }}>
                      <strong>Polarity Score:</strong> {signal.sentiment_score.toFixed(3)}
                    </div>
                    <div style={{ fontSize: '0.85rem' }}>
                      <strong>Direction:</strong> {signal.direction}
                    </div>
                  </div>

                  {/* Step 3: Multi-Factor Impact */}
                  <div style={{ background: '#111827', padding: '1rem', borderRadius: '8px' }}>
                    <div style={{ fontSize: '0.75rem', color: '#9ca3af', textTransform: 'uppercase', marginBottom: '0.5rem', fontWeight: 600 }}>
                      3. Multi-Factor Impact Synthesis
                    </div>
                    <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#3b82f6', marginBottom: '0.25rem' }}>
                      {signal.impact_score.toFixed(2)} / 10
                    </div>
                    <div style={{ fontSize: '0.75rem', color: '#9ca3af' }}>
                      Reliability ({signal.source_reliability}) × Novelty ({signal.novelty_factor}) × Recency ({signal.recency_weight})
                    </div>
                  </div>
                </div>

                {/* Step 4: Downstream Applications action bar */}
                <div
                  style={{
                    background: 'rgba(59, 130, 246, 0.08)',
                    border: '1px solid rgba(59, 130, 246, 0.25)',
                    padding: '1rem',
                    borderRadius: '8px',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    flexWrap: 'wrap',
                    gap: '1rem',
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '0.9rem', color: '#e5e7eb' }}>
                      Downstream Integration Impact:
                    </div>
                    <div style={{ fontSize: '0.8rem', color: '#9ca3af' }}>
                      {signal.direction === 'adverse' ? (
                        <span>
                          • Module A will <strong>reduce exposure</strong> to {signal.ticker} during tactical rebalance.
                        </span>
                      ) : (
                        <span>
                          • Module A will <strong>tilt positive allocation</strong> to {signal.ticker}.
                        </span>
                      )}
                      {signal.triggers_stress_test && (
                        <span> • Meets severe risk threshold for Module B stress-test scenario injection!</span>
                      )}
                    </div>
                  </div>

                  {onForwardToStress && (
                    <button
                      className="btn btn-primary btn-sm"
                      onClick={() => onForwardToStress(signal)}
                    >
                      Forward to Module B Stress Test <ArrowRight size={14} />
                    </button>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
};
