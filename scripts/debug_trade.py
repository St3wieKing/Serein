"""Debug: trace the single trade and equity curve to find the P&L discrepancy."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from serein.config import load_config
from serein.data.synthetic import generate_ohclv
from serein.regimes import RegimeEngine
from serein.strategies.classic import TrendStrategy
from serein.backtest.engine import Backtester

cfg = load_config("config/research_config.json")
bars, true_reg = generate_ohclv(4000, seed=42, start="2019-01-01")
re = RegimeEngine()
reg = re.classify_series(bars)
strat = TrendStrategy({"trend_fast": 20, "trend_slow": 60})
sig = strat.generate(bars, reg)
print("signal rows nonzero:", int((sig["direction"] != 0).sum()))
print("expected_R describe:", sig["expected_R"].describe().to_dict())

res = Backtester(cfg).run({"SYNTH-A": bars}, {"SYNTH-A": sig})
print("\n--- trades ---")
print(res.trades.to_string())
print("\n--- risk ---", res.risk_summary)
eq = res.equity_curve["equity"]
print("equity first 5:", eq.head().to_dict())
print("equity last 5:", eq.tail().to_dict())
print("min equity:", eq.min(), "at", eq.idxmin())
t = res.trades.iloc[0]
et, xt = t["entry_time"], t["exit_time"]
print("\n--- equity around trade ---")
print(eq.loc[et - pd.Timedelta("2h"): xt + pd.Timedelta("2h")].to_string())
