# Serein System Autopsy Report

**Date:** 2026-08-14  
**Scope:** repository-wide audit before autonomous-platform expansion  
**Current authority:** research and paper only; live execution permanently false

## Executive verdict

The project had a strong research/backtest/risk foundation, but it was not yet a
complete autonomous platform. Its strongest components were deterministic risk
limits, causal strategy contracts, realistic next-bar entry timing, stress tests,
registries and honest reporting. Its largest gaps were real point-in-time data,
a scheduled autonomous research loop, authority-separated agents, a durable
experiment database, paper execution orchestration, complete reconciliation,
operational observability and certification automation.

A critical accounting realism bug was found during this autopsy: backtest exit
slippage was reported in `costs_total` but did not alter exit cash or P&L. This
made previous returns optimistic. It is fixed and regression tested; historical
reports generated before this commit must be regenerated and must not be cited
as current evidence.

## Component autopsies

### 1. Strategy layer

- **What it does:** causal rule-based trend, momentum, reversion, breakout,
  intraday, ML and public-behavior proxy candidates.
- **Why it exists:** isolate hypotheses behind a strict signal schema.
- **Inputs/outputs:** OHLCV/regime data → direction, confidence, expected R,
  horizon, regime gate, reason, optional structural stop/target/session exit.
- **Dependencies:** pandas/numpy; sklearn for ML candidates.
- **Assumptions:** bars are timestamp-correct; rolling features are causal;
  modeled fills represent tradable prices.
- **Known bugs:** no current known schema bug. OpeningRangeChallenger is
  selection-contaminated and frozen accordingly.
- **Potential bugs/leakage:** session/calendar mismatch, bad adjustment data,
  universe survivorship, repeated OOS inspection, broker-specific microstructure.
- **Overfitting/complexity:** zoo and ML search create selection risk; PBO and
  holdout firewall mitigate but do not remove it.
- **Performance contribution:** only opening-range continuation was promising in
  synthetic OOS; full router and ML failed durable OOS.
- **Risk contribution:** structural stops and session liquidation reduce risk;
  signal confidence is not allowed to override hard limits.
- **Decision:** keep modular library; freeze OR as challenger; reject failed
  components as champions; require real fresh holdout.

### 2. Market context and regime engine

- **What it does:** EMA/VWAP/ATR, volatility percentiles, CUSUM regimes,
  cross-sectional breadth, time/session context.
- **Purpose:** choose when a setup is eligible, especially NO_TRADE regimes.
- **Inputs/outputs:** causal prices/volume → labels/features and gates.
- **Assumptions:** regime proxies are observable soon enough to trade.
- **Potential leakage:** revised macro/event labels would leak if added without
  point-in-time timestamps.
- **Complexity:** moderate; correlated indicators can create fake confluence.
- **Contribution:** useful routing/risk context, not an independent alpha source.
- **Decision:** keep; every context filter must pass ablation.

### 3. Data pipeline

- **What it does:** synthetic generators, bar validation, leakage audit, strict
  intraday CSV ingestion and content fingerprints.
- **Inputs/outputs:** CSV/generated bars → validated per-symbol frames/reports.
- **Dependencies:** pandas, zoneinfo.
- **Assumptions:** vendor timestamps and corporate-action policy are known.
- **Known limitation:** no licensed real intraday/NBBO source is connected.
- **Potential bugs:** early closes/holidays are reported incomplete because a
  full exchange calendar is not bundled; bid/ask schema is not yet ingested.
- **Risk:** bad data correctly causes rejection rather than guessing.
- **Decision:** keep strict loader; add licensed point-in-time provider and
  exchange calendar before any real evidence claim.

### 4. Feature layer

- **What it does:** 41 causal general features plus intraday meta features.
- **Purpose:** support diagnostics and governed ML challengers.
- **Inputs/outputs:** validated bars → feature matrices.
- **Assumptions:** rolling windows have sufficient warm-up and no universe leak.
- **Evidence:** direct direction ML produced near-chance AUC; intraday ML won
  validation and failed locked OOS.
- **Risk:** feature proliferation and correlated confluence.
- **Decision:** retain for research; ML disabled from champion authority; require
  feature lineage, drift and removal tests.

### 5. Machine learning

- **What it does:** logistic/RF/GBM direction models, calibration tools and
  intraday setup-quality meta-labels.
- **Purpose:** reject weak deterministic setups, never replace risk.
- **Dependencies:** scikit-learn.
- **Assumptions:** labels, embargo and distribution remain relevant.
- **Known failure:** validation performance did not persist OOS.
- **Potential leakage:** cutoff movement, overlap and repeated model selection;
  fixed train boundaries and event spacing mitigate.
- **Complexity:** higher than current evidence justifies.
- **Decision:** challenger/quarantined by default; no approved ML champion.

### 6. Risk Engine

- **What it does:** exposure, leverage, sizing, daily/weekly loss, drawdown,
  volatility, frequency and kill-switch enforcement.
- **Purpose:** final deterministic authority.
- **Inputs/outputs:** proposed order and portfolio state → allow/deny/force exit.
- **Dependencies:** configuration only; deliberately independent of alpha.
- **Assumptions:** prices and positions are reconciled and gaps remain bounded.
- **Known behavior:** a daily/weekly breach trips the shared drawdown kill switch,
  making the halt persistent until an authorized reset. This is conservative but
  conflates temporary and persistent states.
- **Potential bugs:** correlation is controlled through gross/net caps rather
  than a dynamic covariance limit; simultaneous gaps can exceed intended risk.
- **Decision:** keep as ultimate authority; add persistent state and external
  reconciliation (implemented); consider separate halt taxonomy later.

### 7. Position sizing

- **What it does:** fixed fractional structural-stop risk with volatility,
  confidence and drawdown scaling plus notional/liquidity caps.
- **Assumptions:** stop fill approximates risk; confidence is informative.
- **Overfitting risk:** confidence scaling can amplify model miscalibration.
- **Safety:** no P&L history input, so martingale is structurally unavailable.
- **Decision:** keep 0.25–0.5% research caps; confidence multiplier remains small
  and should be removed if real ablation does not help.

### 8. Backtester

- **What it does:** event-driven multi-symbol cash accounting, next-open fills,
  intrabar stops/targets, gaps, structural levels, session exits and metrics.
- **Assumptions:** OHLC path unknown; stop-first handles ambiguity.
- **Known bug fixed:** exit slippage previously did not affect cash/P&L. It now
  changes actual exit fills and accounting.
- **Potential gaps:** no quote-level queue, borrow availability, halt/auction,
  corporate action or asynchronous partial-fill model.
- **Decision:** keep; invalidate and regenerate pre-fix performance artifacts.

### 9. Costs and stress

- **What it does:** commissions, spread, slippage, impact; shocks for costs,
  volatility, liquidity, latency and missing data.
- **Known improvement:** latency no longer delays mandatory session liquidation.
- **Assumptions:** bps models approximate realized execution.
- **Decision:** keep; calibrate only from paper fills, never lower assumptions to
  rescue a candidate.

### 10. Validation and robustness

- **What it does:** chronological splits, walk-forward, embargo, CSCV/PBO,
  perturbations, ablations, block bootstrap and promotion gates.
- **Potential weakness:** small candidate/subperiod matrices make PBO unstable;
  bootstrap intervals do not correct strategy-selection bias.
- **Decision:** keep; require sealed holdout and independent replication.

### 11. Execution layer

- **What it does:** broker interface, PaperBroker, pretrade validator,
  paper-only gateway, shadow recorder, idempotency and reconciliation.
- **Known bugs fixed:** PaperBroker did not deduct commissions from cash; now it
  does. Duplicate idempotency keys are rejected.
- **Potential limitations:** market order fills are synchronously simulated at
  the next bar; partial remainder lifecycle is simplified; no stop orders.
- **Live status:** no live adapter and no code path to enable one.
- **Decision:** retain paper/shadow only.

### 12. Order validation

- **What it does:** market/data/symbol/price/qty/spread/quote/liquidity/exposure/
  duplicate/loss/risk/broker/strategy/model/account authorization checks.
- **Potential gap:** external market calendar and account authorization source
  are caller inputs and must be independently attested.
- **Decision:** keep; all mandatory false values mean NO_TRADE.

### 13. Registries and database

- **What it does:** JSONL experiment/model history, hash-chain journals,
  holdout firewall and SQLite autonomous experiment/failure/decision/budget DB.
- **Known limitation:** old JSONL registry is append-only but not itself hash
  chained; critical new decisions use the tamper-evident journal.
- **Decision:** retain compatibility, route new autonomous cycles through SQLite
  plus hash journal; back up and verify before startup.

### 14. Autonomous agents

- **What it does:** ResearchAgent proposes diagnosis-driven experiments;
  RedTeamAgent attacks; ReviewAgent identifies missing evidence; orchestrator
  queues one governed offline cycle.
- **Authority:** agents cannot approve risk, submit live orders, erase audits or
  mark a revealed holdout pristine.
- **Assumptions:** deterministic templates are narrower than general AI research.
- **Decision:** keep constrained autonomy; broad generative research remains a
  proposal source, never a deployment authority.

### 15. Strategy factory and experiment budget

- **What it does:** validates context/setup/trigger/risk/exit combinations,
  restricts filter and candidate counts, tracks dataset search budget.
- **Risk:** a constrained factory can still overfit if the same holdout is reused.
- **Decision:** keep; stop when budget is exhausted and demand fresh evidence.

### 16. Drift and health monitoring

- **What it does:** PSI, CUSUM-like feature/performance alerts, slippage drift and
  ACTIVE→DEGRADED→QUARANTINED health decisions.
- **Assumptions:** minimum sample is adequate; multiple alerts are correlated.
- **Decision:** keep; one bad day with <50 trades cannot trigger adaptation;
  critical operational failure quarantines immediately.

### 17. Observability and reporting

- **What it does:** static dashboards, markdown reports and decompositions.
- **Known bug:** dashboard metadata always says synthetic even for a future real
  dataset; must be corrected before real-data dashboards.
- **Missing:** long-running health endpoint, alert transport and scheduled daily/
  weekly report service.
- **Decision:** keep static reporting; build daemon observability only after a
  real paper feed exists.

### 18. Security

- **What it does:** no credentials in repo, strict symbol validation, paper-only
  flag, capability separation, checksummed restart state and tamper evidence.
- **Potential gaps:** dependency wheel hashes, OS sandboxing, secret manager,
  database encryption and operator identity are deployment-environment concerns.
- **Decision:** safe for research; not certified for controlled deployment.

### 19. Configuration and dependencies

- **What it does:** dataclass/JSON configuration and exact direct-dependency lock.
- **Risk:** full transitive wheels are not hash locked; configuration signatures
  are manifests rather than external approvals.
- **Decision:** keep; require immutable deployment image and signed config for any
  future authorized controlled environment.

### 20. Documentation and tests

- **What it does:** architecture, research, failure, deployment, security,
  1,500-question recursive review and automated tests.
- **Potential weakness:** documentation can become stale; generated artifacts are
  gitignored and must include manifests.
- **Decision:** keep docs coupled to tests and certification generation.

## Final autopsy decision

**No strategy is approved. No live stage exists.** The platform may autonomously
research, queue, attack, review and paper-simulate candidates, but deterministic
gates preserve authority. The next critical dependency is licensed real
point-in-time intraday quote data and a genuinely sealed holdout.
