# Strategy changelog

## v0.3.0 platform — 2026-08-14

- Added governed autonomous Research, Experiment, Red-Team and Review agents,
  SQLite experiment/failure/decision journals, constrained strategy factory,
  experiment budgets, opportunity ranking and strategy health quarantine.
- Added paper-only execution gateway, idempotency, broker reconciliation,
  complete shadow-decision schema and strict strategy/model/account gates.
- Fixed critical exit-slippage accounting: exit slippage now changes fill, cash
  and P&L. Fixed PaperBroker commission booking. All earlier performance reports
  are superseded until regenerated.
- Added system autopsy, 520 structured research questions and 1,000 structured
  adversarial questions. Live execution remains permanently disabled.
- Frozen opening-range challenger failed a fresh synthetic cycle and two sealed
  public external samples; status changed to REJECTED_EXTERNAL_REPLICATION.
- On a third public dataset no training candidate passed, so the reserved
  40-session holdout was deliberately left SEALED and uninspected.

## v2.0.0 — 2026-08-14

- Destroy/rebuild cycle: no v1 alpha rule was grandfathered.
- Added four objective candidate families: trend-pullback continuation,
  compression breakout, failed breakout, and session-VWAP reversion.
- Added A/B/C/D simplification experiment and transparent simplicity score.
- Added optional structural stop/target fields; next-open gap invalidates rather
  than silently rewriting the planned trade.
- Added Matthew Scriv public-evidence ledger, trading-book hypothesis table,
  component library, and 100-question adversarial review.
- Added fail-closed champion/challenger promotion policy.
- Decision: **no candidate approved**. Compression is inconclusive with 21 OOS
  trades. Pullback A was isolated-OOS positive but failed full/stress/risk
  consistency; B–D were negative OOS.

## v1.0.0 — 2026-08-14

- Original four-family ensemble, research/risk/backtest/ML framework.
- Decision: not approved; synthetic Sharpe approximately 0.09 and ML at chance.

## v1.1.0 — 2026-08-14

- 30-strategy zoo and tournament/PBO harness.
- Slow-trend synthetic finalist remained weak in absolute terms; no 20% weekly
  result and no real-market approval.
