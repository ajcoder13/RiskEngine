"""Module A backtester.

Methodology
-----------
Walk forward over historical price data in weekly steps.
Each week:
  1. For each ticker, look up the most recent risk signal in the store (or use base weights).
  2. Apply the rebalancing formula to get new weights.
  3. Compute the portfolio return for the next week using actual prices.

Compares against:
  - Equal-weight buy & hold
  - Base-weight (market-cap proxy) buy & hold

NOTE: All signals in the store are used as if they arrived contemporaneously (the store does not have
historical signal timestamps aligned to market dates).  The backtest therefore uses the *current*
signal store as a constant sentiment overlay, which is a simplification.  This is explicitly labelled.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from app.portfolio.universe import INDEX_UNIVERSE
from app.risk.store import SignalStore

log = logging.getLogger(__name__)

TRADING_DAYS_PER_YEAR = 252
REBALANCE_FREQ = 5        # weekly in business days


@dataclass
class BacktestResult:
    strategy_cumret: list[float] = field(default_factory=list)
    equal_cumret: list[float]    = field(default_factory=list)
    base_cumret: list[float]     = field(default_factory=list)
    dates: list[str]             = field(default_factory=list)

    strategy_ann_return: float = 0.0
    equal_ann_return: float    = 0.0
    base_ann_return: float     = 0.0

    strategy_volatility: float = 0.0
    equal_volatility: float    = 0.0
    base_volatility: float     = 0.0

    strategy_sharpe: float = 0.0
    equal_sharpe: float    = 0.0
    base_sharpe: float     = 0.0

    strategy_max_dd: float = 0.0
    equal_max_dd: float    = 0.0
    base_max_dd: float     = 0.0

    total_turnover: float = 0.0
    simulated: bool = False
    note: str = ""


def _max_drawdown(cum: np.ndarray) -> float:
    peak = np.maximum.accumulate(cum)
    dd = (cum - peak) / np.where(peak == 0, 1, peak)
    return float(dd.min())


def _sharpe(rets: np.ndarray, rf: float = 0.04) -> float:
    if len(rets) < 2 or rets.std() == 0:
        return 0.0
    excess = rets.mean() * TRADING_DAYS_PER_YEAR - rf
    return float(excess / (rets.std() * np.sqrt(TRADING_DAYS_PER_YEAR)))


def _ann_return(cum: np.ndarray, n_days: int) -> float:
    if n_days < 1 or cum[-1] <= 0:
        return 0.0
    return float(cum[-1] ** (TRADING_DAYS_PER_YEAR / n_days) - 1)


def run_backtest(prices: pd.DataFrame, store: SignalStore) -> BacktestResult:
    """prices: DataFrame with tickers as columns, sorted date index (business days)."""
    tickers = [t for t in INDEX_UNIVERSE if t in prices.columns]
    if len(tickers) < 5:
        return BacktestResult(note="Insufficient price history for backtest.", simulated=True)

    prices = prices[tickers].dropna(how="all").ffill().bfill()
    rets = prices.pct_change().fillna(0.0)
    n = len(rets)
    if n < 20:
        return BacktestResult(note="Too few rows for backtest.", simulated=True)

    bw = np.array([INDEX_UNIVERSE[t]["base_weight"] for t in tickers])
    bw /= bw.sum()
    ew = np.ones(len(tickers)) / len(tickers)

    # Load sentiment signals once and keep as fixed overlay
    signal_sent: dict[str, float] = {}
    for t in tickers:
        sigs = store.query(limit=5, ticker=t, order="impact")
        if sigs:
            adverse = [s for s in sigs if s.direction.value == "adverse"]
            pool = adverse or sigs
            w = [s.confidence for s in pool]
            tw = sum(w) or 1.0
            signal_sent[t] = sum(s.sentiment_score * c for s, c in zip(pool, w)) / tw
        else:
            signal_sent[t] = 0.0
    sent_arr = np.array([signal_sent.get(t, 0.0) for t in tickers])

    alpha = 0.40
    cur_weights = bw.copy()
    strategy_rets, equal_rets, base_rets = [], [], []
    total_turnover = 0.0

    for i in range(0, n - 1):
        r = rets.iloc[i + 1].values

        strategy_rets.append(float(cur_weights @ r))
        equal_rets.append(float(ew @ r))
        base_rets.append(float(bw @ r))

        if i % REBALANCE_FREQ == 0:
            raw = bw * (1.0 + alpha * sent_arr)
            raw /= raw.sum()
            raw = np.clip(raw, 0.02, 0.12)
            raw /= raw.sum()
            total_turnover += float(np.abs(raw - cur_weights).sum())
            cur_weights = raw

    s_arr = np.array(strategy_rets)
    e_arr = np.array(equal_rets)
    b_arr = np.array(base_rets)
    s_cum = np.cumprod(1 + s_arr)
    e_cum = np.cumprod(1 + e_arr)
    b_cum = np.cumprod(1 + b_arr)
    dates = [str(d.date()) for d in rets.index[1:]]

    nd = len(s_arr)
    return BacktestResult(
        strategy_cumret=[round(float(v), 6) for v in s_cum],
        equal_cumret=[round(float(v), 6) for v in e_cum],
        base_cumret=[round(float(v), 6) for v in b_cum],
        dates=dates,
        strategy_ann_return=round(_ann_return(s_cum, nd), 4),
        equal_ann_return=round(_ann_return(e_cum, nd), 4),
        base_ann_return=round(_ann_return(b_cum, nd), 4),
        strategy_volatility=round(float(s_arr.std() * np.sqrt(TRADING_DAYS_PER_YEAR)), 4),
        equal_volatility=round(float(e_arr.std() * np.sqrt(TRADING_DAYS_PER_YEAR)), 4),
        base_volatility=round(float(b_arr.std() * np.sqrt(TRADING_DAYS_PER_YEAR)), 4),
        strategy_sharpe=round(_sharpe(s_arr), 4),
        equal_sharpe=round(_sharpe(e_arr), 4),
        base_sharpe=round(_sharpe(b_arr), 4),
        strategy_max_dd=round(_max_drawdown(s_cum), 4),
        equal_max_dd=round(_max_drawdown(e_cum), 4),
        base_max_dd=round(_max_drawdown(b_cum), 4),
        total_turnover=round(total_turnover, 4),
        simulated=False,
        note="Sentiment overlay is current signal store (fixed); not historically aligned — directional only.",
    )
