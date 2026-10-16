"""NLPResult -> RiskSignal: confidence fusion, novelty tracking, relevance gating, scoring, explanation."""
import hashlib
import logging
import math
from collections import defaultdict
from datetime import datetime, timezone

from app.config import get_settings
from app.risk import scoring as sc
from app.risk.params import SYSTEMIC, RiskParams
from app.schemas.nlp import NLPResult
from app.schemas.signal import Direction, RiskLevel, RiskSignal

log = logging.getLogger(__name__)


def _utc(ts: datetime) -> datetime:
    return ts.replace(tzinfo=timezone.utc) if ts.tzinfo is None else ts.astimezone(timezone.utc)


def signal_id(doc_id: str, ticker: str | None) -> str:
    return hashlib.sha1(f"{doc_id}|{ticker or 'MKT'}".encode()).hexdigest()[:16]


def build_signals(results: list[NLPResult], p: RiskParams | None = None, bands: dict[str, float] | None = None,
                  reference_time: datetime | None = None, relevant_only: bool = True) -> list[RiskSignal]:
    p = p or RiskParams()
    bands = bands or get_settings().risk_bands
    if not results:
        return []
    ordered = sorted(results, key=lambda r: _utc(r.timestamp))
    ref = _utc(reference_time) if reference_time else _utc(ordered[-1].timestamp)
    history: dict[tuple, list[datetime]] = defaultdict(list)
    out: list[RiskSignal] = []
    dropped = 0
    for r in ordered:
        ts = _utc(r.timestamp)
        if relevant_only and r.ticker is None and r.event_type not in SYSTEMIC:
            dropped += 1          # no identifiable company and not a market-wide event type
            continue
        key = (r.ticker or "MKT", r.event_type)
        n_similar = sum(1 for t in history[key] if 0 <= (ts - t).total_seconds() / 3600 <= p.novelty_window_hours)
        history[key].append(ts)

        conf = math.sqrt(r.sentiment_confidence * r.event_confidence)
        rel = sc.source_reliability(r.source, r.source_name)
        mkt = sc.market_relevance(r.ticker, r.event_type, p)
        nov = sc.novelty(n_similar, p)
        rec = sc.recency(ts, ref, p)
        impact, b = sc.compute_impact(event=r.event_type, sentiment=r.sentiment_score, confidence=conf,
                                      reliability=rel, relevance=mkt, novelty_=nov, recency_=rec, p=p)
        dirn = sc.direction(r.sentiment_score, r.event_type, p)
        level = sc.risk_level(impact, bands) if dirn == Direction.ADVERSE else RiskLevel.LOW
        out.append(RiskSignal(
            id=signal_id(r.doc_id, r.ticker), doc_id=r.doc_id, ticker=r.ticker, company=r.company, source=r.source,
            source_name=r.source_name, timestamp=ts, text=r.text, sentiment_score=round(r.sentiment_score, 4),
            sentiment_probs={k: round(v, 4) for k, v in r.sentiment_probs.items()}, event_type=r.event_type, impact_score=impact,
            confidence=round(conf, 4), risk_level=level, entities=r.entities, direction=dirn, score_breakdown=b,
            reason=sc.explain(event=r.event_type, company=r.company, sentiment=r.sentiment_score, dirn=dirn,
                              impact=impact, level=level, b=b, simulated=r.simulated),
            simulated=r.simulated, model_info=f"{r.model_info}; event={r.event_method}"))
    log.info("Built %d signals (%d dropped as not relevant)", len(out), dropped)
    return out
