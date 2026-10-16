import pytest
from fastapi.testclient import TestClient

from app.api.deps import set_engine
from app.config import Settings
from app.main import app
from app.nlp.events import EventClassifier
from app.nlp.sentiment import LexiconBackend
from app.risk.engine import RiskEngine
from app.risk.store import SignalStore
from app.risk.triggers import trigger_signals


def make_engine():
    return RiskEngine(Settings(_env_file=None), SignalStore(), LexiconBackend(), EventClassifier(None))


@pytest.fixture
def client():
    eng = make_engine()
    eng.ingest_and_score()
    set_engine(eng)
    yield TestClient(app), eng
    set_engine(None)


def test_signals_default_and_limit(client):
    c, eng = client
    r = c.get("/signals?limit=5").json()
    assert r["count"] == 5 == len(r["signals"])
    s = r["signals"][0]
    assert {"ticker", "sentiment_score", "event_type", "impact_score", "confidence", "reason", "score_breakdown"} <= s.keys()


def test_signals_brief_matches_spec_shape(client):
    c, _ = client
    s = c.get("/signals?limit=3&view=brief").json()["signals"][0]
    assert {"ticker", "sentiment", "event_type", "impact_score", "confidence"} <= s.keys() and "text" not in s


def test_signals_filters_and_ordering(client):
    c, eng = client
    hi = c.get("/signals?min_impact=7&order=impact&limit=100").json()["signals"]
    assert hi and all(s["impact_score"] >= 7 for s in hi)
    assert [s["impact_score"] for s in hi] == sorted((s["impact_score"] for s in hi), reverse=True)
    t = c.get("/signals?ticker=tsla&limit=100").json()["signals"]
    assert t and all(s["ticker"] == "TSLA" for s in t)
    ev = c.get("/signals?event_type=Cybersecurity&limit=100").json()["signals"]
    assert ev and all(s["event_type"] == "Cybersecurity" for s in ev)
    assert all(s["source"] == "social" for s in c.get("/signals?source=social&limit=100").json()["signals"])


@pytest.mark.parametrize("q", ["limit=0", "limit=501", "min_impact=0", "min_impact=11", "event_type=Nope",
                               "risk_level=EXTREME", "order=random", "view=huge", "source=fax"])
def test_signals_validation_422(client, q):
    assert client[0].get(f"/signals?{q}").status_code == 422


def test_signals_by_ticker(client):
    c, _ = client
    assert all(s["ticker"] == "AAPL" for s in c.get("/signals/aapl").json()["signals"])
    assert c.get("/signals/ZZZZ").status_code == 404
    assert c.get("/signals/HD").json() == {"count": 0, "signals": []}   # tracked but no signals


def test_analyze(client):
    c, eng = client
    before = eng.store.count()
    r = c.post("/analyze", json={"text": "Tesla faces federal probe, regulators weigh mandatory recall"})
    assert r.status_code == 200
    body = r.json()
    sig = body["signals"][0]
    assert sig["ticker"] == "TSLA" and sig["event_type"] == "Regulatory" and 1 <= sig["impact_score"] <= 10
    assert "lexicon" in body["model_info"] and sig["score_breakdown"]["impact"] == sig["impact_score"]
    assert eng.store.count() == before                       # not persisted by default
    c.post("/analyze", json={"text": "Boeing delays deliveries after manufacturing defects", "persist": True})
    assert eng.store.count() == before + 1


@pytest.mark.parametrize("payload", [{"text": ""}, {"text": "ab"}, {"text": "x" * 5001}, {}, {"text": "ok text", "source": "fax"}])
def test_analyze_validation(client, payload):
    assert client[0].post("/analyze", json=payload).status_code == 422


def test_events_consistent_with_store(client):
    c, eng = client
    r = c.get("/events").json()
    assert r["total_signals"] == eng.store.count() == sum(e["count"] for e in r["events"])
    assert all(e["max_impact"] >= e["avg_impact"] for e in r["events"])


def test_risk_summary(client):
    c, eng = client
    r = c.get("/risk-summary").json()
    assert r["total_signals"] == eng.store.count() and r["data_mode"] == "simulated"
    assert sum(r["by_risk_level"].values()) == r["total_signals"]
    expected = trigger_signals(eng.store.query(limit=500), r["stress_trigger_threshold"])
    assert {t["id"] for t in r["stress_triggers"]} == {t.id for t in expected} and expected
    assert r["event_method_note"] == "rules-only" and "lexicon" in r["sentiment_backend"]


def test_refresh_is_idempotent_and_reset(client):
    c, eng = client
    n = eng.store.count()
    r = c.post("/refresh").json()
    assert r["total_in_store"] == n and r["signals_built"] == n and {s["mode"] for s in r["sources"]} == {"sample"}
    assert c.post("/refresh?reset=true").json()["total_in_store"] == n


def test_sources_reports_fallback(client):
    c, _ = client
    r = c.get("/sources").json()
    assert r["live_data_enabled"] is False and {s["name"] for s in r["sources"]} == {"news_sample.jsonl", "tweets_sample.jsonl"}


def test_module_endpoints_are_implemented(client):
    c, _ = client
    assert c.get("/portfolio").status_code == 200
    assert c.post("/rebalance").status_code == 200
    r = c.post("/stress-test", json={"event_type": "Market Shock", "impact_score": 8.0})
    assert r.status_code == 200 and "portfolio_value_before" in r.json()


def test_openapi_documents_all_endpoints(client):
    paths = client[0].get("/openapi.json").json()["paths"]
    for p in ["/health", "/analyze", "/signals", "/signals/{ticker}", "/events", "/risk-summary", "/refresh",
              "/sources", "/portfolio", "/rebalance", "/stress-test"]:
        assert p in paths


def test_lifespan_populates_empty_store():
    eng = make_engine()
    set_engine(eng)
    try:
        assert eng.store.count() == 0
        with TestClient(app) as c:
            assert eng.store.count() > 0 and c.get("/risk-summary").json()["total_signals"] == eng.store.count()
    finally:
        set_engine(None)


def test_unhandled_error_returns_json_500(client):
    c, eng = client
    eng.store.db.close()                                      # force a DB failure
    r = TestClient(app, raise_server_exceptions=False).get("/signals")
    assert r.status_code == 500 and r.json()["error"] == "internal_error"
