from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum


class EvidenceLabel(str, Enum):
    FACT = "FACT"
    CLAIM = "CLAIM"
    HYPOTHESIS = "HYPOTHESIS"
    INFERENCE = "INFERENCE"
    UNKNOWN = "UNKNOWN"


class ExperimentStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    DEFERRED = "DEFERRED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class ExperimentProposal:
    experiment_id: str
    hypothesis: str
    reason: str
    source: str
    evidence_label: EvidenceLabel
    dataset_id: str
    components: tuple[str, ...]
    expected_information: float
    compute_cost: float
    contamination_risk: float
    complexity: int
    parameters: dict = field(default_factory=dict)

    def priority(self) -> float:
        denominator = max(.1, self.compute_cost) * (1 + self.contamination_risk) * (1 + .15*self.complexity)
        return self.expected_information/denominator

    def to_dict(self):
        d = asdict(self); d["evidence_label"] = self.evidence_label.value
        return d


@dataclass(frozen=True)
class ExperimentOutcome:
    experiment_id: str
    status: ExperimentStatus
    metrics: dict
    robustness: dict
    failure_cases: tuple[str, ...]
    decision: str
    confidence: str
    remaining_uncertainty: tuple[str, ...]

    def to_dict(self):
        d = asdict(self); d["status"] = self.status.value
        return d


@dataclass(frozen=True)
class Attack:
    name: str
    category: str
    severity: str
    test: str
    pass_condition: str


@dataclass(frozen=True)
class ReviewDecision:
    decision: str
    missing_evidence: tuple[str, ...]
    contradictions: tuple[str, ...]
    next_actions: tuple[str, ...]
