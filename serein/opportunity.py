"""Post-cost expected-value opportunity ranking with hard disqualifiers."""
from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class Opportunity:
    symbol: str
    strategy_id: str
    setup: str
    direction: int
    probability_win: float
    average_win_r: float
    average_loss_r: float
    costs_r: float
    slippage_r: float
    regime_fit: float
    liquidity_score: float
    execution_score: float
    confidence: float
    data_fresh: bool = True
    risk_allowed: bool = True
    strategy_approved: bool = False

    @property
    def expected_r(self):
        return (self.probability_win*self.average_win_r
                -(1-self.probability_win)*self.average_loss_r
                -self.costs_r-self.slippage_r)

    @property
    def quality(self):
        if not self.eligible: return 0.0
        ev_score = max(0, min(1, self.expected_r/1.0))
        return 100*(.35*ev_score+.20*self.regime_fit+.15*self.liquidity_score
                    +.15*self.execution_score+.15*self.confidence)

    @property
    def eligible(self):
        return (self.direction in (-1, 1) and self.data_fresh and self.risk_allowed
                and self.strategy_approved and self.expected_r > 0
                and self.regime_fit >= .5 and self.liquidity_score >= .5)


class OpportunityRanker:
    def __init__(self, max_opportunities: int = 3, min_quality: float = 60):
        self.max_opportunities = max_opportunities; self.min_quality = min_quality

    def rank(self, opportunities: list[Opportunity]) -> list[Opportunity]:
        valid = [o for o in opportunities if o.eligible and o.quality >= self.min_quality]
        return sorted(valid, key=lambda o: (o.quality, o.expected_r), reverse=True)[:self.max_opportunities]
