# Three-round recursive review implementation log

**Date:** 2026-08-14  
**Coverage:** 1,500 unique questions and answers across three sequential rounds.  
**Validation:** `python scripts/validate_recursive_review.py`

The reviews are in `research/recursive_review/round_1_500.md` through
`round_3_500.md`. They are versioned design decisions, not evidence that a
strategy is profitable.

## Round 1 — foundations and evidence

The first 500 questions challenged objectives, data lineage, signal mechanisms,
risk, execution, ML, validation, governance, security and operations.

### Main findings

1. Real intraday data ingestion was not strict enough for future research.
2. Dataset identity and run reproduction were implicit rather than immutable.
3. A viewed holdout could be mislabeled pristine by process error.
4. The three-setup strategy contained more complexity than evidence supported.
5. Synthetic results needed stronger evidence-class enforcement.

### Implemented after round 1

- `serein/data/intraday_csv.py`: timezone-explicit, session-aware CSV ingestion;
  duplicate/nonfinite/OHLC rejection; missing-session reporting; no silent fill.
- `serein/reproducibility.py`: deterministic frame/universe fingerprints and
  code/data/config/strategy run manifests.
- `serein/holdout.py`: append-only hash-chained holdout firewall. Once revealed,
  a dataset can never become pristine again.
- `serein/strategies/institutional_intraday.OpeningRangeChallenger`: frozen
  selection-contaminated challenger; parameters cannot be silently retuned.

## Round 2 — adversarial destruction

The second 500 questions combined market, infrastructure, model and governance
failures rather than testing one shock at a time.

### Main findings

1. Logs could be edited without cryptographic evidence.
2. Point estimates hid uncertainty and small-sample fragility.
3. Restarting from corrupt or unresolved state needed an explicit fail-closed rule.
4. Latency stress must never delay safety/session liquidation.
5. ML validation success was not durable and should remain disabled by evidence.

### Implemented after round 2

- `serein/audit_journal.py`: append-only hash-chain for decisions and risk events.
- `serein/backtest/uncertainty.py`: dependent block bootstrap for equity and
  bootstrap confidence intervals for trade expectancy.
- `serein/safety_state.py`: atomic checksummed state persistence; any missing,
  corrupt, unhealthy, tripped or non-flat state returns `HALT_AND_RECONCILE`.
- Latency stress now delays alpha fields only; `force_flat` safety is never delayed.
- ML remains a veto-only challenger and is not the strategy champion.

## Round 3 — simplification, promotion and operations

The final 500 questions asked what could be deleted, what must be monitored, who
may authorize changes, and what evidence permits paper promotion.

### Main findings

1. “Bulletproof” is an invalid requirement; bounded failure is testable.
2. Synthetic success must never pass a promotion gate.
3. A positive point estimate is insufficient if expectancy uncertainty includes zero.
4. Paper observation and independent replication are mandatory.
5. Flat, healthy and reconciled state is required before entries after restart.

### Implemented after round 3

- `serein/promotion.py`: strict promotion evidence schema requiring real
  point-in-time data, ≥100 OOS trades, positive lower expectancy bound, stress
  survival, cross-symbol/regime replication, pristine holdout, zero safety
  breaches and 12 paper weeks.
- Frozen OR challenger rather than retaining failed pullback/reversion/ML
  complexity as an apparent production ensemble.
- Tests for holdout reuse, journal tampering, data duplicates/timezones,
  fingerprints, synthetic promotion rejection, uncertainty, atomic safety state,
  and frozen strategy parameters.

## Final architecture decision

```text
strict real data + fingerprint
→ sealed holdout firewall
→ frozen deterministic setup
→ optional evidence-approved ML veto
→ Risk Engine
→ paper broker
→ atomic safety state + hash journal
→ reconciliation and monitoring
→ strict promotion gate
```

## Current decision

**NOT APPROVED.** The best existing challenger was selected after synthetic OOS
inspection, one of five synthetic replications lost, and 5× slippage erased the
result. No amount of additional code changes that evidence.

The bot is now harder to fool, easier to audit, and safer to stop. The next
highest-value input is real point-in-time intraday data—not another indicator.
