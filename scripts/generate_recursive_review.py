#!/usr/bin/env python3
"""Generate the three reproducible 500-question recursive design reviews."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/"research"/"recursive_review"

CATEGORIES = {
"Objective and evidence": ["capital preservation objective", "return objective", "NO_TRADE behavior", "evidence classification", "synthetic-data boundary", "real-data requirement", "benchmark selection", "economic mechanism", "strategy capacity", "claim language"],
"Data and lineage": ["timestamp semantics", "timezone conversion", "session calendar", "duplicate bars", "missing bars", "corporate actions", "survivorship bias", "symbol mapping", "bid-ask data", "dataset fingerprint"],
"Signals and regimes": ["opening range", "VWAP pullback", "VWAP reversion", "trend context", "breadth confirmation", "relative volume", "volatility gate", "structural stop", "target realism", "session close"],
"Portfolio risk": ["per-trade risk", "daily loss stop", "weekly loss stop", "portfolio drawdown", "gross exposure", "net exposure", "correlation concentration", "liquidity capacity", "gap risk", "kill-switch reset"],
"Execution": ["next-bar timing", "spread model", "slippage model", "market impact", "partial fills", "order rejection", "latency", "same-bar ambiguity", "broker outage", "overnight liquidation"],
"Machine learning": ["meta-label definition", "training boundary", "label overlap", "feature causality", "class imbalance", "probability calibration", "model drift", "feature drift", "model complexity", "ML authority"],
"Validation": ["walk-forward design", "purging", "embargo", "locked holdout", "multiple testing", "PBO", "parameter perturbation", "cross-symbol replication", "regime decomposition", "uncertainty interval"],
"Governance": ["champion selection", "challenger promotion", "experiment registry", "holdout contamination", "model approval", "version pinning", "audit journal", "decision ownership", "paper-only boundary", "retirement rule"],
"Security and reliability": ["credential handling", "configuration integrity", "dependency pinning", "input validation", "log tampering", "state recovery", "clock drift", "duplicate orders", "resource exhaustion", "safe shutdown"],
"Operations and monitoring": ["data freshness", "broker heartbeat", "realized slippage", "daily reconciliation", "position reconciliation", "performance decay", "alert routing", "incident response", "paper observation", "human override"],
}

ROUND_LENSES = {
1: ["What evidence would justify", "What failure would invalidate", "What is the simplest defensible form of", "What implementation is mandatory for", "What result forces rejection of"],
2: ["How could an adversarial market exploit", "How could hidden dependence corrupt", "What stress must try to destroy", "What correlated failure can bypass the intent of", "What recovery behavior is safe after"],
3: ["What must be monitored continuously for", "Who or what may authorize changes to", "What can be deleted without weakening", "What proof is required before paper promotion of", "What final fail-closed rule governs"],
}

POLICY = {
"Objective and evidence": "Returns never override survival. Claims are limited to the weakest evidence class, and ambiguous evidence yields INCONCLUSIVE.",
"Data and lineage": "Reject or quarantine invalid observations; never forward-fill unknown market events. Fingerprint every dataset and preserve event-time semantics.",
"Signals and regimes": "Each rule must map to one economic role and add locked OOS value. Conflicting or unsuitable context produces NO_TRADE.",
"Portfolio risk": "Risk limits are hard ceilings controlled outside alpha. Correlation, liquidity and gap assumptions must be stressed jointly, not one at a time.",
"Execution": "A signal is not a fill. Use next-observable execution, conservative ambiguity, explicit costs and fail-closed broker handling.",
"Machine learning": "ML is a governed setup veto, not an oracle or risk authority. It remains disabled when samples, calibration or drift evidence are inadequate.",
"Validation": "Chronology, purging, holdout sealing and selection adjustment are mandatory. A beautiful validation score has no authority after OOS failure.",
"Governance": "Every promotion needs immutable evidence, a pristine holdout and independent approval. Revealed holdouts never become pristine again.",
"Security and reliability": "Secrets never enter logs or chat; state and journals are integrity checked. Any uncertain state stops entries before attempting recovery.",
"Operations and monitoring": "Reconcile external truth before internal state. Alerts must identify owner, severity, evidence and a tested shutdown procedure.",
}

CONTROL_HINTS = {
"data": "strict CSV ingestion and a content fingerprint",
"timestamp": "timezone-explicit event-time validation",
"holdout": "the append-only HoldoutFirewall",
"journal": "the hash-chained decision journal",
"fingerprint": "the deterministic run manifest",
"uncertainty": "block-bootstrap confidence intervals",
"machine": "a veto-only model behind Risk Engine authority",
"ML": "a veto-only model behind Risk Engine authority",
"risk": "hard pre-trade limits and persistent kill switches",
"loss": "hard pre-trade limits and persistent kill switches",
"execution": "next-open fills and cost/latency stress",
"slippage": "next-open fills and cost/latency stress",
"broker": "health checks, reconciliation and fail-closed state",
"overnight": "mandatory session liquidation",
"session": "explicit market-calendar boundaries",
"promotion": "the strict real-data promotion gate",
"registry": "append-only experiment and model records",
"version": "code/data/config hashes in the run manifest",
}


def hint(topic):
    for k, v in CONTROL_HINTS.items():
        if k.lower() in topic.lower(): return v
    return "an explicit invariant, test and recorded decision"


EVIDENCE_BAR = {
"Objective and evidence": "a real-data net-return distribution with drawdown and benchmark comparisons",
"Data and lineage": "zero unexplained integrity errors plus source-to-decision lineage",
"Signals and regimes": "positive locked-OOS expectancy with a confidence interval excluding zero",
"Portfolio risk": "property tests, joint stress scenarios and observed compliance with every hard ceiling",
"Execution": "quote-aware fills that survive cost, slippage, latency and reject scenarios",
"Machine learning": "purged OOS lift, calibration, stability and a simpler-rule comparison",
"Validation": "a sealed chronological holdout, selection adjustment and independent replication",
"Governance": "an immutable record, named approver and reproducible evidence package",
"Security and reliability": "fault injection showing safe failure without secret or state corruption",
"Operations and monitoring": "a rehearsed paper incident with reconciliation, alert and recovery evidence",
}

def answer(round_no, category, topic, lens):
    control = hint(topic); bar = EVIDENCE_BAR[category]
    if round_no == 1:
        clauses = [
            f"Justification requires {bar}; popularity, a point estimate, or one favorable period is insufficient.",
            f"It is invalidated when truncation, independent replication, or a realistic cost assumption reverses its decision or when its economic mechanism cannot be stated before seeing outcomes.",
            f"The smallest defensible form is one observable input, one threshold, one logged reason and one removal test; additional conditions need incremental OOS evidence.",
            f"Implementation must encode {control}, test both acceptance and rejection paths, and record the data/config/code identity used for the decision.",
            f"Reject it if evidence is synthetic-only, the lower uncertainty bound is non-positive, safety depends on optimistic fills, or the control cannot fail closed.",
        ]
    elif round_no == 2:
        clauses = [
            f"An adversary can target stale assumptions, clustered volatility and the exact moment liquidity disappears; test those jointly rather than replaying average bars.",
            f"Hidden dependence on broker, clock, correlated symbols, prior outcomes or revised data corrupts inference; isolate each dependency and then shock their combination.",
            f"The destructive test must exceed the design assumption—missing clusters, gap-through stops, spread expansion, latency and state loss—and must preserve conservative accounting.",
            f"Nominally separate safeguards may share one clock, feed or process; a common-mode outage therefore requires {control} outside the alpha path.",
            f"Recovery is safe only after external reconciliation, immutable incident recording and explicit authorization; automatic risk loosening or immediate re-entry is forbidden.",
        ]
    else:
        clauses = [
            f"Monitor a threshold, baseline, owner and expiry for {topic}; missing telemetry is itself an unhealthy state, not evidence of stability.",
            f"Changes require a versioned challenger, fresh evidence and an authorized review; a model, strategy or ordinary operator may never loosen its own safety constraint.",
            f"Delete forecasts, indicators and dependencies that do not change locked-OOS decisions or safety; preserve {control} because auditability is part of correctness.",
            f"Paper promotion requires {bar}, at least 100 OOS trades where applicable, stress survival and twelve weeks of forward observation without a safety breach.",
            f"The final rule is: when {topic} is missing, stale, inconsistent, contaminated or outside its approved envelope, block new orders, preserve exits and require reconciliation.",
        ]
    idx = ROUND_LENSES[round_no].index(lens)
    decision = "KEEP only with evidence" if category not in ("Machine learning", "Signals and regimes") else "CHALLENGER until OOS proof"
    return (f"{POLICY[category]} For **{topic}**, the concrete control is {control}. "
            f"{clauses[idx]} Residual uncertainty must remain visible in the report. "
            f"**Decision: {decision}.**")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for rnd, lenses in ROUND_LENSES.items():
        lines = [f"# Recursive Review Round {rnd} — 500 Questions and Answers", "",
                 "Generated from a versioned category/topic/lens matrix so coverage is reproducible. Answers are design decisions, not claims of market performance.", ""]
        q = 0
        for cat, topics in CATEGORIES.items():
            lines += [f"## {cat}", ""]
            for topic in topics:
                for lens in lenses:
                    q += 1
                    lines += [f"**R{rnd}-Q{q:03d}. {lens} {topic}?**", "",
                              f"**Answer:** {answer(rnd, cat, topic, lens)}", ""]
        assert q == 500
        (OUT/f"round_{rnd}_500.md").write_text("\n".join(lines))

if __name__ == "__main__":
    main()
