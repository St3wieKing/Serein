# Research Decision Log — 03 · Risk Questions (40)

**Q1.** What is the maximum amount of capital one position may expose?
**A:** 25% of equity notional (per-symbol cap) with ≤0.5-1% equity at risk
per trade — two independent ceilings.
**Conf:** H. **Δ:** Risk-budget sensitivity study.

**Q2.** How many correlated positions may exist simultaneously?
**A:** Gross exposure ≤100%, net ≤80%, max 5 positions, per-symbol ≤25%;
correlated-exposure cap is a roadmap item (factor-aware).
**Conf:** M. **Δ:** Correlation-aware exposure limits.

**Q3.** How does the system recognize correlation explosions?
**A:** Not yet (portfolio-level correlation monitor is roadmap); stress
tests assume worst-case correlation.
**Conf:** L-M. **Δ:** Rolling correlation monitor.

**Q4.** Does diversification reduce risk under stress?
**A:** Less than models assume — correlations rise in stress; caps must
assume stress-correlation, not average.
**Conf:** H. **Δ:** Stress correlation scenario.

**Q5.** What happens when every asset moves together?
**A:** The portfolio behaves like one big position; gross/net caps are the
backstop. No assumption of diversification benefit.
**Conf:** H. **Δ:** —.

**Q6.** Should the system trade or remain flat in a crisis?
**A:** Flat-first: volatility kill + drawdown kill + event avoidance.
**Conf:** H. **Δ:** —.

**Q7.** How should confidence influence position size?
**A:** Linearly from a floor to a max multiplier (1.5x), inside the risk
budget. Confidence can never raise the risk ceiling.
**Conf:** H (safety), M (shape). **Δ:** Size-vs-outcome study.

**Q8.** How should uncertainty influence position size?
**A:** Disagreement/regime-uncertainty gates cut size to zero or half
(meta layer). Calibration ECE also feeds a confidence haircut (roadmap).
**Conf:** M. **Δ:** Calibration-linked sizing.

**Q9.** How should drawdown influence position size?
**A:** Linear scaling to zero at 100% of the DD limit + hard kill switch
at the limit. Never increases after losses.
**Conf:** H. **Δ:** —.

**Q10.** How should volatility influence position size?
**A:** Vol targeting (√(target/realized) scaling, clipped 0.25-1.5x) —
implemented and active (vol_frac in runs).
**Conf:** M. **Δ:** Vol-target constant choice.

**Q11.** How should liquidity influence position size?
**A:** Hard cap at 2% of bar dollar-volume; order validator rejects
beyond. Impact model charges the rest.
**Conf:** H. **Δ:** —.

**Q12.** How should spread influence position size?
**A:** Spread gate (≤30bps) at validation; size does not scale with spread
yet — a cheap improvement (roadmap).
**Conf:** M. **Δ:** Spread-scaled sizing.

**Q13.** What is the daily loss limit?
**A:** 2% of day-start equity → halt for the day (configurable).
**Conf:** H. **Δ:** —.

**Q14.** What is the weekly loss limit?
**A:** 4% of week-start equity → halt (configurable).
**Conf:** H. **Δ:** —.

**Q15.** What is the maximum portfolio drawdown?
**A:** 10% from peak → drawdown kill switch + liquidation (configurable).
**Conf:** H. **Δ:** —.

**Q16.** What is the maximum leverage?
**A:** 1.0 (no leverage) — paper system; hard-coded in limits.
**Conf:** H. **Δ:** —.

**Q17.** What is the emergency equity floor?
**A:** 80% of starting equity → forced flat + halt.
**Conf:** H. **Δ:** —.

**Q18.** Should consecutive losses halt trading?
**A:** Yes — 6 consecutive losses trip the drawdown kill (configurable).
**Conf:** M. **Δ:** Threshold sensitivity.

**Q19.** Is a 1% risk-per-trade budget safe?
**A:** For a diversified 5-position portfolio: worst-case daily ~5-10%
before halts — acceptable for research; 0.5% default for research mode.
**Conf:** M. **Δ:** Monte Carlo ruin study.

**Q20.** What is the probability of ruin under the current risk system?
**A:** Not yet computed properly — Monte Carlo ruin analysis is a
roadmap item; the structural caps (no leverage, kill switches, daily/
weekly limits) make ruin unlikely but not impossible.
**Conf:** L-M. **Δ:** Monte Carlo + bootstrap analysis.

**Q21.** Should risk limits ever be relaxed?
**A:** Only by explicit operator config change with audit; never by a
model, never automatically after losses.
**Conf:** H. **Δ:** —.

**Q22.** Who wins if the model and risk engine disagree?
**A:** The risk engine, structurally (check_entry is the only gate; a
rejection is logged and the order dies).
**Conf:** H. **Δ:** —.

**Q23.** What happens when the model says confidence=99%?
**A:** Size scales to 1.5x of the risk budget — nothing more. The risk
engine treats 99% as a claim, not a fact (calibration ECE reported).
**Conf:** H. **Δ:** —.

**Q24.** Should the system size by Kelly?
**A:** Fractional Kelly is the theoretical baseline; our risk-per-trade
sizing is a conservative cousin (≈1/8-1/4 Kelly given estimates).
**Conf:** M. **Δ:** Kelly-estimate comparison.

**Q25.** Should the system hold cash?
**A:** Yes — cash/flat is a position; exposure caps make it structural.
**Conf:** H. **Δ:** —.

**Q26.** Should risk budgets adapt to regime?
**A:** Vol scaling and gates already do; deeper regime-based budget
allocation is a roadmap item.
**Conf:** M. **Δ:** —.

**Q27.** Should the system reduce size before known events?
**A:** Default yes (event-avoidance); quantified later.
**Conf:** M. **Δ:** Event engine.

**Q28.** Should stop-losses be guaranteed?
**A:** No — gaps happen; stops are instructions, not guarantees. The
engine models gap-through-stops; sizing assumes worst case.
**Conf:** H. **Δ:** —.

**Q29.** Are stop prices part of the order?
**A:** In research, yes (validated at entry). In live execution, stops are
broker-side orders — the execution layer's responsibility (roadmap).
**Conf:** H. **Δ:** —.

**Q30.** Should we use stop-market or stop-limit orders?
**A:** Stop-limit avoids bad fills but risks no-fill; research uses
stop-price exits. Live: stop-market for risk priority.
**Conf:** M. **Δ:** Fill simulation comparison.

**Q31.** How should portfolio-level risk override trade quality?
**A:** Exposure/position-count caps run before the trade; a great trade
is rejected when the book is full (logged).
**Conf:** H. **Δ:** —.

**Q32.** Should the risk engine know strategy identity?
**A:** It logs it; limits are strategy-agnostic (a broken strategy must
not get looser limits).
**Conf:** H. **Δ:** —.

**Q33.** Is there a risk in the risk engine itself (model error)?
**A:** Yes — that's why limits are simple arithmetic, unit-tested, and
the kill switches are independent of the ML stack.
**Conf:** H. **Δ:** Fault-injection tests (implemented for broker; extend).

**Q34.** Should the system stop after N consecutive winning days?
**A:** No — no target-chasing; wins don't obligate anything.
**Conf:** H. **Δ:** —.

**Q35.** Should the system stop after reaching the 20% weekly target?
**A:** The target is not a target for the risk system; the risk system
stops on loss limits and risk events only. Reaching +20% does not force
more or fewer trades.
**Conf:** H. **Δ:** —.

**Q36.** Is tail-risk hedging (options) worth it?
**A:** Costs exceed expected benefit for a small paper system; position
caps + kill switches are the chosen tail defense.
**Conf:** M. **Δ:** Costed tail-hedge simulation.

**Q37.** How fast should drawdown scaling react?
**A:** Immediately at the hard limits; linearly below them. Hysteresis
prevents flapping.
**Conf:** M. **Δ:** Speed-of-reaction study.

**Q38.** Should risk limits be percentile-based (dynamic)?
**A:** Dynamic limits invite overfitting; fixed limits with documented
rationale are the default. Dynamic tightening only.
**Conf:** M. **Δ:** —.

**Q39.** What is the worst-case daily loss the system can produce?
**A:** Bounded by: per-trade risk × positions + gap risk + slippage
shock; the missing-data stress showed -20% possible under 1% missing
data with gap-through-stops — a real finding, mitigation: data-freshness
kill switch + tighter holding in illiquid windows.
**Conf:** M. **Δ:** Worst-case sequencing bound (implemented as bound).

**Q40.** What single risk property must never be violated?
**A:** No martingale, no revenge sizing, no stop removal, no leverage
increase to chase the target. Enforced by construction (no code path
accepts prior PnL as a sizing input).
**Conf:** H. **Δ:** —.
