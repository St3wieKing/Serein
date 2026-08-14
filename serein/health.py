"""Governed strategy-health state machine."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HealthEvidence:
    n_recent_trades: int
    rolling_expectancy_r: float
    baseline_expectancy_r: float
    expectancy_z: float
    drawdown: float
    slippage_ratio: float
    data_drift_alerts: int
    calibration_error: float | None
    critical_system_failure: bool = False


@dataclass(frozen=True)
class HealthDecision:
    state: str
    reasons: tuple[str, ...]
    action: str


class HealthSupervisor:
    """Maintains strategy health; quarantine transitions are automatic."""
    def __init__(self):
        self.states: dict[str, str] = {}
        self.history: list[dict] = []

    def update(self, strategy_id: str, evidence: HealthEvidence) -> HealthDecision:
        previous = self.states.get(strategy_id, "ACTIVE")
        decision = assess_health(evidence, previous)
        self.states[strategy_id] = decision.state
        self.history.append({"strategy_id": strategy_id, "from": previous,
                             "to": decision.state, "reasons": decision.reasons,
                             "action": decision.action})
        return decision

    def can_trade(self, strategy_id: str) -> bool:
        return self.states.get(strategy_id, "ACTIVE") == "ACTIVE"


def assess_health(e: HealthEvidence, previous: str = "ACTIVE") -> HealthDecision:
    if e.critical_system_failure:
        return HealthDecision("QUARANTINED", ("critical_system_failure",), "STOP_NEW_TRADES")
    if e.n_recent_trades < 50:
        return HealthDecision(previous, ("insufficient_sample",), "MONITOR_NO_ADAPTATION")
    reasons = []
    if e.expectancy_z <= -3 and e.rolling_expectancy_r < 0: reasons.append("expectancy_degradation")
    if e.drawdown <= -.06: reasons.append("drawdown_limit")
    if e.slippage_ratio >= 2: reasons.append("execution_drift")
    if e.data_drift_alerts >= 3: reasons.append("feature_drift")
    if e.calibration_error is not None and e.calibration_error > .12: reasons.append("calibration_drift")
    if any(r in reasons for r in ("drawdown_limit", "execution_drift")) or len(reasons) >= 2:
        return HealthDecision("QUARANTINED", tuple(reasons), "STOP_AND_REVALIDATE")
    if reasons:
        return HealthDecision("DEGRADED", tuple(reasons), "REDUCE_RISK_AND_INVESTIGATE")
    return HealthDecision("ACTIVE", (), "CONTINUE_APPROVED_LIMITS")
