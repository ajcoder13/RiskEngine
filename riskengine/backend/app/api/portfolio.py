"""Module A API: /portfolio, /rebalance, /backtest"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_engine
from app.portfolio.backtest import run_backtest
from app.portfolio.market_data import fetch_market_data, fetch_history
from app.portfolio.rebalancer import RebalanceParams, RebalanceResult, rebalance
from app.portfolio.universe import INDEX_UNIVERSE, TICKERS
from app.risk.engine import RiskEngine
from app.schemas.modules import (BacktestMetrics, BacktestPeriodResult, BacktestResponse,
                                  HoldingSchema, RebalanceResponse)

log = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["module-a"])

# In-process state: persist last rebalance result so /portfolio is always populated
_last_result: RebalanceResult | None = None


def _to_holding_schema(h) -> HoldingSchema:
    return HoldingSchema(
        ticker=h.ticker, name=h.name, sector=h.sector,
        base_weight=round(h.base_weight, 6), current_weight=round(h.current_weight, 6),
        new_weight=round(h.new_weight, 6), weight_change=round(h.weight_change, 6),
        sentiment_score=h.sentiment_score, impact_score=h.impact_score,
        price=h.price, prev_close=h.prev_close,
        return_1d=h.return_1d, return_5d=h.return_5d,
        volatility_30d=h.volatility_30d, simulated_price=h.simulated_price,
        reason=h.reason,
    )


@router.get("/portfolio", response_model=RebalanceResponse,
            summary="Current index portfolio with latest risk-adjusted weights (Module A)")
def get_portfolio(engine: RiskEngine = Depends(get_engine)) -> RebalanceResponse:
    """Returns the most recently rebalanced portfolio.  If no rebalance has been run yet,
    triggers one automatically using current signals and market data."""
    global _last_result
    if _last_result is None:
        market, _ = fetch_market_data(TICKERS)
        _last_result = rebalance(engine.store, market)
    r = _last_result
    return RebalanceResponse(
        holdings=[_to_holding_schema(h) for h in r.holdings],
        total_turnover=r.total_turnover, turnover_capped=r.turnover_capped,
        weighted_sentiment=r.weighted_sentiment, sector_exposure=r.sector_exposure,
        simulated_prices=r.simulated_prices, rebalanced_at=r.rebalanced_at, params=r.params,
    )


@router.post("/rebalance", response_model=RebalanceResponse,
             summary="Rebalance the index from current risk signals (Module A)")
def do_rebalance(
    alpha: float = Query(0.40, ge=0.0, le=2.0, description="Sentiment sensitivity"),
    beta:  float = Query(0.30, ge=0.0, le=2.0, description="Volatility penalty"),
    min_weight: float = Query(0.02, ge=0.0, le=0.10),
    max_weight: float = Query(0.12, ge=0.05, le=0.30),
    max_turnover: float = Query(0.30, ge=0.0, le=1.0),
    engine: RiskEngine = Depends(get_engine),
) -> RebalanceResponse:
    """Run the rebalancing algorithm using current signals from the risk engine."""
    global _last_result
    params = RebalanceParams(alpha=alpha, beta=beta, min_weight=min_weight,
                             max_weight=max_weight, max_turnover=max_turnover)
    prev = {h.ticker: h.new_weight for h in _last_result.holdings} if _last_result else None
    market, _ = fetch_market_data(TICKERS)
    _last_result = rebalance(engine.store, market, params=params, prev_weights=prev)
    r = _last_result
    return RebalanceResponse(
        holdings=[_to_holding_schema(h) for h in r.holdings],
        total_turnover=r.total_turnover, turnover_capped=r.turnover_capped,
        weighted_sentiment=r.weighted_sentiment, sector_exposure=r.sector_exposure,
        simulated_prices=r.simulated_prices, rebalanced_at=r.rebalanced_at, params=r.params,
    )


@router.get("/backtest", response_model=BacktestResponse,
            summary="Walk-forward backtest vs equal-weight and base-weight benchmarks (Module A)")
def backtest(
    lookback_days: int = Query(252, ge=60, le=756, description="Trading days of history to fetch"),
    engine: RiskEngine = Depends(get_engine),
) -> BacktestResponse:
    """Run a historical backtest of the sentiment-adjusted strategy."""
    prices, sim = fetch_history(TICKERS, lookback_days)
    result = run_backtest(prices, engine.store)
    return BacktestResponse(
        strategy=BacktestMetrics(ann_return=result.strategy_ann_return,
                                 volatility=result.strategy_volatility,
                                 sharpe=result.strategy_sharpe,
                                 max_drawdown=result.strategy_max_dd),
        equal_weight=BacktestMetrics(ann_return=result.equal_ann_return,
                                     volatility=result.equal_volatility,
                                     sharpe=result.equal_sharpe,
                                     max_drawdown=result.equal_max_dd),
        base_weight=BacktestMetrics(ann_return=result.base_ann_return,
                                    volatility=result.base_volatility,
                                    sharpe=result.base_sharpe,
                                    max_drawdown=result.base_max_dd),
        total_turnover=result.total_turnover,
        series=BacktestPeriodResult(dates=result.dates,
                                    strategy_cumret=result.strategy_cumret,
                                    equal_cumret=result.equal_cumret,
                                    base_cumret=result.base_cumret),
        simulated=result.simulated or sim,
        note=result.note,
    )
