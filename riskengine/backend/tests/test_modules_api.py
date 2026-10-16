"""Integration tests for Module A and B API endpoints."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.deps import get_engine
from app.risk.engine import RiskEngine
from app.risk.store import SignalStore
from app.schemas.signal import RiskSignal, EventType, RiskLevel, Direction, SourceType
from datetime import datetime, timezone


def _make_signal(ticker="AAPL", impact=8.5, event=EventType.GEOPOLITICAL,
                 direction=Direction.ADVERSE) -> RiskSignal:
    return RiskSignal(
        id=f"test-{ticker}-{event.value}", doc_id="doc1",
        ticker=ticker, company="Test Co", source=SourceType.NEWS, source_name="test",
        timestamp=datetime.now(timezone.utc), text="Test signal",
        sentiment_score=-0.72, event_type=event, impact_score=impact,
        confidence=0.90, risk_level=RiskLevel.HIGH, direction=direction,
    )


@pytest.fixture
def client_with_signals():
    store = SignalStore(":memory:")
    # populate with signals spanning multiple tickers
    sigs = [
        _make_signal("AAPL", 8.5, EventType.REGULATORY),
        _make_signal("TSLA", 7.8, EventType.GEOPOLITICAL),
        _make_signal("JPM",  9.1, EventType.CREDIT_EVENT),
        _make_signal("XOM",  6.5, EventType.COMMODITY_SHOCK),
    ]
    store.upsert_many(sigs)
    engine = RiskEngine(store=store)

    app.dependency_overrides[get_engine] = lambda: engine
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def client_empty():
    store = SignalStore(":memory:")
    engine = RiskEngine(store=store)
    app.dependency_overrides[get_engine] = lambda: engine
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---- Module A ---------------------------------------------------------------

class TestPortfolioEndpoint:
    def test_get_portfolio_returns_200(self, client_with_signals):
        r = client_with_signals.get("/portfolio")
        assert r.status_code == 200

    def test_portfolio_holdings_count(self, client_with_signals):
        r = client_with_signals.get("/portfolio")
        data = r.json()
        assert data["holdings"] and len(data["holdings"]) == 20

    def test_portfolio_weights_sum_to_one(self, client_with_signals):
        r = client_with_signals.get("/portfolio")
        total = sum(h["new_weight"] for h in r.json()["holdings"])
        assert abs(total - 1.0) < 1e-4

    def test_portfolio_sector_exposure_present(self, client_with_signals):
        r = client_with_signals.get("/portfolio")
        data = r.json()
        assert "sector_exposure" in data
        assert sum(data["sector_exposure"].values()) == pytest.approx(1.0, abs=1e-4)


class TestRebalanceEndpoint:
    def test_rebalance_200(self, client_with_signals):
        r = client_with_signals.post("/rebalance?alpha=0.5&max_turnover=0.25")
        assert r.status_code == 200

    def test_rebalance_weights_sum(self, client_with_signals):
        r = client_with_signals.post("/rebalance?alpha=0.5")
        total = sum(h["new_weight"] for h in r.json()["holdings"])
        assert abs(total - 1.0) < 1e-4

    def test_rebalance_turnover_not_exceeded(self, client_with_signals):
        cap = 0.10
        r = client_with_signals.post(f"/rebalance?alpha=2.0&max_turnover={cap}")
        data = r.json()
        assert data["total_turnover"] <= cap + 1e-4

    def test_rebalance_empty_store_still_works(self, client_empty):
        r = client_empty.post("/rebalance")
        assert r.status_code == 200
        total = sum(h["new_weight"] for h in r.json()["holdings"])
        assert abs(total - 1.0) < 1e-4


class TestBacktestEndpoint:
    def test_backtest_returns_200(self, client_with_signals):
        r = client_with_signals.get("/backtest?lookback_days=60")
        assert r.status_code == 200

    def test_backtest_has_all_metrics(self, client_with_signals):
        r = client_with_signals.get("/backtest?lookback_days=60")
        data = r.json()
        for key in ("strategy", "equal_weight", "base_weight", "total_turnover", "series"):
            assert key in data, f"Missing key: {key}"

    def test_backtest_series_aligned(self, client_with_signals):
        r = client_with_signals.get("/backtest?lookback_days=60")
        s = r.json()["series"]
        assert len(s["dates"]) == len(s["strategy_cumret"]) == len(s["equal_cumret"])


# ---- Module B ---------------------------------------------------------------

class TestPortfolioComposition:
    def test_composition_returns_list(self, client_empty):
        r = client_empty.get("/portfolio-composition")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list) and len(data) > 0

    def test_composition_has_required_fields(self, client_empty):
        r = client_empty.get("/portfolio-composition")
        pos = r.json()[0]
        for field in ("asset_id", "asset_type", "market_value", "sector", "credit_rating"):
            assert field in pos


class TestStressTestEndpoint:
    def test_geopolitical_stress_200(self, client_empty):
        r = client_empty.post("/stress-test", json={"event_type": "Geopolitical", "impact_score": 8.5})
        assert r.status_code == 200

    def test_stress_produces_loss(self, client_empty):
        r = client_empty.post("/stress-test", json={"event_type": "Market Shock", "impact_score": 9.0})
        data = r.json()
        assert data["total_loss"] < 0

    def test_portfolio_after_lt_before(self, client_empty):
        r = client_empty.post("/stress-test", json={"event_type": "Credit Event", "impact_score": 9.0})
        data = r.json()
        assert data["portfolio_value_after"] < data["portfolio_value_before"]

    def test_loss_attribution_present(self, client_empty):
        r = client_empty.post("/stress-test", json={"event_type": "Geopolitical", "impact_score": 8.0})
        data = r.json()
        assert "loss_by_asset_class" in data
        assert "loss_by_sector" in data
        assert "shock_details" in data
        assert len(data["shock_details"]) > 0

    def test_override_shocks(self, client_empty):
        """Custom shock overrides must be reflected in the result."""
        r = client_empty.post("/stress-test", json={
            "event_type": "Geopolitical", "impact_score": 8.0,
            "override_shocks": {"equity_shock": -0.30}
        })
        assert r.status_code == 200
        data = r.json()
        assert data["shocks_applied"]["equity_shock"] == pytest.approx(-0.30, abs=1e-6)

    def test_auto_stress_200(self, client_with_signals):
        r = client_with_signals.post("/stress-test/auto?threshold=7.0")
        assert r.status_code == 200
        data = r.json()
        assert data["triggered_automatically"] is True
        assert data["total_loss"] < 0

    def test_auto_stress_no_signals_falls_back(self, client_empty):
        r = client_empty.post("/stress-test/auto?threshold=7.0")
        assert r.status_code == 200
        data = r.json()
        assert data["triggered_automatically"] is False
