"""Fail-closed champion/challenger governance for strategy promotion."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PromotionPolicy:
    min_oos_trades: int = 25
    min_oos_sharpe: float = 0.50
    max_drawdown: float = 0.10
    require_positive_cost2x: bool = True
    require_positive_slip5x: bool = True
    require_real_point_in_time_data: bool = True
    require_pristine_holdout: bool = True
    min_paper_weeks: int = 12


@dataclass(frozen=True)
class CandidateEvidence:
    name: str
    version: str
    oos_trades: int
    oos_sharpe: float
    max_drawdown: float
    cost2x_sharpe: float
    slip5x_sharpe: float
    real_point_in_time_data: bool = False
    pristine_holdout: bool = False
    paper_weeks: int = 0
    risk_breaches: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class PromotionDecision:
    approved: bool
    stage: str
    failures: tuple[str, ...]


def evaluate_challenger(e: CandidateEvidence,
                        policy: PromotionPolicy = PromotionPolicy()) -> PromotionDecision:
    """Evaluate evidence only; never mutates or replaces the champion.

    Passing means eligible to be considered as a paper champion. It never means
    eligible for live deployment; Serein has no live stage or adapter.
    """
    failures = []
    if e.oos_trades < policy.min_oos_trades:
        failures.append("insufficient_oos_trades")
    if e.oos_sharpe <= policy.min_oos_sharpe:
        failures.append("oos_sharpe_gate")
    if e.max_drawdown < -policy.max_drawdown:
        failures.append("drawdown_gate")
    if policy.require_positive_cost2x and e.cost2x_sharpe <= 0:
        failures.append("cost2x_gate")
    if policy.require_positive_slip5x and e.slip5x_sharpe <= 0:
        failures.append("slip5x_gate")
    if policy.require_real_point_in_time_data and not e.real_point_in_time_data:
        failures.append("real_data_required")
    if policy.require_pristine_holdout and not e.pristine_holdout:
        failures.append("pristine_holdout_required")
    if e.paper_weeks < policy.min_paper_weeks:
        failures.append("paper_observation_required")
    if e.risk_breaches:
        failures.append("risk_breach")
    return PromotionDecision(not failures, "paper_champion_candidate" if not failures else "challenger",
                             tuple(failures))
