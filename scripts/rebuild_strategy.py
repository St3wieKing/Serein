#!/usr/bin/env python3
"""Controlled Strategy v2 rebuild experiments.

This is an engineering validation on synthetic data, not evidence of a real
market edge.  Parameters are declared before execution; every candidate receives
the same costs, risk engine, chronological split, and stress shocks.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from serein.backtest.engine import Backtester
from serein.backtest.stress import _shocked_config
from serein.config import BacktestConfig, load_config
from serein.data.synthetic import generate_universe
from serein.strategies.rebuild import (
    CompressionBreakoutV2Strategy, FailedBreakoutStrategy,
    TrendPullbackStrategy, VWAPReversionV2Strategy,
)

ART = ROOT / "artifacts"


def candidates():
    # A-D are the mandatory simplification experiment.  D is the core setup,
    # each earlier letter adds exactly one concept.
    return {
        "A_full": TrendPullbackStrategy({"use_trend": True, "use_volatility": True, "use_volume": True}),
        "B_no_volume": TrendPullbackStrategy({"use_trend": True, "use_volatility": True, "use_volume": False}),
        "C_trigger_trend": TrendPullbackStrategy({"use_trend": True, "use_volatility": False, "use_volume": False}),
        "D_core_trigger": TrendPullbackStrategy({"use_trend": False, "use_volatility": False, "use_volume": False}),
        "failed_breakout": FailedBreakoutStrategy(),
        "compression_breakout": CompressionBreakoutV2Strategy(),
        "vwap_reversion": VWAPReversionV2Strategy(),
    }


def _signals(strat, bars):
    return {s: strat.generate(b) for s, b in bars.items()}


def _run(cfg, bars, sig):
    return Backtester(cfg).run(bars, sig)


def _safe(v):
    return float(v) if v is not None and np.isfinite(v) else np.nan


def evaluate(name, strat, bars, cfg, split):
    sig = _signals(strat, bars)
    full = _run(cfg, bars, sig)
    is_b = {s: b[b.index < split] for s, b in bars.items()}
    oos_b = {s: b[b.index >= split] for s, b in bars.items()}
    ins = _run(cfg, is_b, sig)
    oos = _run(cfg, oos_b, sig)
    c2 = _run(_shocked_config(cfg, cost_mult=2.0), bars, sig)
    c5 = _run(_shocked_config(cfg, cost_mult=5.0), bars, sig)
    s5 = _run(_shocked_config(cfg, slippage_mult=5.0), bars, sig)
    m, mi, mo = full.metrics, ins.metrics, oos.metrics
    return {
        "name": name,
        "simplicity": getattr(strat, "simplicity", np.nan),
        "trades": m["n_trades"], "return": m["total_return"],
        "sharpe": _safe(m["sharpe"]), "max_dd": m["max_drawdown"],
        "expectancy_r": _safe(m["expectancy_r"]), "win_rate": m["win_rate"],
        "is_sharpe": _safe(mi["sharpe"]), "oos_sharpe": _safe(mo["sharpe"]),
        "oos_return": mo["total_return"], "oos_trades": mo["n_trades"],
        "cost2_sharpe": _safe(c2.metrics["sharpe"]),
        "cost5_sharpe": _safe(c5.metrics["sharpe"]),
        "slip5_sharpe": _safe(s5.metrics["sharpe"]),
        "risk_tripped": ",".join(full.risk_summary.get("tripped", [])),
    }


def walkforward(strat, bars, cfg, n_windows=4):
    """Locked-rule, expanding-boundary evaluation; no fitting occurs."""
    n = len(next(iter(bars.values())))
    edges = np.linspace(int(n*0.40), n, n_windows+1, dtype=int)
    sig = _signals(strat, bars)
    rows = []
    for i in range(n_windows):
        # A 24-bar embargo separates the notional research boundary and test.
        start, end = min(edges[i]+24, edges[i+1]), edges[i+1]
        test_b = {s: b.iloc[start:end] for s, b in bars.items()}
        r = _run(cfg, test_b, sig)
        rows.append({"window": i+1, "start": str(next(iter(test_b.values())).index[0]),
                     "end": str(next(iter(test_b.values())).index[-1]),
                     "trades": r.metrics["n_trades"], "return": r.metrics["total_return"],
                     "sharpe": _safe(r.metrics["sharpe"]),
                     "max_dd": r.metrics["max_drawdown"]})
    return rows


def report(df, wf, n_bars, split):
    show = df.copy()
    pct = ["return", "max_dd", "win_rate", "oos_return"]
    for c in pct:
        show[c] = show[c].map(lambda x: f"{x:.2%}")
    for c in ["simplicity", "sharpe", "expectancy_r", "is_sharpe", "oos_sharpe",
              "cost2_sharpe", "cost5_sharpe", "slip5_sharpe"]:
        show[c] = show[c].map(lambda x: "n/a" if pd.isna(x) else f"{x:.2f}")
    verdict = "NO CANDIDATE APPROVED"
    eligible = df[(df.oos_trades >= 25) & (df.oos_sharpe > 0.5) &
                  (df.cost2_sharpe > 0) & (df.slip5_sharpe > 0)]
    if len(eligible):
        verdict = "PAPER-TEST CHALLENGER ONLY: " + str(eligible.iloc[0]["name"])
    return f"""# Serein Strategy v2.0 — controlled rebuild experiment

**Label:** SYNTHETIC engineering experiment; no real-market performance claim.  
**Data:** {n_bars:,} hourly bars × 3 synthetic symbols.  
**Chronological boundary:** {split}. Parameters were declared before this run.

## Decision

**{verdict}.** A positive synthetic backtest is not proof of a tradable edge.
Promotion requires real, point-in-time data and a never-tuned holdout.

## Smallest viable edge / simplification test

A = full trend + pullback + trigger + volatility + volume; B removes volume;
C removes volume and volatility; D retains only pullback + trigger + structural
risk. Higher simplicity is better. The correct winner is the simplest version
whose OOS and stressed performance is not materially worse—not the highest raw return.

{show.to_markdown(index=False)}

## Locked-rule walk-forward windows (best eligible by OOS, or B fallback)

{pd.DataFrame(wf).to_markdown(index=False)}

## Promotion gates

- at least 25 OOS trades;
- OOS Sharpe > 0.50 (research gate, not a promise);
- positive at 2× costs and 5× slippage;
- no severe risk kill-switch dependency;
- broad parameter stability;
- replication on real point-in-time data;
- paper shadow test before any further stage.

## Limits

The generator contains planted trend/breakout behavior. Session VWAP is only a
mechanical test on continuous synthetic hourly bars, not a realistic exchange
session. News, L2/order flow, options, borrow, halts, and real spreads are absent.
Results therefore validate code paths, not alpha.
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true", help="26,500 rather than 7,000 bars")
    ap.add_argument("--config", default=str(ROOT/"config"/"research_config.json"))
    args = ap.parse_args()
    cfg = load_config(args.config) if Path(args.config).exists() else BacktestConfig()
    n = 26_500 if args.full else 7_000
    bars = generate_universe(["SYNTH-A", "SYNTH-B", "SYNTH-C"], periods=n,
                             freq=cfg.freq, seed=cfg.seed)
    split = next(iter(bars.values())).index[int(n*0.60)]
    rows = [evaluate(name, strat, bars, copy.deepcopy(cfg), split)
            for name, strat in candidates().items()]
    df = pd.DataFrame(rows).sort_values(["oos_sharpe", "simplicity"], ascending=False)
    viable = df[df.oos_trades >= 5]
    choice = str(viable.iloc[0]["name"]) if len(viable) else "B_no_volume"
    wf = walkforward(candidates()[choice], bars, cfg)
    ART.mkdir(exist_ok=True)
    df.to_csv(ART/"rebuild_results.csv", index=False)
    (ART/"rebuild_walkforward.json").write_text(json.dumps(wf, indent=2))
    text = report(df, wf, n, split)
    (ART/"rebuild_report.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
