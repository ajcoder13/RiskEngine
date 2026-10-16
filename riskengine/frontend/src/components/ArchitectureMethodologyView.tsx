import React from 'react';
import { Layers, Database, Cpu, Compass, Activity, ShieldCheck, FileText, CheckCircle2 } from 'lucide-react';

export const ArchitectureMethodologyView: React.FC = () => {
  return (
    <div>
      {/* Overview Card */}
      <div className="glass-card" style={{ marginBottom: '1.75rem' }}>
        <div className="card-header">
          <div>
            <div className="card-title">
              <Layers size={20} style={{ color: '#3b82f6' }} />
              System Architecture & Quantitative Methodology
            </div>
            <div className="card-subtitle">
              End-to-end engineering pipeline converting unstructured news & social feeds into structured financial risk signals.
            </div>
          </div>
        </div>

        {/* Visual Architecture Flow */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
            gap: '1rem',
            margin: '1.5rem 0',
          }}
        >
          <div style={{ background: '#111827', padding: '1.25rem', borderRadius: '10px', borderTop: '3px solid #3b82f6' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#60a5fa', fontWeight: 700, marginBottom: '0.5rem' }}>
              <Database size={16} /> 1. Ingestion Engine
            </div>
            <div style={{ fontSize: '0.8rem', color: '#9ca3af' }}>
              • Dual-source: News headlines & Twitter/X streams
              <br />• SHA-1 content deduplication
              <br />• Source trust priors: Reuters 0.95, NewsAPI 0.75, GDELT 0.70, Tweets 0.40
            </div>
          </div>

          <div style={{ background: '#111827', padding: '1.25rem', borderRadius: '10px', borderTop: '3px solid #8b5cf6' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#a78bfa', fontWeight: 700, marginBottom: '0.5rem' }}>
              <Cpu size={16} /> 2. NLP Pipeline
            </div>
            <div style={{ fontSize: '0.8rem', color: '#9ca3af' }}>
              • High-precision Entity Recognition ($TICKER / aliases)
              <br />• FinBERT financial sentiment model
              <br />• 14-class Event taxonomy classifier
            </div>
          </div>

          <div style={{ background: '#111827', padding: '1.25rem', borderRadius: '10px', borderTop: '3px solid #f59e0b' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#fbbf24', fontWeight: 700, marginBottom: '0.5rem' }}>
              <Compass size={16} /> 3. Risk Signal Engine
            </div>
            <div style={{ fontSize: '0.8rem', color: '#9ca3af' }}>
              • Multi-factor ordinal impact synthesis (1.0 - 10.0)
              <br />• Exponential time decay & novelty gating
              <br />• Automated stress trigger thresholding
            </div>
          </div>

          <div style={{ background: '#111827', padding: '1.25rem', borderRadius: '10px', borderTop: '3px solid #10b981' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#34d399', fontWeight: 700, marginBottom: '0.5rem' }}>
              <Activity size={16} /> 4. Module A: Rebalance
            </div>
            <div style={{ fontSize: '0.8rem', color: '#9ca3af' }}>
              • Tactical weight tilting based on sentiment
              <br />• Strict turnover budget constraint (L1 norm)
              <br />• Historical backtesting vs. equal & cap weights
            </div>
          </div>

          <div style={{ background: '#111827', padding: '1.25rem', borderRadius: '10px', borderTop: '3px solid #ef4444' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#f87171', fontWeight: 700, marginBottom: '0.5rem' }}>
              <ShieldCheck size={16} /> 5. Module B: Stress Test
            </div>
            <div style={{ fontSize: '0.8rem', color: '#9ca3af' }}>
              • ~$89.92M multi-asset wholesale portfolio (20 positions)
              <br />• Multi-factor shock transmission (equity, credit, rate)
              <br />• Asset class & rating loss attribution
            </div>
          </div>
        </div>
      </div>

      {/* Quantitative Formulations */}
      <div className="grid-2" style={{ marginBottom: '1.75rem' }}>
        <div className="glass-card">
          <div className="card-title" style={{ marginBottom: '1rem' }}>
            Multi-Factor Risk Impact Formula
          </div>
          <div style={{ fontSize: '0.85rem', color: '#d1d5db', lineHeight: 1.7 }}>
            Impact represents an <strong>ordinal severity index</strong> calibrated between 1.0 and 10.0:
            <div
              className="mono"
              style={{
                background: '#111827',
                padding: '0.85rem',
                borderRadius: '6px',
                margin: '0.75rem 0',
                color: '#60a5fa',
                fontSize: '0.8rem',
              }}
            >
              raw = (0.60×severity + 0.40×|sentiment|) × f_conf × f_rel × f_mkt × f_nov × f_rec
              Impact = clamp(1.0 + 9.0 × raw^0.70, 1.0, 10.0)
            </div>
            where:
            <ul style={{ paddingLeft: '1.25rem', marginTop: '0.5rem', color: '#9ca3af', fontSize: '0.8rem' }}>
              <li><strong>severity:</strong> Event-class prior 0.15 (Other) → 0.90 (Credit Event). Weight w_sev=0.60.</li>
              <li><strong>sentiment:</strong> Signed polarity [-1.0, +1.0] from FinBERT/lexicon. Weight w_sent=0.40.</li>
              <li><strong>f_rel:</strong> Source reliability: Reuters/Bloomberg 0.95, NewsAPI 0.75, GDELT 0.70, Tweets 0.40.</li>
              <li><strong>f_nov:</strong> Novelty = 1/(1 + 0.5 × n_similar). Decays for repeated stories.</li>
              <li><strong>f_rec:</strong> Recency = exp(−ln2 × age_hours / 48). Half-life of 48 hours.</li>
              <li><strong>gamma=0.70:</strong> Power-law curve lifts mid-range scores; each f_x has a floor so no single factor zeroes a signal.</li>
            </ul>
          </div>
        </div>

        <div className="glass-card">
          <div className="card-title" style={{ marginBottom: '1rem' }}>
            Module A & B Quantitative Invariants
          </div>
          <div style={{ fontSize: '0.85rem', color: '#d1d5db', lineHeight: 1.7 }}>
            <strong>Module A (Tactical Portfolio Optimization):</strong>
            <div
              className="mono"
              style={{
                background: '#111827',
                padding: '0.85rem',
                borderRadius: '6px',
                margin: '0.75rem 0',
                color: '#34d399',
                fontSize: '0.8rem',
              }}
            >
              w_raw = w_base × (1 + tilt × s_i)
              <br />
              subject to: ∑ w_i = 1, w_min ≤ w_i ≤ w_max, 0.5 ∑ |w_i - w_base| ≤ turnover_cap
            </div>
            <strong>Module B (Stress Shock Transmission):</strong>
            <div
              className="mono"
              style={{
                background: '#111827',
                padding: '0.85rem',
                borderRadius: '6px',
                margin: '0.75rem 0',
                color: '#f87171',
                fontSize: '0.8rem',
              }}
            >
              ΔV_equity = V × shock_equity
              <br />
              ΔV_bonds = V × (-Duration × Δyield)
              <br />
              ΔV_credit = V × (-Duration × Δspread + ΔPD × (1 - Recovery))
            </div>
          </div>
        </div>
      </div>

      {/* Honest Engineering Disclosure Card */}
      <div className="glass-card" style={{ borderLeft: '4px solid #10b981' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem', color: '#34d399', fontWeight: 700 }}>
          <CheckCircle2 size={18} /> Transparency & Hackathon Credibility Disclosures
        </div>
        <div style={{ fontSize: '0.825rem', color: '#9ca3af', lineHeight: 1.6 }}>
          • <strong>No Fabricated Performance:</strong> Market prices are retrieved live via Yahoo Finance (yfinance) when connectivity is active; synthetic price simulations fallback transparently with explicit metadata flags.
          <br />• <strong>Non-Predictive Honesty:</strong> Risk impact scores are ordinal severity metrics, not crystal-ball price forecasts.
          <br />• <strong>Turnover Feasibility:</strong> Module A strictly enforces institutional turnover caps to eliminate unrealistic backtest churn.
          <br />• <strong>Real Multi-Asset Book:</strong> Module B models duration, convexity, credit spread widening, and counterparty default probabilities across corporate bonds, sovereign debt, equities, and credit default swaps.
        </div>
      </div>
    </div>
  );
};
