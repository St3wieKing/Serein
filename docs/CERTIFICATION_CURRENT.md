# Trading System Certification Report

**Status: FAILED**

**Promotion failures:** real_point_in_time_data_required, minimum_100_oos_trades, oos_sharpe, expectancy_confidence_interval, cost_2x, cost_5x, slippage_2x, latency_1bar, regime_replication, paper_forward_12_weeks

## Strategy Id

opening_range_challenger_v1

## Strategy Version

1.0.0-selection-contaminated

## Model Id

None

## Code Revision

7e536a00eaceeac6d72473846e7f8bc05524aa06

## Data Fingerprint

cc751830f538378815a8c0a3927f83eb3db163daa3c95404517f52efcc6bd2c4

## Evidence Class

HISTORICAL_PUBLIC_UNVERIFIED

## Research History

Selected after synthetic OOS ablation; frozen, then failed two sealed public external samples.

## Backtest

Fresh public AAL/AMD/BAC last-40-session holdout: -0.28%, 8 trades, Sharpe -2.08.

## Walk Forward

Prior synthetic results mixed; both public external samples were negative and insufficient.

## Oos

Expectancy -0.34R; confidence interval unavailable with eight trades.

## Stress

2x/5x costs, 2x slippage and one-bar latency all negative.

## Costs

2x cost return -0.35%.

## Slippage

2x slippage return -0.41%.

## Drawdown

Fresh public holdout max drawdown -0.51%.

## Calibration

No approved model.

## Drift

No real live feature stream.

## Paper

0 weeks.

## Failure Cases

- fresh replication failed
- cost stress failed
- slippage stress failed

## Red Team Failures

- future leakage attack unexecuted
- missing cluster unexecuted
- drift unexecuted

## Known Limitations

- no real NBBO data
- selection contamination
- no paper feed
- no legal/broker authorization

## Authority boundary

This report cannot enable live execution. It may only support a governed paper-stage review.
