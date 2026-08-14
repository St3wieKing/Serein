# Serein Strategy v2.0 — research, destruction, simplification, rebuild

> **Superseded performance artifact:** generated before the 2026-08-14 exit-fill
> slippage accounting correction. Architecture conclusions remain useful, but
> numerical returns must be regenerated and are not current evidence.

**Date:** 2026-08-14  
**Status:** PAPER_TRADING_ONLY · **Decision: NO CANDIDATE APPROVED**  
**Evidence boundary:** latest v2 experiment is synthetic (26,500 hourly bars ×
3 symbols). It validates implementation, not a real-market edge.

## Part 1 — Research

The strongest reusable evidence supports slow momentum/trend as a broad prior,
volatility clustering as a risk/context fact, realistic costs as a first-order
constraint, and strict controls against data snooping. It does **not** prove that
an hourly retail strategy has positive expectancy. See
`research/literature_notes.md`, `source_register.md`, and
`trading_book_analysis.md`.

## Part 2 — Trading book analysis

Books were converted into hypotheses rather than authority. The useful common
core is: testable market context, a small number of setups, explicit
invalidation, expectancy in R, fixed fractional risk, and disciplined review.
The complete source→mechanism→test→failure table is in
`research/trading_book_analysis.md`.

## Part 3 — Matthew Scriv analysis

Public material supports only that Scriv discusses pre-marked levels, explicit
entries/exits and a repeatable model, and says he does not use trend lines.
Public profit displays are unaudited. Anonymous claims about “Chrome,” OTE,
IFVG, ICT or liquidity are Tier-5 claims. Serein neither copies nor pretends to
know proprietary rules. See `research/matthew_scriv_analysis.md`.

## Part 4 — Strategy component library

Twelve objective components are catalogued in
`research/component_library_v2.md`: trend context, pullback, continuation
trigger, structural stop, volatility, volume, compression, range break, failed
break, VWAP deviation, R target, and NO_TRADE. Missing-data concepts—news,
order flow, options, breadth—are not approximated.

## Part 5 — Experiment results

Mandatory simplification:

- A: trend + pullback + trigger + volatility + volume + structural stop;
- B: A without volume;
- C: B without volatility;
- D: pullback + trigger + structural stop only.

Independent challengers test compression breakout, failed breakout, and VWAP
reversion. Every candidate received the same risk engine, next-open fills,
costs, chronological 60/40 split, 2×/5× costs, and 5× slippage.

Quick results:

| Candidate | Simplicity | Trades | Full return | OOS Sharpe | OOS trades | 2× cost Sharpe | 5× slip Sharpe |
|---|---:|---:|---:|---:|---:|---:|---:|
| A full | 0 | 11 | −2.42% | +0.85 | 95 | −0.46 | −0.53 |
| Compression breakout | 58 | 56 | +3.17% | +0.56 | 21 | +0.24 | +0.16 |
| C +trend | 36 | 8 | −1.09% | −0.14 | 29 | −0.28 | −0.35 |
| B no volume | 19 | 8 | −1.09% | −0.18 | 27 | −0.28 | −0.35 |
| Failed breakout | 68 | 38 | +1.01% | −0.37 | 8 | +0.09 | −0.13 |
| VWAP reversion | 64 | 22 | +0.26% | −0.37 | 18 | +0.02 | −0.21 |
| D core | 60 | 8 | −1.24% | −0.93 | 7 | −0.31 | −0.37 |

A's isolated OOS result does not rescue it: the full run lost money, the
in-sample Sharpe was −0.57, both stressed full runs were negative, and the Risk
Engine halted it. Compression is more stable but has only 21 OOS trades and
fails the 25-trade gate. Neither is approved. The fact that OOS can contain more
trades than full is expected here: each OOS test starts with a fresh risk state,
whereas a full-period kill switch can halt later entries. Full generated table:
`artifacts/rebuild_report.md`.

## Part 6 — Rejected ideas

- Indicator accumulation/confluence: rejected as redundant unless incremental
  OOS value is shown.
- Direct ML direction: prior AUC ≈0.50; rejected at the current feature set.
- A full strategy: volume/volatility complexity did not rescue OOS performance.
- VWAP and failed breakouts: negative quick OOS; rejected for this specification.
- Scriv/Athena/influencer profit claims: unusable as performance evidence.
- ICT/SMC labels: translated only when objective; terminology is not causality.

## Part 7 — Final strategy

There is no approved final alpha strategy. The **paper challenger specification**
remains simple:

> In a directional context, wait for a pullback that preserves the slow trend.
> Enter next bar only after price closes beyond the prior bar in the trend
> direction. Place the stop beyond the pullback swing, size from that distance,
> and use a predeclared R target. If any condition or risk gate fails, do nothing.

This is a research candidate, not a claim that it works.

## Part 8 — Mathematical specification

For close `C`, high `H`, low `L`, ATR14 `A`, EMA20 `F`, EMA60 `S`:

```text
long_context(t)  = F_t > S_t and S_t - S_(t-5) > 0
long_pullback(t) = L_(t-1) <= F_(t-1) + 0.25 A_(t-1)
                   and C_(t-1) >= S_(t-1)
long_trigger(t)  = C_t > H_(t-1)
long_signal(t)   = context and pullback and trigger and optional gates
long_stop(t)     = min(L_(t-4)..L_t) - 0.10 A_t
risk(t)          = C_t - long_stop(t)
target(t)        = C_t + k risk(t), k predeclared
```

Short rules are sign-symmetric. Decision is at close `t`; fill is next open.
If the open gaps beyond stop or target, the order is rejected. Every rolling
quantity is trailing/causal and truncation-tested.

## Part 9 — Risk system

Risk Engine authority is unchanged: 0.5% research risk/trade, volatility and
drawdown scaling, 25% symbol notional cap, 2% bar-volume cap, no leverage,
daily/weekly/drawdown/consecutive-loss limits, and fail-closed kill switches.
Sizing uses the actual structural stop distance. No PnL-chasing input exists;
martingale and revenge sizing are structurally absent.

## Part 10 — Backtesting results

Results above include commission, spread, slippage, impact, next-open execution,
stop-first ambiguous bars, missing-bar gap stops, and exact cash accounting.
They are poor. That is the result, not a defect to hide.

## Part 11 — Walk-forward results

Four locked-rule windows for the top isolated-OOS candidate had 55, 27, 22,
and 117 trades. Returns were −0.27%, +2.15%, −1.06%, and −2.95%; Sharpes were
−0.05, +0.62, −0.37, and −0.47. The instability directly contradicts a
repeatable edge. Verdict: **REJECT current specification**.

## Part 12 — Out-of-sample results

A produced positive OOS performance in isolation but failed full-period,
in-sample, cost, slippage, and kill-switch consistency. B–D were negative OOS.
Compression was positive but had only 21 OOS trades. No candidate passes the
complete gate set: sufficient OOS sample, OOS Sharpe, positive stressed full
performance, no risk breach, real point-in-time replication, and paper
observation. Viewing these results means this synthetic split is no longer
pristine.

## Part 13 — Stress tests

2× and 5× cost and 5× slippage tests are recorded for every candidate.
Compression remained positive under the recorded shocks but lacked enough OOS
trades. A looked positive only in isolated OOS; its full stressed Sharpes were
negative. B–D were negative, and failed-breakout/VWAP deteriorated under high
stress. Existing system
stress also covers latency, missing data, volatility, liquidity and parameter
perturbation.

## Part 14 — Robustness

Causality, structural-level direction, deterministic output, accounting and risk
paths are tested. 108 tests pass and one is skipped. Statistical robustness is
not established: real cross-symbol, regime, parameter, and never-tuned holdout
replication remain mandatory.

## Part 15 — Simplicity analysis

The score penalizes rule, parameter, indicator, dependency and execution count.
D is simpler than C, C than B, and B than A. A scored lowest and performed
poorly. Nothing supports keeping volume. The simplest core also failed, so
simplicity cannot manufacture edge; it only makes failure easier to see.

## Part 16 — Final architecture

```text
point-in-time data → validation → context → setup → trigger
→ objective stop/target → NO_TRADE gate → Risk Engine
→ next-open paper execution → management → audit → challenger review
```

The alpha layer cannot bypass Risk Engine authority. Optional structural levels
extend the signal contract without breaking ATR/R fallback behavior.

## Part 17 — Remaining weaknesses

1. Synthetic data, including planted effects.
2. No real exchange-session calendar in the quick test.
3. No point-in-time universe, tick/L2, news, options, breadth, borrow, or halts.
4. Tiny OOS trade counts.
5. No pristine real holdout.
6. R targets and structural stops need a broad, predeclared sweep.
7. Strategy selection still creates multiple-testing risk.
8. No live adapter; paper only.

## Part 18 — Next research cycle

1. Acquire lawful point-in-time data with exchange sessions and lock a holdout.
2. Freeze A–D and challenger parameters before loading it.
3. Add random/slow-trend/buy-hold controls under matched risk.
4. Run 1/1.5/2/2.5/3/4R and ATR/structural/time exits as a declared factorial
   experiment with PBO/deflated-Sharpe reporting.
5. Test parameter neighborhoods and block-bootstrap confidence intervals.
6. Reject anything below gates; paper-shadow only if a challenger survives.

The 335-question decision log still passes validation, and another 100-question
red-team review is in `research/adversarial_100.md`.
