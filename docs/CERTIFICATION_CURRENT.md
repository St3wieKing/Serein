# Trading System Certification Report

**Status: FAILED**

**Promotion failures:** real_point_in_time_data_required, minimum_100_oos_trades, oos_sharpe, expectancy_confidence_interval, cost_2x, cost_5x, slippage_2x, latency_1bar, risk_breach, paper_forward_12_weeks

## Strategy Id

opening_range_challenger_v1

## Strategy Version

1.0.0-selection-contaminated

## Model Id

None

## Code Revision

4d42893b1995927fbf21317ec574f8597fdb40bc

## Data Fingerprint

SYNTH-FRESH-777

## Evidence Class

SYNTHETIC

## Research History

Selected after prior synthetic OOS ablation; frozen, then independently retested.

## Backtest

Fresh synthetic return -0.53%, 55 trades, Sharpe -1.60.

## Walk Forward

Prior walk-forward/seed results mixed.

## Oos

Mean expectancy -0.21R; 95% interval -0.44R to +0.05R.

## Stress

2x costs and 5x slippage both negative; multiple attacks not yet executed.

## Costs

2x cost return -0.63%.

## Slippage

5x slippage return -0.50%.

## Drawdown

Fresh synthetic max drawdown -0.53%; consecutive-loss risk halt occurred.

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
