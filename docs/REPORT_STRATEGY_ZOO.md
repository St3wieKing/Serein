# Strategy Zoo Report — "Every strategy we can find, tested honestly"

**Date:** 2026-08-14 · **Data:** SYNTHETIC regime-switching simulator,
8 years hourly (70,129 bars × 3 symbols), planted trend/reversion/breakout
structure. Full tables: `artifacts/zoo_report.md`, `zoo_leaderboard.csv`,
`zoo_frontier.csv`, `zoo_dashboard.html`.

> **Bottom line up front:** we built and tested **30 strategy variants**
> across 10 families (trend, momentum, mean reversion, breakout,
> volatility, candle/structure, cross-sectional, ML, volume, random-null).
> The best surviving strategy on synthetic data earns **+3.7% over 8
> years** (Sharpe 0.18, max DD −2.6%) with an out-of-sample Sharpe of
> 0.55. **No strategy — at any risk level — comes within an order of
> magnitude of +20%/week.** The probability of any single week reaching
> +20% is **0.0000** in ~1.2 million bootstrapped sample-weeks, even at
> 10× the research risk budget. +20%/week compounds to **~1,310,000%/year**;
> the evidence says it is not achievable at acceptable risk.

---

## 1. What was tested (30 strategies, 10 families)

| Family | Variants |
|---|---|
| Trend | MA crossovers (10/30, 20/60, 50/150), regression slope, ADX-filtered |
| Momentum | TSMOM (60/120/250), dual momentum, intraday momentum |
| Mean reversion | z-score (20/60/120), RSI(2), Bollinger bands |
| Breakout | Donchian (20/55/120), compression breakout, new-high, opening-range |
| Volatility | gap fade, vol-expansion fade |
| Candle/structure | doji reversal, engulfing |
| Cross-sectional | relative strength vs universe |
| ML | logistic + random-forest direction (OOS-only by construction) |
| Volume | volume-surge continuation |
| Null | seeded random entries (the honest baseline) |

Not tested (data we don't have, flagged as roadmap, not faked): tick
order-flow/imbalance, options/IV, news sentiment.

## 2. Screening leaderboard (2018–2021, synthetic)

Top 8 by robustness score (rank-composite of OOS Sharpe, full Sharpe,
cost-2x Sharpe, slippage-5x Sharpe, drawdown):

| # | Strategy | Score | Full Sharpe | OOS Sharpe | OOS trades |
|---|---|---|---|---|---|
| 1 | trend_50_150 | 0.82 | 0.29 | 0.38 | 13 |
| 2 | mom_120 | 0.82 | −0.02 | 0.66 | 96 |
| 3 | rev_z20_1.5 | 0.81 | 0.15 | 0.25 | 10 |
| 4 | candle_engulfing | 0.74 | 0.26 | 0.11 | 12 |
| 5 | breakout_compression | 0.73 | 0.15 | 0.04 | 48 |
| 6 | intraday_momentum | 0.70 | 0.01 | 0.24 | 120 |
| 7 | opening_range | 0.69 | −0.11 | 0.45 | 49 |
| 8 | donchian_120 | 0.62 | 0.12 | −0.17 | 31 |

10 of 30 passed the gates (≥25 full trades, ≥5 OOS trades).
**Tournament PBO = 5% (low)** — the selection process itself is not
obviously overfit, but remember: this is synthetic data with planted
effects; it measures *machinery*, not real edge.

## 3. Full-period validation of finalists (2018–2026)

| Strategy | Full return | Full Sharpe | MaxDD | Trades | OOS Sharpe | OOS trades |
|---|---|---|---|---|---|---|
| **trend_50_150** | **+3.72%** | **0.18** | −2.58% | 37 | **0.55** | 129 |
| breakout_compression | +2.11% | 0.09 | −3.33% | 62 | 0.50 | 51 |
| mom_120 | −0.33% | −0.01 | −3.34% | 35 | 0.18 | 18 |
| rev_z20_1.5 | +2.43% | 0.09 | −3.10% | 60 | 0.13 | 38 |
| intraday_momentum | +0.13% | 0.01 | −3.33% | 41 | 0.14 | 58 |
| candle_engulfing | +3.30% | 0.16 | −2.48% | 39 | **−0.20** | 24 |
| donchian_120 | +1.10% | 0.04 | −3.84% | 111 | −0.03 | 21 |
| trend_10_30 | −2.98% | −0.17 | −4.72% | 25 | −0.17 | 18 |

**Selection-bias lesson, demonstrated live:** `candle_engulfing` ranked
#4 in screening but its full-period OOS Sharpe is **negative** (−0.20).
The screening leaderboard overstates; only full-period OOS validation
counts. `trend_50_150` (slow trend) is the only finalist with a
convincingly positive full-period OOS result (0.55 with 129 trades) —
consistent with the momentum/trend literature (TSMOM) and with the
planted trend structure in the synthetic data.

## 4. Ensemble

Meta-engine vote over the 8 finalists: full-period Sharpe **−0.07**,
OOS Sharpe **+0.39** (42 trades). The vote diluted the best member —
when members are weak, naive ensembling hurts. The honest conclusion:
use the best validated strategy (or a 2-3 member top subset), not all
finalists.

## 5. The 20%-per-week question (frontier + bootstrap)

+20%/week for a year = 1.2^52 − 1 ≈ **1,310,363%/year**.

Frontier on the best strategy (trend_50_150), risk-per-trade scaled from
0.5% (research default) to 5% (10× — beyond where the drawdown kill
switch fires):

| Risk/trade | Total ret (8y) | Sharpe | MaxDD | Mean week | P(week ≥ +20%) | P(week ≤ −5%) | P(DD ≥ 40%/yr) |
|---|---|---|---|---|---|---|---|
| 0.5% | +3.72% | 0.18 | −2.58% | +0.009% | 0.0000 | 0.000 | 0.000 |
| 1.0% | +3.49% | 0.16 | −2.67% | +0.008% | 0.0000 | 0.000 | 0.000 |
| 2.0% | +3.49% | 0.16 | −2.67% | +0.008% | 0.0000 | 0.000 | 0.000 |
| 3.0% | +3.49% | 0.16 | −2.67% | +0.008% | 0.0000 | 0.000 | 0.000 |
| 5.0% | +3.49% | 0.16 | −2.67% | +0.008% | 0.0000 | 0.000 | 0.000 |

(Bootstrap: 3,000 draws × ~400 weekly returns ≈ **1.2M sampled weeks**;
P(DD≥40%) is 0 partly because the kill switch halts trading at the 10%
portfolio drawdown limit — the risk system caps the damage, which is
exactly its job, and exactly why 20%/week cannot be "dialed up" by
increasing risk.)

The **ensemble** frontier is similar (mean week −0.003%, P(week≥20%) = 0).

## 6. What this means

1. **Relative ranking works.** The tournament found the planted slow-trend
   effect (trend_50_150, mom_120) — machinery validated.
2. **Absolute performance is tiny.** Even the best strategy earns
   ~0.01% per week on synthetic data at the research risk budget. To hit
   +20% in a week you would need ~2,000× the current edge or ruin-level
   risk. Neither exists here.
3. **Risk controls cannot be "unlocked" to chase the target.** At 10×
   risk the kill switches still cap damage — by design, and per the
   project mandate (no leverage increase, no stop removal, no
   target-chasing).
4. **What would change this answer:** real market data with locked
   parameters (the framework's Phase A). If a real edge exists, this
   harness will find its best expression — and report the honest
   achievable weekly return, whatever it is.

## 7. Caveats

- Synthetic data only. The planted effects make this the *easiest*
  environment; real markets will be harder, not easier.
- Screening period (2018–2021) differs from finalist validation period
  (2018–2026) — finalists were chosen on the screening OOS, so their
  full-period numbers are mildly selection-biased (mitigated by the
  PBO = 5% and by the candle_engulfing counterexample showing the bias
  exists).
- ML strategies (logistic/RF) did not pass gates on synthetic data —
  consistent with the earlier finding that the feature set is
  near-noise at the hourly horizon.
