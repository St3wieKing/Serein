# Serein — Failure Recovery Procedures

## 1. Kill switches (any trip ⇒ NO_NEW_TRADES)

| Switch | Trip condition |
|---|---|
| DATA_KILL_SWITCH | stale/missing/corrupt feed, anomaly flood |
| EXECUTION_KILL_SWITCH | fill anomalies, order storms |
| BROKER_KILL_SWITCH | disconnect, malformed responses, rejected auth |
| MODEL_KILL_SWITCH | NaN outputs, calibration collapse, prediction-distribution shift |
| DRAWDOWN_KILL_SWITCH | portfolio DD ≥ 10%, daily/weekly loss limits, consecutive losses, equity floor |
| SLIPPAGE_KILL_SWITCH | realized slippage >> model |
| VOLATILITY_KILL_SWITCH | realized vol > 120% annualized |
| ANOMALY_KILL_SWITCH | impossible prices / absurd spreads |
| SYSTEM_HEALTH_KILL_SWITCH | unhandled errors, clock drift, state divergence |

- Drawdown/equity-floor trips additionally request **liquidation at
  next close** (`force_exit`).
- Kill switches are tripped by simple, unit-tested arithmetic; no ML
  component can trip or clear them. Clearing requires an operator
  procedure + audit record.

## 2. Emergency stop

`EMERGENCY_STOP` semantics (documented; implemented as the kill-switch
mechanism in `RiskEngine`):

1. Immediately prevent new orders (validator + `new_trades_allowed`).
2. No model can override it.
3. Positions follow the predefined policy (hold-and-monitor vs
   liquidate) selected at config time.
4. Everything is logged.

## 3. Restart recovery (never trust local state)

1. Reconnect and authenticate.
2. Fetch account, positions, open orders from the broker/feed.
3. Diff against local state; reconcile every discrepancy (prefer
   broker truth; if both are suspect, freeze).
4. Run the full risk check (limits, kill switches, exposure).
5. Only then resume trading.

## 4. Data-outage procedure

1. Staleness detection → DATA_KILL_SWITCH → halt new orders.
2. Positions keep their stops (they are price-based, not
   data-based); the engine marks at last known price.
3. On feed recovery, validate the gap (missing bars) and reconcile
   fills that may have occurred (gap-through-stop model in backtests;
   broker-side stop confirmations in live).

## 5. Broker-outage procedure (paper and future live)

1. BROKER_KILL_SWITCH trips on connectivity loss.
2. No new orders; no blind retries.
3. On reconnect: reconcile orders/positions (duplicate prevention via
   order IDs).
4. Resume only after risk re-check.

## 6. Model-anomaly procedure

1. NaN/non-finite predictions → order rejected + MODEL_KILL_SWITCH on
   repetition.
2. Calibration/PSI drift → DEGRADED status → risk reduction →
   quarantine → revalidation → paper → redeploy.

## 7. Clock-sync procedure

- All timestamps UTC; monotonicity checks; a clock jump > threshold
   trips SYSTEM_HEALTH_KILL_SWITCH.
- Recovery: resync (NTP), replay last N events for ordering, reconcile
   any order timestamps before resuming.

## 8. Post-incident discipline

1. Preserve logs/registries (append-only).
2. Categorize the incident (data/execution/broker/model/risk/system).
3. Root-cause analysis; add a regression test for the failure mode
   (failure-injection tests).
4. Re-run the affected stage of the ladder before resuming.
5. Never resume "because it looks fine now".
