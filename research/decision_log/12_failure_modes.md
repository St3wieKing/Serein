# Research Decision Log — 12 · Failure-Mode Questions (20)

**Q1.** What is the worst failure mode for a trading system?
**A:** Uncontrolled order flow (duplicates, runaway size, bypassed
limits) — mitigated by validator + risk engine + kill switches, all
unit-tested.
**Conf:** H. **Δ:** —.

**Q2.** What if the price feed becomes stale?
**A:** Staleness detection → data kill switch → no new trades; positions
marked at last known price (documented).
**Conf:** H. **Δ:** —.

**Q3.** What if prices become absurd (data corruption)?
**A:** Anomaly flags + price-sanity validation reject the feed; the
engine skips non-finite rows; stress tested.
**Conf:** H. **Δ:** —.

**Q4.** What if the model outputs NaN?
**A:** Non-finite outputs fail validation; model kill switch tripped on
repeated failure.
**Conf:** H. **Δ:** —.

**Q5.** What if the broker disconnects mid-position?
**A:** Broker kill switch → halt new orders; reconciliation procedure on
reconnect; positions are not guessed.
**Conf:** H. **Δ:** —.

**Q6.** What if an order is duplicated by a retry?
**A:** Order IDs + duplicate check in validator; idempotency contract in
the broker interface.
**Conf:** H. **Δ:** —.

**Q7.** What if the account state differs from local state?
**A:** Freeze new orders; full reconciliation from broker truth before
resume (restart-recovery procedure).
**Conf:** H. **Δ:** —.

**Q8.** What if the clock drifts?
**A:** Timestamps are monotonic-checked; UTC storage; clock-sync check is
part of system health.
**Conf:** M. **Δ:** —.

**Q9.** What if the machine restarts mid-trade?
**A:** Restart recovery: reconnect → fetch state → reconcile → risk
check → resume; local state never trusted blindly.
**Conf:** H. **Δ:** —.

**Q10.** What if the database/registry is corrupted?
**A:** JSONL append-only; corruption detected by parse errors → research
mode only; experiments are reproducible from code + seeds.
**Conf:** M. **Δ:** —.

**Q11.** What if the strategy's largest historical loss happens tomorrow?
**A:** Per-trade risk caps make a single loss bounded (~1% of equity);
the loss is categorized (GOOD/BAD/MODEL/etc.) and the system continues
per rules — no revenge, no panic.
**Conf:** H. **Δ:** —.

**Q12.** What if all strategies fail at once (correlated losses)?
**A:** Portfolio-level drawdown kill + daily/weekly halts; stress tests
assume correlation = 1.
**Conf:** H. **Δ:** —.

**Q13.** What if transaction costs double?
**A:** Cost stress: Sharpe degrades but system stays within limits; 10x
costs nearly halve the edge — cost-fragility is reported per strategy.
**Conf:** H. **Δ:** —.

**Q14.** What if latency quintuples?
**A:** Latency stress shows edge erosion; the system does not adapt by
widening stops (that would be stop-removal in disguise).
**Conf:** H. **Δ:** —.

**Q15.** What if the market gaps through every stop?
**A:** Gap-through-stop is modeled, not assumed away; missing-data stress
quantifies the tail; worst-case sequencing bound reported.
**Conf:** H. **Δ:** —.

**Q16.** What if a kill switch fires incorrectly?
**A:** False trip = lost opportunities, never losses; switches are
independent and simple; log + investigation procedure.
**Conf:** H. **Δ:** —.

**Q17.** What if the model is confident and wrong systematically?
**A:** Calibration drift detection + rolling expectancy + quarantine;
confidence never overrides risk.
**Conf:** H. **Δ:** —.

**Q18.** What if the research pipeline itself is flawed?
**A:** Red-team reviews (PBO, leakage audit, stress, adversarial
questions) exist precisely to attack the pipeline; every major result
must survive them.
**Conf:** M. **Δ:** —.

**Q19.** What failures are impossible to test?
**A:** Novel market structures with no historical analog; exogenous
geopolitical shocks; these are handled by risk posture (small size,
kill switches), not prediction.
**Conf:** M. **Δ:** —.

**Q20.** What is the failure-mode cardinal rule?
**A:** Fail safe: any error, uncertainty, or anomaly defaults to
NO_NEW_TRADES. The system must be boring in failure.
**Conf:** H. **Δ:** —.
