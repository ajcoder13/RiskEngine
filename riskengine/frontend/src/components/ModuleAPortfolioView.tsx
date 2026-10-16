import React, { useState, useEffect } from 'react';
import { RebalanceResult, BacktestResult } from '../api/types';
import { apiClient } from '../api/client';
import {
  TrendingUp,
  TrendingDown,
  Sliders,
  RotateCcw,
  BarChart3,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
} from 'lucide-react';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

export const ModuleAPortfolioView: React.FC = () => {
  const [tilt, setTilt] = useState(0.35);
  const [turnoverCap, setTurnoverCap] = useState(0.08);
  const [minWeight, setMinWeight] = useState(0.01);
  const [maxWeight, setMaxWeight] = useState(0.12);

  const [portfolio, setPortfolio] = useState<RebalanceResult | null>(null);
  const [backtest, setBacktest] = useState<BacktestResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [backtestPeriod, setBacktestPeriod] = useState(30);

  const loadData = async (
    params = { sentiment_tilt: tilt, turnover_cap: turnoverCap, min_weight: minWeight, max_weight: maxWeight }
  ) => {
    setLoading(true);
    try {
      const [pRes, bRes] = await Promise.all([
        apiClient.rebalance(params),
        apiClient.getBacktest(backtestPeriod),
      ]);
      setPortfolio(pRes);
      setBacktest(bRes);
    } catch (err) {
      console.error('Error loading Module A data', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [backtestPeriod]);

  const handleApplyRebalance = () => {
    loadData({
      sentiment_tilt: tilt,
      turnover_cap: turnoverCap,
      min_weight: minWeight,
      max_weight: maxWeight,
    });
  };

  // Format chart data for backtest cumulative return series
  const backtestChartData =
    backtest?.series?.dates?.map((date, idx) => ({
      date: date.slice(5),
      Strategy: parseFloat(((backtest.series.strategy_cumret[idx] - 1) * 100).toFixed(2)),
      BaseWeight: parseFloat(((backtest.series.base_cumret[idx] - 1) * 100).toFixed(2)),
      EqualWeight: parseFloat(((backtest.series.equal_cumret[idx] - 1) * 100).toFixed(2)),
    })) ?? [];

  // Sector exposure chart data
  const sectorData = portfolio?.sector_exposure
    ? Object.entries(portfolio.sector_exposure).map(([sector, weight]) => ({
        sector: sector.length > 12 ? sector.slice(0, 10) + '..' : sector,
        Allocated: parseFloat((weight * 100).toFixed(1)),
      }))
    : [];

  return (
    <div>
      {/* Parameter Control Panel */}
      <div className="glass-card" style={{ marginBottom: '1.75rem' }}>
        <div className="card-header">
          <div>
            <div className="card-title">
              <Sliders size={20} style={{ color: '#3b82f6' }} />
              Module A: Dynamic Tactical Index Rebalancer
            </div>
            <div className="card-subtitle">
              Adjusts benchmark weights based on real-time NLP sentiment & risk impact signals under rigorous turnover constraints.
            </div>
          </div>
          <button className="btn btn-primary" onClick={handleApplyRebalance} disabled={loading}>
            {loading ? 'Rebalancing...' : 'Execute Rebalance'}
          </button>
        </div>

        <div className="grid-2" style={{ gap: '2rem' }}>
          <div>
            <div className="form-group">
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <label className="form-label">Sentiment Tilt Intensity</label>
                <span className="mono" style={{ color: '#60a5fa', fontWeight: 600 }}>
                  {(tilt * 100).toFixed(0)}%
                </span>
              </div>
              <input
                type="range"
                className="range-slider"
                min="0.0"
                max="1.0"
                step="0.05"
                value={tilt}
                onChange={(e) => setTilt(parseFloat(e.target.value))}
              />
              <span style={{ fontSize: '0.75rem', color: '#6b7280' }}>
                Higher tilt amplifies allocation toward positive sentiment and trims adverse risk tickers.
              </span>
            </div>

            <div className="form-group">
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <label className="form-label">Turnover Cap (Max 1-way trade volume)</label>
                <span className="mono" style={{ color: '#60a5fa', fontWeight: 600 }}>
                  {(turnoverCap * 100).toFixed(1)}%
                </span>
              </div>
              <input
                type="range"
                className="range-slider"
                min="0.01"
                max="0.20"
                step="0.01"
                value={turnoverCap}
                onChange={(e) => setTurnoverCap(parseFloat(e.target.value))}
              />
              <span style={{ fontSize: '0.75rem', color: '#6b7280' }}>
                Limits transaction cost drag and prevents excessive portfolio churn.
              </span>
            </div>
          </div>

          <div>
            <div className="form-group">
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <label className="form-label">Max Single Asset Weight</label>
                <span className="mono" style={{ color: '#60a5fa', fontWeight: 600 }}>
                  {(maxWeight * 100).toFixed(0)}%
                </span>
              </div>
              <input
                type="range"
                className="range-slider"
                min="0.05"
                max="0.25"
                step="0.01"
                value={maxWeight}
                onChange={(e) => setMaxWeight(parseFloat(e.target.value))}
              />
              <span style={{ fontSize: '0.75rem', color: '#6b7280' }}>
                Concentration limit to prevent idiosyncratic company blowup risk.
              </span>
            </div>

            <div className="form-group">
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <label className="form-label">Min Single Asset Weight</label>
                <span className="mono" style={{ color: '#60a5fa', fontWeight: 600 }}>
                  {(minWeight * 100).toFixed(1)}%
                </span>
              </div>
              <input
                type="range"
                className="range-slider"
                min="0.00"
                max="0.05"
                step="0.005"
                value={minWeight}
                onChange={(e) => setMinWeight(parseFloat(e.target.value))}
              />
              <span style={{ fontSize: '0.75rem', color: '#6b7280' }}>
                Floor constraint to retain broad market index representation.
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="metrics-grid">
        <div className="metric-card">
          <div className="metric-label">Total Turnover</div>
          <div className="metric-value">
            {portfolio ? `${(portfolio.total_turnover * 100).toFixed(2)}%` : '--'}
          </div>
          <div className="metric-subtext">
            {portfolio?.turnover_capped ? (
              <span style={{ color: '#f59e0b' }}>Hit {(turnoverCap * 100).toFixed(1)}% cap constraint</span>
            ) : (
              'Within maximum turnover allowance'
            )}
          </div>
        </div>

        <div className="metric-card success">
          <div className="metric-label">Weighted Sentiment</div>
          <div className="metric-value">
            {portfolio ? `${portfolio.weighted_sentiment > 0 ? '+' : ''}${portfolio.weighted_sentiment.toFixed(3)}` : '--'}
          </div>
          <div className="metric-subtext">Aggregate sentiment polarity of portfolio</div>
        </div>

        <div className="metric-card purple">
          <div className="metric-label">Strategy Sharpe Ratio</div>
          <div className="metric-value">
            {backtest?.strategy?.sharpe ? backtest.strategy.sharpe.toFixed(2) : '--'}
          </div>
          <div className="metric-subtext">
            Benchmark: {backtest?.base_weight?.sharpe?.toFixed(2) ?? '--'}
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Max Drawdown</div>
          <div className="metric-value" style={{ color: '#f87171' }}>
            {backtest?.strategy?.max_drawdown
              ? `${(backtest.strategy.max_drawdown * 100).toFixed(2)}%`
              : '--'}
          </div>
          <div className="metric-subtext">Peak-to-trough decline over window</div>
        </div>
      </div>

      {/* Backtest & Sector Charts Row */}
      <div className="grid-2" style={{ marginBottom: '2rem' }}>
        <div className="glass-card">
          <div className="card-header">
            <div>
              <div className="card-title">Backtest: Cumulative Return (%)</div>
              <div className="card-subtitle">
                Signal-driven rebalanced strategy vs. equal weight & benchmark index
              </div>
            </div>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button
                className={`btn btn-sm ${backtestPeriod === 30 ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setBacktestPeriod(30)}
              >
                30D
              </button>
              <button
                className={`btn btn-sm ${backtestPeriod === 60 ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setBacktestPeriod(60)}
              >
                60D
              </button>
            </div>
          </div>
          <div style={{ height: '280px', width: '100%' }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={backtestChartData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                <XAxis dataKey="date" stroke="#6b7280" fontSize={11} />
                <YAxis stroke="#6b7280" fontSize={11} unit="%" />
                <Tooltip
                  contentStyle={{ backgroundColor: '#111827', borderColor: '#374151', borderRadius: '8px' }}
                />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="Strategy"
                  stroke="#3b82f6"
                  strokeWidth={2.5}
                  dot={false}
                  name="NLP-Tilted Strategy"
                />
                <Line
                  type="monotone"
                  dataKey="BaseWeight"
                  stroke="#9ca3af"
                  strokeWidth={1.5}
                  strokeDasharray="4 4"
                  dot={false}
                  name="Base Market Index"
                />
                <Line
                  type="monotone"
                  dataKey="EqualWeight"
                  stroke="#a855f7"
                  strokeWidth={1.5}
                  dot={false}
                  name="Equal-Weight"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="glass-card">
          <div className="card-header">
            <div>
              <div className="card-title">Sector Allocation Breakdown</div>
              <div className="card-subtitle">Resulting exposure across economic sectors</div>
            </div>
          </div>
          <div style={{ height: '280px', width: '100%' }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={sectorData} margin={{ top: 10, right: 10, left: -10, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                <XAxis dataKey="sector" stroke="#6b7280" fontSize={11} angle={-15} textAnchor="end" />
                <YAxis stroke="#6b7280" fontSize={11} unit="%" />
                <Tooltip
                  contentStyle={{ backgroundColor: '#111827', borderColor: '#374151', borderRadius: '8px' }}
                />
                <Bar dataKey="Allocated" fill="#8b5cf6" radius={[4, 4, 0, 0]} name="Sector Weight (%)" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Holdings & Weights Table */}
      <div className="glass-card">
        <div className="card-header">
          <div>
            <div className="card-title">Constituent Holdings & Tactical Weight Allocations</div>
            <div className="card-subtitle">
              Detailed rebalance attribution showing sentiment scores and rationale
            </div>
          </div>
        </div>

        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Ticker</th>
                <th>Company</th>
                <th>Sector</th>
                <th>Market Price</th>
                <th>Sentiment Score</th>
                <th>Base Weight</th>
                <th>New Weight</th>
                <th>Delta</th>
                <th>Rationale</th>
              </tr>
            </thead>
            <tbody>
              {portfolio?.holdings?.map((h) => {
                const delta = h.weight_change;
                const isPositive = delta > 0.0001;
                const isNegative = delta < -0.0001;

                return (
                  <tr key={h.ticker}>
                    <td className="mono" style={{ fontWeight: 700, color: '#60a5fa' }}>
                      {h.ticker}
                    </td>
                    <td>{h.name}</td>
                    <td>
                      <span className="badge badge-neutral">{h.sector}</span>
                    </td>
                    <td className="mono">${h.price.toFixed(2)}</td>
                    <td>
                      <span
                        className={`badge ${
                          h.sentiment_score > 0.05
                            ? 'badge-positive'
                            : h.sentiment_score < -0.05
                            ? 'badge-negative'
                            : 'badge-neutral'
                        }`}
                      >
                        {h.sentiment_score > 0 ? '+' : ''}
                        {h.sentiment_score.toFixed(2)}
                      </span>
                    </td>
                    <td className="mono">{(h.base_weight * 100).toFixed(2)}%</td>
                    <td className="mono" style={{ fontWeight: 700, color: '#e5e7eb' }}>
                      {(h.new_weight * 100).toFixed(2)}%
                    </td>
                    <td className="mono">
                      <span
                        style={{
                          color: isPositive ? '#34d399' : isNegative ? '#f87171' : '#9ca3af',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '0.2rem',
                          fontWeight: 600,
                        }}
                      >
                        {isPositive && <TrendingUp size={14} />}
                        {isNegative && <TrendingDown size={14} />}
                        {isPositive ? '+' : ''}
                        {(delta * 100).toFixed(2)}%
                      </span>
                    </td>
                    <td style={{ fontSize: '0.8rem', color: '#9ca3af', maxWidth: '280px' }}>
                      {h.reason}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
