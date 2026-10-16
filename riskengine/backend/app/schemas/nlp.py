from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.signal import EventType, SourceType


class NLPResult(BaseModel):
    """Output of the NLP stage, one per (document, company). Impact scoring (Phase 4) turns this into a RiskSignal."""
    doc_id: str
    source: SourceType
    source_name: str
    timestamp: datetime
    text: str
    simulated: bool = False
    ticker: str | None = None
    company: str | None = None
    sentiment_score: float = Field(ge=-1.0, le=1.0)
    sentiment_probs: dict[str, float]
    sentiment_confidence: float = Field(ge=0.0, le=1.0)
    event_type: EventType
    event_confidence: float = Field(ge=0.0, le=1.0)
    event_method: str
    event_scores: dict[str, float] = Field(default_factory=dict)  # top-3
    entities: dict[str, list[str]] = Field(default_factory=dict)
    model_info: str = ""
