"""Strategy tournament harness.

Every registered strategy is evaluated through the SAME pipeline:
  full-period backtest (risk engine in the loop)
  IS / OOS split
  cost shock (2x) and slippage shock (5x)
  per-subperiod performance matrix (feeds CSCV-PBO)

A transparent rank-based composite score ranks candidates; hard gates
(minimum trades in-sample and out-of-sample) filter un-testable ones.
Multiple-testing warning: the top of ANY leaderboard is inflated by
selection; the tournament-level PBO quantifies exactly that.

Parallelized with multiprocessing; bars/regimes/config are provided via
a module-level context set by the initializer.
"""

from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from ..config import BacktestConfig
from ..backtest.engine import Backtester
from ..backtest.stress import _shocked_config
from ..backtest.robustness import cscv_pbo

_CTX: dict = {}


def _init_worker(bars, regimes, cfg, symbols, split):
    _CTX["bars"] = bars
    _CTX["regimes"] = regimes
    _CTX["cfg"] = cfg
    _CTX["symbols"] = symbols
    _CTX["split"] = split


def _make_signals(strat) -> dict[str, pd.DataFrame]:
    if hasattr(strat, "generate_universe"):
        return strat.generate_universe(_CTX["bars"])
    return {s: strat.generate(_CTX["bars"][s], _CTX["regimes"][s])
            for s in _CTX["symbols"]}


def _sharpe_of(res) -> float:
    v = res.metrics.get("sharpe")
    return float(v) if v is not None and np.isfinite(v) else np.nan


def _evaluate_one(item):
    name, factory = item
    cfg = _CTX["cfg"]
    symbols = _CTX["symbols"]
    try:
        strat = factory()
        signals = _make_signals(strat)
    except Exception as e:  # noqa: BLE001
        return {"name": name, "error": str(e)}

    bars = _CTX["bars"]
    split = _CTX["split"]
    row: dict = {"name": name}

    res_full = Backtester(cfg).run(bars, signals)
    m = res_full.metrics
    row.update({
        "n_trades": m.get("n_trades", 0),
        "total_return": m.get("total_return", np.nan),
        "sharpe": _sharpe_of(res_full),
        "max_drawdown": m.get("max_drawdown", np.nan),
        "win_rate": m.get("win_rate", np.nan),
        "expectancy_r": m.get("expectancy_r", np.nan),
        "profit_factor": m.get("profit_factor", np.nan),
        "avg_bars_held": m.get("avg_bars_held", np.nan),
    })

    # IS / OOS
    is_bars = {s: b.loc[b.index < split] for s, b in bars.items()}
    oos_bars = {s: b.loc[b.index >= split] for s, b in bars.items()}
    res_is = Backtester(cfg).run(is_bars, signals)
    row["is_sharpe"] = _sharpe_of(res_is)
    row["is_return"] = res_is.metrics.get("total_return", np.nan)
    if any(len(b) > 0 for b in oos_bars.values()):
        res_oos = Backtester(cfg).run(oos_bars, signals)
        row["oos_sharpe"] = _sharpe_of(res_oos)
        row["oos_return"] = res_oos.metrics.get("total_return", np.nan)
        row["oos_trades"] = res_oos.metrics.get("n_trades", 0)
        row["oos_maxdd"] = res_oos.metrics.get("max_drawdown", np.nan)
    else:
        row.update({"oos_sharpe": np.nan, "oos_return": np.nan,
                    "oos_trades": 0, "oos_maxdd": np.nan})

    # cost / slippage shocks
    c2 = _shocked_config(cfg, cost_mult=2.0, slippage_mult=1.0)
    res_c2 = Backtester(c2).run(bars, signals)
    row["cost2x_sharpe"] = _sharpe_of(res_c2)
    s5 = _shocked_config(cfg, cost_mult=1.0, slippage_mult=5.0)
    res_s5 = Backtester(s5).run(bars, signals)
    row["slip5x_sharpe"] = _sharpe_of(res_s5)

    # per-subperiod performance (6 segments) for CSCV
    n = len(bars[symbols[0]])
    sub = []
    for seg in np.array_split(np.arange(n), 6):
        seg_bars = {s: b.iloc[seg] for s, b in bars.items()}
        r = Backtester(cfg).run(seg_bars, signals)
        sub.append(_sharpe_of(r))
    row["subperiods"] = sub
    row["tripped"] = res_full.risk_summary.get("tripped", [])
    return row


def run_tournament(
    zoo: dict[str, callable],
    bars: dict[str, pd.DataFrame],
    regimes: dict[str, pd.DataFrame],
    cfg: BacktestConfig,
    split,
    n_workers: int | None = None,
    min_trades: int = 25,
    min_oos_trades: int = 5,
) -> pd.DataFrame:
    """Run the full tournament. Returns the leaderboard DataFrame."""
    symbols = list(bars)
    workers = n_workers or min(8, os.cpu_count() or 4)
    items = list(zoo.items())
    with ProcessPoolExecutor(
        max_workers=workers,
        initializer=_init_worker,
        initargs=(bars, regimes, cfg, symbols, split),
    ) as ex:
        results = list(ex.map(_evaluate_one, items, chunksize=1))

    df = pd.DataFrame(results)
    if "error" in df.columns:
        bad = df[df["error"].notna()]
        for _, r in bad.iterrows():
            print(f"[tournament] ERROR {r['name']}: {r['error']}")
        df = df[df["error"].isna()].drop(columns=["error"])
    df = df.reset_index(drop=True)

    # ---- gates -------------------------------------------------------------
    df["pass_gates"] = (
        df["n_trades"].fillna(0).astype(int) >= min_trades
    ) & (df["oos_trades"].fillna(0).astype(int) >= min_oos_trades)

    # ---- composite score (rank-based, transparent) -------------------------
    def _rank_pct(col, higher_better=True):
        s = df[col]
        r = s.rank(pct=True)
        return r if higher_better else 1.0 - r

    score = (
        0.30 * _rank_pct("oos_sharpe")
        + 0.25 * _rank_pct("sharpe")
        + 0.15 * _rank_pct("cost2x_sharpe")
        + 0.15 * _rank_pct("slip5x_sharpe")
        + 0.15 * _rank_pct("max_drawdown", higher_better=False)
    )
    df["score"] = score.fillna(0.0).round(4)
    df = df.sort_values("score", ascending=False).reset_index(drop=True)
    return df


def tournament_pbo(leaderboard: pd.DataFrame, n_partitions: int = 6,
                   seed: int = 42) -> dict:
    """CSCV-PBO across the whole tournament: rows = strategies,
    columns = subperiods. Measures how much the 'best strategy' pick is
    overfit by construction."""
    valid = leaderboard[leaderboard["subperiods"].apply(
        lambda v: isinstance(v, list) and len(v) == 6)]
    M = pd.DataFrame(valid["subperiods"].tolist()).fillna(0.0)
    M.columns = [f"p{i}" for i in range(M.shape[1])]
    if M.shape[0] < 3 or M.shape[1] < 4:
        return {"pbo": np.nan, "note": "insufficient data"}
    res = cscv_pbo(M, n_partitions=n_partitions, max_trials=2000, seed=seed)
    return {
        "pbo": float(res.pbo),
        "logit": float(res.logit) if np.isfinite(res.logit) else None,
        "n_strategies": int(res.n_configs),
        "n_partitions": int(res.n_partitions),
        "best_in_sample": res.best_in_sample,
        "summary": res.summary(),
    }
