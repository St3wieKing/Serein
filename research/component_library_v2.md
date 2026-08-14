# Strategy v2 component library

**Status:** all alpha values below are **not established on real data**. Quick
synthetic results are diagnostic and must not be generalized.

| ID | Component | Objective definition | Mechanism | Complexity | Regime dependence | Execution | Verdict |
|---|---|---|---|---:|---|---|---|
| C001 | Trend context | EMA20 > EMA60 and 5-bar EMA60 slope > 0 (reverse for shorts) | Directional persistence | Low | Trends only | Easy | Challenger filter |
| C002 | Pullback | Prior low touches EMA20 ±0.25 ATR while close remains beyond EMA60 (reverse short) | Temporary countertrend pressure | Low | Trends | Moderate | Challenger setup |
| C003 | Continuation trigger | Current close breaks prior high/low in context direction | Renewed imbalance | Very low | Directional | Next-open gap risk | Core trigger |
| C004 | Structural invalidation | Long stop below 5-bar swing low −0.1 ATR; reverse short | Thesis is false beyond setup extreme | Low | All | Gap risk | Implemented |
| C005 | Volatility gate | ATR/price trailing percentile between 10th and 90th | Avoid dead or explosive conditions | Low | Conditional | Easy | Must earn place OOS |
| C006 | Relative volume | Current volume / rolling-20 mean ≥1.10 | Activity confirmation | Low | Session-specific | Data quality | Quick synthetic test harmful/inconclusive |
| C007 | Compression | mean ATR20 <0.8 × long baseline | Stored movement may precede expansion | Low | Transition | False-break risk | Synthetic OOS positive, only 5 trades—insufficient |
| C008 | Lagged range break | Close exceeds prior shifted 40-bar high/low | Price discovery beyond accepted range | Low | Expansion | Gap/slippage | Challenger |
| C009 | Failed break/re-entry | Prior bar breaches shifted range and closes inside; current confirms inward | Trapped breakout traders | Low | Range/transition | Fast execution | Quick synthetic OOS negative |
| C010 | Session VWAP deviation | Prior close ±2 ATR from causal session VWAP; current turns inward | Temporary liquidity imbalance | Low | Range | Correct session required | Quick synthetic OOS negative |
| C011 | Fixed R target | target = decision close ± k × structural risk, k∈{1,1.5,2,2.5,3,4} | Positive asymmetry | Very low | Setup-dependent | Touch-fill uncertainty | Sweep required; no universal k assumed |
| C012 | NO_TRADE | Any missing context, trigger, valid stop, target, liquidity, or risk approval | Avoid negative-EV exposure | Very low | All | Easy | Mandatory |

## Controlled combinations

- **D (core):** C002 + C003 + C004.
- **C:** D + C001.
- **B:** C + C005.
- **A (full):** B + C006.
- Independent challengers: C007+C008+C004, C009+C004, C010+C004.

The 26,500-bar synthetic run rejected the A–D family. A had an isolated OOS
Sharpe of +0.85 but lost −2.42% in the full run, had negative stressed Sharpes,
and tripped the Risk Engine; B–D were negative OOS. Compression breakout had
OOS Sharpe +0.56 but only 21 OOS trades, below the 25-trade gate. It remains
**inconclusive**, not a winner.
