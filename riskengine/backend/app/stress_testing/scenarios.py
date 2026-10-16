"""Event → Shock mapping for Module B stress tests.

All shocks are ILLUSTRATIVE SCENARIO ASSUMPTIONS, not forecasts.
Each entry documents its rationale.  All values are configurable at runtime.

Shock types:
  equity_shock          fractional price change applied to equity_exposure > 0
  rate_shock_bps        parallel shift in interest rates (basis points)
  credit_spread_bps     spread widening on credit-sensitive assets
  default_prob_mult     multiplier applied to default_probability
  recovery_adj          additive adjustment to recovery_rate
  fx_shock              fractional FX shock (affects EM / non-domestic assets)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from app.schemas.signal import EventType

ScenarioLabel = Literal[
    "Geopolitical Shock",
    "Macroeconomic Shock",
    "Credit Crisis",
    "Market Crash",
    "Supply Chain Disruption",
    "Regulatory Crackdown",
    "Cybersecurity Attack",
    "Commodity Shock",
    "M&A Distress",
    "Generic High Impact",
]


@dataclass(frozen=True)
class ScenarioShocks:
    label: ScenarioLabel
    equity_shock: float = 0.0           # e.g. -0.10 = equity positions lose 10%
    rate_shock_bps: float = 0.0         # positive = rates rise → bond prices fall
    credit_spread_bps: float = 0.0      # spread widening hurts credit assets
    default_prob_mult: float = 1.0      # 2.0 = PD doubles
    recovery_adj: float = 0.0           # negative = lower recovery
    fx_shock: float = 0.0               # affects EM / cross-border positions
    commodity_vol_pct: float = 0.0      # extra volatility for energy/commodity sectors
    rationale: str = ""

    def as_dict(self) -> dict[str, float]:
        return {
            "equity_shock": self.equity_shock,
            "rate_shock_bps": self.rate_shock_bps,
            "credit_spread_bps": self.credit_spread_bps,
            "default_prob_mult": self.default_prob_mult,
            "recovery_adj": self.recovery_adj,
            "fx_shock": self.fx_shock,
            "commodity_vol_pct": self.commodity_vol_pct,
        }


# Scenario library — calibrated to historical stress analogues (GFC, COVID, Russia-Ukraine)
SCENARIOS: dict[EventType, ScenarioShocks] = {
    EventType.GEOPOLITICAL: ScenarioShocks(
        label="Geopolitical Shock",
        equity_shock=-0.10,          # ref: Russian invasion 2022: S&P -10% in 2 weeks
        rate_shock_bps=50.0,         # flight-to-quality initially, then repricing
        credit_spread_bps=150.0,     # HY spreads widened ~200 bps
        default_prob_mult=1.5,
        recovery_adj=-0.05,
        fx_shock=-0.08,
        commodity_vol_pct=0.15,
        rationale="Geopolitical events (e.g., armed conflict, sanctions): equity sell-off, "
                  "commodity spike, credit spread widening. Analogues: Russia-Ukraine 2022, "
                  "Gulf War 1990.",
    ),
    EventType.MACROECONOMIC: ScenarioShocks(
        label="Macroeconomic Shock",
        equity_shock=-0.07,
        rate_shock_bps=200.0,        # aggressive central bank hiking cycle
        credit_spread_bps=100.0,
        default_prob_mult=1.30,
        recovery_adj=-0.03,
        fx_shock=-0.05,
        rationale="Macro shock (e.g., inflation surge, recession signal): rate hike cycle "
                  "compresses bond prices via duration, risk premia widen. Analogue: 2022 Fed tightening.",
    ),
    EventType.CREDIT_EVENT: ScenarioShocks(
        label="Credit Crisis",
        equity_shock=-0.12,
        rate_shock_bps=-50.0,        # flight-to-quality: rates fall
        credit_spread_bps=400.0,     # GFC analogue: IG +200, HY +600 bps
        default_prob_mult=3.0,
        recovery_adj=-0.15,
        rationale="Credit event (e.g., sovereign default, bank failure): PD surge, "
                  "spreads explode. Analogue: GFC 2008, Evergrande 2021.",
    ),
    EventType.MARKET_SHOCK: ScenarioShocks(
        label="Market Crash",
        equity_shock=-0.15,          # ref: COVID March 2020: S&P -34% peak-trough; 2-week slice ~-15%
        rate_shock_bps=-75.0,
        credit_spread_bps=250.0,
        default_prob_mult=2.0,
        recovery_adj=-0.10,
        rationale="Sudden broad market shock: rapid de-risking across all asset classes. "
                  "Analogue: COVID March 2020, Black Monday 1987.",
    ),
    EventType.SUPPLY_CHAIN: ScenarioShocks(
        label="Supply Chain Disruption",
        equity_shock=-0.06,          # sector-specific: Consumer/Industrials/Tech harder hit
        rate_shock_bps=30.0,
        credit_spread_bps=80.0,
        commodity_vol_pct=0.12,
        rationale="Supply chain disruption: sector-specific margin compression, commodity repricing. "
                  "Analogue: COVID chip shortage 2021, Suez Canal 2021.",
    ),
    EventType.REGULATORY: ScenarioShocks(
        label="Regulatory Crackdown",
        equity_shock=-0.08,          # targeted at affected sectors
        rate_shock_bps=0.0,
        credit_spread_bps=60.0,
        default_prob_mult=1.20,
        rationale="Regulatory action (e.g., antitrust, banking capital requirements): "
                  "valuation compression for affected companies/sectors. Analogue: China tech crackdown 2021.",
    ),
    EventType.CYBERSECURITY: ScenarioShocks(
        label="Cybersecurity Attack",
        equity_shock=-0.05,
        credit_spread_bps=50.0,
        default_prob_mult=1.15,
        rationale="Cyber attack on critical infrastructure or major counterparty: "
                  "operational risk premium, reputational damage.",
    ),
    EventType.COMMODITY_SHOCK: ScenarioShocks(
        label="Commodity Shock",
        equity_shock=-0.05,
        rate_shock_bps=75.0,         # inflationary commodity spike → rate response
        credit_spread_bps=70.0,
        commodity_vol_pct=0.20,
        fx_shock=-0.06,
        rationale="Commodity price shock (oil spike or crash): inflation pass-through, "
                  "EM currency pressure. Analogue: oil price crash 2020, OPEC+ 2022.",
    ),
    EventType.MNA: ScenarioShocks(
        label="M&A Distress",
        equity_shock=-0.04,
        credit_spread_bps=50.0,
        default_prob_mult=1.10,
        rationale="Failed or distressed M&A: target/acquirer leverage, counterparty risk. "
                  "Analogue: Shire/AbbVie inversion collapse 2014.",
    ),
}

# Fallback for unclassified / Other events
DEFAULT_SCENARIO = ScenarioShocks(
    label="Generic High Impact",
    equity_shock=-0.05,
    credit_spread_bps=75.0,
    default_prob_mult=1.20,
    rationale="Unclassified high-impact event: conservative generic shock applied.",
)


def get_scenario(event_type: EventType, impact_score: float,
                 override_shocks: dict[str, float] | None = None) -> ScenarioShocks:
    """Select and optionally scale scenario shocks by impact_score (1-10)."""
    base = SCENARIOS.get(event_type, DEFAULT_SCENARIO)
    # Scale shocks linearly by impact_score relative to the trigger threshold (7.0)
    # Impact 7 → scale 1.0; Impact 10 → scale ~1.43; Impact 1 → scale ~0.14
    scale = max(0.1, impact_score / 7.0)

    fields = {
        "label": base.label,
        "equity_shock": base.equity_shock * scale,
        "rate_shock_bps": base.rate_shock_bps * scale,
        "credit_spread_bps": base.credit_spread_bps * scale,
        "default_prob_mult": 1.0 + (base.default_prob_mult - 1.0) * scale,
        "recovery_adj": base.recovery_adj * scale,
        "fx_shock": base.fx_shock * scale,
        "commodity_vol_pct": base.commodity_vol_pct * scale,
        "rationale": base.rationale + f" [Scaled by impact {impact_score:.1f}/10, factor {scale:.2f}]",
    }
    if override_shocks:
        for k, v in override_shocks.items():
            if k in fields and isinstance(v, (int, float)):
                fields[k] = float(v)
    return ScenarioShocks(**fields)
