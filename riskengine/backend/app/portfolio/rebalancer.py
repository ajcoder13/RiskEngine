"""Module A: Tactical Index Rebalancer.

Strategy
--------
For each ticker i, an adjusted score is computed:

    raw_i = base_weight_i × (1 + alpha × sentiment_i) × volatility_adj_i

where:
  alpha              = sentiment sensitivity (default 0.40)
  sentiment_i        = sentiment score from the highest-impact adverse signal for that ticker,
                       or 0.0 if no signal exists
  volatility_adj_i   = 1 / (1 + beta × vol_30d_i)  downweights high-vol stocks

Weights are then normalised to sum to 1 and clamped to [min_weight, max_weight].
Turnover is penalised so consecutive rebalances stay realistic.

All assumptions are explicit and configurable.  The method is documented in the reason field
of every holding so the dashboard can explain "why did TSLA decrease?".
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

import numpy as np

from app.portfolio.universe import INDEX_UNIVERSE, SECTORS
from app.risk.store import SignalStore

log = logging.getLogger(__name__)

# ---- rebalance parameters (can be overridden per request) ---
@dataclass
class RebalanceParams:
    alpha: float = 0.40          # sentiment sensitivity
    beta: float  = 0.30          # volatility penalty
    min_weight: float = 0.02     # 2 % floor
    max_weight: float = 0.12     # 12 % cap
    max_turnover: float = 0.30   # 30 % total portfolio turnover limit
    signal_lookback_signals: int = 10  # max signals considered per ticker


# ---- holding DTO ----
@dataclass
class Holding:
    ticker: str
    name: str
    sector: str
    base_weight: float
    current_weight: float          # before rebalance
    new_weight: float = 0.0
    weight_change: float = 0.0
    sentiment_score: float = 0.0
    impact_score: float = 0.0
    price: float = 0.0
    prev_close: float = 0.0
    return_1d: float = 0.0
    return_5d: float = 0.0
    volatility_30d: float = 0.25
    simulated_price: bool = False
    reason: str = ""


@dataclass
class RebalanceResult:
    holdings: list[Holding] = field(default_factory=list)
    total_turnover: float = 0.0
    turnover_capped: bool = False
    simulated_prices: bool = False
    rebalanced_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    params: dict = field(default_factory=dict)

    # portfolio-level metrics
    weighted_sentiment: float = 0.0
    sector_exposure: dict[str, float] = field(default_factory=dict)


def _get_ticker_sentiment(ticker: str, store: SignalStore, max_signals: int) -> tuple[float, float]:
    """Return (sentiment_score, impact_score) for a ticker from the most recent adverse signals."""
    sigs = store.query(limit=max_signals, ticker=ticker, order="impact")
    if not sigs:
        return 0.0, 0.0
    # Weight by confidence; use adverse signals primarily but any signal contributes
    adverse = [s for s in sigs if s.direction.value == "adverse"]
    pool = adverse if adverse else sigs
    weights = [s.confidence for s in pool]
    total_w = sum(weights) or 1.0
    sent = sum(s.sentiment_score * s.confidence for s in pool) / total_w
    imp = max(s.impact_score for s in pool)
    return round(sent, 4), round(imp, 2)


def rebalance(store: SignalStore, market: dict[str, dict], params: RebalanceParams | None = None,
              prev_weights: dict[str, float] | None = None) -> RebalanceResult:
    """Core rebalancing algorithm."""
    p = params or RebalanceParams()
    result = RebalanceResult(params={
        "alpha": p.alpha, "beta": p.beta,
        "min_weight": p.min_weight, "max_weight": p.max_weight,
        "max_turnover": p.max_turnover,
    })

    tickers = list(INDEX_UNIVERSE.keys())
    base_weights = {t: INDEX_UNIVERSE[t]["base_weight"] for t in tickers}
    # normalise base weights so they sum exactly to 1
    bw_sum = sum(base_weights.values())
    base_weights = {t: w / bw_sum for t, w in base_weights.items()}

    # use prev_weights if provided, else equal-weight start
    cur_weights = prev_weights or base_weights

    # ---- step 1: gather sentiment signals ----
    sentiments: dict[str, float] = {}
    impacts: dict[str, float] = {}
    for t in tickers:
        sentiments[t], impacts[t] = _get_ticker_sentiment(t, store, p.signal_lookback_signals)

    # ---- step 2: compute raw adjusted scores ----
    raw_scores: dict[str, float] = {}
    vols: dict[str, float] = {}
    for t in tickers:
        mkt = market.get(t, {})
        vol = mkt.get("volatility_30d", 0.25)
        vols[t] = vol
        vol_adj = 1.0 / (1.0 + p.beta * vol)
        raw_scores[t] = base_weights[t] * (1.0 + p.alpha * sentiments[t]) * vol_adj

    # ---- step 3: normalise ----
    total = sum(raw_scores.values()) or 1.0
    norm_weights = {t: raw_scores[t] / total for t in tickers}

    # ---- step 4: clamp to [min, max] and renormalise (iterative) ----
    clamped_weights = _clamp_weights(norm_weights, p.min_weight, p.max_weight)

    # ---- step 5: turnover constraint ----
    turnover = sum(abs(clamped_weights[t] - cur_weights.get(t, base_weights[t])) for t in tickers)
    turnover_capped = False
    if turnover > p.max_turnover:
        turnover_capped = True
        ratio = p.max_turnover / turnover
        final_weights = {t: cur_weights.get(t, base_weights[t]) + ratio * (clamped_weights[t] - cur_weights.get(t, base_weights[t]))
                         for t in tickers}
        # renormalise after scaling
        fw_sum = sum(final_weights.values())
        final_weights = {t: w / fw_sum for t, w in final_weights.items()}
        actual_turnover = p.max_turnover
    else:
        final_weights = clamped_weights
        actual_turnover = turnover

    # ---- step 6: assemble holdings ----
    simulated_any = False
    for t in tickers:
        mkt = market.get(t, {})
        sim = mkt.get("simulated", True)
        simulated_any = simulated_any or sim
        sent = sentiments[t]
        imp = impacts[t]
        old_w = cur_weights.get(t, base_weights[t])
        new_w = final_weights[t]
        delta = new_w - old_w

        if abs(sent) < 0.05 and imp == 0.0:
            reason = f"No material signal; weight held near base ({base_weights[t]:.1%})."
        else:
            direction = "increased" if delta > 0 else "decreased" if delta < 0 else "unchanged"
            tone = "positive" if sent > 0 else "negative"
            reason = (f"Weight {direction} ({old_w:.1%} → {new_w:.1%}): "
                      f"{tone} sentiment ({sent:+.2f}), impact {imp:.1f}/10, "
                      f"vol-adj factor {1/(1+p.beta*vols[t]):.2f}.")
            if turnover_capped:
                reason += " Turnover cap applied."

        result.holdings.append(Holding(
            ticker=t, name=INDEX_UNIVERSE[t]["name"], sector=INDEX_UNIVERSE[t]["sector"],
            base_weight=base_weights[t], current_weight=old_w, new_weight=round(new_w, 6),
            weight_change=round(delta, 6), sentiment_score=sent, impact_score=imp,
            price=mkt.get("price", 0.0), prev_close=mkt.get("prev_close", 0.0),
            return_1d=mkt.get("return_1d", 0.0), return_5d=mkt.get("return_5d", 0.0),
            volatility_30d=vols[t], simulated_price=sim, reason=reason,
        ))

    result.total_turnover = round(actual_turnover, 6)
    result.turnover_capped = turnover_capped
    result.simulated_prices = simulated_any

    # sector exposure
    sec_exp: dict[str, float] = {s: 0.0 for s in SECTORS}
    for h in result.holdings:
        sec_exp[h.sector] = round(sec_exp.get(h.sector, 0.0) + h.new_weight, 6)
    result.sector_exposure = sec_exp

    # portfolio-level weighted sentiment
    result.weighted_sentiment = round(
        sum(h.new_weight * h.sentiment_score for h in result.holdings), 4)

    return result


def _clamp_weights(w: dict[str, float], lo: float, hi: float, max_iter: int = 50) -> dict[str, float]:
    """Iteratively clamp weights to [lo, hi] and renormalise until stable."""
    out = dict(w)
    for _ in range(max_iter):
        changed = False
        for t, v in out.items():
            if v < lo:
                out[t] = lo; changed = True
            elif v > hi:
                out[t] = hi; changed = True
        total = sum(out.values())
        if total > 0:
            out = {t: v / total for t, v in out.items()}
        if not changed:
            break
    return out
