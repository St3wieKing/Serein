# Trading books → falsifiable hypotheses

Books are practitioner sources, not proof. The table records the useful concept
we would test, not an endorsement of every claim by an author.

| Source | Concept | Underlying mechanism | Testable rule | Expected failure | Evidence quality | Difficulty | Simplicity (1–5) |
|---|---|---|---|---|---|---:|---:|
| Adam Grimes, *The Art and Science of Technical Analysis* | Pullbacks, failures, trend/range context | Temporary countertrend pressure or trapped breakout traders | Trend-pullback-break and failed-range-break candidates | Subjective structure; trend reversal | Practitioner + stated statistical orientation | 2 | 4 |
| Robert Carver, *Systematic Trading* | Forecast scaling and diversification | Normalize heterogeneous risk; avoid one forecast dominating | Volatility-scaled positions with hard caps | Correlations jump; vol estimates lag | Strong practitioner methodology | 2 | 4 |
| Perry Kaufman, *Trading Systems and Methods* | Efficiency/adaptive speed | Trend rules should react differently in noise and direction | Compare fixed vs efficiency-gated lookback | Adaptive rule overfits | Broad reference; hypotheses vary | 3 | 3 |
| Ernest Chan, *Algorithmic Trading* | Mean reversion, stationarity, implementation costs | Temporary relative mispricing | Locked z-score with half-life and cost gate | Structural break; nonstationarity | Practitioner/quantitative | 3 | 4 |
| Van K. Tharp, *Trade Your Way to Financial Freedom* | Expectancy and position sizing | Outcome distribution matters more than win rate | Report R expectancy; fixed fractional risk | Estimated expectancy unstable | Practitioner | 1 | 5 |
| Mark Douglas, *Trading in the Zone* | Process discipline | Prevent discretionary rule changes after random outcomes | Immutable risk limits and decision journal | Psychology claims hard to quantify | Behavioral practitioner | 1 | 5 |
| Jack Schwager, *Market Wizards* series | Diverse edges, common risk discipline | No universal setup; survival depends on loss control | Treat interviews as hypothesis catalog only | Selection/survivorship bias | Interview evidence | 1 | 4 |
| Brett Steenbarger, *The Daily Trading Coach* | Deliberate review | Structured feedback may improve execution consistency | Predeclared checklist and post-trade error taxonomy | Narrative hindsight | Practitioner/psychology | 2 | 4 |
| Alexander Elder, *Trading for a Living* | Multi-timeframe context and risk | Higher-level regime conditions lower-level setup | Compare setup alone vs lagged HTF trend | Reduces sample; redundant smoothing | Practitioner | 2 | 3 |
| Larry Connors & Cesar Alvarez, *Short Term Trading Strategies That Work* | Very short-term oversold reversion | Liquidity-driven overshoot | RSI(2)-style baseline with trend gate | Published edge decay; gap risk | Practitioner with tests, not independent replication | 1 | 5 |
| Linda Raschke & Laurence Connors, *Street Smarts* | Setup specialization | Repeated execution of a few patterns | Code each setup separately, no story-based discretion | Pattern ambiguity; data mining | Practitioner | 2 | 4 |
| Andreas Clenow, *Following the Trend* | Multi-market trend + risk parity | Persistent trends and diversified crisis convexity | Donchian/MA trend, ATR sizing, many liquid markets | Whipsaw and crowding | Practitioner aligned with academic evidence | 2 | 4 |
| Michael Covel, *Trend Following* | Cut losses, hold trends | Positive skew from persistent moves | Slow trend baseline with fixed risk | Anecdotal manager selection; long droughts | Practitioner compilation | 1 | 5 |
| Howard Bandy, *Quantitative Trading Systems* | Development protocol | Separate design and test to reduce overfit | Locked OOS, walk-forward, parameter plateaus | Repeated OOS inspection contaminates test | Practitioner/quant methods | 2 | 4 |
| John Carter, *Mastering the Trade* | Volatility squeeze | Contraction may precede expansion | ATR contraction + lagged range break | Direction unknown; false breakouts | Practitioner; mechanism plausible, edge unproven | 2 | 4 |
| Andreas Clenow / Robert Carver (combined theme) | Trade fewer independent forecasts | Redundant indicators add turnover, not information | Signal/return correlation clustering; retain simplest | Misses conditional complementarity | Strong methodological rationale | 2 | 5 |

## Academic control layer

The book-derived hypotheses are subordinate to reproducible evidence and
multiple-testing controls:

- Moskowitz, Ooi & Pedersen (2012): time-series momentum across futures;
  useful prior, not proof at hourly single-asset horizons.
- Sullivan, Timmermann & White (1999): technical-rule winners can be artifacts
  of data snooping; evaluate the whole search universe.
- Bailey et al. (2015): CSCV/PBO for strategy-selection overfit.
- López de Prado (2018): purging and embargo for overlapping labels.
- Schwarz (2025): actual retail equity execution costs vary materially by
  broker, making cost stress a first-order test.

## Extracted design decision

The smallest plausible candidate is not a multi-indicator “confluence” system.
It is: **directional context → temporary pullback → objective continuation
trigger → structural invalidation → fixed risk**. Volume and volatility are
challenger filters and must earn their place OOS. Failed breakouts and VWAP
reversion remain separate challengers rather than being forced into one hybrid.
