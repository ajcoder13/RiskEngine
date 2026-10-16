import React, { useState, useEffect } from 'react';
import { StressTestResponse, Signal, PortfolioPosition } from '../api/types';
import { apiClient } from '../api/client';
import {
  ShieldAlert,
  Flame,
  AlertTriangle,
  Play,
  TrendingDown,
  Layers,
  PieChart as PieIcon,
  DollarSign,
  Activity,
  Sliders,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';

const SCENARIOS = [
  { event_type: 'Geopolitical', label: 'Geopolitical Escalation / War', defaultSeverity: 8.5 },
  { event_type: 'Market Shock', label: 'Global Equity Market Crash', defaultSeverity: 8.5 },
  { event_type: 'Credit Event', label: 'Corporate Default Wave', defaultSeverity: 9.0 },
  { event_type: 'Macroeconomic', label: 'Central Bank Emergency Rate Hike', defaultSeverity: 8.0 },
  { event_type: 'Cybersecurity', label: 'Systemic Critical Infrastructure Cyberattack', defaultSeverity: 7.5 },
  { event_type: 'Regulatory', label: 'Antitrust & Heavy Regulatory Sanctions', defaultSeverity: 7.0 },
  { event_type: 'Supply Chain', label: 'Global Shipping & Semiconductor Chokepoint', defaultSeverity: 6.5 },
];

const ASSET_COLORS = ['#ef4444', '#f97316', '#f59e0b', '#3b82f6', '#8b5cf6'];

interface Props {
  presetSignal?: Signal | null;
}

export const ModuleBStressTestingView: React.FC<Props> = ({ presetSignal }) => {
  const [selectedEventType, setSelectedEventType] = useState('Geopolitical');
  const [impactScore, setImpactScore] = useState(8.5);
  const [customEquityShock, setCustomEquityShock] = useState<number | null>(null);

  const [stressResult, setStressResult] = useState<StressTestResponse | null>(null);
  const [portfolioBase, setPortfolioBase] = useState<PortfolioPosition[]>([]);
  const [loading, setLoading] = useState(false);
  const [autoTriggered, setAutoTriggered] = useState(false);

  useEffect(() => {
    // Load initial composition and default stress test
    apiClient.getPortfolioComposition().then((res) => setPortfolioBase(res)).catch(() => {});
    runStressTest('Geopolitical', 8.5);
  }, []);

  useEffect(() => {
    if (presetSignal) {
      setSelectedEventType(presetSignal.event_type);
      setImpactScore(presetSignal.impact_score);
      runStressTest(presetSignal.event_type, presetSignal.impact_score);
    }
  }, [presetSignal]);

  const runStressTest = async (eventType: string, severity: number, overrides?: Record<string, number>) => {
    setLoading(true);
    setAutoTriggered(false);
    try {
      const res = await apiClient.runStressTest({
        event_type: eventType,
        impact_score: severity,
        override_shocks: overrides,
      });
      setStressResult(res);
    } catch (err) {
      console.error('Error running stress test', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAutoStress = async () => {
    setLoading(true);
    try {
      const res = await apiClient.runAutoStressTest();
      setStressResult(res);
      setSelectedEventType(res.event_type);
      setImpactScore(res.impact_score);
      setAutoTriggered(true);
    } catch (err) {
      console.error('Auto stress failed', err);
    } finally {
      setLoading(false);
    }
  };

  const handleExecute = () => {
    const overrides = customEquityShock !== null ? { equity: customEquityShock / 100 } : undefined;
    runStressTest(selectedEventType, impactScore, overrides);
  };

  // Format charts data
  const assetClassData = stressResult?.loss_by_asset_class
    ? Object.entries(stressResult.loss_by_asset_class).map(([name, loss]) => ({
        name,
        Loss: Math.abs(loss) / 1_000_000,
      }))
    : [];

  const sectorData = stressResult?.loss_by_sector
    ? Object.entries(stressResult.loss_by_sector).map(([name, loss]) => ({
        name: name.length > 12 ? name.slice(0, 10) + '..' : name,
        Loss: Math.abs(loss) / 1_000_000,
      }))
    : [];

  const ratingData = stressResult?.loss_by_credit_rating
    ? Object.entries(stressResult.loss_by_credit_rating).map(([name, loss]) => ({
        name,
        Loss: Math.abs(loss) / 1_000_000,
      }))
    : [];

  return (
    <div>
      {/* Control Configuration Panel */}
      <div className="glass-card" style={{ marginBottom: '1.75rem' }}>
        <div className="card-header">
          <div>
            <div className="card-title">
              <ShieldAlert size={20} style={{ color: '#ef4444' }} />
              Module B: Event-Driven Macro & Credit Stress Testing Engine
            </div>
            <div className="card-subtitle">
              Simulates extreme tail-risk loss scenarios on a synthetic ~$89.92M wholesale banking book (20 positions) triggered by live news signals.
            </div>
          </div>
          <div style={{ display: 'flex', gap: '0.75rem' }}>
            <button className="btn btn-danger" onClick={handleAutoStress} disabled={loading}>
              <Flame size={16} /> Auto-Trigger from Live Alert
            </button>
            <button className="btn btn-primary" onClick={handleExecute} disabled={loading}>
              <Play size={16} /> Execute Stress Test
            </button>
          </div>
        </div>

        <div className="grid-2" style={{ gap: '2rem' }}>
          <div>
            <div className="form-group">
              <label className="form-label">Scenario Event Class</label>
              <select
                className="form-select"
                value={selectedEventType}
                onChange={(e) => {
                  setSelectedEventType(e.target.value);
                  const sc = SCENARIOS.find((s) => s.event_type === e.target.value);
                  if (sc) setImpactScore(sc.defaultSeverity);
                }}
              >
                {SCENARIOS.map((s) => (
                  <option key={s.event_type} value={s.event_type}>
                    {s.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <label className="form-label">Signal Impact Severity</label>
                <span className="mono" style={{ color: '#f87171', fontWeight: 700 }}>
                  {impactScore.toFixed(1)} / 10
                </span>
              </div>
              <input
                type="range"
                className="range-slider"
                min="1.0"
                max="10.0"
                step="0.5"
                value={impactScore}
                onChange={(e) => setImpactScore(parseFloat(e.target.value))}
              />
              <span style={{ fontSize: '0.75rem', color: '#6b7280' }}>
                Scales non-linear factor shocks according to NLP event severity calibration.
              </span>
            </div>
          </div>

          <div>
            <div className="form-group">
              <label className="form-label">Active Scenario Applied Shocks</label>
              <div
                style={{
                  background: '#111827',
                  padding: '0.85rem',
                  borderRadius: '8px',
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr',
                  gap: '0.5rem',
                  fontSize: '0.8rem',
                }}
              >
                {stressResult?.shocks_applied &&
                  Object.entries(stressResult.shocks_applied).map(([key, val]) => (
                    <div key={key} style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: '#9ca3af', textTransform: 'capitalize' }}>{key}:</span>
                      <span
                        className="mono"
                        style={{
                          color: val < 0 ? '#f87171' : val > 0 ? '#34d399' : '#e5e7eb',
                          fontWeight: 600,
                        }}
                      >
                        {val < 0 ? '' : '+'}
                        {(val * 100).toFixed(1)}%
                      </span>
                    </div>
                  ))}
              </div>
            </div>

            {autoTriggered && (
              <div
                style={{
                  padding: '0.65rem 0.85rem',
                  background: 'rgba(239, 68, 68, 0.15)',
                  border: '1px solid rgba(239, 68, 68, 0.3)',
                  borderRadius: '6px',
                  fontSize: '0.8rem',
                  color: '#f87171',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                }}
              >
                <AlertTriangle size={14} /> Automatically triggered by highest-impact adverse event currently in store!
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Primary Loss KPIs */}
      <div className="metrics-grid">
        <div className="metric-card">
          <div className="metric-label">Base Portfolio Value</div>
          <div className="metric-value">
            ${stressResult ? (stressResult.portfolio_value_before / 1_000_000).toFixed(2) : '--'}M
          </div>
          <div className="metric-subtext">Synthetic 20-position wholesale banking book (~$89.92M)</div>
        </div>

        <div className="metric-card critical">
          <div className="metric-label">Total Simulated Loss</div>
          <div className="metric-value" style={{ color: '#ef4444' }}>
            -${stressResult ? (Math.abs(stressResult.total_loss) / 1_000_000).toFixed(2) : '--'}M
          </div>
          <div className="metric-subtext">
            {stressResult ? `${(stressResult.total_loss_pct * 100).toFixed(2)}% portfolio destruction` : '--'}
          </div>
        </div>

        <div className="metric-card warning">
          <div className="metric-label">Stressed Portfolio Value</div>
          <div className="metric-value">
            ${stressResult ? (stressResult.portfolio_value_after / 1_000_000).toFixed(2) : '--'}M
          </div>
          <div className="metric-subtext">Post-shock valuation under tail scenario</div>
        </div>

        <div className="metric-card purple">
          <div className="metric-label">Scenario Event</div>
          <div className="metric-value" style={{ fontSize: '1.25rem', marginTop: '0.6rem' }}>
            {stressResult?.event_type ?? '--'}
          </div>
          <div className="metric-subtext">Severity index: {stressResult?.impact_score.toFixed(1) ?? '--'}/10</div>
        </div>
      </div>

      {/* Loss Attribution Visualizations */}
      <div className="grid-3" style={{ marginBottom: '2rem' }}>
        <div className="glass-card">
          <div className="card-header">
            <div>
              <div className="card-title">Loss by Asset Class ($M)</div>
              <div className="card-subtitle">Vulnerability across asset types</div>
            </div>
          </div>
          <div style={{ height: '220px', width: '100%' }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={assetClassData} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                <XAxis dataKey="name" stroke="#6b7280" fontSize={10} angle={-15} textAnchor="end" />
                <YAxis stroke="#6b7280" fontSize={10} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#111827', borderColor: '#374151', borderRadius: '8px' }}
                />
                <Bar dataKey="Loss" fill="#ef4444" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="glass-card">
          <div className="card-header">
            <div>
              <div className="card-title">Loss by Sector ($M)</div>
              <div className="card-subtitle">Industry concentration risk</div>
            </div>
          </div>
          <div style={{ height: '220px', width: '100%' }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={sectorData} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                <XAxis dataKey="name" stroke="#6b7280" fontSize={10} angle={-15} textAnchor="end" />
                <YAxis stroke="#6b7280" fontSize={10} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#111827', borderColor: '#374151', borderRadius: '8px' }}
                />
                <Bar dataKey="Loss" fill="#f97316" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="glass-card">
          <div className="card-header">
            <div>
              <div className="card-title">Loss by Rating ($M)</div>
              <div className="card-subtitle">Credit quality sensitivity</div>
            </div>
          </div>
          <div style={{ height: '220px', width: '100%' }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={ratingData} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                <XAxis dataKey="name" stroke="#6b7280" fontSize={10} />
                <YAxis stroke="#6b7280" fontSize={10} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#111827', borderColor: '#374151', borderRadius: '8px' }}
                />
                <Bar dataKey="Loss" fill="#f59e0b" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Position Breakdown Table */}
      <div className="glass-card">
        <div className="card-header">
          <div>
            <div className="card-title">Position-Level Stress Testing Breakdown</div>
            <div className="card-subtitle">
              Detailed transmission of shocks across all individual portfolio positions
            </div>
          </div>
        </div>

        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Asset ID</th>
                <th>Asset Name</th>
                <th>Asset Class</th>
                <th>Sector</th>
                <th>Pre-Stress Value</th>
                <th>Shock Applied</th>
                <th>Simulated Loss</th>
                <th>Post-Stress Value</th>
              </tr>
            </thead>
            <tbody>
              {stressResult?.shock_details?.map((detail) => (
                <tr key={detail.asset_id}>
                  <td className="mono" style={{ fontWeight: 700, color: '#60a5fa' }}>
                    {detail.asset_id}
                  </td>
                  <td>{detail.name}</td>
                  <td>
                    <span className="badge badge-neutral">{detail.asset_type}</span>
                  </td>
                  <td>{detail.sector}</td>
                  <td className="mono">${(detail.value_before / 1_000_000).toFixed(2)}M</td>
                  <td className="mono" style={{ color: detail.shock_applied < 0 ? '#f87171' : '#9ca3af' }}>
                    {(detail.shock_applied * 100).toFixed(2)}%
                  </td>
                  <td className="mono" style={{ color: '#ef4444', fontWeight: 700 }}>
                    -${(Math.abs(detail.loss) / 1_000_000).toFixed(2)}M
                  </td>
                  <td className="mono" style={{ fontWeight: 600 }}>
                    ${(detail.value_after / 1_000_000).toFixed(2)}M
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
