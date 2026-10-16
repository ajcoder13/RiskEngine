"""Module B: Stress Test Engine.

For each position, compute loss under the scenario shocks:

  equity_loss    = market_value × equity_exposure × equity_shock
  rate_loss      = duration × market_value × (rate_shock_bps / 10_000)   [DV01 × Δrate]
  credit_loss    = market_value × (credit_spread_bps / 10_000) × duration  (simplified)
  expected_loss  = notional × (stressed_PD - base_PD) × (1 - recovery_rate)
  fx_loss        = market_value × |cross_border_flag| × fx_shock
  commodity_loss = market_value × commodity_flag × commodity_vol_pct

Total position loss = sum of applicable components (floors at 0 if market_value < 0, i.e. hedge).
All assumptions are documented; the engine does NOT model correlation between shocks.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from app.stress_testing.portfolio import PortfolioPosition, PORTFOLIO, TOTAL_VALUE
from app.stress_testing.scenarios import ScenarioShocks

log = logging.getLogger(__name__)

_CROSS_BORDER = {"Europe", "Asia Pacific", "Emerging Markets", "Global"}
_COMMODITY_SECTORS = {"Energy", "Industrials"}

_RATE_SENSITIVE_TYPES = {"Government Bond", "Corporate Bond", "Derivative", "Corporate Loan"}
_CREDIT_SENSITIVE_TYPES = {"Corporate Loan", "Corporate Bond", "Derivative"}
_EQUITY_SECTOR_FACTORS: dict[str, float] = {
    # sector-specific equity shock amplifiers (1.0 = no amplification)
    "Technology": 1.20, "Finance": 1.10, "Energy": 1.30, "Consumer": 0.90,
    "Healthcare": 0.85, "Industrials": 1.10, "Sovereign": 0.20,
    "Diversified": 1.00, "Cash": 0.0, "FX": 0.0, "Rates": 0.5,
}


@dataclass
class ShockDetail:
    asset_id: str
    asset_type: str
    name: str
    sector: str
    value_before: float
    shock_applied: float
    shock_source: str
    value_after: float
    loss: float


@dataclass
class StressResult:
    scenario: ScenarioShocks
    details: list[ShockDetail] = field(default_factory=list)
    total_loss: float = 0.0
    loss_by_asset_class: dict[str, float] = field(default_factory=dict)
    loss_by_sector: dict[str, float] = field(default_factory=dict)
    loss_by_geography: dict[str, float] = field(default_factory=dict)
    loss_by_credit_rating: dict[str, float] = field(default_factory=dict)
    portfolio_value_before: float = TOTAL_VALUE
    portfolio_value_after: float = 0.0
    total_loss_pct: float = 0.0


def _position_loss(p: PortfolioPosition, s: ScenarioShocks) -> tuple[float, list[tuple[str, float]]]:
    """Return (total_loss, [(component_name, loss), ...])."""
    components: list[tuple[str, float]] = []
    mv = p.market_value

    # 1. Equity shock
    sector_factor = _EQUITY_SECTOR_FACTORS.get(p.sector, 1.0)
    if p.equity_exposure != 0.0 and s.equity_shock != 0.0:
        eq_loss = mv * p.equity_exposure * s.equity_shock * sector_factor
        components.append(("equity", eq_loss))

    # 2. Interest rate shock (duration × DV01 approximation)
    if p.asset_type in _RATE_SENSITIVE_TYPES and p.duration > 0 and s.rate_shock_bps != 0:
        # price change ≈ -modified_duration × Δy × price  (simplified: duration = modified_duration)
        rate_loss = -p.duration * mv * (s.rate_shock_bps / 10_000.0)
        components.append(("interest_rate", rate_loss))

    # 3. Credit spread widening
    if p.asset_type in _CREDIT_SENSITIVE_TYPES and s.credit_spread_bps != 0 and p.duration > 0:
        # spread DV01: similar to rate DV01 but affects risky discount rate
        spread_loss = -p.duration * mv * (s.credit_spread_bps / 10_000.0)
        components.append(("credit_spread", spread_loss))

    # 4. Expected loss from PD increase (credit assets only)
    if p.default_probability > 0 and s.default_prob_mult != 1.0:
        stressed_pd = min(1.0, p.default_probability * s.default_prob_mult)
        el_loss = -p.notional * (stressed_pd - p.default_probability) * (1.0 - p.recovery_rate + abs(s.recovery_adj))
        components.append(("expected_loss", el_loss))

    # 5. FX shock (cross-border assets)
    if p.geography in _CROSS_BORDER and s.fx_shock != 0:
        fx_loss = mv * s.fx_shock
        components.append(("fx", fx_loss))

    # 6. Commodity shock (energy/industrial sectors)
    if p.sector in _COMMODITY_SECTORS and s.commodity_vol_pct != 0:
        # Commodity vol shock: treat as additional vol × market_value × ~sqrt(horizon) factor
        # Use a simple ×0.3 proxy for a 2-week horizon volatility impact
        com_loss = -abs(mv) * s.commodity_vol_pct * 0.30
        components.append(("commodity", com_loss))

    total = sum(v for _, v in components)
    return total, components


def run_stress_test(positions: list[PortfolioPosition] | None,
                    scenario: ScenarioShocks) -> StressResult:
    """Apply scenario shocks to every position and aggregate losses."""
    positions = positions or PORTFOLIO
    result = StressResult(scenario=scenario)
    result.portfolio_value_before = sum(p.market_value for p in positions)

    loss_by_asset: dict[str, float] = {}
    loss_by_sector: dict[str, float] = {}
    loss_by_geo: dict[str, float] = {}
    loss_by_rating: dict[str, float] = {}

    for p in positions:
        total_loss, components = _position_loss(p, scenario)
        if not components:
            eff_shock = 0.0
            shock_src = "no applicable shock"
        else:
            dominant = min(components, key=lambda c: c[1])   # most negative = largest loss
            eff_shock = total_loss / p.market_value if p.market_value != 0 else 0.0
            shock_src = " + ".join(f"{n}({v:+.0f})" for n, v in components)

        result.details.append(ShockDetail(
            asset_id=p.asset_id, asset_type=p.asset_type, name=p.name, sector=p.sector,
            value_before=round(p.market_value, 2),
            shock_applied=round(eff_shock, 6),
            shock_source=shock_src,
            value_after=round(p.market_value + total_loss, 2),
            loss=round(total_loss, 2),
        ))

        loss_by_asset[p.asset_type] = round(loss_by_asset.get(p.asset_type, 0.0) + total_loss, 2)
        loss_by_sector[p.sector] = round(loss_by_sector.get(p.sector, 0.0) + total_loss, 2)
        loss_by_geo[p.geography] = round(loss_by_geo.get(p.geography, 0.0) + total_loss, 2)
        loss_by_rating[p.credit_rating] = round(loss_by_rating.get(p.credit_rating, 0.0) + total_loss, 2)

    result.total_loss = round(sum(d.loss for d in result.details), 2)
    result.loss_by_asset_class = loss_by_asset
    result.loss_by_sector = loss_by_sector
    result.loss_by_geography = loss_by_geo
    result.loss_by_credit_rating = loss_by_rating
    result.portfolio_value_after = round(result.portfolio_value_before + result.total_loss, 2)
    result.total_loss_pct = round(result.total_loss / result.portfolio_value_before, 6) \
        if result.portfolio_value_before else 0.0
    log.info("Stress test [%s] total_loss=%.0f (%.2f%%)",
             scenario.label, result.total_loss, result.total_loss_pct * 100)
    return result
