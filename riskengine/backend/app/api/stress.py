"""Module B API: /stress-test, /portfolio-composition"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_engine
from app.risk.engine import RiskEngine
from app.risk.triggers import trigger_signals
from app.schemas.modules import (PortfolioPositionSchema, StressShockDetail,
                                  StressTestRequest, StressTestResponse)
from app.schemas.signal import EventType
from app.stress_testing.engine import run_stress_test
from app.stress_testing.portfolio import PORTFOLIO, TOTAL_VALUE
from app.stress_testing.scenarios import get_scenario

log = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["module-b"])


def _pos_schema(p) -> PortfolioPositionSchema:
    return PortfolioPositionSchema(
        asset_id=p.asset_id, asset_type=p.asset_type, name=p.name,
        notional=p.notional, market_value=p.market_value,
        sector=p.sector, geography=p.geography, credit_rating=p.credit_rating,
        duration=p.duration, interest_rate_sensitivity=p.interest_rate_sensitivity,
        equity_exposure=p.equity_exposure, counterparty=p.counterparty,
        default_probability=p.default_probability, recovery_rate=p.recovery_rate,
        weight=p.weight,
    )


@router.get("/portfolio-composition", response_model=list[PortfolioPositionSchema],
            summary="Synthetic wholesale banking portfolio (Module B)")
def portfolio_composition() -> list[PortfolioPositionSchema]:
    """Returns the synthetic ~$89.92M portfolio (20 positions) used as stress-test base.
    All positions are SIMULATED for demonstration purposes."""
    return [_pos_schema(p) for p in PORTFOLIO]


@router.post("/stress-test", response_model=StressTestResponse,
             summary="Event-driven stress test on the synthetic portfolio (Module B)")
def stress_test(req: StressTestRequest, engine: RiskEngine = Depends(get_engine)) -> StressTestResponse:
    """Apply an event scenario to the portfolio.

    If event_type and impact_score are not provided, the highest-impact adverse signal
    from the store is used to auto-select the scenario.
    """
    try:
        event_type = EventType(req.event_type)
    except ValueError:
        event_type = EventType.OTHER

    scenario = get_scenario(event_type, req.impact_score, req.override_shocks)
    result = run_stress_test(None, scenario)

    return StressTestResponse(
        event_type=req.event_type,
        impact_score=req.impact_score,
        triggered_automatically=False,
        scenario_label=scenario.label,
        portfolio_value_before=round(result.portfolio_value_before, 2),
        portfolio_value_after=round(result.portfolio_value_after, 2),
        total_loss=round(result.total_loss, 2),
        total_loss_pct=round(result.total_loss_pct, 4),
        loss_by_asset_class=result.loss_by_asset_class,
        loss_by_sector=result.loss_by_sector,
        loss_by_geography=result.loss_by_geography,
        loss_by_credit_rating=result.loss_by_credit_rating,
        shock_details=[StressShockDetail(
            asset_id=d.asset_id, asset_type=d.asset_type, name=d.name, sector=d.sector,
            value_before=d.value_before, shock_applied=d.shock_applied, shock_source=d.shock_source,
            value_after=d.value_after, loss=d.loss,
        ) for d in result.details],
        positions=[_pos_schema(p) for p in PORTFOLIO],
        shocks_applied=scenario.as_dict(),
        data_mode="simulated",
    )


@router.post("/stress-test/auto", response_model=StressTestResponse,
             summary="Auto-trigger stress test from highest-impact signal (Module B)")
def stress_test_auto(
    threshold: float = Query(7.0, ge=1.0, le=10.0, description="Impact score threshold"),
    engine: RiskEngine = Depends(get_engine),
) -> StressTestResponse:
    """Reads the risk signal store, finds the highest-impact adverse signal above threshold,
    and triggers a stress test automatically."""
    triggers = trigger_signals(engine.store.query(limit=500, order="impact"), threshold)
    if triggers:
        top = triggers[0]
        event_type = top.event_type
        impact = top.impact_score
        auto = True
    else:
        event_type = EventType.MARKET_SHOCK
        impact = threshold
        auto = False

    scenario = get_scenario(event_type, impact)
    result = run_stress_test(None, scenario)

    return StressTestResponse(
        event_type=event_type.value,
        impact_score=impact,
        triggered_automatically=auto,
        scenario_label=scenario.label,
        portfolio_value_before=round(result.portfolio_value_before, 2),
        portfolio_value_after=round(result.portfolio_value_after, 2),
        total_loss=round(result.total_loss, 2),
        total_loss_pct=round(result.total_loss_pct, 4),
        loss_by_asset_class=result.loss_by_asset_class,
        loss_by_sector=result.loss_by_sector,
        loss_by_geography=result.loss_by_geography,
        loss_by_credit_rating=result.loss_by_credit_rating,
        shock_details=[StressShockDetail(
            asset_id=d.asset_id, asset_type=d.asset_type, name=d.name, sector=d.sector,
            value_before=d.value_before, shock_applied=d.shock_applied, shock_source=d.shock_source,
            value_after=d.value_after, loss=d.loss,
        ) for d in result.details],
        positions=[_pos_schema(p) for p in PORTFOLIO],
        shocks_applied=scenario.as_dict(),
        data_mode="simulated",
    )
