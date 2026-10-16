"""All impact-scoring assumptions in one place. These are JUDGEMENT-BASED priors, not fitted parameters:
the impact score is an ordinal severity index, NOT a forecast of price moves."""
import json
from dataclasses import dataclass, field, replace
from pathlib import Path

from app.schemas.signal import EventType as E

EVENT_SEVERITY: dict[E, float] = {   # 0-1: intrinsic potential market significance of the event class
    E.CREDIT_EVENT: 0.90, E.GEOPOLITICAL: 0.85, E.MARKET_SHOCK: 0.85, E.CYBERSECURITY: 0.70,
    E.REGULATORY: 0.65, E.SUPPLY_CHAIN: 0.60, E.COMMODITY_SHOCK: 0.60, E.MACROECONOMIC: 0.60,
    E.LEGAL: 0.55, E.MNA: 0.50, E.EARNINGS: 0.45, E.MANAGEMENT_CHANGE: 0.35, E.PRODUCT_LAUNCH: 0.25, E.OTHER: 0.15,
}
SYSTEMIC = {E.GEOPOLITICAL, E.MACROECONOMIC, E.MARKET_SHOCK, E.COMMODITY_SHOCK}   # market-wide reach
ADVERSE_BY_NATURE = {E.GEOPOLITICAL, E.MARKET_SHOCK, E.CREDIT_EVENT, E.CYBERSECURITY, E.SUPPLY_CHAIN}

SOURCE_BY_NAME = {"reuters": 0.95, "bloomberg": 0.95, "associated press": 0.92, "apnews": 0.92,
                  "wall street journal": 0.92, "wsj.com": 0.92, "financial times": 0.92, "ft.com": 0.92, "cnbc": 0.85}
SOURCE_BY_PREFIX = {"newsapi:": 0.75, "gdelt:": 0.70, "kaggle-financial-news": 0.80, "kaggle-tweets": 0.40,
                    "sample-synthetic-news": 0.70, "sample-synthetic-social": 0.40}
SOURCE_DEFAULT = {"news": 0.65, "social": 0.35}


@dataclass(frozen=True)
class RiskParams:
    w_severity: float = 0.60          # base = w_sev*severity + w_sent*|sentiment|   (weights sum to 1)
    w_sentiment: float = 0.40
    gamma: float = 0.70               # curve: impact = 1 + 9 * raw**gamma  (<1 lifts mid-range scores)
    floor_confidence: float = 0.50    # modulator factor = floor + (1-floor)*x ; keeps any one factor from zeroing a signal
    floor_reliability: float = 0.60
    floor_relevance: float = 0.60
    floor_novelty: float = 0.60
    floor_recency: float = 0.50
    relevance_ticker: float = 1.0
    relevance_systemic: float = 0.85
    relevance_none: float = 0.45
    novelty_decay: float = 0.5        # novelty = 1/(1 + decay * #similar signals in window)
    novelty_window_hours: float = 24.0
    recency_halflife_hours: float = 48.0
    adverse_sentiment: float = -0.20
    favourable_sentiment: float = 0.20
    adverse_nature_override: float = 0.30   # adverse-by-nature events flip to favourable only above this sentiment
    min_abs_sentiment_for_systemic_signal: float = 0.0
    severity: dict = field(default_factory=lambda: dict(EVENT_SEVERITY))


def load_params(path: Path | None = None) -> RiskParams:
    """Optional JSON override of scalar parameters, e.g. {"gamma": 0.8}. Event severities override via {"severity": {"Legal": 0.6}}."""
    p = RiskParams()
    if path and Path(path).exists():
        raw = json.loads(Path(path).read_text())
        sev = dict(p.severity)
        sev.update({E(k): v for k, v in raw.pop("severity", {}).items()})
        p = replace(p, severity=sev, **raw)
    return p
