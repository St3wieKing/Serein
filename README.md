# Serein

An institutional-grade, adaptive, autonomous **trading-research framework**
built from first principles: research → hypothesize → implement →
backtest → stress-test → reject → refine → out-of-sample → paper → monitor.

> **Preserving capital comes before maximizing returns.**
> The system must be willing to conclude: *"There is no sufficiently
> attractive trade right now."* That is not failure. That is intelligence.

**Status: PAPER_TRADING_ONLY. Research + paper stages only.**
No live broker adapter exists. `PAPER_TRADING_ONLY = True` is a hard
constant.

## What is in this repository

| Area | Where |
|---|---|
| Research decision log (335 Q&A) | `research/decision_log/` |
| Public-method analyses | `research/athena_analysis.md`, `research/matthew_scriv_analysis.md` |
| Literature, books & source register | `research/literature_notes.md`, `research/trading_book_analysis.md`, `research/source_register.md` |
| Strategy hypothesis/component matrices | `research/strategy_matrix.md`, `research/component_library_v2.md` |
| Strategy v2 final rebuild report | `docs/FINAL_REBUILD_REPORT.md` |
| Quantum Athena account forensics + safe proxy | `docs/QUANTUM_ATHENA_FORENSIC_REPORT.md`, `scripts/analyze_quantum_athena.py` |
| Quant-fund research + institutional intraday system | `research/quant_fund_research.md`, `docs/INSTITUTIONAL_INTRADAY_REPORT.md`, `scripts/run_institutional_intraday.py` |
| Three-round 1,500-question recursive audit | `research/recursive_review/`, `docs/RECURSIVE_REVIEW_IMPLEMENTATION.md` |
| Master 520-question inquiry + final 1,000 adversarial challenge | `research/master_questions/` |
| Complete autopsy + autonomous platform result | `docs/SYSTEM_AUTOPSY_REPORT.md`, `docs/AUTONOMOUS_PLATFORM_REPORT.md` |
| Core package | `serein/` (data, features, regimes, strategies, meta, risk, backtest, ML, drift, registries, execution, reporting, dashboard) |
| Full research pipeline | `scripts/run_research.py` |
| Test suite (137 passing, 1 skipped) | `tests/` |
| Architecture / security / deployment / failure docs | `docs/` |
| Run artifacts (report, dashboard, registries) | `artifacts/` (gitignored) |

## Architecture in one line

```
data → strategy engines → meta decision → RISK ENGINE (ultimate authority)
     → order validation → paper broker
```

The Risk Engine is structurally unbypassable; kill switches stop new
trades on data/execution/broker/model/drawdown/volatility/anomaly
failures; position sizing is risk-budget based with **no martingale
path**; every decision is journaled.

## Honest results so far (SYNTHETIC data only)

No strategy is approved. Earlier v0/v1 numerical reports are marked superseded
because the system autopsy found that reported exit slippage did not alter exit
cash/P&L. The correction made all current intraday candidates weaker: the
validation-selected ML model lost −0.13% in locked synthetic OOS; the post-OOS
opening-range challenger gained +1.07% but its bootstrap expectancy interval
includes zero, it failed 5× costs and 2× slippage reduced return to effectively
zero. Direct ML direction models remain near chance.

**These results validate the engineering, not an edge.** No claim about
real markets is made. The framework's job is to find out whether a
robust edge exists — not to manufacture the appearance of one.

## Quickstart

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/run_research.py --quick      # v1 smoke run
.venv/bin/python scripts/rebuild_strategy.py          # v2 controlled quick run
.venv/bin/python -m pytest tests/ -q                  # test suite
.venv/bin/python scripts/validate_questions.py     # decision-log check
```

Full run (`scripts/run_research.py`) takes ~20 minutes and writes
`artifacts/research_report.md` + `artifacts/dashboard.html`.

## The 20% weekly objective

Treated as an **aspirational research benchmark with a near-zero prior
at acceptable risk**. The risk system ignores return targets entirely:
no target-chasing, no leverage increases, no revenge sizing. If the
best honest strategy produces 3–8% under the risk budget, that is what
gets reported.

## Legal & age note

Live trading requires lawful authorization and brokerage eligibility.
This project does not bypass age/identity/broker requirements — the
correct behavior is to stop and report the requirement. The system
remains paper-only.

See `docs/` for architecture, security, deployment stages, and failure
recovery; `research/` for the full decision log and evidence base.
