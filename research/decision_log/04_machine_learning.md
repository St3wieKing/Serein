# Research Decision Log — 04 · Machine-Learning Questions (40)

**Q1.** Do we need ML at all?
**A:** No — not yet. Rule baselines ran first; ML adds value only if it
beats baselines OOS after costs. Current ML: AUC≈0.50 (chance).
**Conf:** H. **Δ:** Better features/labels then re-compare.

**Q2.** Does deep learning beat linear models on hourly bars?
**A:** Not with weak features; DL adds capacity, not information.
**Conf:** M. **Δ:** Benchmarked challengers (roadmap: TCN/LSTM vs LR).

**Q3.** Is logistic regression a fair baseline?
**A:** Yes — simple, calibrated, interpretable; anything more complex
must beat it OOS after costs.
**Conf:** H. **Δ:** —.

**Q4.** Do tree ensembles overfit financial data?
**A:** They overfit noise easily; depth/leaf constraints help; PBO must
be reported for any selection.
**Conf:** H. **Δ:** —.

**Q5.** What should the ML predict: direction, return, or R-multiple?
**A:** R-multiple / triple-barrier labels capture path and timing; simple
horizon-sign labels are the v0 (AUC≈0.50).
**Conf:** M. **Δ:** Label-scheme comparison.

**Q6.** Are hourly labels too noisy to learn?
**A:** Yes, mostly — hourly R² is tiny; longer horizons have more signal
but fewer samples.
**Conf:** M. **Δ:** Horizon sweep.

**Q7.** How do we prevent lookahead in features?
**A:** Causal construction + audit (audit.py: alignment, monotonic index,
perfect-correlation, overlap warnings). Tested.
**Conf:** H. **Δ:** —.

**Q8.** How do we prevent label leakage?
**A:** Labels are forward returns stored at t (knowable only after t);
horizon>1 forces purged/embargoed CV (tested).
**Conf:** H. **Δ:** —.

**Q9.** Is standard k-fold acceptable?
**A:** No — temporal order breaks it; walk-forward + embargo is the only
accepted evaluation (tested).
**Conf:** H. **Δ:** —.

**Q10.** How much data is enough to train?
**A:** Thousands of independent events minimum; our WFA used ~70k rows but
effective independence is far lower (overlapping labels).
**Conf:** M. **Δ:** Sample-size curves.

**Q11.** When does more history become harmful?
**A:** When regimes shift and the old data is a different market; drift
detection (PSI/CUSUM) decides relevance.
**Conf:** M. **Δ:** —.

**Q12.** Does feature standardization leak?
**A:** If fit on the full sample — yes; fit inside each training window
only. Current pipeline uses tree-friendly raw features; standardization
is a roadmap item with fit-on-train-only.
**Conf:** H. **Δ:** —.

**Q13.** Are rolling z-scores safer than raw prices as features?
**A:** Yes — stationary-ish and causal; raw levels (ma_, vwap_) were
excluded from drift PSI for this reason.
**Conf:** H. **Δ:** —.

**Q14.** Should we use ensemble prediction diversity?
**A:** Yes — but measure prediction correlation first; "different"
models often learn the same signal.
**Conf:** M. **Δ:** Prediction-correlation matrix.

**Q15.** Are model probabilities trustworthy as confidence?
**A:** No — they need calibration checks (ECE/Brier). Our OOS ECE was
0.04-0.08 (well-calibrated only because predictions hug the base rate).
**Conf:** H. **Δ:** —.

**Q16.** How should calibration feed decisions?
**A:** Confidence gates/sizing use calibrated probabilities; a
calibration-collapse trips the model kill switch (roadmap wiring).
**Conf:** M. **Δ:** —.

**Q17.** Is AUC the right metric for trading models?
**A:** No — economic value after costs is the metric; AUC is a diagnostic.
Both are reported.
**Conf:** H. **Δ:** —.

**Q18.** Should we optimize the threshold?
**A:** Only on validation data, never test; the meta layer's gates serve
as the threshold system.
**Conf:** M. **Δ:** —.

**Q19.** Can a model trained on regime A transfer to regime B?
**A:** Rarely; regime features help the model adapt or abstain; drift
detection flags the boundary.
**Conf:** M. **Δ:** Regime transfer experiments.

**Q20.** Is online learning dangerous here?
**A:** Yes — drift risk; controlled retraining with triggers and
champion/challenger gates is the only allowed path.
**Conf:** H. **Δ:** —.

**Q21.** Is reinforcement learning needed?
**A:** No — RL adds dangerous exploration and sample inefficiency for a
problem that supervised/rule approaches handle; not on the roadmap.
**Conf:** M. **Δ:** —.

**Q22.** Can RL accidentally learn dangerous behavior?
**A:** Yes (reward hacking, stop-removal, leverage) — one more reason RL
is excluded from the decision path entirely.
**Conf:** H. **Δ:** —.

**Q23.** Do transformers help on hourly financial data?
**A:** No evidence for small-data financial tasks; huge overfit risk.
Not adopted.
**Conf:** L-M. **Δ:** Fair benchmark with PBO.

**Q24.** Is a meta-model over strategy outputs useful?
**A:** Only as a calibrated combiner; currently the transparent weighted
vote is preferred. Challenger idea.
**Conf:** M. **Δ:** —.

**Q25.** How do we measure feature importance honestly?
**A:** Ablation in walk-forward (implemented) — importance = ΔOOS, not
tree-importance.
**Conf:** H. **Δ:** —.

**Q26.** Do we keep features that help IS but not OOS?
**A:** No — OOS ablation is the only vote that counts.
**Conf:** H. **Δ:** —.

**Q27.** Should the model predict P(sideways) too?
**A:** Ternary labels exist (make_labels mode='ternary'); the meta layer
uses the no-trade class implicitly. Keep.
**Conf:** M. **Δ:** —.

**Q28.** How do we handle class imbalance?
**A:** Balanced class weights for LR; base rate reported with every
metric so accuracy is never misleading.
**Conf:** H. **Δ:** —.

**Q29.** Is the base rate a strategy?
**A:** No — but beating it is the entry ticket; every ML report prints
base rate alongside AUC.
**Conf:** H. **Δ:** —.

**Q30.** What is the role of uncertainty estimates?
**A:** Wide uncertainty → smaller size or flat; disagreement + ECE are
the current proxies; conformal prediction is a roadmap challenger.
**Conf:** M. **Δ:** —.

**Q31.** Should models be retrained on a schedule?
**A:** Trigger-based (drift/regime/performance) + milestone schedule;
never daily, never after one bad week.
**Conf:** M. **Δ:** —.

**Q32.** How do we prevent retraining from erasing knowledge?
**A:** Model registry keeps every version; champion/challenger replaces
only after gates.
**Conf:** H. **Δ:** —.

**Q33.** What happens when the model outputs NaN?
**A:** Model kill switch trips; no trades until investigation. (Check in
execution validation + risk engine.)
**Conf:** H. **Δ:** —.

**Q34.** Should features be regime-conditional?
**A:** Yes, cheaply (regime dummies); ablation on synthetic showed
regime dummies ~neutral — keep but don't over-trust.
**Conf:** M. **Δ:** —.

**Q35.** Do volume features deserve their weight?
**A:** They had the largest positive ablation delta on synthetic (still
small); keep, re-test on real data.
**Conf:** M. **Δ:** —.

**Q36.** Is feature selection per-regime worth it?
**A:** Plausible; adds complexity; challenger idea.
**Conf:** L-M. **Δ:** —.

**Q37.** Should ML confidence gates be as strict as rule gates?
**A:** Stricter — ML probabilities get calibration haircuts and the
model kill switch; rules are deterministic and auditable.
**Conf:** H. **Δ:** —.

**Q38.** What evidence would make us trust an ML signal?
**A:** Positive OOS AUC/EV after costs in purged WFA, stable across
regimes, PBO low, calibration OK, and economic size that survives 2x
costs.
**Conf:** H. **Δ:** —.

**Q39.** What evidence would make us kill an ML model?
**A:** Calibration collapse, PSI alert on core features, rolling
expectancy drift, or OOS decay below baseline — quarantine path exists.
**Conf:** H. **Δ:** —.

**Q40.** What is the most important ML lesson so far?
**A:** With 41 features and 3 model families, the best OOS AUC was 0.509
vs base rate 0.503 — the bottleneck is information in the features, not
model capacity. Feature research comes first.
**Conf:** H. **Δ:** —.
