"""The contract between the Risk Engine and both downstream modules."""
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class EventType(str, Enum):
    GEOPOLITICAL = "Geopolitical"
    MACROECONOMIC = "Macroeconomic"
    CREDIT_EVENT = "Credit Event"
    MNA = "Merger & Acquisition"
    EARNINGS = "Earnings"
    PRODUCT_LAUNCH = "Product Launch"
    REGULATORY = "Regulatory"
    LEGAL = "Legal"
    SUPPLY_CHAIN = "Supply Chain"
    MANAGEMENT_CHANGE = "Management Change"
    CYBERSECURITY = "Cybersecurity"
    MARKET_SHOCK = "Market Shock"
    COMMODITY_SHOCK = "Commodity Shock"
    OTHER = "Other"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Direction(str, Enum):
    ADVERSE = "adverse"
    FAVOURABLE = "favourable"
    NEUTRAL = "neutral"


class SourceType(str, Enum):
    NEWS = "news"
    SOCIAL = "social"


class RiskSignal(BaseModel):
    id: str = ""
    doc_id: str = ""
    ticker: str | None = None
    company: str | None = None
    source: SourceType
    source_name: str | None = None
    timestamp: datetime
    text: str
    sentiment_score: float = Field(ge=-1.0, le=1.0)
    sentiment_probs: dict[str, float] | None = None  # raw model probabilities
    event_type: EventType
    impact_score: float = Field(ge=1.0, le=10.0)
    confidence: float = Field(ge=0.0, le=1.0)
    risk_level: RiskLevel
    entities: dict[str, list[str]] = Field(default_factory=dict)
    reason: str = ""
    direction: Direction = Direction.NEUTRAL
    score_breakdown: dict[str, float] = Field(default_factory=dict)  # every factor behind impact_score
    simulated: bool = False  # True for any synthetic / fallback record
    model_info: str = ""     # which sentiment/event backend produced this
