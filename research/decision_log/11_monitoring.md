# Research Decision Log — 11 · Monitoring Questions (15)

**Q1.** What must be monitored at minimum?
**A:** System health, data freshness, risk state, model state, strategy
state, execution quality — each with concrete signals below.
**Conf:** H. **Δ:** —.

**Q2.** How is system health shown?
**A:** Dashboard sections: equity, drawdown, monthly heatmap, trades,
decomposition, risk summary (generated from every run).
**Conf:** M. **Δ:** —.

**Q3.** How is data freshness monitored?
**A:** Validation staleness flags + anomaly counts per symbol; stale or
anomalous → data kill switch.
**Conf:** H. **Δ:** —.

**Q4.** How is risk state monitored?
**A:** RiskEngine.summary(): kill switches, rejections, vol_frac,
force_exit, daily/weekly halts — printed in every backtest and
dashboard.
**Conf:** H. **Δ:** —.

**Q5.** How is model state monitored?
**A:** OOS metrics per family (AUC, accuracy, ECE, Brier) + calibration
reliability tables + feature drift PSI.
**Conf:** H. **Δ:** —.

**Q6.** How is strategy state monitored?
**A:** Rolling expectancy/win-rate with CUSUM drift flags
(performance_drift_report) + decomposition by strategy.
**Conf:** M. **Δ:** —.

**Q7.** How is execution monitored?
**A:** Realized slippage per fill vs cost model (paper broker); slippage
drift report; rejection log with reasons.
**Conf:** M. **Δ:** —.

**Q8.** What alerts exist?
**A:** Kill-switch trips (any), PSI alerts, drift detection, slippage
drift, stress-test failure — all machine-readable in reports.
**Conf:** M. **Δ:** —.

**Q9.** How is drawdown monitored intra-run?
**A:** Equity curve with drawdown panel + live peak tracking + kill
switch at limit.
**Conf:** H. **Δ:** —.

**Q10.** How are rejections reviewed?
**A:** Rejection log with time/symbol/direction/reason — reviewed in
post-run analysis; many rejections = either discipline or over-blocking.
**Conf:** M. **Δ:** —.

**Q11.** How is the weekly/monthly return distribution shown?
**A:** Metrics table (mean/std/worst/best week & month) + monthly
heatmap chart.
**Conf:** H. **Δ:** —.

**Q12.** How are anomalies in monitoring detected?
**A:** The monitoring layer itself is tested (unit tests on drift
detectors); a monitoring failure fails safe (no trading decision
depends on the dashboard).
**Conf:** M. **Δ:** —.

**Q13.** What is the difference between monitoring and control?
**A:** Monitoring observes; only the risk engine controls. A dashboard
cannot trade and a control cannot be hidden from logs.
**Conf:** H. **Δ:** —.

**Q14.** How is live-vs-backtest discrepancy measured?
**A:** Paper broker fills vs backtest fills → slippage/execution drift
report; the required comparison loop (backtest vs paper vs shadow) is
documented in deployment.md.
**Conf:** M. **Δ:** —.

**Q15.** What is the monitoring cardinal rule?
**A:** Every decision the system makes must be visible: entries,
rejections, exits, kill switches, adaptations — with reasons. If it
isn't logged, it didn't happen.
**Conf:** H. **Δ:** —.
