"""Complete normalized journal schemas."""
from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class TradeJournalRecord:
    timestamp: str; instrument: str; strategy: str; setup: str; context: str
    regime: str; direction: int; entry: float; stop: float; target: float
    expected_r: float; confidence: float; expected_value_r: float
    position_size: int; risk_amount: float; execution: dict; exit: float | None
    pnl: float | None; mae: float | None; mfe: float | None
    decision_quality: str; outcome: str; data_fingerprint: str
    code_revision: str; config_hash: str

    def validate(self):
        if self.direction not in (-1, 0, 1): raise ValueError("direction")
        if not 0 <= self.confidence <= 1: raise ValueError("confidence")
        if self.position_size < 0 or self.risk_amount < 0: raise ValueError("risk/size")
        if self.direction and (self.entry-self.stop)*self.direction <= 0: raise ValueError("stop side")
        return True

    def to_dict(self): self.validate(); return asdict(self)


@dataclass(frozen=True)
class FailureJournalRecord:
    failure_id: str; date: str; component: str; description: str; impact: str
    root_cause: str; detection: str; fix: str; regression_test: str


@dataclass(frozen=True)
class ExperimentJournalRecord:
    experiment_id: str; hypothesis: str; reason: str; source: str; data: str
    code_version: str; parameters: dict; model: str; results: dict
    oos: dict; stress: dict; decision: str
