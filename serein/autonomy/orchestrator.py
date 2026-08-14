"""One governed autonomous offline research cycle."""
from __future__ import annotations

import json

from .agents import ResearchAgent, RedTeamAgent, ReviewAgent
from .store import AutonomyStore
from .types import ExperimentOutcome, ExperimentStatus


class AutonomousResearchLoop:
    def __init__(self, store: AutonomyStore, *, max_experiments_per_dataset: int = 100):
        self.store = store; self.max_experiments = max_experiments_per_dataset
        self.research = ResearchAgent(); self.red_team = RedTeamAgent(); self.review = ReviewAgent()

    def propose_next(self, diagnostic: dict, *, dataset_id: str):
        budget = self.store.budget(dataset_id)
        if budget["experiments"] >= self.max_experiments:
            self.store.record_decision("RESEARCH_BUDGET_EXHAUSTED", {
                "dataset_id": dataset_id, "budget": budget,
                "action": "require fresh dataset or independent authorization"})
            return []
        accepted = []
        for proposal in self.research.propose(diagnostic, dataset_id=dataset_id):
            try:
                self.store.enqueue(proposal); accepted.append(proposal)
            except Exception as e:
                # Duplicate IDs are expected when the same unresolved weakness
                # is diagnosed again; record instead of silently multiplying tests.
                self.store.record_decision("PROPOSAL_NOT_ENQUEUED", {
                    "experiment_id": proposal.experiment_id, "reason": str(e)})
        return accepted

    def run_one(self, runner, *, evidence_class: str, holdout_pristine: bool):
        row = self.store.next()
        if row is None: return None
        experiment_id = row["id"]
        proposal = json.loads(row["proposal_json"])
        self.store.transition(experiment_id, ExperimentStatus.RUNNING)
        attacks = self.red_team.attacks(proposal)
        try:
            metrics, robustness, failure_cases, attack_results = runner(proposal, attacks)
            decision = self.review.review(outcome=metrics, red_team_results=attack_results,
                                          evidence_class=evidence_class,
                                          holdout_pristine=holdout_pristine)
            final = "REJECTED" if decision.decision == "NOT_APPROVED" else "RESEARCH_MORE"
            outcome = ExperimentOutcome(
                experiment_id, ExperimentStatus.COMPLETED, metrics, robustness,
                tuple(failure_cases), final, metrics.get("confidence", "LOW"),
                tuple(decision.missing_evidence+decision.contradictions))
            self.store.record_outcome(outcome)
            self.store.record_decision("REVIEW", {"experiment_id": experiment_id,
                                                   "review": decision.__dict__})
            return outcome, decision
        except Exception as exc:
            outcome = ExperimentOutcome(experiment_id, ExperimentStatus.FAILED, {}, {},
                                        (type(exc).__name__,), "FAILED", "NONE", (str(exc),))
            self.store.record_outcome(outcome)
            self.store.record_failure(failure_id=f"EXP-{experiment_id}", component="experiment_runner",
                                      description=str(exc), impact="experiment failed",
                                      detection="exception boundary", fix="OPEN",
                                      regression_test="MISSING")
            return outcome, None
