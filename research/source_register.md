# Source Register & Currentness Log

Every external claim used in this project is logged here: source, tier,
publication date, access date, claim, and the confidence with which we
use it. Rule: no Tier-4/5 claim may override a Tier-1/2 claim without
explicit justification (see `decision_log/01_market.md`).

Tier key:
  1 = primary academic / regulatory / exchange
  2 = established quantitative research / peer-reviewed secondary
  3 = professional practitioners with transparent methods
  4 = public strategy documentation / vendor sites
  5 = influencer claims / anonymous reviews

| # | Source | Tier | Published | Accessed | Claim used | Confidence |
|---|--------|------|-----------|----------|-----------|-------------|
| S01 | Moskowitz, Ooi & Pedersen, "Time Series Momentum", JFE 2012 | 1 | 2012 | 2026-08-14 | TSMOM: past 12m return predicts 1-12m returns across 55+ futures | High (as literature fact); the tradable size is contested |
| S02 | "Time-series momentum: Is it there?", SMU working paper | 2 | ~2019 | 2026-08-14 | TSMOM evidence weak at asset level; sample/concentration sensitive | High (as critique); means: test, don't assume |
| S03 | Asness, Moskowitz & Pedersen, "Value and Momentum Everywhere", JFE 2013 | 1 | 2013 | 2026-08-14 | Value & momentum premia across asset classes; corr ≈ −0.46 | High |
| S04 | Bailey, Borwein, López de Prado & Zhu, "The Probability of Backtest Overfitting", 2015 | 1 | 2015 | 2026-08-14 | CSCV estimates PBO; search produces false winners | High |
| S05 | López de Prado, "Advances in Financial Machine Learning", 2018 | 1 | 2018 | 2026-08-14 | Purged k-fold + embargo against temporal leakage | High |
| S06 | Schwarz, "The Actual Retail Price of Equity Trades", J. of Finance 2025 | 1 | 2025 | 2026-08-14 | Retail round-trip costs 7-46 bps; PI $0.03-0.08/sh | High |
| S07 | financialmodelslab.com spread analysis (2025-2026) | 3 | 2026-05 | 2026-08-14 | S&P500 effective spread ~1.5bps; mid-caps 3x widen in stress | Medium |
| S08 | Barber, Lee, Liu & Odean day-trader studies (Taiwan) | 1 | 2006-2020 | 2026-08-14 | ~1% of day traders persistently profitable; ≥64-70% lose | High |
| S09 | currentmarketvaluation.com & vettedpropfirms.com day-trading stats roundups | 3 | 2024-2026 | 2026-08-14 | 70-95% lose; 97% lose on a given day after fees | Medium (consistent with S08) |
| S10 | tradewithathena.com | 4 | 2026 | 2026-08-14 | Athena public positioning + CFTC 4.41 disclaimer + entity | High for positioning only |
| S11 | coinspot.io & telegramsignalsreviews.com SwingTradingLab reviews | 5 | 2025-2026 | 2026-08-14 | Claims of ~32% free-signal win rate; VIP upsells | Low — allegations only |
| S12 | r/Daytrading thread "Is Alex G or Swingtradinglab serious?" | 5 | 2024-09 | 2026-08-14 | Community skepticism; mixed user reports | Low |
| S13 | CFTC Rule 4.41 | 1 | (regulation) | 2026-08-14 | Simulated results are hindsight-biased; must be labeled | High |
| S14 | Cont, "Empirical properties of asset returns" 2001 | 1 | 2001 | (domain knowledge) | Volatility clustering stylized fact | High |
| S15 | Kelly, "A New Interpretation of Information Rate" 1956 | 1 | 1956 | (domain knowledge) | Fractional-Kelly sizing baseline | High (theory) |
| S16 | SEC market access rule (15c3-5) | 1 | 2010 | (domain knowledge) | Pre-trade risk controls & erroneous-order prevention | High |

**Staleness policy:** market-structure numbers (spreads, costs) are
re-verified at research milestones; anything older than 12 months is
flagged stale in new reports. All Serein-generated experiments embed
`recorded_at` UTC timestamps.

**Confidence of the overall research base:** the *machinery* (backtest
overfitting, leakage, cost realism, drawdown control) is Tier-1 solid.
The *existence of a retail-scale tradable edge* is not established by any
source here; it is treated as an open empirical question with a strongly
negative prior.
