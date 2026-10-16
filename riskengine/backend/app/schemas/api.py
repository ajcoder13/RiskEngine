from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.document import SourceStatus
from app.schemas.signal import Direction, EventType, RiskLevel, RiskSignal, SourceType


class AnalyzeRequest(BaseModel):
    text: str = Field(min_length=3, max_length=5000)
    source: SourceType = SourceType.NEWS
    source_name: str = Field("user-input", max_length=100)
    timestamp: datetime | None = None
    persist: bool = Field(False, description="Store the resulting signals so Modules A/B can see them.")
    model_config = {"json_schema_extra": {"example": {
        "text": "Tesla faces federal probe over driver-assistance crashes, regulators weigh mandatory recall",
        "source": "news", "source_name": "newsapi:Reuters"}}}


class AnalyzeResponse(BaseModel):
    count: int
    signals: list[RiskSignal]
    model_info: str
    note: str = "Impact is an ordinal severity index built from documented priors, not a price forecast."


class SignalBrief(BaseModel):
    id: str
    ticker: str | None
    sentiment: float
    event_type: EventType
    impact_score: float
    confidence: float
    risk_level: RiskLevel
    direction: Direction
    timestamp: datetime


class SignalsResponse(BaseModel):
    count: int
    signals: list[RiskSignal]


class BriefSignalsResponse(BaseModel):
    count: int
    signals: list[SignalBrief]


class EventSummary(BaseModel):
    event_type: str
    count: int
    avg_impact: float
    max_impact: float
    adverse_count: int


class EventsResponse(BaseModel):
    total_signals: int
    events: list[EventSummary]


class TriggerBrief(BaseModel):
    id: str
    ticker: str | None
    event_type: EventType
    impact_score: float
    text: str


class RiskSummary(BaseModel):
    total_signals: int
    by_risk_level: dict[str, int]
    by_event_type: dict[str, int]
    by_source: dict[str, int]
    top_risky_tickers: list[dict]
    stress_trigger_threshold: float
    stress_triggers: list[TriggerBrief]
    data_mode: Literal["empty", "simulated", "mixed", "real"]
    sentiment_backend: str
    event_method_note: str


class RefreshResponse(BaseModel):
    signals_built: int
    total_in_store: int
    sources: list[SourceStatus]


class SourcesResponse(BaseModel):
    sources: list[SourceStatus]
    live_data_enabled: bool
