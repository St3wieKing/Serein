# Research Decision Log — 05 · Backtesting Questions (30)

**Q1.** Is a spectacular backtest proof of edge?
**A:** No — it is the starting point of an investigation, not the end.
Selection among many backtests manufactures winners (S04).
**Conf:** H. **Δ:** —.

**Q2.** What is the minimum realistic backtest standard?
**A:** Next-open fills, commission+spread+slippage+impact, intrabar stop
checking, position limits, risk engine in the loop, and full metric
reporting (all implemented).
**Conf:** H. **Δ:** —.

**Q3.** Should fills happen at candle close?
**A:** No — that assumes away costs and timing; our engine fills at next
open with slippage (tested).
**Conf:** H. **Δ:** —.

**Q4.** How should intrabar stop/target conflicts be resolved?
**A:** Stop-first (conservative) — if both hit in one bar, assume the
stop. Documented and tested.
**Conf:** H. **Δ:** —.

**Q5.** What happens if data is missing mid-trade?
**A:** Gap-through-stop modeling: fill at the next open (worse than
stop). Stress showed -20% drawdowns possible under 1% missing data —
honest and important.
**Conf:** H. **Δ:** —.

**Q6.** Should backtests include the risk engine?
**A:** Yes — a backtest without limits overstates everything; ours
embeds the full RiskEngine (tested: kill switches tripped in runs).
**Conf:** H. **Δ:** —.

**Q7.** Is in-sample performance ever reported alone?
**A:** Never — IS/OOS split and WFA are mandatory; the report prints both
and the difference.
**Conf:** H. **Δ:** —.

**Q8.** What is the role of the validation period?
**A:** Parameter/model selection; the test period stays locked. Any
peek invalidates the test.
**Conf:** H. **Δ:** —.

**Q9.** How long should the embargo be?
**A:** ≥ label horizon (6 bars used; 24 in WFA) — prevents overlap
leakage.
**Conf:** H. **Δ:** —.

**Q10.** Does walk-forward eliminate overfitting?
**A:** No — it reduces temporal leakage; selection over many WFA runs
still needs PBO accounting.
**Conf:** H. **Δ:** —.

**Q11.** How do we estimate PBO?
**A:** CSCV on the per-subperiod performance matrix (implemented,
tested on noise vs structure). Current sweep: PBO 15% (nothing to
select — all configs ~noise).
**Conf:** H. **Δ:** —.

**Q12.** Should parameter grids be exhaustive?
**A:** Exhaustive grids invite overfitting; small grids + stability
neighborhoods + perturbation tests are the practice.
**Conf:** M. **Δ:** —.

**Q13.** What does parameter stability look like?
**A:** A plateau of acceptable performance, not a spike. Our trend sweep:
median Sharpe -0.13, all configs similar (stable, but uniformly weak).
**Conf:** H. **Δ:** —.

**Q14.** Are stress tests proof of robustness?
**A:** They are falsification attempts; passing them is necessary, not
sufficient.
**Conf:** H. **Δ:** —.

**Q15.** Which cost shocks matter most?
**A:** 2x costs (plausible) and 5-10x (tail). Our ensemble: +2.9% at 1x,
+0.2% at 10x — cost-fragile.
**Conf:** H. **Δ:** —.

**Q16.** Should slippage be modeled as a fixed bps?
**A:** As a baseline yes; stochastic slippage and impact-by-size are
better; the cost model includes both (bps + impact term).
**Conf:** M. **Δ:** —.

**Q17.** Is the impact model (notional/ADV) realistic?
**A:** It is a first-order approximation; calibration on real fills is
required before live.
**Conf:** L-M. **Δ:** Paper-fill calibration.

**Q18.** How should latency be stress-tested?
**A:** Shift decisions by k bars (implemented: 1/3/6 bars). 6-bar delay
turned +2.9% into -0.7% — the edge (such as it is) is latency-sensitive.
**Conf:** H. **Δ:** —.

**Q19.** Should backtests use bid/ask data?
**A:** Where available, yes; OHLCV with spread model is the fallback
(current). Roadmap: trade-and-quote data.
**Conf:** M. **Δ:** —.

**Q20.** How do we test for survivorship bias?
**A:** Use point-in-time universes with delisted names; current synthetic
data has no delisting — flagged as a real-data requirement.
**Conf:** M. **Δ:** —.

**Q21.** Are Monte Carlo methods used as evidence?
**A:** As risk analysis (drawdown/streak distributions) only, never as
proof of returns. Ruin analysis is a roadmap item.
**Conf:** H. **Δ:** —.

**Q22.** What is the worst-case sequencing bound?
**A:** All-losses-first ordering gives an adversarial drawdown bound
(implemented, clearly labeled as a bound, not a simulation).
**Conf:** M. **Δ:** —.

**Q23.** Should we benchmark against buy-and-hold?
**A:** Yes — every strategy report should include the market benchmark;
synthetic data has no real benchmark — the OOS report on real data will.
**Conf:** H. **Δ:** —.

**Q24.** Are random entries a fair null?
**A:** Yes — random entries + same risk management is the correct null
for "does the signal add anything"; not yet implemented — roadmap.
**Conf:** H. **Δ:** —.

**Q25.** How many trades are needed for statistical trust?
**A:** Hundreds at minimum for expectancy; our OOS had 8 trades — 
insufficient; reported as such, strategy unapprovable at this sample.
**Conf:** H. **Δ:** —.

**Q26.** Should the same backtest be run on multiple seeds?
**A:** For synthetic data, yes (parameter/simulation noise); real data
needs multiple periods instead.
**Conf:** M. **Δ:** —.

**Q27.** Is the equity curve the right way to judge a strategy?
**A:** No — the full metric suite (drawdowns, streaks, tails, costs,
decomposition) is the way; the curve is one view.
**Conf:** H. **Δ:** —.

**Q28.** How do we detect a lucky config among many?
**A:** PBO + stability + OOS lock + perturbation tests; a lucky spike
fails at least one.
**Conf:** H. **Δ:** —.

**Q29.** Should backtest parameters ever be tuned on the OOS period?
**A:** Never — that period is locked; touching it voids the result.
**Conf:** H. **Δ:** —.

**Q30.** What makes a backtest result publishable?
**A:** Leakage audit pass + full metrics + costs + IS/OOS/WFA + stress +
PBO + sample size + provenance (data version, code commit, seed). The
reporting module assembles exactly this.
**Conf:** H. **Δ:** —.
