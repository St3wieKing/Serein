# SEREIN — FINAL RESEARCH REPORT (v0.1)

> **Superseded performance artifact:** generated before the 2026-08-14 exit-fill
> slippage accounting correction. Numerical performance is audit history only.

**Date:** 2026-08-14 · **Branch:** arena/019ffdd9-serein
**System state:** PAPER_TRADING_ONLY · Automation level 0–3 (research,
backtest, paper). No live adapter exists.

> **Data provenance: SYNTHETIC.** Every number in this report comes from
> the regime-switching simulator (`serein/data/synthetic.py`), 8 years of
> hourly bars, 3 symbols, 70,129 bars each, with planted trend/reversion/
> breakout structure. These results validate the engineering and
> statistical machinery. **They are not evidence of any tradable edge.**
> Raw outputs: `artifacts/research_report.md`, `artifacts/dashboard.html`,
> `artifacts/experiments.jsonl`, `artifacts/models.jsonl`. Regenerate:
> `.venv/bin/python scripts/run_research.py`.

---

## 1. Executive summary

1. **A complete research framework was built and tested** — data
   validation, leakage auditing, causal features, regime detection,
   four strategy families, a disagreement-aware meta engine, an
   unbypassable risk engine with nine kill switches, an event-driven
   backtester with realistic costs and gap-through-stop modeling, ML
   with purged walk-forward, stress testing, PBO/CSCV, ablation,
   drift detection, a paper broker with failure injection, append-only
   registries, a dashboard, and 61 passing tests.
2. **The 335-question research decision log was produced and validated**
   (`research/decision_log/`, `scripts/validate_questions.py`).
3. **On synthetic data the default ensemble shows no exploitable edge:**
   +2.9% total over 8 years (Sharpe 0.09), negative out-of-sample
   (−2.8%, 8 trades), underwater ~99% of the sample after the first
   year, profits entirely from the short side. ML direction models are
   at chance (OOS AUC 0.503–0.509 vs base rate 0.503).
4. **The risk machinery works as designed:** daily/weekly limits,
   drawdown kill switch (tripped at 6 consecutive losses), 984
   pre-trade rejections, vol scaling, gap-through-stop honesty,
   graceful degradation under cost shocks.
5. **Honest conclusion:** no strategy in this report is approvable.
   The framework now exists to find out whether *anything* survives on
   real data — the central open question (roadmap Phase A).
6. **The 20% weekly objective is an aspirational benchmark with a
   near-zero prior at acceptable risk** (70–95% of day traders lose
   money; ~1% are persistently profitable — S08/S09). The risk system
   ignores return targets by construction.

## 2. Research methodology

Phase order followed: literature + Athena public-info research →
question generation (335) → architecture → baselines → backtest engine
→ risk engine → ensemble → ML → regime engine → meta → walk-forward →
OOS → stress → red-team-style checks → paper broker. Every layer is
documented in `research/` and every experiment is registry-logged.

## 3. Athena public-information analysis

Full analysis: `research/athena_analysis.md`. Summary:

- **VERIFIED:** public positioning ("high-probability vs low-probability
  trades", "automatic discipline"), legal entity (Swing Trading Lab LLC /
  Alex Gonzalez), CFTC 4.41 simulated-performance disclaimer, no audited
  track record anywhere public.
- **CLAIMED (unverified):** community reviews alleging ~32% free-signal
  win rate and VIP upsells; conflicting user reports.
- **INFERRED (not fact):** methodology family is retail market-structure/
  liquidity-style education; business model is subscriptions.
- **UNKNOWN:** actual algorithms, actual performance, ML role.
- **Legitimately incorporated:** the public *philosophy* — explicit
  probability filtering, automatic discipline, no-trade as an option.
  Nothing proprietary is claimed or copied; the mandate's distinction
  (VERIFIED/CLAIMED/INFERRED/UNKNOWN) is respected.

## 4. Strategy research

Four baseline families implemented (`strategies/classic.py`): vol-adjusted
trend, TSMOM-style momentum, z-score mean reversion (calm-vol gated),
volatility-compression breakout (volume-confirmed). Each emits a strict
signal schema (direction, confidence, expected_R, horizon, regime_ok,
reason). Full-period synthetic results:

| Strategy (via meta) | Trades | WR | Expectancy (R) | Notes |
|---|---|---|---|---|
| trend+momentum (dominant) | 78 total | 38.5% | +0.09R | PF 1.13; OOS negative |
| mean reversion | ~0 active | — | — | gate rarely satisfied |
| breakout | ~0 active | — | — | compression rare in regime chain |

Decision log verdicts: H01–H04 **INCONCLUSIVE/weak**; H05 (meta gating)
**supported as risk filter**; H06 (regime gates) **partially supported**;
H07 (ML direction) **rejected at current feature set**.

## 5. Feature research

41 causal features (returns, volatility family, momentum family,
z-scores, VWAP distance, relative volume, time, regime dummies).
Ablation (Δ OOS AUC vs ALL=0.5067, logistic, 3-fold purged WFA):

| Remove | Δ AUC | Verdict |
|---|---|---|
| volume | −0.012 | harmful to remove |
| time | +0.001 | ~neutral |
| regime | +0.005 | ~neutral (keep, cheap) |
| momentum | +0.011 | harmful to remove |
| volatility | +0.005 | ~neutral |

Conclusion: no feature group is decisive; the entire set is near-noise
at the hourly horizon. **Feature research is the bottleneck**, not model
capacity (Q40 ML log).

## 6. Model comparison (ML)

| Family | OOS AUC | Acc | ECE | Brier | n |
|---|---|---|---|---|---|
| Logistic | 0.5093 | 0.506 | 0.037 | 0.2539 | 62,613 |
| Random Forest | 0.5056 | 0.504 | 0.048 | 0.2550 | 62,613 |
| Gradient Boosting | 0.5031 | 0.503 | 0.079 | 0.2642 | 62,613 |
| Base rate | 0.503 | — | — | — | — |

All at chance; ECE low only because predictions hug the base rate.
Calibration machinery (reliability curves, ECE, Brier, Platt/isotonic)
is implemented and tested.

## 7. Risk architecture

- **Risk Engine is the only gate** (check_entry) and cannot be bypassed:
  unit-tested invariant.
- Limits: 0.5% risk/trade, 25% per-symbol, 100% gross/80% net exposure,
  5 positions, leverage 1.0, 2% daily / 4% weekly loss halts, 10%
  drawdown kill, 6-consecutive-loss kill, 80% equity floor, vol kill
  (>120% annualized), frequency caps (20/day, 6/hour).
- Sizing: risk-budget × confidence (≤1.5×) × drawdown scale × vol
  target; liquidity cap 2% of bar ADV; **martingale structurally
  impossible** (no PnL-history input — tested).
- Live risk behavior observed in run: kill switch tripped on 6
  consecutive losses; 984 orders rejected pre-trade; vol_frac scaled
  to 0.586.

## 8. Backtesting methodology

Event-driven, multi-instrument; signals at close t → fills at open t+1
± (half-spread + slippage + impact(notional/ADV)) + commission; stops/
targets checked intrabar, stop-first on conflict; gap-through-stop at
next open when bars are missing (conservative); positions marked every
bar; risk engine embedded in the loop. Accounting identity
(final equity == initial + ΣPnL) is unit-tested. Costs: ~5.5 bps
one-way + commission ≈ 16–20 bps round trip at retail size (calibrated
to Schwarz 2025, JOFI: measured retail round-trip 7–46 bps).

## 9. Overfitting analysis

- **PBO (CSCV):** 15% across a 9-config trend sweep × 6 subperiods —
  "low", but only because all configs are uniformly weak (median Sharpe
  −0.13, frac>0 = 0%). Selection among noise is meaningless; reported as
  such.
- **Parameter stability:** plateau of uniformly weak performance, not a
  fragile spike — stable, but stable-wrong.
- **Perturbation stress:** ±15% parameter jitter → median Sharpe −0.06,
  10% positive.
- **Multiple-testing discipline:** experiment budget tracked in
  registries; no test-set tuning ever (OOS locked).

## 10. Walk-forward & out-of-sample

- WFA: 4 chronological splits with 24-bar embargo; parameters locked.
- IS (2018–2021): 78 trades, Sharpe 0.13, +2.9%.
- OOS (2022–2026): **8 trades, Sharpe −0.43, −2.8%** — insufficient
  sample, negative result. The strategy is **not approvable**.

## 11. Stress tests (synthetic, full table in artifacts)

| Shock | Return | Sharpe | MaxDD | Trades |
|---|---|---|---|---|
| baseline | +2.87% | 0.09 | −5.4% | 78 |
| costs ×2 | +2.59% | 0.08 | −5.5% | 78 |
| costs ×10 | +0.22% | 0.01 | −3.8% | 30 |
| slippage ×10 | −0.19% | −0.01 | −4.2% | 29 |
| vol ×1.5 | −1.03% | −0.06 | −4.1% | 33 |
| vol ×3 | 0.00% | n/a | 0% | 0 (risk-off) |
| liquidity ×0.1 | +2.85% | 0.09 | −5.4% | 78 |
| latency 6 bars | −0.72% | −0.03 | −4.1% | 26 |
| missing 1% random | +4.38% | 0.04 | **−20.3%** | 14 |
| missing 5% clustered | +2.87% | 0.09 | −5.4% | 78 |

Key findings: (a) the small edge is cost-fragile; (b) latency erodes it;
(c) extreme vol → the system correctly goes flat; (d) **missing data
creates gap-through-stop risk (−20% drawdowns)** — a real operational
hazard, mitigated by data-freshness kill switch and gap modeling.

## 12. Execution analysis

PaperBroker fills at next bar with realized slippage recording (5.5 bps
on demo orders); partial-fill simulation; failure injection (broker
unhealthy → REJECTED, tested); OrderValidator implements the full
pre-trade checklist (19 checks, unit-tested, incl. symbol validity,
spread, size, conflicts, duplicates, model approval, risk-engine state).
Broker abstraction (`BrokerInterface`) keeps research independent of any
broker.

## 13. Regime analysis

Regime engine (vol-percentile + normalized trend slope + CUSUM change
points) classified the synthetic chain into 11 labels. Regime gates
worked as filters (fewer, better trades), transition/uncertain bars
were vetoed by the meta engine. Drift: 1/33 stationary features PSI-
alerted (atr_14); performance-drift detector flagged win-rate drift.
Full regime×strategy interaction research remains Phase B.

## 14. Failure cases (red-team findings)

1. **Accounting bug found & fixed** during development (entry costs
   double-counted) — caught by the accounting-identity test.
2. **Cash booking bug** (shorts looked like −25% day) — caught by
   equity-trace debugging; regression-tested.
3. **Meta-confidence normalization** initially vetoed nearly all trades —
   fixed to active-weight normalization; tested.
4. **Gap-through-stop** under missing data: −20% drawdowns — modeled
   honestly, flagged as operational risk.
5. **8-trade OOS** — the strategy cannot be approved at this sample
   size, regardless of direction of the result.

## 15. Drawdown analysis

Max DD −5.4% (within the 10% limit; the kill switch prevented worse),
average DD −3.4%, but **max drawdown duration ≈ 69,359 bars** — the
equity curve never recovered to its first-year peak. This is the most
important single metric in this report: the strategy's losses were
small but persistent. Weekly std 0.28%, worst week −3.6%.

## 16. Strategy comparison & final architecture

No strategy earned deployment. The architecture (data → strategies →
meta → risk → validation → paper broker, with monitoring across all
layers) is the deliverable; the strategy slots are designed to be
filled only by evidence. Component-level verdicts: H05 meta gating —
keep (risk filter); H06 regime gates — keep (filter); H12/H13/H14/H15
risk & methodology — keep (validated).

## 17. Deployment readiness

- **Ready:** research pipeline, test suite, paper broker, registries,
  reporting, failure procedures (docs/failure_recovery.md).
- **Not ready / required before any real-data work:** real ingestion
  with corporate actions + delisted names; universe selection; locked-
  parameter rerun of the full ladder; random-entry null; benchmark
  comparisons; shadow mode.
- **Never without explicit authorization:** live trading. Brokerage
  age/identity requirements are not bypassed; the system stops and
  reports the requirement instead (docs/deployment.md).

## 18. Known weaknesses

1. Synthetic data only — no real-market evidence of anything.
2. ML at chance; feature set uninformative at hourly horizon.
3. OOS sample tiny (8 trades); long underwater periods.
4. No tick/order-book data; spread model approximates microstructure.
5. No event calendar; news not modeled.
6. Correlation-aware exposure caps not yet implemented (gross/net caps
   are the current backstop).
7. Monte Carlo ruin analysis not yet run.
8. Strategy weights are static config; automatic health-based weights
   are roadmap.
9. PBO only for the trend sweep; not yet wired to every experiment.

## 19. Future research

Full list in `docs/roadmap.md`. Priority: (1) real-data replication with
locked parameters; (2) random-entry null; (3) better labels
(triple-barrier, meta-labeling); (4) event engine; (5) horizon ladder;
(6) correlation-aware portfolio layer; (7) MC ruin analysis;
(8) shadow mode.

## 20. Final statements

- **Never claimed:** an edge, a 20% week, a profitable bot, or a
  validated strategy. None exists yet.
- **Claimed and evidenced:** a rigorous, tested, honest research
  framework; 335 answered research questions; a working risk-and-
  validation stack; and the explicit capability to conclude
  **"there is no sufficiently attractive trade right now"** — which is
  exactly what the current evidence supports.
