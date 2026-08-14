# Literature & Evidence Notes

**Research date:** 2026-08-14 · Full source register with access dates in
`source_register.md`. Every strategy family in Serein traces to a public
finding below — and to its *critiques*, which are read with equal weight.

---

## 1. Momentum / time-series momentum

**Moskowitz, Ooi & Pedersen (2012), "Time Series Momentum", JFE.**
- Finding: past 12-month return positively predicts next 1–12 month
  returns across 55+ futures (equities, bonds, FX, commodities);
  "time-series momentum is everywhere".
- Implication for us: trend/momentum is the most robustly documented
  alpha family in liquid markets. → `MomentumStrategy`, `TrendStrategy`.
- **Critical companion: "Time-series momentum: Is it there?" (SMU).**
  Finds the effect is much weaker at the individual-asset level, largely
  concentrated, and sensitive to sample. Implication: do not assume the
  edge; expect it to be small after costs; test per asset.

**Asness, Moskowitz & Pedersen (2013), "Value and Momentum Everywhere".**
- Value and momentum premia exist across 8 asset classes; their returns
  are negatively correlated (−0.46 in the sample). Implication: a
  portfolio that holds BOTH trend/momentum and mean-reversion/value
  families is structurally more robust than either alone. →
  ensemble architecture with opposite-sign strategy families.

## 2. Backtest overfitting

**Bailey, Borwein, López de Prado & Zhu (2015), "The Probability of
Backtest Overfitting".**
- Selection among many backtests produces false winners; holdout is
  unreliable; CSCV estimates PBO. A Sharpe of 10 over 50 years is
  attainable by search alone. Implication: every parameter selection in
  Serein reports PBO (implemented in `backtest/robustness.cscv_pbo`).

**López de Prado (2018), "Advances in Financial Machine Learning".**
- Purged k-fold CV + embargo prevent temporal leakage; backtests must be
  treated as statistical selection problems. Implication: all ML
  evaluation uses walk-forward with embargo; leakage auditor gates.

## 3. Transaction costs (current)

**Schwarz (2025), "The Actual Retail Price of Equity Trades", Journal of
Finance.**
- Six retail brokerages, real experimental orders: average price
  improvement (vs NBBO) varied $0.03–$0.08/share = 19–47% of the NBBO
  spread; average ROUND-TRIP cost 7–46 bps depending on broker.
- Implication: Serein's default cost model (≈5.5 bps one-way + impact +
  commission ≈ 14–20 bps round trip at retail size) is in the plausible
  range; the slippage stress tests (2x/5x/10x) cover the dispersion.

**Market data points (2025–2026):** effective spreads on liquid S&P 500
names ≈1.5 bps; mid-caps widened ~3x (0.05%→0.15%) within 48h during the
Q3-2025 stress. Implication: spread widening under stress is a first-order
risk for any intraday strategy → spread kill switch, liquidity stress.

## 4. What happens to retail traders

**Barber, Lee, Liu & Odean (Taiwan day-trader studies, 2000s-2020s) and
aggregating analyses (2024–2026).**
- ~70–95% of day traders lose money; ~1–3% are persistently profitable;
  on any given day ~97% of day traders lose after fees; most quit within
  two years.
- Implication: the prior on a retail-scale autonomous strategy is
  strongly negative. This is the single most important calibration
  anchor for the whole project: **the default expectation is that no
  edge exists, and extraordinary evidence is required to conclude
  otherwise.** The 20%-per-week figure is treated as an aspirational
  benchmark with near-zero prior probability at acceptable risk.

## 5. Regime & volatility

- Volatility clustering is among the most robust stylized facts
  (Mandelbrot; Cont 2001 "Empirical properties of asset returns").
  Implication: regime features built on realized-vol percentiles and
  change-point detection are defensible; a regime engine is a filter,
  not a predictor.
- Hurst/trend-persistence evidence is mixed by asset and sample —
  treated as a research question, not an assumption.

## 6. Risk & sizing foundations

- Kelly criterion (1956) and fractional-Kelly practice: sizing from
  edge/odds with a fraction (1/4–1/2 Kelly) is the academic baseline.
  Serein's risk-per-trade sizing is a conservative, calibrated cousin:
  0.5% risk per trade, confidence-scaled, capped, with drawdown scaling —
  deliberately far below full Kelly to protect against estimation error
  and regime change.
- Drawdown control literature (e.g., Kaminski & Lo on drawdown-based
  risk management): cutting exposure after drawdowns is defensible; the
  key design choice is speed (we use linear scaling + hard kill switch,
  with a documented adaptation-speed research question).

## 7. Regulators / legal

- CFTC Rule 4.41: simulated performance must be labeled as such and is
  inherently hindsight-biased. → Serein labels every synthetic result.
- SEC market-access rule framework: pre-trade financial limits and
  erroneous-order controls are mandatory for automated access. →
  OrderValidator checklist + Risk Engine as the ultimate authority.
- Brokerage age/identity requirements are not bypassable and never
  attempted; live trading is out of scope for this project state.
