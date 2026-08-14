"""Strict promotion gate for intraday strategy evidence."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IntradayPromotionEvidence:
    strategy_id: str
    evidence_class: str  # SYNTHETIC, HISTORICAL_REAL, PAPER_FORWARD
    oos_trades: int
    oos_sharpe: float
    expectancy_r_ci_low: float
    max_drawdown: float
    cost_2x_return: float
    cost_5x_return: float
    slippage_2x_return: float
    latency_1bar_return: float
    independent_symbols: int
    independent_regimes: int
    holdout_pristine_at_reveal: bool
    overnight_breaches: int
    risk_breaches: int
    paper_weeks: int


@dataclass(frozen=True)
class GateResult:
    approved_for_paper_champion: bool
    failures: tuple[str, ...]


def evaluate_intraday_promotion(e: IntradayPromotionEvidence) -> GateResult:
    failures = []
    if e.evidence_class not in ("HISTORICAL_REAL", "PAPER_FORWARD"):
        failures.append("real_point_in_time_data_required")
    if e.oos_trades < 100: failures.append("minimum_100_oos_trades")
    if e.oos_sharpe <= .5: failures.append("oos_sharpe")
    if e.expectancy_r_ci_low <= 0: failures.append("expectancy_confidence_interval")
    if e.max_drawdown < -.06: failures.append("drawdown_limit")
    if e.cost_2x_return <= 0: failures.append("cost_2x")
    if e.cost_5x_return <= 0: failures.append("cost_5x")
    if e.slippage_2x_return <= 0: failures.append("slippage_2x")
    if e.latency_1bar_return <= 0: failures.append("latency_1bar")
    if e.independent_symbols < 3: failures.append("cross_symbol_replication")
    if e.independent_regimes < 4: failures.append("regime_replication")
    if not e.holdout_pristine_at_reveal: failures.append("contaminated_holdout")
    if e.overnight_breaches: failures.append("overnight_safety_breach")
    if e.risk_breaches: failures.append("risk_breach")
    if e.paper_weeks < 12: failures.append("paper_forward_12_weeks")
    return GateResult(not failures, tuple(failures))
