"""Process-wide RiskEngine (loading FinBERT is expensive, so it is created once and cached)."""
import logging
import threading

from app.risk.engine import RiskEngine

log = logging.getLogger(__name__)
_engine: RiskEngine | None = None
_lock = threading.Lock()


def get_engine() -> RiskEngine:
    global _engine
    with _lock:
        if _engine is None:
            _engine = RiskEngine()
            log.info("RiskEngine ready (sentiment=%s)", _engine.model_info)
        return _engine


def set_engine(engine: RiskEngine | None) -> None:
    global _engine
    with _lock:
        _engine = engine
