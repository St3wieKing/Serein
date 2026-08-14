"""Block-bootstrap uncertainty intervals for dependent strategy returns."""
from __future__ import annotations

import numpy as np
import pandas as pd


def block_bootstrap_equity(equity: pd.Series, *, freq: str = "D", block: int = 5,
                           n_boot: int = 2000, seed: int = 42) -> dict:
    sampled = equity.resample(freq).last().dropna().pct_change().dropna().to_numpy()
    if len(sampled) < max(20, 2*block):
        return {"status": "INSUFFICIENT", "n": int(len(sampled))}
    rng = np.random.default_rng(seed)
    starts = np.arange(0, len(sampled)-block+1)
    finals = np.empty(n_boot); maxdds = np.empty(n_boot)
    for j in range(n_boot):
        chunks = []
        while sum(map(len, chunks)) < len(sampled):
            i = rng.choice(starts); chunks.append(sampled[i:i+block])
        r = np.concatenate(chunks)[:len(sampled)]
        path = np.cumprod(1+r); peak = np.maximum.accumulate(path)
        finals[j] = path[-1]-1; maxdds[j] = np.min(path/peak-1)
    lo, med, hi = np.quantile(finals, [.025, .5, .975])
    dd_lo, dd_med, dd_hi = np.quantile(maxdds, [.025, .5, .975])
    return {"status": "OK", "n": int(len(sampled)), "block": block,
            "n_boot": n_boot, "return_ci95": [float(lo), float(hi)],
            "return_median": float(med), "p_return_le_zero": float((finals <= 0).mean()),
            "maxdd_ci95": [float(dd_lo), float(dd_hi)],
            "maxdd_median": float(dd_med)}


def trade_expectancy_bootstrap(trades: pd.DataFrame, *, n_boot: int = 5000,
                               seed: int = 42) -> dict:
    if len(trades) < 30:
        return {"status": "INSUFFICIENT", "n": int(len(trades))}
    risk = (trades.entry_price-trades.stop).abs()*trades.qty
    r = (trades.pnl/risk.replace(0, np.nan)).dropna().to_numpy()
    if len(r) < 30:
        return {"status": "INSUFFICIENT", "n": int(len(r))}
    rng = np.random.default_rng(seed)
    means = rng.choice(r, size=(n_boot, len(r)), replace=True).mean(axis=1)
    lo, hi = np.quantile(means, [.025, .975])
    return {"status": "OK", "n": int(len(r)), "mean_r": float(r.mean()),
            "ci95": [float(lo), float(hi)],
            "p_expectancy_le_zero": float((means <= 0).mean())}
