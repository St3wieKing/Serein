# Research Decision Log — 09 · Adaptation Questions (20)

**Q1.** How quickly should the system adapt?
**A:** Three speeds: fast (execution thresholds, gates), medium
(strategy weights, regime probabilities), slow (retraining, feature
sets). Never instant.
**Conf:** M. **Δ:** Adaptation-speed sensitivity study.

**Q2.** How slowly should it adapt?
**A:** Slowly enough that a single week cannot move anything material;
statistical thresholds (CUSUM, PSI) gate every adaptation.
**Conf:** M. **Δ:** —.

**Q3.** When should retraining be allowed?
**A:** On triggers: feature drift, performance drift, regime change,
milestone schedule. Never daily.
**Conf:** M. **Δ:** —.

**Q4.** When should retraining be forbidden?
**A:** During market stress, after a bad week, or when data quality is
suspicious; quarantine first, investigate, then retrain.
**Conf:** H. **Δ:** —.

**Q5.** Can online learning introduce catastrophic drift?
**A:** Yes — unbounded updates can walk a model into a corner; that is
why all updates go through champion/challenger gates.
**Conf:** H. **Δ:** —.

**Q6.** How do we distinguish noise from degradation?
**A:** Rolling metrics with sample thresholds + CUSUM on the rolling
expectancy (implemented); "DRIFT_DETECTED" requires persistent signal.
**Conf:** M. **Δ:** False-positive audit of the detector.

**Q7.** How does the system detect regime change?
**A:** CUSUM change-points on returns + vol-percentile shifts + regime
label transitions (implemented, exercised in all runs).
**Conf:** M. **Δ:** —.

**Q8.** What happens on detected drift?
**A:** REDUCE RISK → INVESTIGATE → REVALIDATE → PAPER → REDEPLOY; the
pipeline enforces the order (documented).
**Conf:** H. **Δ:** —.

**Q9.** Should weights react to recent OOS performance?
**A:** Yes but damped: long-term baseline + slow updates + uncertainty
bounds; never chase the last 10 trades.
**Conf:** M. **Δ:** —.

**Q10.** How is strategy weight updated?
**A:** Not yet automatic — meta weights are config; the health-score
wiring is the roadmap item.
**Conf:** L-M. **Δ:** —.

**Q11.** Should the system adapt to the 20% target?
**A:** Never — the risk system ignores return targets entirely.
**Conf:** H. **Δ:** —.

**Q12.** Can adaptation itself overfit?
**A:** Yes — adapting to noise is overfitting in time; sample minimums
and statistical gates are the defense.
**Conf:** H. **Δ:** —.

**Q13.** How is adaptation logged?
**A:** Every weight/threshold change is an audit event with reason;
registries store versions.
**Conf:** M. **Δ:** —.

**Q14.** Should the system adapt position sizing to realized vol?
**A:** Yes — vol targeting is live (vol_frac 0.25-1.5x).
**Conf:** M. **Δ:** —.

**Q15.** Should the system adapt to widening spreads?
**A:** Spread gate rejects; sizing response is roadmap.
**Conf:** M. **Δ:** —.

**Q16.** How does the system know its own skill changed?
**A:** Rolling expectancy, calibration ECE, PSI, slippage drift — all
implemented as reports; wiring to automatic weight changes is roadmap.
**Conf:** M. **Δ:** —.

**Q17.** What if the market becomes unprecedented?
**A:** By definition no training data covers it; volatility kill +
anomaly kill + reduced size are the automatic responses; the model is
quarantined if feature space leaves the trained envelope.
**Conf:** M. **Δ:** —.

**Q18.** Should adaptation speed differ by strategy family?
**A:** Yes — fast-moving families (intraday) need faster gates; slow
families (swing) need slower ones. Configurable per strategy (roadmap).
**Conf:** M. **Δ:** —.

**Q19.** How do we prevent oscillation between regimes?
**A:** Hysteresis: enter a regime only after sustained evidence; exit
after sustained opposite evidence (transition class absorbs boundary
bars).
**Conf:** M. **Δ:** —.

**Q20.** What is the adaptation layer's cardinal rule?
**A:** Adaptation must never increase risk exposure beyond the absolute
limits, and must never be triggered by a single outcome.
**Conf:** H. **Δ:** —.
