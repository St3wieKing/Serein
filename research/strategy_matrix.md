# Strategy Hypothesis Matrix (v0)

Ranked by evidence, expected edge, testability, robustness potential,
complexity, execution feasibility, and risk. This matrix is a living
document — hypotheses are added by the research loop and re-ranked after
each experiment. Nothing here is "the best strategy"; everything is a
candidate to be destroyed by evidence.

Scoring: 1 (weak) – 5 (strong).

| # | Hypothesis | Evidence (Tier) | Expected edge | Testability | Robustness pot. | Complexity | Exec feasibility | Risk | Verdict |
|---|-----------|-----------------|---------------|-------------|-----------------|------------|------------------|------|---------|
| H01 | Vol-adjusted trend following (MA structure + vol gate) | TSMOM literature S01/S02 (1-2) | Low-med after costs | High | High | Low | High | Med (whipsaw, vol spikes) | TESTED → INCONCLUSIVE on synthetic; needs real OOS |
| H02 | Time-series momentum (past-k return sign, vol-scaled) | S01/S02 | Low-med | High | High | Low | High | Med | TESTED → near-zero after costs on synthetic |
| H03 | Z-score mean reversion gated by calm vol | Reversion literature (S03 value side); contested | Low | High | Med | Low | High | High in trends | TESTED → weak on synthetic |
| H04 | Volatility-compression breakout (Donchian + vol confirm) | Practitioner lore (Tier 3-4) + microstructure theory | Low | High | Med | Low-Med | High | High (false breakouts) | TESTED → weak on synthetic |
| H05 | Meta-ensemble gating (agree → trade, disagree → flat) | Ensemble literature; agreement≠correctness caveat | Med (risk reduction) | High | High | Med | High | Low | SUPPORTED as risk filter; NOT as alpha source |
| H06 | Regime-conditional allocation (trend in trends, reversion in ranges) | Vol clustering (S14); regime literature | Med | Med | Med | Med | High | Med | PARTIALLY SUPPORTED (vol regime gates work as designed) |
| H07 | ML direction prediction (LR/RF/GBM on 41 features) | ML literature | Low — features are weak | High | Med | Med-High | High | Med (overfit) | REJECTED at current feature set: AUC≈0.50 OOS |
| H08 | Time-of-day / session features | Intraday seasonality literature | Low | High | Med | Low | High | Low | INCONCLUSIVE (weak ablation delta) |
| H09 | Volume-confirmation features | Volume-price literature | Low | High | Med | Low | High | Low | INCONCLUSIVE |
| H10 | Cross-asset / index-relative features | Relative-strength literature | Med | Med | Med | Med | Med | Med | NOT TESTED (synthetic universe is isolated) — deferred |
| H11 | News / event-avoidance (skip known events) | Event-study literature; announcement drift | Med (loss avoidance) | Med | High | Med | High | Low | NOT TESTED — deferred to event engine phase |
| H12 | Risk-engine kill switches & drawdown scaling | Drawdown-management literature | N/A (risk) | High | High | Low | High | N/A | SUPPORTED — demonstrated in all runs |
| H13 | Gap-through-stop modeling under missing data | Market microstructure | N/A (realism) | High | N/A | Low | N/A | N/A | SUPPORTED — implemented & tested |
| H14 | Walk-forward + embargo as the only valid evaluation | S05 | N/A (method) | High | N/A | Low | N/A | N/A | SUPPORTED — all pipelines use it |
| H15 | PBO/CSCV on parameter selection | S04 | N/A (method) | High | N/A | Med | N/A | N/A | SUPPORTED — implemented |
| H16 | Purged labels with horizon>1 need embargo | S05 | N/A (method) | High | N/A | Low | N/A | N/A | SUPPORTED |
| H17 | Retail-scale intraday alpha survives ~15-20bps round-trip | S06 | Very low prior | High | Med | N/A | Med | High | NOT ESTABLISHED — the central open question |
| H18 | Trend pullback + objective continuation trigger | Grimes S21 + momentum prior S01/S02 | Low | High | Med | Low | High | Med | TESTED v2 synthetic: A isolated OOS positive but full/stress/kill-switch failed; B–D negative OOS → REJECT current specification |
| H19 | Failed range break + re-entry confirmation | Grimes S21; generic microstructure hypothesis | Low | High | Med | Low | Med | Med | TESTED v2 quick synthetic: OOS Sharpe −1.16 → REJECT current specification |
| H20 | Session VWAP extreme turns inward | Practitioner hypothesis | Low | High | Low-Med | Low | Med | High in trends | TESTED v2 quick synthetic: OOS Sharpe −0.38, 42 trades → REJECT current specification |
| H21 | Compression + lagged range break | Practitioner hypothesis; expansion mechanism | Low | High | Med | Low | Med | High false-break risk | TESTED v2 synthetic: OOS Sharpe +0.56 but only 21 trades → INCONCLUSIVE, fails sample gate |

## Ranking for next experiments (by value-of-information per unit cost)

1. Real-market OOS replication of H01/H02/H05 with locked defaults
   (highest value: replaces synthetic-only evidence).
2. Cost-sensitivity frontier for any candidate (H17) — a strategy that
   dies at 2x costs is dead.
3. Regime-conditional strategy weighting (H06) with drift detection.
4. Event-avoidance engine (H11).
5. Cross-asset features (H10) once a multi-asset data source is wired.
6. Challenger ML models on better labels (triple-barrier, per S05)
   with PBO reporting — only after baseline features improve.

## Explicitly rejected hypotheses (so far)

- R01: "More indicators ⇒ better predictions" — ablation on synthetic:
  removing momentum/volatility groups did not hurt (AUC ±0.01); the
  feature set as a whole is near-noise. Complexity penalty applied.
- R02: "ML confidence ≈ true probability" — ECE is computed and
  probabilities are treated as calibrated-until-proven; confidence never
  overrides risk.
- R03: "Ensemble agreement ⇒ correct" — tested as a filter only; the
  meta layer reports disagreement and treats it as uncertainty, not truth.
