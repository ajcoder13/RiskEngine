export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' | 'low' | 'medium' | 'high' | 'critical';
export type Direction = 'adverse' | 'favourable' | 'neutral';

export interface Signal {
  id: string;
  doc_id?: string;
  ticker?: string | null;
  company?: string | null;
  company_name?: string | null;
  sector?: string;
  source: string;
  source_type?: string;
  source_name?: string | null;
  timestamp: string;
  published_at?: string;
  text: string;
  raw_text?: string;
  sentiment_label?: string;
  sentiment_score: number;
  sentiment_probs?: Record<string, number> | null;
  event_type: string;
  event_confidence?: number;
  source_reliability?: number;
  recency_weight?: number;
  novelty_factor?: number;
  impact_score: number;
  confidence: number;
  risk_level: RiskLevel;
  direction: Direction;
  score_breakdown?: Record<string, number>;
  impact_breakdown?: Record<string, number>;
  simulated?: boolean;
  simulated_data?: boolean;
  triggers_stress_test?: boolean;
}

export interface RiskSummary {
  total_signals: number;
  by_risk_level?: Record<string, number>;
  by_level?: Record<string, number>;
  by_event_type?: Record<string, number>;
  by_event?: Record<string, number>;
  by_source?: Record<string, number>;
  top_risky_tickers?: Array<[string, number]>;
  top_risk_tickers?: Array<[string, number]>;
  stress_trigger_threshold?: number;
  stress_triggers?: Array<{
    id: string;
    ticker: string;
    event_type: string;
    impact_score: number;
    text: string;
  }>;
  stress_triggers_count?: number;
  data_mode?: string;
  sentiment_backend?: string;
}

export interface DataSourceStatus {
  live_data_enabled: boolean;
  sources: Array<{
    name?: string;
    path?: string;
    exists?: boolean;
    format?: string;
    [key: string]: any;
  }>;
  note?: string;
}

// Module A
export interface Holding {
  ticker: string;
  name: string;
  sector: string;
  base_weight: number;
  current_weight: number;
  new_weight: number;
  weight_change: number;
  sentiment_score: number;
  impact_score: number;
  price: number;
  prev_close: number;
  return_1d: number;
  return_5d: number;
  volatility_30d: number;
  simulated_price: boolean;
  reason: string;
}

export interface RebalanceResult {
  holdings: Holding[];
  total_turnover: number;
  turnover_capped: boolean;
  weighted_sentiment: number;
  sector_exposure: Record<string, number>;
  simulated_prices: boolean;
  rebalanced_at: string;
  params: {
    sentiment_tilt: number;
    turnover_cap: number;
    min_weight: number;
    max_weight: number;
  };
  note: string;
}

export interface BacktestMetrics {
  ann_return: number;
  volatility: number;
  sharpe: number;
  max_drawdown: number;
}

export interface BacktestResult {
  strategy: BacktestMetrics;
  equal_weight: BacktestMetrics;
  base_weight: BacktestMetrics;
  total_turnover: number;
  series: {
    dates: string[];
    strategy_cumret: number[];
    equal_cumret: number[];
    base_cumret: number[];
  };
  simulated: boolean;
  note: string;
}

// Module B
export interface PortfolioPosition {
  asset_id: string;
  asset_type: string;
  name: string;
  notional: number;
  market_value: number;
  sector: string;
  geography: string;
  credit_rating: string;
  duration: number;
  interest_rate_sensitivity: number;
  equity_exposure: number;
  counterparty: string;
  default_probability: number;
  recovery_rate: number;
  weight: number;
}

export interface ShockDetail {
  asset_id: string;
  asset_type: string;
  name: string;
  sector: string;
  value_before: number;
  shock_applied: number;
  shock_source: string;
  value_after: number;
  loss: number;
}

export interface StressTestResponse {
  event_type: string;
  impact_score: number;
  triggered_automatically: boolean;
  scenario_label: string;
  portfolio_value_before: number;
  portfolio_value_after: number;
  total_loss: number;
  total_loss_pct: number;
  loss_by_asset_class: Record<string, number>;
  loss_by_sector: Record<string, number>;
  loss_by_geography: Record<string, number>;
  loss_by_credit_rating: Record<string, number>;
  shock_details: ShockDetail[];
  positions: PortfolioPosition[];
  shocks_applied: Record<string, number>;
  note: string;
  data_mode: 'simulated' | 'real';
}
