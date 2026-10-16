import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from app.config import get_settings
from app.api.deps import get_engine
from app.nlp.companies import COMPANIES
from app.risk.engine import RiskEngine
from app.risk.triggers import trigger_signals
from app.schemas.api import (AnalyzeRequest, AnalyzeResponse, BriefSignalsResponse, EventsResponse, RefreshResponse,
                             RiskSummary, SignalBrief, SignalsResponse, SourcesResponse, TriggerBrief)
from app.schemas.signal import EventType, RiskLevel, RiskSignal, SourceType

log = logging.getLogger(__name__)
router = APIRouter(tags=["risk-engine"])


def _brief(s: RiskSignal) -> SignalBrief:
    return SignalBrief(id=s.id, ticker=s.ticker, sentiment=s.sentiment_score, event_type=s.event_type,
                       impact_score=s.impact_score, confidence=s.confidence, risk_level=s.risk_level,
                       direction=s.direction, timestamp=s.timestamp)


def _respond(sigs: list[RiskSignal], view: str):
    if view == "brief":
        return BriefSignalsResponse(count=len(sigs), signals=[_brief(s) for s in sigs])
    return SignalsResponse(count=len(sigs), signals=sigs)


@router.post("/analyze", response_model=AnalyzeResponse, summary="Analyze arbitrary text into risk signals")
def analyze(req: AnalyzeRequest, engine: RiskEngine = Depends(get_engine)) -> AnalyzeResponse:
    sigs = engine.analyze_text(req.text, req.source, req.source_name, req.timestamp, req.persist)
    return AnalyzeResponse(count=len(sigs), signals=sigs, model_info=engine.model_info)


@router.get("/signals", response_model=SignalsResponse | BriefSignalsResponse, summary="List stored risk signals")
def list_signals(limit: int = Query(20, ge=1, le=500), ticker: str | None = None, event_type: EventType | None = None,
                 source: SourceType | None = None, risk_level: RiskLevel | None = None,
                 min_impact: float | None = Query(None, ge=1, le=10), order: Literal["time", "impact"] = "time",
                 view: Literal["full", "brief"] = "full", engine: RiskEngine = Depends(get_engine)):
    sigs = engine.store.query(limit=limit, ticker=ticker.upper() if ticker else None,
                              event_type=event_type.value if event_type else None,
                              source=source.value if source else None,
                              risk_level=risk_level.value if risk_level else None, min_impact=min_impact, order=order)
    return _respond(sigs, view)


@router.get("/signals/{ticker}", response_model=SignalsResponse | BriefSignalsResponse,
            summary="Signals for one tracked ticker")
def signals_for_ticker(ticker: str, limit: int = Query(20, ge=1, le=500), order: Literal["time", "impact"] = "time",
                       view: Literal["full", "brief"] = "full", engine: RiskEngine = Depends(get_engine)):
    t = ticker.upper()
    if t not in COMPANIES:
        raise HTTPException(404, f"Ticker {t} is not in the tracked universe ({len(COMPANIES)} companies)")
    return _respond(engine.store.query(limit=limit, ticker=t, order=order), view)


@router.get("/events", response_model=EventsResponse, summary="Signal counts and impact by event type")
def events(engine: RiskEngine = Depends(get_engine)) -> EventsResponse:
    stats = engine.store.event_stats()
    return EventsResponse(total_signals=sum(e["count"] for e in stats), events=stats)


@router.get("/risk-summary", response_model=RiskSummary, summary="Dashboard summary + stress-test triggers")
def risk_summary(engine: RiskEngine = Depends(get_engine)) -> RiskSummary:
    st = get_settings()
    s = engine.store.summary()
    trig = trigger_signals(engine.store.query(limit=500, order="impact"), st.stress_trigger_impact)
    share = s["simulated_share"]
    mode = "empty" if s["total"] == 0 else "simulated" if share >= 0.999 else "real" if share <= 0.001 else "mixed"
    return RiskSummary(
        total_signals=s["total"], by_risk_level=s["by_risk_level"], by_event_type=s["by_event_type"],
        by_source=s["by_source"], top_risky_tickers=s["top_risky_tickers"],
        stress_trigger_threshold=st.stress_trigger_impact,
        stress_triggers=[TriggerBrief(id=t.id, ticker=t.ticker, event_type=t.event_type, impact_score=t.impact_score,
                                      text=t.text) for t in trig],
        data_mode=mode, sentiment_backend=engine.model_info,
        event_method_note="rules-only" if engine.events.zs is None else "hybrid (rules + zero-shot)")


@router.post("/refresh", response_model=RefreshResponse, summary="Re-ingest sources and rebuild signals")
def refresh(reset: bool = Query(False, description="Clear stored signals first."),
            engine: RiskEngine = Depends(get_engine)) -> RefreshResponse:
    if reset:
        engine.store.clear()
    sigs, rep = engine.ingest_and_score()
    return RefreshResponse(signals_built=len(sigs), total_in_store=engine.store.count(), sources=rep.report)


@router.get("/sources", response_model=SourcesResponse, summary="Which sources were used (live / local / sample) and why")
def sources(engine: RiskEngine = Depends(get_engine)) -> SourcesResponse:
    rep = engine.last_ingestion.report if engine.last_ingestion else []
    return SourcesResponse(sources=rep, live_data_enabled=get_settings().use_live_data)
