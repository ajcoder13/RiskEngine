import axios from 'axios';
import {
  Signal,
  RiskSummary,
  DataSourceStatus,
  RebalanceResult,
  BacktestResult,
  PortfolioPosition,
  StressTestResponse,
} from './types';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '',
  timeout: 15000,
});

function normalizeSignal(s: any): Signal {
  const breakdown = s.score_breakdown || s.impact_breakdown || {};
  const sentimentScore = typeof s.sentiment_score === 'number' ? s.sentiment_score : (s.sentiment ?? 0);
  const sentimentLabel =
    s.sentiment_label ||
    (sentimentScore > 0.15 ? 'positive' : sentimentScore < -0.15 ? 'negative' : 'neutral');

  return {
    ...s,
    ticker: s.ticker || 'GLOBAL',
    company_name: s.company || s.company_name || 'Market Macro',
    sector: s.sector || (s.entities?.SECTOR?.[0] || 'Broad Market'),
    published_at: s.timestamp || s.published_at || new Date().toISOString(),
    raw_text: s.text || s.raw_text || '',
    source_type: s.source || s.source_type || 'news',
    source_name: s.source_name || s.source || 'wire',
    sentiment_score: sentimentScore,
    sentiment_label: sentimentLabel,
    event_confidence: s.confidence ?? s.event_confidence ?? 0.85,
    source_reliability: breakdown.reliability ?? breakdown.source_weight ?? 0.85,
    novelty_factor: breakdown.novelty ?? 1.0,
    recency_weight: breakdown.recency ?? 1.0,
    risk_level: (s.risk_level || 'LOW').toLowerCase() as any,
    score_breakdown: breakdown,
    impact_breakdown: breakdown,
    triggers_stress_test: s.stress_trigger ?? (s.impact_score >= 8.0 && s.direction === 'adverse'),
  };
}

export const apiClient = {
  // Signals & Intelligence
  async getSignals(params?: {
    ticker?: string;
    level?: string;
    direction?: string;
    event_type?: string;
    limit?: number;
  }): Promise<Signal[]> {
    const res = await api.get<{ count: number; signals: any[] }>('/signals', { params });
    const rawList = res.data && Array.isArray(res.data.signals) ? res.data.signals : Array.isArray(res.data) ? res.data : [];
    return rawList.map(normalizeSignal);
  },

  async getRiskSummary(): Promise<RiskSummary> {
    const res = await api.get<any>('/risk-summary');
    const data = res.data;
    const rawTop = data.top_risky_tickers || data.top_risk_tickers || [];
    const normalizedTop = rawTop.map((t: any) =>
      Array.isArray(t) ? t : [t.ticker || 'N/A', typeof t.max_impact === 'number' ? t.max_impact : (t.impact ?? 0)]
    );
    return {
      ...data,
      by_level: data.by_risk_level || data.by_level || {},
      by_event: data.by_event_type || data.by_event || {},
      top_risk_tickers: normalizedTop,
      stress_triggers_count: data.stress_triggers ? data.stress_triggers.length : (data.stress_triggers_count || 0),
    };
  },

  async getSources(): Promise<DataSourceStatus> {
    const res = await api.get<DataSourceStatus>('/sources');
    return res.data;
  },

  async refreshData(): Promise<{ signals_built: number; total_in_store: number }> {
    const res = await api.post('/refresh');
    return res.data;
  },

  async analyzeText(text: string, source_type: 'news' | 'tweet' = 'news'): Promise<Signal[]> {
    const sourceVal = source_type === 'tweet' ? 'social' : 'news';
    const res = await api.post<{ count: number; signals: any[] }>('/analyze', {
      text,
      source: sourceVal,
      source_name: 'interactive_demo',
      persist: false,
    });
    const rawList = res.data && Array.isArray(res.data.signals) ? res.data.signals : [];
    return rawList.map(normalizeSignal);
  },

  // Module A: Portfolio Rebalancing & Backtest
  async getPortfolio(): Promise<RebalanceResult> {
    const res = await api.get<RebalanceResult>('/portfolio');
    return res.data;
  },

  async rebalance(params?: {
    sentiment_tilt?: number;
    turnover_cap?: number;
    min_weight?: number;
    max_weight?: number;
  }): Promise<RebalanceResult> {
    const res = await api.post<RebalanceResult>('/rebalance', null, { params });
    return res.data;
  },

  async getBacktest(period_days: number = 30): Promise<BacktestResult> {
    const res = await api.get<BacktestResult>('/backtest', {
      params: { period_days },
    });
    return res.data;
  },

  // Module B: Stress Testing
  async getPortfolioComposition(): Promise<PortfolioPosition[]> {
    const res = await api.get<PortfolioPosition[]>('/portfolio-composition');
    return res.data;
  },

  async runStressTest(req: {
    event_type: string;
    impact_score: number;
    ticker?: string;
    override_shocks?: Record<string, number>;
  }): Promise<StressTestResponse> {
    const res = await api.post<StressTestResponse>('/stress-test', req);
    return res.data;
  },

  async runAutoStressTest(): Promise<StressTestResponse> {
    const res = await api.post<StressTestResponse>('/stress-test/auto');
    return res.data;
  },
};
