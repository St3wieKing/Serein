# Public Intraday External Evaluation

**Evidence:** real historical trade bars from a public GitHub repository that
states Alpha Vantage provenance; source files were malformed concatenations and
were strictly cleaned. Source: `chemicoPy/SP500-data` on GitHub. The repository
does not establish institutional data quality or NBBO provenance. This is
UNVERIFIED research data, not licensed NBBO.

**Holdout:** last 40 common complete sessions, sealed then revealed once.  
**Fingerprint:** `0b866a9e5be9c12fb3ac44c35ed6764e8e60747fc0daffb90343c166bf99156a`  
**Ledger valid:** True  
**Decision:** **REJECTED** — fewer than 100 OOS trades, profit factor gate, expectancy lower bound not positive, 2x costs failed, 2x slippage failed, public source is unverified/revised and has no bid-ask quotes, no paper-forward evidence.

## Data report

```json
{
  "symbols": [
    "AAPL",
    "JPM"
  ],
  "rows": 22464,
  "start": "2020-01-10 09:30:00-05:00",
  "end": "2021-03-10 15:55:00-05:00",
  "source_timezone": "America/New_York",
  "market_timezone": "America/New_York",
  "out_of_session_removed": 0,
  "missing_session_bars": 0,
  "duplicate_rows": 0,
  "nonfinite_rows": 0
}
```

## Baseline result

- Symbols: AAPL, JPM
- Trades: 4
- Return: -0.14%
- Sharpe: -2.39
- Profit factor: 0.28
- Expectancy: -0.51R
- Max drawdown: -0.19%
- Costs: $52.12

## Uncertainty

```json
{
  "status": "INSUFFICIENT",
  "n": 4
}
```

## Cost stress

| shock    |   total_return |   sharpe |   max_drawdown |   n_trades |   profit_factor |   total_costs |
|:---------|---------------:|---------:|---------------:|-----------:|----------------:|--------------:|
| costs x1 |    -0.00136756 | -2.38536 |    -0.00190677 |          4 |        0.282788 |       52.1195 |
| costs x2 |    -0.00161481 | -2.78139 |    -0.00208956 |          4 |        0.225534 |       76.8449 |
| costs x5 |    -0.00235657 | -3.83207 |    -0.00272849 |          4 |        0.100529 |      151.021  |

## Slippage stress

| shock       |   total_return |   sharpe |   max_drawdown |   n_trades |
|:------------|---------------:|---------:|---------------:|-----------:|
| slippage x1 |    -0.00136756 | -2.38536 |    -0.00190677 |          4 |
| slippage x2 |    -0.00184695 | -3.13289 |    -0.00228614 |          4 |

## Latency stress

| shock          |   total_return |   sharpe |   max_drawdown |   n_trades |
|:---------------|---------------:|---------:|---------------:|-----------:|
| latency 0 bars |    -0.00136756 | -2.38536 |    -0.00190677 |          4 |
| latency 1 bars |    -0.00142729 | -2.40274 |    -0.00187991 |          4 |

This holdout is now contaminated and cannot be reused for tuning.
