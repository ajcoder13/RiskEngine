from app.schemas.signal import Direction, RiskSignal


def should_trigger_stress(sig: RiskSignal, threshold: float) -> bool:
    """Module B trigger: only ADVERSE signals at or above the impact threshold. A strongly positive
    headline can score a high impact, but it is not a stress scenario."""
    return sig.direction == Direction.ADVERSE and sig.impact_score >= threshold


def trigger_signals(signals: list[RiskSignal], threshold: float) -> list[RiskSignal]:
    return sorted((s for s in signals if should_trigger_stress(s, threshold)), key=lambda s: -s.impact_score)
