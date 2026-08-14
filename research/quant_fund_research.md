# Quantitative-fund research: public evidence versus proprietary unknowns

**Research date:** 2026-08-14

## Critical boundary

No public source reveals the complete strategy of Renaissance Medallion, D. E.
Shaw, Two Sigma, Citadel Global Quantitative Strategies, or Citadel Equity
Quantitative Research. Their data, features, model parameters, execution logic,
financing, hedges, and portfolio construction are proprietary. A retail system
cannot honestly “backtest Citadel's strategy.” This research extracts public
principles and independently testable academic mechanisms.

Citadel LLC (investment manager) and Citadel Securities (market maker) are
separate businesses. Market-making economics—two-sided quoting, exchange
connectivity, internalized flow, inventory control and microsecond execution—are
not reproducible from five-minute OHLCV bars.

## What leading firms publicly support

| Organization | Publicly verified principle | What remains unknown | Serein translation |
|---|---|---|---|
| Citadel EQR | Structural analysis, rigorous statistics, computer science, economics, diverse data, market-flow understanding, systematic and semi-systematic strategies | Actual datasets, signals, models, time horizons, portfolio weights, performance by signal | Economic hypothesis registry, cross-sectional context, strict validation |
| Citadel risk organization | Central risk tolerance and portfolio oversight | Position limits, stress scenarios, capital allocation algorithms | Risk Engine remains ultimate authority; alpha cannot loosen controls |
| Citadel Securities | Quantitative research, large-scale data, ML/AI, models as inputs to market making | Quoting, inventory, adverse-selection and routing models | Do not imitate; use only cost/latency awareness |
| Two Sigma | Scientific method, ML/distributed computing, real-time risk monitoring, execution optimization | Production models and proprietary data | ML as challenger/meta-filter, model governance, live drift controls |
| AQR | Diversified time-series momentum, multiple lookbacks, volatility scaling, transaction costs | Current implementation and proprietary enhancements | Slow-trend baseline and vol scaling, not falsely relabeled as day trading |
| Man AHL | Moving-average/breakout trend models, broad market diversification, complementary mean-reversion/seasonal/volatility signals | Current proprietary models and alternative markets | Regime routing and strategy diversification; no one model everywhere |
| Bailey et al./López de Prado | Multiple testing, CSCV/PBO, purging and embargo | N/A methodology | Locked chronology, PBO, no repeated holdout tuning |

## Source notes

### Citadel

Citadel's EQR page says it seeks market inefficiencies through structural
analysis, quantitative research and technology; researchers apply statistical
methods to diverse datasets and ground signals in economic practicality:
https://www.citadel.com/what-we-do/equities/equity-quantitative-research-eqr/

Citadel's fixed-income/macro description emphasizes relative value,
quantitative modeling, macroeconomics, continual idea generation and portfolio
construction/risk management:
https://www.citadel.com/what-we-do/fixed-income-and-macro/

Citadel's Chief Risk Officer chairs its Portfolio Committee and advises risk
tolerance across strategies and funds:
https://www.citadel.com/who-we-are/leadership/joanna-welsh/

Citadel Securities describes quantitative research, compute, ML and AI as parts
of its market-making analytics, not as a disclosed directional recipe:
https://www.citadelsecurities.com/who-we-are/

### Two Sigma

Two Sigma publicly frames its process as scientific inquiry using data,
technology, ML and distributed computing. It says execution systems monitor
risk in real time and adjust optimization parameters:
https://www.twosigma.com/about-us/

This supports disciplined research and governance; it does not disclose a
tradable signal.

### AQR and Man AHL

Hurst, Ooi and Pedersen's *A Century of Evidence on Trend-Following Investing*
constructs diversified 1-, 3- and 12-month time-series momentum with volatility
scaling and transaction costs. This is strong evidence for a broad trend family,
but not for five-minute prediction:
https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2993026

Man AHL has publicly described moving-average crossovers and breakouts as its
early trend core, with diversification across hundreds of markets and additional
non-trend strategies. The key lesson is breadth and risk allocation—not a magic
indicator:
https://thehedgefundjournal.com/man-ahl-marks-30-years/

### Intraday evidence

The peer-reviewed literature reports conditional intraday momentum, including
relationships between early and late session returns, but effects vary by
sample, volatility, volume, instrument and overnight information. Transaction
costs and execution determine economic value. It is inappropriate to extrapolate
long-horizon hedge-fund trend results to day trading.

## Research design derived from evidence

The implemented strategy is a state machine, not an indicator vote:

1. **Context:** causal EMA trend, session VWAP, realized-volatility percentile,
   cross-sectional breadth and market return.
2. **Setup router:** opening-range continuation in directional/liquid regimes;
   VWAP pullback in established trends; VWAP reversion only in range regimes.
3. **Trigger:** close through an objective prior level.
4. **Invalidation:** recent structural swing plus ATR buffer.
5. **Execution:** decision at bar close, fill next open, modeled spread,
   commission, slippage and impact.
6. **Risk:** 0.25% per trade, no leverage, exposure/frequency caps, daily/weekly
   stops and portfolio kill switch.
7. **Session:** mandatory 15:55 liquidation; zero overnight risk.
8. **ML:** logistic and shallow gradient-boosting models predict whether a
   pre-existing setup is worth taking. They cannot create trades or override risk.
9. **Validation:** train/validation/locked OOS, cost/slippage/latency shocks,
   setup ablation, CSCV/PBO and independent synthetic seeds.

## Why “bulletproof” is rejected

Markets can gap through stops, correlations can converge, spreads can explode,
brokers can fail, models can drift, and future distributions can differ from all
historical samples. No strategy is bulletproof. Institutional quality means:

- known maximum intended risk;
- fail-closed behavior;
- no hidden leverage or averaging down;
- many weak, independently validated opportunities;
- conservative execution assumptions;
- willingness to remain flat;
- rapid detection and slow, governed adaptation;
- honest shutdown when evidence disappears.
