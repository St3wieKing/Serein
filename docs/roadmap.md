# Serein — Future Research Roadmap

Prioritized by value-of-information per unit cost. Nothing here is
"planned features" — each item is a hypothesis to be tested with the
same discipline as everything else.

## Phase A — evidence, not features (next)

1. **Real-data replication (highest priority).** Wire an ingestion
   adapter (corporate actions, delisted names, point-in-time
   universes) and re-run the ENTIRE gate ladder with parameters locked
   from the synthetic phase. The central open question: does anything
   survive on real data?
2. **Random-entry null benchmark.** Same risk engine, random signals —
   the correct null for "does the signal add anything".
3. **Buy-and-hold / benchmark comparison** in every report.
4. **Overnight vs intraday decomposition** on real data (gap risk
   quantification).

## Phase B — signal research

5. **Better labels:** triple-barrier / R-multiple labels (per
   López de Prado) vs horizon-sign; meta-labeling ("should we take this
   trade at all").
6. **Feature families:** order-flow imbalance (needs tick data),
   cross-asset/relative-strength features, calendar/event features.
7. **Event engine:** timestamped economic calendar; test avoidance vs
   post-event confirmation (never headline-trading).
8. **Horizon ladder:** 5m/15m/1h/4h/D experiments to find where any
   edge actually lives (holding-time optimization).
9. **Session decomposition:** open/midday/close behavior per strategy.
10. **Trailing stops & partial exits** (profit-protection research).

## Phase C — adaptation & portfolio

11. **Strategy health-score → automatic weight updates** with sample
    minimums and hysteresis (the manual weights are the interim).
12. **Correlation-aware exposure limits:** factor/sector concentration
    caps; rolling correlation monitor; stress-correlation sizing.
13. **Monte Carlo ruin analysis** and drawdown/streak distributions as
    standard risk output.
14. **Conformal prediction / uncertainty quantification** for sizing.
15. **Adaptation-speed study:** how fast is too fast / too slow, with
    false-positive audits of the drift detectors.

## Phase D — engineering hardening

16. **Shadow-mode loop** against a live feed (observe, never transmit).
17. **Purged-CV + PBO** wired into every ML experiment automatically.
18. **Replay engine** for debugging and manual review of any trade.
19. **LLM research agent + red team + independent review** — three
    separate processes with no execution authority, per the mandate.
20. **Hash-chained registries**, containerization, CI pipeline.
21. **Broker adapters** only after all gates pass and legal/brokerage
    eligibility is confirmed (never before).

## Explicitly out of scope (with reasons)

- **RL / deep RL:** reward-hacking risk, sample inefficiency, no
  demonstrated need (decision log 04).
- **LLM in the decision path:** deterministic controls only.
- **Live real-money trading:** requires authorization the project does
  not assume; PAPER_TRADING_ONLY stays hard-coded.
- **Chasing the 20% weekly target:** structurally ignored by the risk
  system.

## Success criteria (the only ones that count)

- Positive expectancy after realistic costs on real OOS data,
- stable across parameter neighborhoods and regimes,
- bounded drawdowns with functioning kill switches,
- PBO and leakage audits clean,
- measured over hundreds of trades,
- with the system freely reporting "no attractive trade" — including
  indefinitely.
