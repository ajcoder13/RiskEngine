import React, { useState } from 'react';
import { Signal, RiskSummary } from '../api/types';
import {
  AlertTriangle,
  Flame,
  TrendingDown,
  TrendingUp,
  Minus,
  Search,
  ExternalLink,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';

interface Props {
  signals: Signal[];
  summary: RiskSummary | null;
  loading: boolean;
  onSelectSignalForStress?: (signal: Signal) => void;
}

const COLORS = ['#10b981', '#f59e0b', '#f97316', '#ef4444'];
const EVENT_COLORS = ['#3b82f6', '#8b5cf6', '#06b6d4', '#ec4899', '#f59e0b', '#10b981'];

export const SignalsFeedView: React.FC<Props> = ({
  signals,
  summary,
  loading,
  onSelectSignalForStress,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [levelFilter, setLevelFilter] = useState('all');
  const [directionFilter, setDirectionFilter] = useState('all');
  const [expandedSignalId, setExpandedSignalId] = useState<string | null>(null);

  const safeSignals = Array.isArray(signals) ? signals : [];
  const filteredSignals = safeSignals.filter((s) => {
    const tickerStr = (s.ticker || '').toLowerCase();
    const companyStr = (s.company_name || s.company || '').toLowerCase();
    const textStr = (s.raw_text || s.text || '').toLowerCase();
    const eventStr = (s.event_type || '').toLowerCase();
    const searchLower = searchTerm.toLowerCase();

    const matchesSearch =
      tickerStr.includes(searchLower) ||
      companyStr.includes(searchLower) ||
      textStr.includes(searchLower) ||
      eventStr.includes(searchLower);

    const sLevel = (s.risk_level || '').toLowerCase();
    const matchesLevel = levelFilter === 'all' || sLevel === levelFilter.toLowerCase();
    const matchesDirection = directionFilter === 'all' || s.direction === directionFilter;
    return matchesSearch && matchesLevel && matchesDirection;
  });

  const levelChartData = summary?.by_level
    ? Object.entries(summary.by_level).map(([name, value]) => ({ name, value }))
    : [];

  const eventChartData = summary?.by_event
    ? Object.entries(summary.by_event)
        .slice(0, 6)
        .map(([name, count]) => ({ name: name.length > 14 ? name.slice(0, 12) + '...' : name, count }))
    : [];

  return (
    <div>
      {/* Metric KPI cards */}
      <div className="metrics-grid">
        <div className="metric-card">
          <div className="metric-label">Total Risk Signals</div>
          <div className="metric-value">{summary?.total_signals ?? signals.length}</div>
          <div className="metric-subtext">Processed from news & market feeds</div>
        </div>

        <div className="metric-card critical">
          <div className="metric-label">Critical / High Risk</div>
          <div className="metric-value">
            {(summary?.by_level?.critical ?? 0) + (summary?.by_level?.high ?? 0)}
          </div>
          <div className="metric-subtext">High impact score events</div>
        </div>

        <div className="metric-card warning">
          <div className="metric-label">Stress Test Triggers</div>
          <div className="metric-value">{summary?.stress_triggers_count ?? 0}</div>
          <div className="metric-subtext">Adverse signals meeting threshold</div>
        </div>

        <div className="metric-card purple">
          <div className="metric-label">Top At-Risk Asset</div>
          <div className="metric-value" style={{ fontSize: '1.4rem', marginTop: '0.6rem' }}>
            {summary?.top_risk_tickers?.[0]
              ? `${summary.top_risk_tickers[0][0]} (${Number(summary.top_risk_tickers[0][1] ?? 0).toFixed(1)})`
              : 'N/A'}
          </div>
          <div className="metric-subtext">Highest adverse cumulative impact</div>
        </div>
      </div>

      {/* Visual Charts Row */}
      <div className="grid-2" style={{ marginBottom: '2rem' }}>
        <div className="glass-card">
          <div className="card-header">
            <div>
              <div className="card-title">Event Type Distribution</div>
              <div className="card-subtitle">Frequency of detected financial event categories</div>
            </div>
          </div>
          <div style={{ height: '220px', width: '100%' }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={eventChartData} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
                <XAxis dataKey="name" stroke="#6b7280" fontSize={11} interval={0} angle={-15} textAnchor="end" />
                <YAxis stroke="#6b7280" fontSize={11} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1f2937', borderColor: '#374151', borderRadius: '8px' }}
                />
                <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="glass-card">
          <div className="card-header">
            <div>
              <div className="card-title">Risk Severity Breakdown</div>
              <div className="card-subtitle">Signals classified by ordinal severity level</div>
            </div>
          </div>
          <div style={{ height: '220px', width: '100%' }}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={levelChartData}
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={85}
                  paddingAngle={5}
                  dataKey="value"
                  label={({ name, percent }: { name?: string; percent?: number }) =>
                    `${name ?? ''} ${(((percent ?? 0) * 100)).toFixed(0)}%`
                  }
                >
                  {levelChartData.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ backgroundColor: '#1f2937', borderColor: '#374151', borderRadius: '8px' }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="glass-card" style={{ marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'center' }}>
          <div style={{ flex: '1 1 280px', position: 'relative' }}>
            <input
              type="text"
              placeholder="Search ticker, company, keyword, or event..."
              className="form-input"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{ paddingLeft: '2.5rem' }}
            />
            <Search
              size={16}
              style={{ position: 'absolute', left: '0.85rem', top: '50%', transform: 'translateY(-50%)', color: '#9ca3af' }}
            />
          </div>

          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
            <select
              className="form-select"
              value={levelFilter}
              onChange={(e) => setLevelFilter(e.target.value)}
              style={{ width: '150px' }}
            >
              <option value="all">All Severities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>

            <select
              className="form-select"
              value={directionFilter}
              onChange={(e) => setDirectionFilter(e.target.value)}
              style={{ width: '150px' }}
            >
              <option value="all">All Directions</option>
              <option value="adverse">Adverse</option>
              <option value="favourable">Favourable</option>
              <option value="neutral">Neutral</option>
            </select>
          </div>
        </div>
      </div>

      {/* Signals Table */}
      <div className="glass-card">
        <div className="card-header">
          <div>
            <div className="card-title">Live Risk Signals Table ({filteredSignals.length})</div>
            <div className="card-subtitle">
              Unstructured text transformed into structured quantitative risk metrics
            </div>
          </div>
        </div>

        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Ticker</th>
                <th>Company</th>
                <th>Event Type</th>
                <th>Sentiment</th>
                <th>Impact Score</th>
                <th>Risk Level</th>
                <th>Trigger Stress</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {filteredSignals.map((s) => {
                const isExpanded = expandedSignalId === s.id;
                return (
                  <React.Fragment key={s.id}>
                    <tr>
                      <td className="mono" style={{ fontWeight: 700, color: '#60a5fa' }}>
                        {s.ticker}
                      </td>
                      <td>{s.company_name}</td>
                      <td>
                        <span className="badge badge-neutral badge-pill">{s.event_type}</span>
                      </td>
                      <td>
                        <span
                          className={`badge ${
                            s.sentiment_label === 'positive'
                              ? 'badge-positive'
                              : s.sentiment_label === 'negative'
                              ? 'badge-negative'
                              : 'badge-neutral'
                          }`}
                        >
                          {s.sentiment_label === 'positive' && <TrendingUp size={12} />}
                          {s.sentiment_label === 'negative' && <TrendingDown size={12} />}
                          {s.sentiment_label === 'neutral' && <Minus size={12} />}
                          {s.sentiment_label} ({(s.sentiment_score).toFixed(2)})
                        </span>
                      </td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <span className="mono" style={{ fontWeight: 700 }}>
                            {s.impact_score.toFixed(1)} / 10
                          </span>
                          <div
                            style={{
                              width: '50px',
                              height: '6px',
                              background: '#374151',
                              borderRadius: '3px',
                              overflow: 'hidden',
                            }}
                          >
                            <div
                              style={{
                                width: `${(s.impact_score / 10) * 100}%`,
                                height: '100%',
                                background:
                                  s.risk_level === 'critical'
                                    ? '#ef4444'
                                    : s.risk_level === 'high'
                                    ? '#f97316'
                                    : s.risk_level === 'medium'
                                    ? '#f59e0b'
                                    : '#10b981',
                              }}
                            />
                          </div>
                        </div>
                      </td>
                      <td>
                        <span className={`badge badge-${s.risk_level}`}>{s.risk_level}</span>
                      </td>
                      <td>
                        {s.triggers_stress_test ? (
                          <span className="badge badge-critical badge-pill">
                            <Flame size={12} /> Yes
                          </span>
                        ) : (
                          <span style={{ color: '#6b7280', fontSize: '0.75rem' }}>No</span>
                        )}
                      </td>
                      <td>
                        <div style={{ display: 'flex', gap: '0.4rem' }}>
                          <button
                            className="btn btn-secondary btn-sm"
                            onClick={() => setExpandedSignalId(isExpanded ? null : s.id)}
                            title="View impact decomposition"
                          >
                            {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                            Details
                          </button>
                          {onSelectSignalForStress && (
                            <button
                              className="btn btn-primary btn-sm"
                              onClick={() => onSelectSignalForStress(s)}
                              title="Test this event in Module B"
                            >
                              Stress Test
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                    {isExpanded && (
                      <tr>
                        <td colSpan={8} style={{ backgroundColor: 'rgba(17, 24, 39, 0.9)', padding: '1.25rem' }}>
                          <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '1.5rem' }}>
                            <div>
                              <div style={{ fontSize: '0.75rem', color: '#9ca3af', marginBottom: '0.35rem', textTransform: 'uppercase' }}>
                                Raw Source Text ({s.source_type} • {s.source_name})
                              </div>
                              <div
                                style={{
                                  padding: '0.85rem',
                                  backgroundColor: '#1f2937',
                                  borderRadius: '6px',
                                  fontSize: '0.85rem',
                                  lineHeight: 1.5,
                                  borderLeft: '3px solid #3b82f6',
                                }}
                              >
                                "{s.raw_text}"
                              </div>
                              <div style={{ marginTop: '0.75rem', fontSize: '0.75rem', color: '#6b7280' }}>
                                Timestamp: {new Date(s.published_at || Date.now()).toLocaleString()} | Signal ID:{' '}
                                <span className="mono">{s.id.slice(0, 12)}...</span>
                              </div>
                            </div>

                            <div>
                              <div style={{ fontSize: '0.75rem', color: '#9ca3af', marginBottom: '0.35rem', textTransform: 'uppercase' }}>
                                Impact Multi-Factor Decomposition
                              </div>
                              <div style={{ backgroundColor: '#111827', padding: '0.85rem', borderRadius: '6px', fontSize: '0.775rem' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                                  <span style={{ color: '#9ca3af' }}>Event Base Weight:</span>
                                  <span className="mono">{s.impact_breakdown?.event_weight ?? 'N/A'}</span>
                                </div>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                                  <span style={{ color: '#9ca3af' }}>Sentiment Term:</span>
                                  <span className="mono">{s.impact_breakdown?.sentiment_term?.toFixed(3) ?? 'N/A'}</span>
                                </div>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                                  <span style={{ color: '#9ca3af' }}>Source Reliability:</span>
                                  <span className="mono">{(s.source_reliability ?? 0.85).toFixed(2)}</span>
                                </div>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                                  <span style={{ color: '#9ca3af' }}>Novelty Factor:</span>
                                  <span className="mono">{(s.novelty_factor ?? 1.0).toFixed(2)}</span>
                                </div>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                                  <span style={{ color: '#9ca3af' }}>Recency Weight:</span>
                                  <span className="mono">{(s.recency_weight ?? 1.0).toFixed(2)}</span>
                                </div>
                                <div
                                  style={{
                                    borderTop: '1px solid #374151',
                                    paddingTop: '0.35rem',
                                    marginTop: '0.35rem',
                                    display: 'flex',
                                    justifyContent: 'space-between',
                                    fontWeight: 700,
                                    color: '#60a5fa',
                                  }}
                                >
                                  <span>Final Impact Score:</span>
                                  <span className="mono">{s.impact_score.toFixed(2)} / 10</span>
                                </div>
                              </div>
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
