from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import get_settings
from app.main import app
from app.schemas.signal import EventType, RiskLevel, RiskSignal, SourceType

client = TestClient(app)


def _sig(**kw):
    base = dict(source=SourceType.NEWS, timestamp=datetime(2026, 1, 1), text="x",
                sentiment_score=-0.5, event_type=EventType.OTHER, impact_score=5.0,
                confidence=0.8, risk_level=RiskLevel.MEDIUM)
    base.update(kw)
    return RiskSignal(**base)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_openapi_available():
    assert client.get("/openapi.json").status_code == 200


def test_schema_accepts_valid():
    assert _sig().impact_score == 5.0


@pytest.mark.parametrize("kw", [{"sentiment_score": 1.5}, {"impact_score": 0.5},
                                {"impact_score": 10.5}, {"confidence": 1.2}])
def test_schema_rejects_out_of_range(kw):
    with pytest.raises(ValidationError):
        _sig(**kw)


def test_risk_bands_cover_scale():
    b = get_settings().risk_bands
    assert list(b.values()) == sorted(b.values()) and max(b.values()) > 10
