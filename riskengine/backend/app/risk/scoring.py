"""Explainable impact score.

  base   = w_sev * severity(event) + w_sent * |sentiment|                       in [0,1]
  raw    = base * f_conf * f_rel * f_mkt * f_nov * f_rec                        in [0,1]
  impact = clamp(1 + 9 * raw**gamma, 1, 10)

Each modulator f_x = floor_x + (1 - floor_x) * x, so no single weak factor can zero a signal.
Every factor is returned in `breakdown` so the dashboard can answer "why is this risky?".
The score is an ordinal severity index (judgement-based priors), not a price forecast."""
import math
from datetime import datetime

from app.risk.params import ADVERSE_BY_NATURE, SOURCE_BY_NAME, SOURCE_BY_PREFIX, SOURCE_DEFAULT, SYSTEMIC, RiskParams
from app.schemas.signal import Direction, EventType, RiskLevel, SourceType


def _f(floor: float, x: float) -> float:
    return floor + (1.0 - floor) * max(0.0, min(1.0, x))


def source_reliability(source: SourceType, source_name: str) -> float:
    n = (source_name or "").lower()
    for k, v in SOURCE_BY_NAME.items():
        if k in n:
            return v
    for k, v in SOURCE_BY_PREFIX.items():
        if n.startswith(k):
            return v
    return SOURCE_DEFAULT[source.value]


def market_relevance(ticker: str | None, event: EventType, p: RiskParams) -> float:
    if ticker:
        return p.relevance_ticker
    return p.relevance_systemic if event in SYSTEMIC else p.relevance_none


def novelty(n_similar: int, p: RiskParams) -> float:
    return 1.0 / (1.0 + p.novelty_decay * max(0, n_similar))


def recency(ts: datetime, ref: datetime, p: RiskParams) -> float:
    age_h = max(0.0, (ref - ts).total_seconds() / 3600.0)
    return math.exp(-math.log(2) * age_h / p.recency_halflife_hours)


def direction(sentiment: float, event: EventType, p: RiskParams) -> Direction:
    if event in ADVERSE_BY_NATURE:
        return Direction.FAVOURABLE if sentiment >= p.adverse_nature_override else Direction.ADVERSE
    if sentiment <= p.adverse_sentiment:
        return Direction.ADVERSE
    return Direction.FAVOURABLE if sentiment >= p.favourable_sentiment else Direction.NEUTRAL


def compute_impact(*, event: EventType, sentiment: float, confidence: float, reliability: float,
                   relevance: float, novelty_: float, recency_: float, p: RiskParams) -> tuple[float, dict[str, float]]:
    sev = p.severity[event]
    base = p.w_severity * sev + p.w_sentiment * abs(sentiment)
    f = {"f_confidence": _f(p.floor_confidence, confidence), "f_reliability": _f(p.floor_reliability, reliability),
         "f_relevance": _f(p.floor_relevance, relevance), "f_novelty": _f(p.floor_novelty, novelty_),
         "f_recency": _f(p.floor_recency, recency_)}
    raw = base * math.prod(f.values())
    impact = max(1.0, min(10.0, 1.0 + 9.0 * raw ** p.gamma))
    breakdown = {"severity": sev, "sentiment_magnitude": abs(sentiment), "confidence": confidence,
                 "source_reliability": reliability, "market_relevance": relevance, "novelty": novelty_,
                 "recency": recency_, "base": base, **f, "raw": raw, "impact": impact}
    impact = round(impact, 2)
    breakdown["impact"] = impact          # headline and breakdown must agree exactly
    return impact, {k: round(v, 4) for k, v in breakdown.items()}


def risk_level(impact: float, bands: dict[str, float]) -> RiskLevel:
    """`bands` maps level -> exclusive upper bound, ordered ascending (see Settings.risk_bands)."""
    for name, upper in bands.items():
        if impact < upper:
            return RiskLevel(name)
    return RiskLevel.CRITICAL


def explain(*, event: EventType, company: str | None, sentiment: float, dirn: Direction, impact: float,
            level: RiskLevel, b: dict[str, float], simulated: bool) -> str:
    tone = "strongly " if abs(sentiment) >= 0.6 else ""
    word = {"adverse": "negative", "favourable": "positive", "neutral": "neutral"}[dirn.value]
    subject = company or "market-wide"
    drivers = sorted([("event severity", b["severity"]), ("sentiment strength", b["sentiment_magnitude"])],
                     key=lambda kv: -kv[1])
    parts = [f"{event.value} event ({subject}): {tone}{word} sentiment ({sentiment:+.2f}) -> impact {impact:.1f}/10 ({level.value}).",
             f"Main driver: {drivers[0][0]} ({drivers[0][1]:.2f}); source reliability {b['source_reliability']:.2f}, "
             f"novelty {b['novelty']:.2f}, confidence {b['confidence']:.2f}."]
    if dirn != Direction.ADVERSE:
        parts.append("Not adverse, so risk level is capped at LOW for downside-risk purposes.")
    if simulated:
        parts.append("[SIMULATED sample data]")
    return " ".join(parts)
