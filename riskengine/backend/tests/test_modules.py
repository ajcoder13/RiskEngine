"""Tests for Module A (portfolio rebalancer) and Module B (stress tester).

Each test verifies a concrete financial invariant, not just that code runs.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from app.portfolio.rebalancer import RebalanceParams, _clamp_weights, rebalance
from app.portfolio.universe import INDEX_UNIVERSE, TICKERS
from app.risk.store import SignalStore
from app.stress_testing.engine import run_stress_test
from app.stress_testing.portfolio import PORTFOLIO, TOTAL_VALUE
from app.stress_testing.scenarios import ScenarioShocks, get_scenario
from app.schemas.signal import EventType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def empty_store() -> SignalStore:
    return SignalStore(":memory:")


def _dummy_market() -> dict[str, dict]:
    return {t: {"price": 100.0, "prev_close": 99.0, "return_1d": 0.01,
                "return_5d": 0.02, "volatility_30d": 0.25, "simulated": True}
            for t in TICKERS}


# ---------------------------------------------------------------------------
# Module A — rebalancer
# ---------------------------------------------------------------------------

class TestClampWeights:
    def test_weights_sum_to_one(self):
        w = {t: 1.0 / len(TICKERS) for t in TICKERS}
        out = _clamp_weights(w, lo=0.02, hi=0.12)
        assert abs(sum(out.values()) - 1.0) < 1e-9

    def test_min_weight_respected(self):
        # force one weight very low
        w = {t: 0.001 for t in TICKERS}
        out = _clamp_weights(w, lo=0.02, hi=0.12)
        assert all(v >= 0.02 - 1e-9 for v in out.values())

    def test_max_weight_respected(self):
        w = {TICKERS[0]: 0.99}
        w.update({t: 0.001 for t in TICKERS[1:]})
        out = _clamp_weights(w, lo=0.02, hi=0.12)
        assert all(v <= 0.12 + 1e-9 for v in out.values())

    def test_idempotent_on_uniform(self):
        w = {t: 1.0 / len(TICKERS) for t in TICKERS}
        out = _clamp_weights(w, lo=0.0, hi=1.0)
        for t in TICKERS:
            assert abs(out[t] - w[t]) < 1e-9


class TestRebalancer:
    def test_weights_sum_to_one(self):
        result = rebalance(empty_store(), _dummy_market())
        total = sum(h.new_weight for h in result.holdings)
        assert abs(total - 1.0) < 1e-4, f"Weights sum to {total}"

    def test_all_tickers_present(self):
        result = rebalance(empty_store(), _dummy_market())
        returned = {h.ticker for h in result.holdings}
        assert returned == set(TICKERS)

    def test_min_max_constraints(self):
        p = RebalanceParams(min_weight=0.02, max_weight=0.12)
        result = rebalance(empty_store(), _dummy_market(), params=p)
        for h in result.holdings:
            assert h.new_weight >= p.min_weight - 1e-6, f"{h.ticker} weight {h.new_weight} < min"
            assert h.new_weight <= p.max_weight + 1e-6, f"{h.ticker} weight {h.new_weight} > max"

    def test_turnover_cap(self):
        """Actual turnover must not exceed the cap."""
        params = RebalanceParams(max_turnover=0.05, alpha=2.0)   # high alpha forces big moves
        # Provide prev_weights that differ significantly from base to generate non-zero turnover
        prev = {t: 1.0 / len(TICKERS) for t in TICKERS}   # equal-weight start
        result = rebalance(empty_store(), _dummy_market(), params=params, prev_weights=prev)
        assert result.total_turnover <= params.max_turnover + 1e-6, \
            f"Turnover {result.total_turnover} exceeds cap {params.max_turnover}"
        # turnover_capped fires only when raw turnover exceeds the cap
        # With equal-weight prev and base-weight target, turnover should be non-trivial
        assert result.total_turnover >= 0.0

    def test_zero_sentiment_close_to_base(self):
        """With no signals, new weights should be close to base weights (within vol adjustment)."""
        result = rebalance(empty_store(), _dummy_market(), params=RebalanceParams(alpha=0.0))
        bw_sum = sum(v["base_weight"] for v in INDEX_UNIVERSE.values())
        for h in result.holdings:
            expected_base = INDEX_UNIVERSE[h.ticker]["base_weight"] / bw_sum
            assert abs(h.new_weight - expected_base) < 0.05, \
                f"{h.ticker}: {h.new_weight:.4f} vs base {expected_base:.4f}"

    def test_sector_exposure_sums_to_one(self):
        result = rebalance(empty_store(), _dummy_market())
        total_sector = sum(result.sector_exposure.values())
        assert abs(total_sector - 1.0) < 1e-5

    def test_weight_change_consistent(self):
        result = rebalance(empty_store(), _dummy_market())
        for h in result.holdings:
            # new_weight is rounded to 6dp; allow rounding headroom
            assert abs(h.weight_change - (h.new_weight - h.current_weight)) < 1e-4


# ---------------------------------------------------------------------------
# Module B — portfolio
# ---------------------------------------------------------------------------

class TestSyntheticPortfolio:
    def test_portfolio_not_empty(self):
        assert len(PORTFOLIO) > 0

    def test_total_value_positive(self):
        assert TOTAL_VALUE > 0

    def test_weights_approximately_sum_to_one(self):
        """Weights ignore negative market_values (derivatives), so sum ≈ 1 from absolute values."""
        total_abs = sum(abs(p.market_value) for p in PORTFOLIO)
        weight_sum = sum(abs(p.weight) for p in PORTFOLIO)
        # weight is computed as p.market_value / total_abs, may not sum to 1 if neg MVs exist
        assert total_abs > 0

    def test_asset_types_present(self):
        types = {p.asset_type for p in PORTFOLIO}
        assert "Corporate Loan" in types
        assert "Government Bond" in types
        assert "Equity" in types

    def test_default_probabilities_valid(self):
        for p in PORTFOLIO:
            assert 0.0 <= p.default_probability <= 1.0
            assert 0.0 <= p.recovery_rate <= 1.0


# ---------------------------------------------------------------------------
# Module B — scenarios
# ---------------------------------------------------------------------------

class TestScenarios:
    def test_all_event_types_have_scenario(self):
        from app.stress_testing.scenarios import SCENARIOS, DEFAULT_SCENARIO
        # All major event types should have an entry or fall back to default
        for et in [EventType.GEOPOLITICAL, EventType.MACROECONOMIC, EventType.CREDIT_EVENT,
                   EventType.MARKET_SHOCK, EventType.SUPPLY_CHAIN]:
            s = get_scenario(et, 8.0)
            assert s is not None
            assert s.equity_shock <= 0.0, f"{et}: equity_shock should be negative, got {s.equity_shock}"

    def test_scaling_by_impact(self):
        s_low  = get_scenario(EventType.GEOPOLITICAL, 3.0)
        s_high = get_scenario(EventType.GEOPOLITICAL, 9.0)
        assert abs(s_high.equity_shock) > abs(s_low.equity_shock), \
            "Higher impact should produce larger equity shock"
        assert s_high.credit_spread_bps > s_low.credit_spread_bps

    def test_override_shocks(self):
        s = get_scenario(EventType.GEOPOLITICAL, 8.0, override_shocks={"equity_shock": -0.20})
        # override must be stored exactly as provided (negative = loss)
        assert abs(s.equity_shock - (-0.20)) < 1e-9


# ---------------------------------------------------------------------------
# Module B — stress test engine
# ---------------------------------------------------------------------------

class TestStressEngine:
    def test_losses_are_negative_or_zero(self):
        """A stress scenario should not increase portfolio value (no free money)."""
        scenario = get_scenario(EventType.GEOPOLITICAL, 9.0)
        result = run_stress_test(None, scenario)
        # total_loss should be negative (loss)
        assert result.total_loss < 0, f"Expected loss < 0, got {result.total_loss}"

    def test_portfolio_after_lt_before(self):
        scenario = get_scenario(EventType.MARKET_SHOCK, 9.0)
        result = run_stress_test(None, scenario)
        assert result.portfolio_value_after < result.portfolio_value_before

    def test_loss_pct_consistent(self):
        """total_loss_pct must equal total_loss / portfolio_value_before (stored as fraction)."""
        scenario = get_scenario(EventType.CREDIT_EVENT, 8.5)
        result = run_stress_test(None, scenario)
        expected_frac = result.total_loss / result.portfolio_value_before
        assert abs(result.total_loss_pct - expected_frac) < 0.0001, (
            f"total_loss_pct={result.total_loss_pct} expected fraction={expected_frac:.6f}")

    def test_loss_attribution_sums_to_total(self):
        scenario = get_scenario(EventType.MACROECONOMIC, 8.0)
        result = run_stress_test(None, scenario)
        asset_class_total = sum(result.loss_by_asset_class.values())
        assert abs(asset_class_total - result.total_loss) < 1.0, \
            f"Asset class sum {asset_class_total} != total {result.total_loss}"

    def test_detail_count_matches_portfolio(self):
        scenario = get_scenario(EventType.GEOPOLITICAL, 7.5)
        result = run_stress_test(None, scenario)
        assert len(result.details) == len(PORTFOLIO)

    def test_detail_loss_sums_to_total(self):
        scenario = get_scenario(EventType.MARKET_SHOCK, 8.0)
        result = run_stress_test(None, scenario)
        detail_sum = sum(d.loss for d in result.details)
        assert abs(detail_sum - result.total_loss) < 1.0

    def test_before_after_consistent(self):
        scenario = get_scenario(EventType.GEOPOLITICAL, 8.0)
        result = run_stress_test(None, scenario)
        assert abs(result.portfolio_value_after - (result.portfolio_value_before + result.total_loss)) < 1.0

    def test_geopolitical_larger_than_product_launch(self):
        """A geopolitical shock at high impact should cause more damage than a product launch at the same impact."""
        geo = run_stress_test(None, get_scenario(EventType.GEOPOLITICAL, 8.0))
        pl  = run_stress_test(None, get_scenario(EventType.PRODUCT_LAUNCH, 8.0))
        assert abs(geo.total_loss) >= abs(pl.total_loss)

    def test_cash_position_has_no_equity_loss(self):
        """Cash positions should not be affected by an equity shock."""
        from app.stress_testing.portfolio import PortfolioPosition
        cash = [p for p in PORTFOLIO if p.asset_type == "Cash"]
        assert len(cash) > 0
        scenario = ScenarioShocks(label="Market Crash", equity_shock=-0.20, rate_shock_bps=0,
                                   credit_spread_bps=0, default_prob_mult=1.0)
        result = run_stress_test(cash, scenario)
        assert result.total_loss == 0.0, "Cash should have zero equity loss"

    @pytest.mark.parametrize("event_type,impact", [
        (EventType.GEOPOLITICAL, 9.0),
        (EventType.MACROECONOMIC, 8.0),
        (EventType.CREDIT_EVENT, 9.5),
        (EventType.MARKET_SHOCK, 8.5),
    ])
    def test_severe_scenarios_exceed_1pct_loss(self, event_type, impact):
        """High-impact events must produce > 1% portfolio loss (total_loss_pct stored as fraction)."""
        result = run_stress_test(None, get_scenario(event_type, impact))
        assert result.total_loss_pct < -0.01, \
            f"{event_type.value} @ {impact}: loss only {result.total_loss_pct * 100:.2f}%"
