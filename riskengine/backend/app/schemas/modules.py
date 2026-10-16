"""Pydantic schemas for Module A (portfolio) and Module B (stress testing) API responses."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# ---- Module A ----------------------------------------------------------------

class HoldingSchema(BaseModel):
    ticker: str
    name: str
    sector: str
    base_weight: float
    current_weight: float
    new_weight: float
    weight_change: float
    sentiment_score: float
    impact_score: float
    price: float
    prev_close: float
    return_1d: float
    return_5d: float
    volatility_30d: float
    simulated_price: bool
    reason: str


class RebalanceResponse(BaseModel):
    holdings: list[HoldingSchema]
    total_turnover: float
    turnover_capped: bool
    weighted_sentiment: float
    sector_exposure: dict[str, float]
    simulated_prices: bool
    rebalanced_at: datetime
    params: dict
    note: str = ("Weights reflect sentiment-adjusted formula. "
                 "Impact is an ordinal severity index, not a price forecast.")


class BacktestPeriodResult(BaseModel):
    dates: list[str]
    strategy_cumret: list[float]
    equal_cumret: list[float]
    base_cumret: list[float]


class BacktestMetrics(BaseModel):
    ann_return: float
    volatility: float
    sharpe: float
    max_drawdown: float


class BacktestResponse(BaseModel):
    strategy: BacktestMetrics
    equal_weight: BacktestMetrics
    base_weight: BacktestMetrics
    total_turnover: float
    series: BacktestPeriodResult
    simulated: bool
    note: str


# ---- Module B ----------------------------------------------------------------

class PortfolioPositionSchema(BaseModel):
    asset_id: str
    asset_type: str
    name: str
    notional: float
    market_value: float
    sector: str
    geography: str
    credit_rating: str
    duration: float
    interest_rate_sensitivity: float
    equity_exposure: float
    counterparty: str
    default_probability: float
    recovery_rate: float
    weight: float


class StressShockDetail(BaseModel):
    asset_id: str
    asset_type: str
    name: str
    sector: str
    value_before: float
    shock_applied: float        # fractional, e.g. -0.10
    shock_source: str
    value_after: float
    loss: float


class StressTestRequest(BaseModel):
    event_type: str = Field(description="e.g. 'Geopolitical'")
    impact_score: float = Field(ge=1.0, le=10.0)
    ticker: str | None = None
    override_shocks: dict[str, float] | None = Field(
        None, description="Override default shocks, e.g. {\"equity\": -0.15}")


class StressTestResponse(BaseModel):
    event_type: str
    impact_score: float
    triggered_automatically: bool
    scenario_label: str
    portfolio_value_before: float
    portfolio_value_after: float
    total_loss: float
    total_loss_pct: float = Field(description="Loss as a fraction of portfolio value (e.g. -0.0308 = -3.08%). Multiply by 100 for percentage display.")
    loss_by_asset_class: dict[str, float]
    loss_by_sector: dict[str, float]
    loss_by_geography: dict[str, float]
    loss_by_credit_rating: dict[str, float]
    shock_details: list[StressShockDetail]
    positions: list[PortfolioPositionSchema]
    shocks_applied: dict[str, float]
    note: str = ("Stress-test results are illustrative scenario analyses. "
                 "Shocks are documented assumptions, not forecasts.")
    data_mode: Literal["simulated", "real"] = "simulated"
