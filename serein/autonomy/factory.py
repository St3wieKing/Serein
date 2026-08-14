"""Constrained strategy factory; prevents combinatorial brute force."""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product

from ..strategies.institutional_intraday import InstitutionalIntradayStrategy
from ..strategies.rebuild import TrendPullbackStrategy, FailedBreakoutStrategy


@dataclass(frozen=True)
class CandidateSpec:
    context: str
    setup: str
    trigger: str
    risk: str
    exit: str
    filters: tuple[str, ...] = ()

    @property
    def complexity(self): return 5+len(self.filters)


class StrategyFactory:
    CONTEXTS = {"trend", "range", "opening_session"}
    SETUPS = {"trend_pullback", "failed_breakout", "opening_breakout", "vwap_reversion"}
    TRIGGERS = {"prior_bar_break", "range_break", "turn_inward"}
    RISKS = {"structural_atr"}
    EXITS = {"fixed_r", "vwap", "session_close"}
    FILTERS = {"relative_volume", "breadth", "volatility"}

    def __init__(self, max_candidates: int = 20, max_filters: int = 2):
        self.max_candidates = max_candidates; self.max_filters = max_filters
        self.generated = 0

    def validate(self, spec: CandidateSpec):
        if spec.context not in self.CONTEXTS or spec.setup not in self.SETUPS:
            raise ValueError("unsupported context/setup")
        if spec.trigger not in self.TRIGGERS or spec.risk not in self.RISKS or spec.exit not in self.EXITS:
            raise ValueError("unsupported trigger/risk/exit")
        if len(spec.filters) > self.max_filters or not set(spec.filters) <= self.FILTERS:
            raise ValueError("filter budget exceeded or unsupported")
        if spec.setup == "opening_breakout" and spec.context != "opening_session":
            raise ValueError("opening breakout requires opening_session context")
        if spec.setup == "vwap_reversion" and spec.context != "range":
            raise ValueError("VWAP reversion requires range context")

    def build(self, spec: CandidateSpec):
        self.validate(spec)
        if self.generated >= self.max_candidates: raise RuntimeError("strategy research budget exhausted")
        self.generated += 1
        if spec.setup == "trend_pullback":
            return TrendPullbackStrategy({"use_volume": "relative_volume" in spec.filters,
                                          "use_volatility": "volatility" in spec.filters})
        if spec.setup == "failed_breakout": return FailedBreakoutStrategy()
        # Institutional router contains OR and reversion; callers must filter its
        # reason field according to the declared spec during evaluation.
        return InstitutionalIntradayStrategy()
