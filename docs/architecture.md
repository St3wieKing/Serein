# Serein — Architecture

## 1. Layered decision path

```
             ┌──────────────────┐
             │   DATA ENGINE    │  validation, audit, features, regimes
             └────────┬─────────┘
                      ▼
        ┌─────────────────────────┐
        │   STRATEGY ENGINES      │  trend · momentum · mean reversion · breakout
        └───────────┬─────────────┘
                    ▼
        ┌─────────────────────────┐
        │    META DECISION        │  weighted vote, disagreement, gates, NO_TRADE
        └───────────┬─────────────┘
                    ▼
        ┌─────────────────────────┐
        │     RISK ENGINE         │  ← ultimate authority (kill switches, limits)
        └───────────┬─────────────┘
                    ▼
        ┌─────────────────────────┐
        │    EXECUTION ENGINE     │  order validation, paper broker, reconciliation
        └───────────┬─────────────┘
                    ▼
                 BROKER (paper only)
```

Monitoring (dashboard, drift, registries) observes every layer.
**No layer can skip the risk engine; no model can modify it.**

Offline candidate lifecycle is authority-separated:

```text
ResearchAgent → ExperimentQueue/Runner → RedTeamAgent → ReviewAgent
      → deterministic promotion gate → frozen challenger → shadow/paper only
```

The SQLite queue tracks experiment/parameter/model/strategy search budget. A
sealed holdout firewall prevents reuse, and all critical decisions are
hash-journaled. No agent has research, risk, deployment and execution authority.

## 2. Package map

```
serein/
├── constants.py        action space, statuses, kill switches, exit reasons
├── config.py           dataclass config; every threshold has a rationale
├── data/
│   ├── synthetic.py    regime-switching OHLCV generator (labeled SYNTHETIC)
│   ├── validation.py   structural data-quality checks + anomaly flags
│   └── audit.py        leakage auditor (alignment, target leakage, overlap)
├── features.py         causal feature library (returns/vol/momentum/z/vwap/volume/time)
├── regimes.py          rule-based regime classifier + CUSUM change points
├── strategies/
│   ├── base.py         Strategy ABC + strict signal schema (direction/conf/R/regime_ok)
│   └── classic.py      trend, TSMOM momentum, z-reversion, compression breakout
├── meta.py             MetaEngine: weighted vote → action, disagreement-aware
├── risk/
│   ├── engine.py       RiskEngine: kill switches, daily/weekly limits, exposure,
│   │                   pre-trade checklist (the only gate)
│   └── sizing.py       risk-budget sizing: confidence/drawdown/vol scaling, no martingale
├── backtest/
│   ├── engine.py       event-driven multi-instrument backtester (next-open fills,
│   │                   intrabar stops, gap-through-stop, risk-in-the-loop)
│   ├── costs.py        commission + half-spread + slippage + impact
│   ├── metrics.py      full metric suite + decomposition
│   ├── walkforward.py  chronological splits with embargo; purged k-fold
│   ├── robustness.py   parameter sweeps, stability, CSCV-PBO, ablation, perturbation
│   └── stress.py       cost/slippage/vol/liquidity/latency/missing-data shocks
├── ml/
│   ├── models.py       LR / RF / GBM with governance metadata + purged WFA
│   └── calibration.py  reliability curves, ECE, Brier, Platt/isotonic
├── drift.py            PSI feature drift, CUSUM performance drift, slippage drift
├── health.py           ACTIVE/DEGRADED/QUARANTINED strategy-health decisions
├── autonomy/           research/red-team/review agents, queue, factory, authority
├── holdout.py          irreversible sealed/revealed holdout firewall
├── opportunity.py      post-cost EV ranking with hard eligibility gates
├── promotion.py        strict real-data/paper promotion certification gate
├── audit_journal.py    tamper-evident decision journal
├── registry.py         append-only experiment + model registries (JSONL)
├── execution/
│   ├── broker.py       BrokerInterface + PaperBroker (fills, partials, reconciliation)
│   ├── gateway.py      approved paper-order gateway + idempotency
│   ├── shadow.py       no-order shadow decision recorder
│   └── validation.py   deterministic pre-trade checklist (gate #2)
├── reporting.py        markdown report generation from real artifacts
└── dashboard.py        static HTML dashboard (equity, drawdown, monthly, journal)
```

## 3. Key invariants (enforced by tests)

1. **Accounting identity:** final equity == initial + Σ trade PnL (slippage
   lives in fills; commissions are line items). Unit-tested.
2. **Causality:** features/labels at t use only data ≤ t. Unit-tested by
   prefix-recomputation and by the leakage auditor.
3. **Timing:** signal at close t fills at open t+1 with costs; stop-first
   intrabar resolution. Unit-tested.
4. **Risk authority:** no order reaches execution without `check_entry`
   passing; kill switches block everything. Unit-tested.
5. **No martingale:** position size has no PnL-history input. Unit-tested.
6. **No fabrications:** reports are generated from run artifacts;
   synthetic provenance is printed in every report/dashboard.

## 4. Evaluation protocol (the gates)

1. Leakage audit pass
2. Full metrics (never total return alone)
3. IS / OOS temporal split (OOS locked)
4. Walk-forward with embargo (parameters locked)
5. Stress suite (costs 2/5/10x, slippage 2/5/10x, vol 1.5/2/3x,
   liquidity 0.5/0.2/0.1x, latency 1/3/6 bars, missing 1/5%)
6. Parameter stability + perturbation
7. PBO (CSCV) on any selection
8. Ablation (every feature/component earns its place)
9. Drift analysis
10. Minimum sample size (hundreds of trades; 8 OOS trades is NOT enough)

## 5. Automation levels

| Level | Capability | Gate |
|---|---|---|
| 0 | Research / hypotheses | — |
| 1 | Backtest | leakage + metrics + OOS |
| 2 | Shadow (observe, no orders) | stress + PBO |
| 3 | Paper (simulated fills) | drift + calibration review |
| 4 | Controlled live (future, authorized) | human approval + legal/broker eligibility |
| 5 | Adaptive portfolio | sustained level-4 evidence |

The repository ships at level 0–3. Nothing in the codebase can reach
level 4 (no live adapter, PAPER_TRADING_ONLY=True).

## 6. Timing & sessions

- External timestamps are ingested with an explicit source timezone and
  converted to an explicit market timezone; naive timestamps are never assumed.
  The session-aware synthetic generator is deliberately timezone-naive but
  labeled synthetic. Bar indexes are DatetimeIndex.
- Session features use US-equity-style regular hours; real holiday and early-
  close calendars remain a deployment blocker.
- Expected bar step = median of index diffs; gaps beyond that trigger
  gap-through-stop handling.
