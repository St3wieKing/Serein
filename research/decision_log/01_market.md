# Research Decision Log — 01 · Market Questions (40)

Format: **Q** / **A** (current best answer) / **Conf** (H/M/L) /
**Δ** (what experiment would change the conclusion).
Answers reflect evidence from `literature_notes.md` + `source_register.md`
and the synthetic experiments in `artifacts/research_report.md`.

**Q1.** Do financial markets have any exploitable inefficiency at all?
**A:** Academic consensus: some documented premia exist (momentum, value,
carry, short-term reversal), but after retail-scale costs most shrink or
vanish. Prior on retail-scale edge: strongly negative (S08/S09).
**Conf:** H. **Δ:** Real-data OOS replication with locked parameters.

**Q2.** What actually creates persistent predictive power?
**A:** Persistence (momentum/trend), slow-moving risk premia, and
behavioral/flow frictions; NOT indicator geometry. Power decays as capital
and speed compete (S01/S02).
**Conf:** H. **Δ:** —.

**Q3.** Which signals survive transaction costs?
**A:** Slow signals with large gross moves (multi-day/weeks) and low
turnover. Hourly signals at ~15-20bps round-trip need gross edge per trade
> ~0.4-0.6% to survive (S06).
**Conf:** H. **Δ:** Cost-sensitivity frontier per strategy.

**Q4.** Which signals only work during bull markets?
**A:** Long-only momentum and breakout variants degrade in bear/flat
regimes; TSMOM's long side dominates its returns (S01). Short-side
efficiency is asymmetric.
**Conf:** M-H. **Δ:** Regime-conditioned decomposition (implemented in
decompositions by regime).

**Q5.** Which signals reverse during high-volatility regimes?
**A:** Intraday mean reversion tends to fail (gaps dominate); breakout
failures multiply; trend can work if vol is trending, not choppy.
**Conf:** M. **Δ:** Regime-split backtests per strategy.

**Q6.** How much edge remains after slippage?
**A:** In our synthetic full run: ~0 (Sharpe 0.09 gross-of-realism
inclusive). In literature, institutional TSMOM survives modestly (S01);
retail replication rarely does (S06, S09).
**Conf:** H for "little". **Δ:** Paper trading with fill data.

**Q7.** What happens when spreads widen?
**A:** Turnover-heavy strategies die first; per-trade EV shrinks by spread
× 2 × turnover. Q3-2025 stress showed 3x spread widening in 48h (S07).
**Conf:** H. **Δ:** Spread-shock stress (implemented).

**Q8.** What happens during market open?
**A:** Wide spreads, high volume, gaps, auction dynamics; open-based
signals are noisier and costlier. No assumption — session decomposition is
computed, not assumed (decompose by session is a roadmap item).
**Conf:** M. **Δ:** Session-split decomposition on real data.

**Q9.** What happens during market close?
**A:** Volume spikes, benchmark-driven flows, wider impact for size;
intraday strategies that hold through close pay overnight risk.
**Conf:** M. **Δ:** Session analysis.

**Q10.** What happens during economic announcements?
**A:** Vol spikes, spreads widen, liquidity thins briefly, price jumps;
event-avoidance is a reasonable default until tested (H11 deferred).
**Conf:** M. **Δ:** Event engine with timestamped calendar.

**Q11.** What happens during unexpected news?
**A:** Gaps through stops; models trained on smooth data are wrong;
kill-switch + flat bias is the safe default.
**Conf:** H. **Δ:** —.

**Q12.** What happens during flash crashes?
**A:** Liquidity vanishes; stop orders fill far from stop; only structural
protection (position caps, no-leverage, kill switches) helps.
**Conf:** H. **Δ:** Stress data with tail events.

**Q13.** Is the market weakly efficient at the hourly horizon?
**A:** Mostly, for liquid names; residual predictability is small and
regime-dependent. Hourly ML on our 41 features: AUC≈0.50 OOS (chance).
**Conf:** H. **Δ:** Better labels/features on real data.

**Q14.** Does volatility clustering create tradable structure?
**A:** Yes, it's the most robust stylized fact (S14) — useful for regime
filters and sizing, not for direction.
**Conf:** H. **Δ:** —.

**Q15.** Are cross-sectional relative moves more predictable than absolute?
**A:** Relative momentum/mean reversion are documented (S03); absolute
direction is harder. Our synthetic universe is isolated → untested here.
**Conf:** M. **Δ:** Multi-asset real data (H10).

**Q16.** Do intraday seasonalities (first/last hour) persist?
**A:** Documented patterns exist (U-shaped volume/vol) but their tradable
size after costs is disputed. INCONCLUSIVE for us.
**Conf:** L-M. **Δ:** Session ablation (done on synthetic: weak).

**Q17.** How do correlations behave in stress?
**A:** They rise toward 1 (diversification fails exactly when needed);
correlation-based sizing must assume regime-correlation, not average.
**Conf:** H. **Δ:** Correlation stress scenario.

**Q18.** Does retail order flow create exploitable imbalance?
**A:** Possibly intraday (literature mixed; requires tick/level-2 data we
do not have). Not adopted.
**Conf:** L. **Δ:** Requires new data source — deferred.

**Q19.** Are small caps / illiquid names better or worse for this system?
**A:** Worse: wider spreads, thinner books, more gap risk, less reliable
data. Universe selection excludes them by construction (liquidity gates).
**Conf:** H. **Δ:** —.

**Q20.** Do earnings gaps invalidate swing positions?
**A:** Yes — overnight/event gaps dominate swing P&L tails; the system
must either avoid holding through known events or price the gap.
**Conf:** H. **Δ:** Event-aware backtest.

**Q21.** Is there a weekday effect worth trading?
**A:** Documented but tiny and unstable; not worth the costs.
**Conf:** L-M. **Δ:** Day-of-week ablation (feature exists).

**Q22.** How long do regimes last?
**A:** Days to months; hourly regime labels are noisy at the boundary.
Our CUSUM flags transitions; we treat transition bars as untradeable.
**Conf:** M. **Δ:** Regime persistence statistics on real data.

**Q23.** Is high volatility bullish or bearish on average?
**A:** Neither — it amplifies; direction must come from other evidence.
**Conf:** H. **Δ:** —.

**Q24.** Does the VIX/index tell us about single-name tradability?
**A:** Broadly yes (vol regime and liquidity proxy), but only as a filter.
**Conf:** M. **Δ:** Cross-asset features (H10).

**Q25.** Are trending markets the majority of time?
**A:** No — sideways/transition dominates in most samples; trend systems
therefore idle most of the time (our meta: ~27% active bars, 78 trades in
8 years).
**Conf:** M. **Δ:** Regime duration stats.

**Q26.** Does volume confirm price moves?
**A:** Weakly, in aggregate; per-bar volume is noisy. Volume features had
the largest (still small) ablation delta on synthetic.
**Conf:** M. **Δ:** Volume ablation on real data.

**Q27.** Are breakouts real or liquidity artifacts?
**A:** Both: some breakouts are information, many are stop-hunts; no
reliable way to distinguish at bar granularity. Net: low prior.
**Conf:** M. **Δ:** Breakout event study on real data.

**Q28.** Is mean reversion stronger intraday or multi-day?
**A:** Literature: short-term reversal is strongest at very short horizons
(tick/minute), weaker at hourly+. Our z-reversion at hourly was weak.
**Conf:** M. **Δ:** Horizon sweep.

**Q29.** Do gaps predict continuation or reversal?
**A:** Mixed; gap-and-go vs gap-fade depends on context (volume, size).
INCONCLUSIVE. Features exist; not traded directly.
**Conf:** L-M. **Δ:** Gap event study.

**Q30.** How does market structure (auction vs continuous) affect us?
**A:** Bar data hides auctions; open fills assume continuous trading — a
modeling simplification with real cost. Documented, not solved.
**Conf:** M. **Δ:** Use open-auction-aware data.

**Q31.** Is short selling as profitable as longing?
**A:** No — asymmetry documented (short side weaker/harder). Our
decomposition reports long vs short separately; never merged.
**Conf:** M. **Δ:** Long/short decomposition (implemented).

**Q32.** Do liquid ETFs behave differently from single stocks?
**A:** Tighter spreads, more efficient, less idiosyncratic drift —
harder for alpha, easier for execution. Universe question.
**Conf:** M. **Δ:** Multi-instrument real tests.

**Q33.** What is the effective capacity of a strategy like ours?
**A:** Small: with 0.5-2% ADV participation, hourly strategies on liquid
names cap at low single-digit $mm before impact dominates.
**Conf:** M. **Δ:** Impact model calibration.

**Q34.** Do fundamentals/news add hourly predictive power?
**A:** For liquid names, mostly priced within seconds-minutes; the drift
window is thin. Not adopted without evidence.
**Conf:** M. **Δ:** News-feature ablation.

**Q35.** Are there structural events (rebalancing, expiry, month-end) worth
knowing?
**A:** Yes — flows cluster; but edge is small and crowded.
**Conf:** L-M. **Δ:** Calendar features.

**Q36.** Does liquidity vary predictably within the day?
**A:** Yes (U-shape); sizing should scale with expected liquidity —
implemented via bar-ADV caps per fill.
**Conf:** M. **Δ:** —.

**Q37.** What does "risk-on/risk-off" add beyond vol/trend?
**A:** It is largely a restatement of vol + cross-asset trend; marginal
value is small for single-name hourly systems. INCONCLUSIVE.
**Conf:** L. **Δ:** Factor construction + ablation.

**Q38.** Are emerging markets / FX better hunting grounds?
**A:** TSMOM found stronger effects in less liquid markets (S01/S03) but
costs/borrow/data risks scale too. Out of current scope.
**Conf:** M. **Δ:** New market adapter.

**Q39.** How much of equity-index hourly variance is explainable?
**A:** Very little at hourly horizon (R² < 1-3% for direction models).
This sets the ceiling for any hourly ML.
**Conf:** H. **Δ:** —.

**Q40.** What market conditions make ALL strategies correlated?
**A:** Liquidity-stress/vol-expansion regimes (S07, S17). The portfolio
layer assumes correlation spikes in stress and caps correlated exposure.
**Conf:** H. **Δ:** Correlation stress test.
