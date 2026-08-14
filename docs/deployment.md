# Serein — Deployment & Validation Stages

## Status: PAPER_TRADING_ONLY = TRUE; LIVE_EXECUTION_ENABLED = FALSE (hard-coded)

This project is in **research + paper** state. It must remain there
while:

- the strategy set is validated on real (non-synthetic) data,
- execution data is collected and compared to backtest assumptions,
- bugs and discrepancies are measured,
- legal/brokerage eligibility (including age and identity
  requirements) is confirmed — which the project **does not attempt to
  bypass**.

## Stage ladder (never skipped)

| Stage | What happens | Exit gate |
|---|---|---|
| 1. Historical research | hypotheses, literature, decision log | 520 structured master questions logged |
| 2. Backtesting | event-driven, costs, risk-in-loop | leakage audit + full metrics |
| 3. Walk-forward | locked params, embargo | OOS report |
| 4. Out-of-sample | locked period | minimum sample + stability |
| 5. Stress and red team | costs/slippage/vol/liquidity/latency/missing/attacks | degradation and failure tables |
| 6. Shadow mode | hypothetical decisions, structurally no orders | live-vs-research discrepancy |
| 7. Paper trading | approved PaperBroker gateway and simulated fills | 12-week paper evidence + slippage drift |
| 8. Controlled deployment (future) | only where lawful & authorized | independent certification and explicit authorization |
| 9. Live execution (not implemented) | no connector exists | remains FALSE in this repository |

The current codebase implements stage 1–5 tooling plus shadow/paper components,
but no real feed is connected and no strategy has passed the paper promotion
gate. Controlled deployment and live execution are unavailable.

## How to run

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/run_research.py          # full pipeline (synthetic)
.venv/bin/python scripts/run_research.py --quick  # small smoke run
.venv/bin/python scripts/validate_questions.py    # decision-log check
.venv/bin/python -m pytest tests/ -q              # test suite
```

Artifacts (report, dashboard, registries) are written to `artifacts/`
(gitignored).

## Paper-vs-backtest discrepancy analysis (the honest loop)

1. Backtest fills: bar-open ± cost model (deterministic).
2. Paper fills: same feed through PaperBroker (same cost model) — the
   loop validates the plumbing.
3. Shadow: hypothetical orders on live data without transmission —
   records predicted vs actual behavior.
4. Compare: fills, slippage, timing, drift. Any discrepancy is
   investigated before the next stage, never papered over.

## Real-data roadmap (what must change before real-data research)

1. Ingestion adapter with corporate actions, delisted names, point-in-
   time universes (survivorship-bias requirement).
2. Data versioning + immutable raw store.
3. Universe selection module (liquidity/spread/data-quality gates).
4. Re-run the entire gate ladder on real data with parameters LOCKED
   from the synthetic phase (no re-tuning on the new sample).

## Legal & age constraints

- Brokerage accounts have minimum-age and identity requirements;
  this project never attempts to circumvent them.
- If eligibility is absent, the correct system behavior is to **stop
  and report the requirement** — the system remains paper-only.
- No real-money deployment will be documented as "ready" without
  explicit operator confirmation of lawful authorization.
