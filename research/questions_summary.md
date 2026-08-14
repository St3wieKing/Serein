# Research Decision Log — Summary

The full decision log contains **335 questions** across 12 categories
(see `decision_log/01_market.md` … `decision_log/12_failure_modes.md`).
Each entry: question, current best answer, confidence (H/M/L), and the
experiment that could change the conclusion.

| Category | Count |
|---|---|
| Market | 40 |
| Strategy | 50 |
| Risk | 40 |
| Machine Learning | 40 |
| Backtesting | 30 |
| Execution | 25 |
| Data | 20 |
| Software Architecture | 20 |
| Adaptation | 20 |
| Security | 15 |
| Monitoring | 15 |
| Failure Modes | 20 |
| **Total** | **335** |

Validate/regenerate the count:

```bash
.venv/bin/python scripts/validate_questions.py
```

## The ten most load-bearing answers (condensed)

1. **Is there a retail-scale tradable edge?** Unknown; prior strongly
   negative (70–95% of day traders lose; ~1% persistently profitable).
2. **Do backtests prove anything alone?** No; selection manufactures
   winners (PBO/CSCV literature). Every result is OOS/WFA + stress +
   PBO gated.
3. **Does the current feature set predict direction?** No — OOS AUC
   0.503–0.509 vs base rate 0.503 across LR/RF/GBM. Feature research is
   the bottleneck, not model capacity.
4. **Does the current rule ensemble profit after costs?** Marginally on
   synthetic (+2.9% over 8y, Sharpe 0.09), negative OOS (−2.8%, 8
   trades). Not approvable at this sample.
5. **Who controls risk?** The Risk Engine, structurally — kill
   switches, daily/weekly limits, exposure caps, no-martingale
   construction. No model can bypass it.
6. **How much can a single trade lose?** ~≤1% of equity by design
   (0.5% risk budget × 1.5 confidence multiplier); gaps and slippage
   can exceed it, which is why gap-through-stops are modeled and
   stressed.
7. **What kills strategies fastest?** Costs (2x kills most intraday
   edges), latency (6-bar delay eroded the synthetic edge), and
   selection overfitting (PBO).
8. **When is the system allowed to adapt?** Only through gated,
   logged, statistically justified updates — never after one bad week,
   never to chase the 20% target.
9. **What is the 20% weekly objective?** An aspirational benchmark with
   near-zero prior at acceptable risk; the risk system ignores it.
   Honest expectation: single-digit % per month at best until evidence
   says otherwise.
10. **What does "working" mean?** Positive expectancy after realistic
    costs, stable across regimes and parameter neighborhoods, with
    bounded drawdowns — measured over hundreds of trades, not one week.
