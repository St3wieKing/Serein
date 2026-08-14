"""Live-data-compatible shadow decision recorder; never submits orders."""
from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd

from ..audit_journal import HashChainJournal


@dataclass(frozen=True)
class ShadowDecision:
    timestamp: str
    instrument: str
    strategy: str
    setup: str
    context: str
    regime: str
    direction: int
    decision_price: float
    stop: float
    target: float
    expected_r: float
    expected_value_r: float
    confidence: float
    proposed_qty: int
    risk_amount: float
    decision: str
    reason: str


class ShadowRecorder:
    def __init__(self, journal: HashChainJournal):
        self.journal = journal

    def record(self, decision: ShadowDecision):
        if decision.decision not in ("WOULD_TRADE", "NO_TRADE"):
            raise ValueError("invalid shadow decision")
        # Deliberately no broker dependency and no order-submission method.
        return self.journal.append("SHADOW_DECISION", asdict(decision))

    def decisions(self):
        return [r for r in self.journal.read() if r.get("event_type") == "SHADOW_DECISION"]
