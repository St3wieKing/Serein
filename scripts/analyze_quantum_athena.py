#!/usr/bin/env python3
"""Reproduce the public-sample forensic analysis and safe-proxy smoke test."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from serein.backtest.engine import Backtester
from serein.config import BacktestConfig
from serein.data.synthetic import generate_ohclv
from serein.research.trade_forensics import analyze_trades, load_trade_export
from serein.strategies.athena_observed import QuantumAthenaSafeProxy


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trades", default=str(ROOT/"research"/"quantum_athena_public_sample.csv"),
                    help="SignalStart/Myfxbook CSV export; defaults to the ten public rows captured 2026-08-14")
    ap.add_argument("--full-history", action="store_true",
                    help="mark input as complete rather than partial")
    args = ap.parse_args()
    f = analyze_trades(load_trade_export(args.trades), partial_history=not args.full_history)

    # Engineering smoke test only. This is not historical XAUUSD and cannot
    # validate or refute the proprietary EA.
    bars, _ = generate_ohclv(30_000, freq="5min", seed=88, start="2024-01-01")
    cfg = BacktestConfig(freq="5min", initial_equity=100_000,
                         max_holding_bars=12, allow_shorts=False)
    strat = QuantumAthenaSafeProxy()
    sig = strat.generate(bars)
    result = Backtester(cfg).run({"XAUUSD": bars}, {"XAUUSD": sig})
    out = {
        "public_trade_forensics": f.to_dict(),
        "safe_proxy_synthetic_smoke_test": {
            k: result.metrics.get(k) for k in
            ("n_trades", "win_rate", "total_return", "sharpe", "max_drawdown",
             "profit_factor", "expectancy_r", "costs_total", "weekly_mean")
        },
        "warning": "Safe proxy is not Quantum Athena; synthetic smoke test is not market evidence.",
    }
    (ROOT/"artifacts").mkdir(exist_ok=True)
    (ROOT/"artifacts"/"quantum_athena_forensics.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
