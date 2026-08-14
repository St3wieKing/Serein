# Public Intraday External Evaluation

**Evidence:** real historical trade bars from a public GitHub repository that
states Alpha Vantage provenance; source files were malformed concatenations and
were strictly cleaned. Source: `chemicoPy/SP500-data` on GitHub. The repository
does not establish institutional data quality or NBBO provenance. This is
UNVERIFIED research data, not licensed NBBO.

**Holdout:** last 40 common complete sessions, sealed then revealed once.  
**Fingerprint:** `cc751830f538378815a8c0a3927f83eb3db163daa3c95404517f52efcc6bd2c4`  
**Ledger valid:** True  
**Decision:** **REJECTED** — fewer than 100 OOS trades, profit factor gate, expectancy lower bound not positive, 2x costs failed, 2x slippage failed, public source is unverified/revised and has no bid-ask quotes, no paper-forward evidence.

## Data report

```json
{
  "symbols": [
    "AAL",
    "AMD",
    "BAC"
  ],
  "rows": 41418,
  "start": "2019-10-16 09:30:00-04:00",
  "end": "2021-08-05 15:55:00-04:00",
  "source_timezone": "America/New_York",
  "market_timezone": "America/New_York",
  "out_of_session_removed": 0,
  "missing_session_bars": 0,
  "duplicate_rows": 0,
  "nonfinite_rows": 0
}
```

## Baseline result

- Symbols: AAL, AMD, BAC
- Trades: 8
- Return: -0.28%
- Sharpe: -2.08
- Profit factor: 0.34
- Expectancy: -0.34R
- Max drawdown: -0.51%
- Costs: $131.20

## Uncertainty

```json
{
  "status": "INSUFFICIENT",
  "n": 8
}
```

## Cost stress

| shock    |   total_return |   sharpe |   max_drawdown |   n_trades |   profit_factor |   total_costs |
|:---------|---------------:|---------:|---------------:|-----------:|----------------:|--------------:|
| costs x1 |    -0.00278261 | -2.08116 |    -0.00513174 |          8 |       0.341743  |       131.2   |
| costs x2 |    -0.00349804 | -2.57457 |    -0.00560596 |          8 |       0.24565   |       202.959 |
| costs x5 |    -0.00510544 | -4.35236 |    -0.00600215 |          6 |       0.0780048 |       294.169 |

## Slippage stress

| shock       |   total_return |   sharpe |   max_drawdown |   n_trades |
|:------------|---------------:|---------:|---------------:|-----------:|
| slippage x1 |    -0.00278261 | -2.08116 |    -0.00513174 |          8 |
| slippage x2 |    -0.00412611 | -3.51585 |    -0.00586698 |          7 |

## Latency stress

| shock          |   total_return |   sharpe |   max_drawdown |   n_trades |
|:---------------|---------------:|---------:|---------------:|-----------:|
| latency 0 bars |    -0.00278261 | -2.08116 |    -0.00513174 |          8 |
| latency 1 bars |    -0.00650779 | -4.01802 |    -0.0079204  |         13 |

This holdout is now contaminated and cannot be reused for tuning.
