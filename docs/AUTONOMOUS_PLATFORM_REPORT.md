# Autonomous Research and Execution Platform Report

**Date:** 2026-08-14  
**Version:** 0.3.0  
**Mode:** RESEARCH / SHADOW / PAPER ONLY  
**Live execution:** permanently disabled

## What is now autonomous

The bounded research loop can:

1. ingest a diagnostic;
2. generate evidence-labeled hypotheses;
3. score expected information value against compute, complexity and
   contamination risk;
4. enforce a per-dataset experiment budget;
5. queue experiments in SQLite;
6. run one offline experiment through an injected runner;
7. request a fixed red-team attack set;
8. send outcome and attacks to an independent ReviewAgent;
9. record results, failures and decisions;
10. recognize failure and enqueue the next research priorities.

It cannot change live risk, approve itself, erase journals, transmit a live
order or restore a contaminated holdout.

## Authority separation

| Role | May | May not |
|---|---|---|
| Research | propose hypotheses | trade, approve, change risk |
| Experiment | execute offline tests | promote or deploy |
| Red Team | attack and recommend quarantine | modify candidate to pass |
| Review | identify missing evidence | approve risk or execution |
| Trading | scan and propose | approve its own order |
| Risk | approve/deny, tighten, kill | create alpha or loosen limits |
| Execution | submit/cancel/reconcile paper orders | submit live orders |
| Admin | authorize paper reset/stage | enable live in this repository |

No role has strategy-change, risk-change and execution authority together.

## First autonomous cycle

The system tested the frozen opening-range challenger on a fresh synthetic world
(seed 777, 160 sessions, SPY/QQQ/IWM-like instruments). Corrected exit slippage
was included.

| Metric | Result |
|---|---:|
| Trades | 55 |
| Return | **−0.53%** |
| Sharpe | **−1.60** |
| Max drawdown | −0.53% |
| Mean expectancy | −0.21R |
| 95% expectancy interval | −0.44R to +0.05R |
| P(expectancy ≤ 0) | 94% |
| 2× cost return | −0.63% |
| 5× slippage return | −0.50% |

The ReviewAgent returned **NOT_APPROVED** because real data, 100 OOS trades,
positive lower expectancy, paper evidence and multiple red-team results were
missing. The system recorded the rejection and automatically queued three next
research hypotheses: remove the setup, test turnover reduction, and test a
stricter regime gate. They are assigned to `FRESH-DATASET-REQUIRED`, not the
revealed dataset. Those are hypotheses, not promotions or permission to recycle
OOS data.

## Paper execution

`PaperExecutionGateway` now wraps the broker and independently requires:

- fresh quote and data;
- market open;
- valid symbol, price, side and quantity;
- acceptable spread and liquidity;
- no duplicate intent/order;
- position/exposure/leverage limits;
- daily and weekly loss gates;
- healthy broker and Risk Engine;
- approved strategy and model;
- authorized paper account.

Every decision and paper-order result enters a hash-chained journal. The broker
also rejects duplicate idempotency keys and supports position/order
reconciliation. Local/broker disagreement stops new activity.

## Shadow mode

The shadow recorder has no broker dependency or submit method. It records what
would have been traded, including timestamp, instrument, strategy, setup,
context, regime, entry, stop, target, expected R/EV, confidence, proposed size,
risk and NO_TRADE reason.

## Automatic quarantine

Health decisions require at least 50 recent trades for performance adaptation.
One bad day does not rewrite the strategy. Critical system failure quarantines
immediately; joint expectancy, drawdown, slippage, feature and calibration drift
can move ACTIVE → DEGRADED → QUARANTINED.

## New integrity controls

- strict point-in-time CSV validation;
- content and run fingerprints;
- non-reusable sealed holdouts;
- hash-chained audit journal;
- atomic checksummed safety state;
- SQLite experiment/failure/decision/budget database;
- exact direct-dependency lock;
- strict paper-promotion certification gate;
- complete system autopsy;
- 520 structured research questions;
- 1,000 structured adversarial questions;
- 1,500 prior recursive review questions.

## Critical bug corrected

Exit slippage had been reported but not deducted from backtest cash/P&L. It now
changes the actual exit fill. PaperBroker commissions are also deducted from
cash. Earlier performance artifacts are explicitly marked superseded.

## External public-data attempt

Two separate one-shot tests used public Alpha-Vantage-derived minute fragments,
strictly cleaned and aggregated to five minutes. Each last-40-session holdout was
sealed and revealed once. AAPL/JPM produced four trades, −0.14%, Sharpe −2.39,
PF 0.28 and −0.51R. A fresh AAL/AMD/BAC holdout produced eight trades, −0.28%,
Sharpe −2.08, PF 0.34 and −0.34R. Both failed 2× costs and slippage. The source is
unverified and samples are insufficient, but they provide no support. Both
holdouts are permanently contaminated and the OR challenger is rejected.

A third independent C/CAT/CSCO dataset reserved its final 40 sessions. On the
first 79 sessions, OR generated zero trades, VWAP pullback generated one near-flat
loss and VWAP reversion generated four losing trades. Because no training
candidate passed, the system did **not reveal the final 40 sessions**. That
holdout remains sealed instead of being wasted on strategy fishing.

## Remaining blockers

- no licensed point-in-time intraday quote/NBBO data;
- no real exchange calendar for holidays/early closes;
- no real paper feed or twelve-week forward observation;
- no quote-level partial-fill/order-book simulator;
- no long-running scheduler, alert transport or operational host;
- no legally authorized brokerage/account environment;
- no approved strategy or ML model;
- no live adapter by design.

## Final decision

**FAILED / NOT READY FOR PAPER CHAMPION OR CONTROLLED DEPLOYMENT.**

The platform can now research and reject autonomously. Its first fresh autonomous
test rejected the previously promising challenger. This is successful behavior:
it prevented a selection-contaminated synthetic result from becoming a trading
claim.
