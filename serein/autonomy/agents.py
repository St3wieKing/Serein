"""Deterministic, authority-limited research, red-team and review agents."""
from __future__ import annotations

import hashlib

from .types import EvidenceLabel, ExperimentProposal, Attack, ReviewDecision


def _id(text): return hashlib.sha256(text.encode()).hexdigest()[:12]


class ResearchAgent:
    """Proposes offline experiments from diagnosed weaknesses; never trades."""
    def propose(self, diagnostic: dict, *, dataset_id: str,
                max_proposals: int = 5) -> list[ExperimentProposal]:
        weak = diagnostic.get("weak_setup")
        issue = diagnostic.get("issue", "insufficient evidence")
        proposals = []
        templates = []
        if weak:
            templates += [
                (f"Removing {weak} improves net OOS robustness", ("ablation", weak), .90, 1.0, 0),
                (f"A stricter regime gate prevents {weak} failure without deleting core edge", ("regime_gate", weak), .70, 1.5, 1),
            ]
        if "cost" in issue or "slippage" in issue:
            templates += [("Reducing turnover preserves expectancy under doubled execution costs",
                           ("turnover_filter",), .85, 1.2, 1)]
        if "sample" in issue or diagnostic.get("n_trades", 0) < 100:
            templates += [("The candidate replicates on additional symbols without parameter changes",
                           ("cross_symbol_replication",), 1.0, 2.0, 0)]
        if diagnostic.get("drift"):
            templates += [("Quarantine outperforms continuous trading after detected drift",
                           ("quarantine_policy",), .95, 1.0, 0)]
        if not templates:
            templates = [("The current simple champion remains positive on a fresh sealed holdout",
                          ("fresh_holdout_replication",), 1.0, 2.0, 0)]
        for hypothesis, components, info, cost, complexity in templates[:max_proposals]:
            key = f"{dataset_id}|{hypothesis}|{components}"
            proposals.append(ExperimentProposal(
                _id(key), hypothesis, issue, "autonomous diagnostic",
                EvidenceLabel.HYPOTHESIS, dataset_id, tuple(components), info,
                cost, .7 if "holdout" not in components else .1, complexity, {}))
        return sorted(proposals, key=lambda x: x.priority(), reverse=True)


class RedTeamAgent:
    """Returns attacks. It cannot modify the candidate or risk controls."""
    def attacks(self, candidate: dict) -> tuple[Attack, ...]:
        return (
            Attack("future_leakage", "data", "critical", "truncate input at every sampled decision",
                   "signals and features at t are unchanged"),
            Attack("cost_expansion", "execution", "high", "apply 2x and 5x all-in costs",
                   "predeclared stress gate remains positive"),
            Attack("slippage_tail", "execution", "critical", "apply 5x slippage and gap fills",
                   "loss remains within hard risk and strategy gate"),
            Attack("missing_cluster", "data", "critical", "drop clustered bars around open and exits",
                   "NO_TRADE or conservative gap handling"),
            Attack("parameter_neighborhood", "overfit", "high", "perturb every free parameter ±20%",
                   "gradual degradation, no isolated optimum"),
            Attack("symbol_removal", "concentration", "high", "remove best symbol and best period",
                   "expectancy does not depend on one source"),
            Attack("outlier_removal", "statistics", "high", "remove top 1%, 5%, 10% trades",
                   "core expectancy and risk remain acceptable"),
            Attack("authority_escalation", "security", "critical", "request risk override from alpha agent",
                   "authorization denied structurally"),
            Attack("restart_corruption", "operations", "critical", "corrupt local safety state with open broker position",
                   "HALT_AND_RECONCILE"),
            Attack("drift", "model", "high", "shift feature and calibration distributions",
                   "DEGRADED then QUARANTINED; no silent continuation"),
        )

    def failed_attacks(self, results: dict) -> tuple[str, ...]:
        return tuple(name for name, passed in results.items() if not passed)


class ReviewAgent:
    """Reviews research and red-team outputs; cannot promote directly."""
    def review(self, *, outcome: dict, red_team_results: dict,
               evidence_class: str, holdout_pristine: bool) -> ReviewDecision:
        missing, contradictions, next_actions = [], [], []
        if evidence_class != "PAPER_FORWARD": missing.append("12+ weeks paper-forward evidence")
        if evidence_class == "SYNTHETIC": missing.append("real point-in-time data")
        if not holdout_pristine: contradictions.append("holdout was already inspected")
        failed = [k for k, v in red_team_results.items() if not v]
        if failed: contradictions.append("failed red-team attacks: "+", ".join(failed))
        if outcome.get("expectancy_ci_low", -1) <= 0:
            missing.append("positive lower expectancy confidence bound")
        if outcome.get("oos_trades", 0) < 100: missing.append("100 OOS trades")
        if missing or contradictions:
            next_actions += ["remain research-only", "queue highest-value missing-evidence experiment"]
            decision = "NOT_APPROVED"
        else:
            next_actions.append("submit to deterministic promotion gate")
            decision = "GATE_REVIEW_REQUIRED"
        return ReviewDecision(decision, tuple(missing), tuple(contradictions), tuple(next_actions))
