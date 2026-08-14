# Research Decision Log — 02 · Strategy Questions (50)

**Q1.** Is there a universally best strategy?
**A:** No. Different families own different regimes. The system is an
ecosystem, not a single strategy. **Conf:** H.

**Q2.** Does trend following actually work after costs?
**A:** Documented at monthly horizons institutionally (S01); contested at
asset level (S02); at hourly retail scale, prior is low. Our synthetic
trend: expectancy ≈ +0.09R full period, negative OOS. INCONCLUSIVE.
**Conf:** M. **Δ:** Real-data WFA with locked defaults.

**Q3.** Does momentum persistence survive hourly granularity?
**A:** Weaker than monthly TSMOM; hourly momentum partially reflects
vol-clustering artifacts (S02's critique applies a fortiori).
**Conf:** M. **Δ:** Horizon ladder experiments.

**Q4.** Does mean reversion add value in an ensemble with trend?
**A:** Diversification yes (opposite-sign families, S03's −0.46 value/
momentum corr analog), but each family must pass individually.
**Conf:** M. **Δ:** Correlation of strategy returns.

**Q5.** Do breakouts need volume confirmation?
**A:** Volume confirmation reduces false positives but also cuts the
strongest (news) breakouts. Net: neutral-to-positive filter.
**Conf:** L-M. **Δ:** Ablation with/without vol confirm.

**Q6.** Are ATR-based stops better than percentage stops?
**A:** ATR adapts to vol regime; percentage stops are regime-blind.
ATR chosen; not sacred — test both.
**Conf:** M. **Δ:** Stop-method comparison.

**Q7.** Is a 2R target with 2×ATR stop sensible?
**A:** As a starting point, yes; the market decides the realized payoff.
Our realized payoff ≈ 1.8 — worse than 2.0 assumption → targets rarely
fully reached; exit research needed.
**Conf:** M. **Δ:** Target-multiple sweep.

**Q8.** Should stops be at structure (S/R) instead of ATR?
**A:** Structure stops are less mechanical and harder to validate; ATR is
reproducible. Structure-based exits are a challenger idea.
**Conf:** M. **Δ:** Structure-exit challenger.

**Q9.** Are trailing stops better than fixed targets?
**A:** For trends yes, for mean reversion no. Currently: fixed target +
time exit; trailing is a roadmap item (profit-protection research).
**Conf:** M. **Δ:** Trailing-stop variant backtest.

**Q10.** Does time-based exit help or hurt?
**A:** Helps control capital rotation and stale positions; hurts if the
edge needs more time. 120-bar cap on hourly ≈ 2.5 weeks. Fine as bound.
**Conf:** M. **Δ:** Holding-time optimization.

**Q11.** Should the system trade both directions symmetrically?
**A:** No — measured asymmetry (Q31 market log). Tested separately,
sized the same, judged separately.
**Conf:** M. **Δ:** —.

**Q12.** Do multiple confirmations (trend+momentum) actually improve odds?
**A:** Only if the signals are partially independent; identical-input
"confirmations" are one signal. Our meta treats agreement as
risk-reduction, not evidence multiplication.
**Conf:** M. **Δ:** Prediction-correlation audit of strategies.

**Q13.** Is "no trade" ever the wrong choice?
**A:** Sometimes a missed trade, never a blown account. Flat is the
default state.
**Conf:** H. **Δ:** —.

**Q14.** Should strategies be weighted by recent performance?
**A:** Yes, slowly and with statistical thresholds; fast weighting chases
noise (see adaptation log). Current: equal-ish weights, drift detection
active.
**Conf:** M. **Δ:** Weight-schedule experiment.

**Q15.** Do regime gates improve or just reduce trades?
**A:** On synthetic they mostly reduce trades (fewer, better-filtered);
the improvement in per-trade quality was real but small.
**Conf:** M. **Δ:** Gate on/off ablation.

**Q16.** Is expected_R a useful gating variable?
**A:** It gates out low-edge setups cheaply; its absolute calibration is
weak. Used as a relative filter.
**Conf:** M. **Δ:** Calibration of expected_R vs realized R.

**Q17.** How should confidence map to size?
**A:** Linearly within caps (0.52 floor → 1.5x max); never above risk
budget. Martingale impossible by construction.
**Conf:** H (safety), M (optimality). **Δ:** Size-vs-confidence study.

**Q18.** Does the ensemble need a meta-model (ML) on top?
**A:** Not yet — a transparent weighted vote with gates beats an opaque
stack until features prove predictive (ML AUC≈0.50).
**Conf:** M. **Δ:** Meta-model challenger after feature improvement.

**Q19.** Are strategy returns decorrelated enough to combine?
**A:** On synthetic, yes in sign but all are weak; true test needs real
data and prediction-correlation measurement.
**Conf:** M. **Δ:** Correlation matrix of strategy returns.

**Q20.** Should we ever trade against the meta (contrarian)?
**A:** Only if a validated strategy explicitly encodes it; never as a
"fade the system" override.
**Conf:** H. **Δ:** —.

**Q21.** Is intraday momentum (1-6h) distinct from swing momentum?
**A:** Different drivers (flow vs information); treat as separate engines.
Intraday engines not yet built — roadmap.
**Conf:** M. **Δ:** Build + test intraday engine.

**Q22.** Does the opening range predict the day?
**A:** Practitioner staple; evidence mixed. Not adopted.
**Conf:** L-M. **Δ:** Opening-range study.

**Q23.** Is VWAP-deviation mean reversion tradable?
**A:** For market makers; retail costs eat it. Feature exists
(dist_vwap_40); not traded directly.
**Conf:** L-M. **Δ:** VWAP reversion backtest.

**Q24.** Should we fade extremes (z>2) or trade continuation?
**A:** Both exist; they conflict. Resolution: regime gate decides which
family is allowed (trend in trends, reversion in ranges).
**Conf:** M. **Δ:** Regime×strategy interaction test.

**Q25.** Does the system need news sentiment at all?
**A:** Not until it demonstrates incremental OOS value; currently it
avoids events instead of predicting them.
**Conf:** M. **Δ:** Sentiment ablation with quality-controlled feed.

**Q26.** Is there value in multi-timeframe confirmation?
**A:** Plausible (trend on slow TF, entry on fast TF) but adds latency;
currently single-TF hourly with slow features acting as implicit higher TF.
**Conf:** M. **Δ:** Multi-TF variant.

**Q27.** Should each trade carry a "strategy owner"?
**A:** Yes — ownership enables attribution, retirement, and journaling.
Implemented via reason field + decomposition.
**Conf:** H. **Δ:** —.

**Q28.** Do partial profit-taking exits beat all-or-nothing?
**A:** Reduces variance, caps winners; literature mixed. Not implemented;
roadmap (profit-protection research).
**Conf:** L-M. **Δ:** Partial-exit backtest.

**Q29.** Is a fixed risk/reward target better than dynamic?
**A:** Fixed is testable and disciplined; dynamic adds parameters.
Stay fixed until evidence says otherwise.
**Conf:** M. **Δ:** Dynamic target variants.

**Q30.** Should the system trade through high-impact events?
**A:** Default: no (event-avoidance); test later with an event engine.
**Conf:** M. **Δ:** Event engine phase.

**Q31.** Is short-term reversal a source of edge for us?
**A:** Documented at minute scales (market making); at hourly, weak.
**Conf:** L-M. **Δ:** Minute-data study.

**Q32.** Do we need position-level trailing invalidation (structure)?
**A:** Nice-to-have; ATR stop + time exit covers the main failure modes
now. Challenger idea.
**Conf:** L-M. **Δ:** —.

**Q33.** Should entries require a pullback (limit entry) instead of market?
**A:** Limit entries save spread but risk non-fill; for hourly signals the
fill risk dominates. Market-at-open chosen; limit-entry variant is a
challenger.
**Conf:** M. **Δ:** Limit-fill simulation.

**Q34.** Is it better to enter on close or next open?
**A:** Next-open with costs is the honest standard; close-fill assumes
away liquidity. Keep next-open.
**Conf:** H. **Δ:** —.

**Q35.** Should one strategy's losses disable others?
**A:** No — portfolio-level and per-strategy diagnostics are separate;
retirement requires statistical evidence (Q43), not a bad day.
**Conf:** H. **Δ:** —.

**Q36.** Do winning streaks warrant increased size?
**A:** No — confidence-based sizing only; streaks are noise until
proven otherwise (and no pnl-input path exists).
**Conf:** H. **Δ:** —.

**Q37.** Do losing streaks warrant decreased size?
**A:** Yes, via drawdown scaling + consecutive-loss halt (implemented).
**Conf:** H. **Δ:** —.

**Q38.** Should strategies be re-validated on a schedule or on triggers?
**A:** Triggers (drift, regime change, performance degradation) + fixed
milestones; never after a single week.
**Conf:** M. **Δ:** Trigger sensitivity study.

**Q39.** Is a 31% win-rate / 1.8 payoff profile acceptable?
**A:** Only if expectancy is positive after costs. Our synthetic full-run:
+0.09R — marginal. Acceptability gate is expectancy, not win rate.
**Conf:** H. **Δ:** —.

**Q40.** Should we optimize win rate or expectancy?
**A:** Expectancy and tail control. 90% win / 0.15R is worse than 45% /
2.5R (mandate example) — the metrics suite reports both.
**Conf:** H. **Δ:** —.

**Q41.** How many strategies are enough?
**A:** As many as survive validation with independent signal sources; 3-6
is a sane target. Current: 4 families.
**Conf:** M. **Δ:** —.

**Q42.** Is there an edge in trading the same signal on multiple symbols?
**A:** Diversification yes, alpha no; correlated symbols must be capped
as one exposure (portfolio layer).
**Conf:** H. **Δ:** Correlation-aware sizing test.

**Q43.** When is a strategy statistically dead?
**A:** Rolling expectancy/wr drift + regime incompatibility + sufficient
sample; CUSUM-based detection implemented (drift.py). Never one bad week.
**Conf:** M. **Δ:** False-positive rate of the drift detector.

**Q44.** Can a retired strategy come back?
**A:** Yes, but it must pass the full gate again (resurrection rule).
**Conf:** H. **Δ:** —.

**Q45.** Should strategies know their own health score?
**A:** Yes — weights, gates, and journaling use the health score; it is
computed from OOS/live metrics, not from IS backtests.
**Conf:** M. **Δ:** —.

**Q46.** Is a strategy that only trades 8 times in 4 OOS years useful?
**A:** Not with confidence — sample too small; such a strategy cannot be
approved regardless of return. OOS gate includes minimum sample.
**Conf:** H. **Δ:** —.

**Q47.** Does the system need an explicit "challenger queue"?
**A:** Yes — model governance (champion/challenger) is a stated
requirement; registry supports it; the research loop feeds it.
**Conf:** H. **Δ:** —.

**Q48.** Are simpler strategies preferred when equivalent?
**A:** Yes — parsimony rule; complexity must buy measured OOS value.
**Conf:** H. **Δ:** —.

**Q49.** Should the strategy set adapt to detected regime shifts?
**A:** Yes, through weights + gates, with hysteresis to avoid flapping.
**Conf:** M. **Δ:** Regime-shift replay test.

**Q50.** What is the single most important strategy-level rule?
**A:** No trade is required to exist. The system must be comfortable
concluding "no sufficiently attractive trade".
**Conf:** H. **Δ:** —.
