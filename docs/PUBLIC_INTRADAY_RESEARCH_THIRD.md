# Third Public Intraday Research Cycle

**Data:** public, unverified Alpha-Vantage-derived fragments for C, CAT and
CSCO; 119 common complete five-minute sessions after strict cleaning.  
**Training period:** first 79 common sessions.  
**Reserved holdout:** last 40 sessions, fingerprint
`0ccfe5433e42eabfda041b1bafb7d69425ae138db52e8bdacdd4eab539849a12`.  
**Holdout state:** **SEALED / NOT REVEALED**.

## Training results

| Predeclared setup | Trades | Return | Sharpe | PF | Expectancy |
|---|---:|---:|---:|---:|---:|
| Opening-range continuation | 0 | 0.00% | n/a | 0.00 | 0.00R |
| VWAP pullback | 1 | −0.0004% | −0.01 | 0.00 | −0.005R |
| VWAP reversion | 4 | −0.22% | −3.12 | 0.00 | −0.98R |

## Decision

**REJECT ALL TRAINING CANDIDATES. DO NOT OPEN THE HOLDOUT.**

None reached even a minimal sample or positive training gate. Looking at the
reserved period would consume OOS evidence without a candidate worthy of test.
This is the intended autonomous behavior: stop research on this data rather than
searching combinations until something looks profitable.
