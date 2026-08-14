# Research Decision Log — 06 · Execution Questions (25)

**Q1.** Should execution be a separate layer from strategy?
**A:** Yes — the execution layer is the only place orders exist; strategy
outputs are validated, transformed, and monitored there.
**Conf:** H. **Δ:** —.

**Q2.** Market or limit orders for entries?
**A:** Market-at-open for research (honest fill); limit-entry variants
are challengers with fill-risk modeling.
**Conf:** M. **Δ:** —.

**Q3.** How are stops executed?
**A:** As stop-price exits in research; broker-side stop orders in live
(roadmap). Never manual.
**Conf:** H. **Δ:** —.

**Q4.** What happens on partial fills?
**A:** PaperBroker simulates them (fill-ratio); the order manager must
reconcile remainder or cancel (paper path demonstrates).
**Conf:** M. **Δ:** —.

**Q5.** What happens on rejected orders?
**A:** Order status REJECTED + reason; no blind retry; investigation
first (paper broker failure-injection tested).
**Conf:** H. **Δ:** —.

**Q6.** What happens on broker disconnect?
**A:** Broker kill switch trips → no new orders; positions are managed
per policy; state reconciled before resume.
**Conf:** H. **Δ:** —.

**Q7.** How are duplicate orders prevented?
**A:** Order IDs + validator's no-duplicate-open-order check + idempotent
submission contract.
**Conf:** H. **Δ:** —.

**Q8.** How is state reconciled with the broker?
**A:** Restart recovery: reconnect → authenticate → fetch account,
positions, open orders → diff vs local → reconcile → risk check → only
then resume. Documented in failure_recovery.md.
**Conf:** H. **Δ:** —.

**Q9.** What is the maximum order size?
**A:** Validator caps: per-symbol 25% notional, 2% of bar ADV, gross
exposure limits; three independent ceilings.
**Conf:** H. **Δ:** —.

**Q10.** Should orders be sent at bar boundaries only?
**A:** Research: yes (next-open). Live: event-driven with validation;
latency stress shows bar-quantized execution is a real cost.
**Conf:** M. **Δ:** —.

**Q11.** How is slippage measured vs assumed?
**A:** PaperBroker records realized_slippage_bps per fill; slippage drift
report compares vs the cost model (implemented, wired in drift.py).
**Conf:** M. **Δ:** —.

**Q12.** What if the fill price is absurd (fat finger)?
**A:** Validator price-sanity check (0 < price < 1e6, finite) + anomaly
flags on the feed; absurd quotes kill trading.
**Conf:** H. **Δ:** —.

**Q13.** Should execution know the strategy's urgency?
**A:** Yes — horizon informs aggressiveness (roadmap); research uses a
single marketable pace.
**Conf:** L-M. **Δ:** —.

**Q14.** How are exit orders managed at day end?
**A:** Position inventory + exit-reason journal; time exits close stale
positions automatically.
**Conf:** H. **Δ:** —.

**Q15.** Is pre-market/after-hours trading allowed?
**A:** No — session-gated (validator market_open check; research data is
regular-session only).
**Conf:** H. **Δ:** —.

**Q16.** How are corporate actions handled?
**A:** Data layer requirement (adjust/unadjust flags); not yet wired for
real data — flagged as a real-data requirement.
**Conf:** M. **Δ:** —.

**Q17.** Should the system use one broker adapter only?
**A:** No — BrokerInterface with adapters; paper adapter ships, live
adapters are out of scope for this project state.
**Conf:** H. **Δ:** —.

**Q18.** How are order timestamps validated?
**A:** Clock discipline: UTC storage, monotonic timestamps, staleness
checks (data_max_staleness); documented in failure_recovery.
**Conf:** M. **Δ:** —.

**Q19.** What if local and broker positions diverge?
**A:** Divergence freezes new orders until reconciliation completes;
never guess.
**Conf:** H. **Δ:** —.

**Q20.** Should execution retry failed orders?
**A:** Only with a fresh validated order, bounded retries, and a kill
switch on retry storms.
**Conf:** M. **Δ:** —.

**Q21.** Is there a max orders-per-hour?
**A:** Yes — 6/hour and 20/day caps in the risk engine (tested).
**Conf:** H. **Δ:** —.

**Q22.** Should fills be assumed at the exact bar open?
**A:** For research, open±costs is the standard; real fills differ —
paper-vs-backtest discrepancy analysis is the measurement.
**Conf:** M. **Δ:** —.

**Q23.** How is market impact charged?
**A:** impact_bps = coeff × (notional/bar-ADV); stress tests scale
liquidity down (implemented).
**Conf:** M. **Δ:** —.

**Q24.** What execution data must be journaled?
**A:** Order lifecycle (NEW→FILLED/REJECTED/PARTIAL/CANCELLED), fill
price, slippage bps, timestamps, reject reasons (PaperBroker does all).
**Conf:** H. **Δ:** —.

**Q25.** What is the execution layer's cardinal rule?
**A:** The strategy model can never transmit an order directly — every
order passes the validator and risk engine; in this codebase no path
exists to bypass them.
**Conf:** H. **Δ:** —.
