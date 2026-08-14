"""Stress testing: the system must survive the world being worse than assumed.

Every candidate strategy is subjected to:
  * transaction-cost shocks (2x, 5x, 10x)
  * slippage shocks (2x, 5x, 10x)
  * volatility shocks (scaled data)
  * liquidity shocks (scaled volume)
  * latency (delayed decision -> execution k bars later)
  * missing data (random and clustered)
  * parameter perturbation
  * adversarial sequencing (bound, clearly labeled as a bound)

Stress results are reported as degradation tables, never as "proof".
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..config import BacktestConfig, CostModel
from .engine import Backtester


def stress_costs(
    bars: dict[str, pd.DataFrame],
    signals: dict[str, pd.DataFrame],
    cfg: BacktestConfig,
    multipliers=(1.0, 2.0, 5.0, 10.0),
) -> pd.DataFrame:
    rows = []
    for mult in multipliers:
        c = _shocked_config(cfg, cost_mult=mult)
        res = Backtester(c).run(bars, signals)
        rows.append({
            "shock": f"costs x{mult:g}",
            "total_return": res.metrics["total_return"],
            "sharpe": res.metrics["sharpe"],
            "max_drawdown": res.metrics["max_drawdown"],
            "n_trades": res.metrics["n_trades"],
            "profit_factor": res.metrics["profit_factor"],
            "total_costs": res.metrics.get("costs_total", 0),
        })
    return pd.DataFrame(rows)


def stress_slippage(
    bars, signals, cfg, multipliers=(1.0, 2.0, 5.0, 10.0),
) -> pd.DataFrame:
    rows = []
    for mult in multipliers:
        c = _shocked_config(cfg, slippage_mult=mult)
        res = Backtester(c).run(bars, signals)
        rows.append({
            "shock": f"slippage x{mult:g}",
            "total_return": res.metrics["total_return"],
            "sharpe": res.metrics["sharpe"],
            "max_drawdown": res.metrics["max_drawdown"],
            "n_trades": res.metrics["n_trades"],
        })
    return pd.DataFrame(rows)


def stress_volatility(
    bars: dict[str, pd.DataFrame],
    signals: dict[str, pd.DataFrame],
    cfg: BacktestConfig,
    factors=(1.0, 1.5, 2.0, 3.0),
) -> pd.DataFrame:
    """Rescale bar returns by `factor` (vol shock), rerun backtest."""
    rows = []
    for f in factors:
        shocked = {s: _scale_vol(b, f) for s, b in bars.items()}
        res = Backtester(cfg).run(shocked, signals)
        rows.append({
            "shock": f"vol x{f:g}",
            "total_return": res.metrics["total_return"],
            "sharpe": res.metrics["sharpe"],
            "max_drawdown": res.metrics["max_drawdown"],
            "n_trades": res.metrics["n_trades"],
        })
    return pd.DataFrame(rows)


def stress_liquidity(
    bars, signals, cfg, factors=(1.0, 0.5, 0.2, 0.1),
) -> pd.DataFrame:
    """Scale volume down (impact rises), rerun backtest."""
    rows = []
    for f in factors:
        shocked = {s: _scale_volume(b, f) for s, b in bars.items()}
        res = Backtester(cfg).run(shocked, signals)
        rows.append({
            "shock": f"liquidity x{f:g}",
            "total_return": res.metrics["total_return"],
            "sharpe": res.metrics["sharpe"],
            "max_drawdown": res.metrics["max_drawdown"],
            "n_trades": res.metrics["n_trades"],
        })
    return pd.DataFrame(rows)


def stress_latency(
    bars, signals, cfg, delays=(0, 1, 3, 6),
) -> pd.DataFrame:
    """Delay every decision by k bars (signal row used k bars later)."""
    rows = []
    for k in delays:
        shifted = {s: sig.shift(k) for s, sig in signals.items()}
        shifted = {s: sig.dropna() for s, sig in shifted.items()}
        res = Backtester(cfg).run(bars, shifted)
        rows.append({
            "shock": f"latency {k} bars",
            "total_return": res.metrics["total_return"],
            "sharpe": res.metrics["sharpe"],
            "max_drawdown": res.metrics["max_drawdown"],
            "n_trades": res.metrics["n_trades"],
        })
    return pd.DataFrame(rows)


def stress_missing_data(
    bars, signals, cfg,
    random_frac=(0.0, 0.01, 0.05),
    cluster_frac=(0.0, 0.05),
    seed: int = 3,
) -> pd.DataFrame:
    """Drop bars randomly / in clusters from ONE symbol; rerun."""
    rows = []
    rng = np.random.default_rng(seed)
    sym = list(bars)[0]
    base = bars[sym]
    n = len(base)
    def row(shock, res):
        return {"shock": shock,
                "total_return": res.metrics["total_return"],
                "sharpe": res.metrics["sharpe"],
                "max_drawdown": res.metrics["max_drawdown"],
                "n_trades": res.metrics["n_trades"]}

    for frac in random_frac:
        if frac == 0:
            res = Backtester(cfg).run(bars, signals)
            rows.append(row(f"missing random {frac:.0%}", res))
            continue
        drop = rng.choice(n, int(n * frac), replace=False)
        b2 = base.drop(index=base.index[drop])
        bars2 = {**bars, sym: b2}
        res = Backtester(cfg).run(bars2, signals)
        rows.append(row(f"missing random {frac:.0%}", res))
    for frac in cluster_frac:
        if frac == 0:
            continue
        n_clusters = 3
        cluster_len = max(int(n * frac / n_clusters), 1)
        drop = []
        for _ in range(n_clusters):
            start = int(rng.integers(0, n - cluster_len))
            drop.extend(range(start, start + cluster_len))
        b2 = base.drop(index=base.index[sorted(set(drop))])
        bars2 = {**bars, sym: b2}
        res = Backtester(cfg).run(bars2, signals)
        rows.append(row(f"missing clustered {frac:.0%}", res))
    return pd.DataFrame(rows)


def worst_case_sequence_bound(trades: pd.DataFrame) -> dict:
    """Adversarial bound: what if ALL losses come before ALL wins?

    This is NOT a simulation — it is a worst-case ordering bound to expose
    the strategy's structural dependence on win/loss sequencing.
    """
    if len(trades) == 0:
        return {"bound_max_drawdown_pct": np.nan, "note": "no trades"}
    pnl = trades["pnl"].to_numpy()
    pnl_sorted = np.sort(pnl)  # losses first
    cum = np.cumsum(pnl_sorted)
    equity = trades["equity_at_entry"].iloc[0] if len(trades) else 1.0
    return {
        "bound_max_drawdown_pct": float(-cum.min() / equity),
        "note": "adversarial worst-case ordering bound (not a simulation)",
        "sum_losses": float(-pnl[pnl < 0].sum()),
    }


def stress_parameter_perturbation(
    make_strategy, base_params: dict, bars, regime, cfg,
    frac: float = 0.15, n: int = 15, seed: int = 7,
) -> pd.DataFrame:
    from .robustness import perturb_params
    rows = []
    for i, p in enumerate(perturb_params(base_params, frac=frac, seed=seed, n=n)):
        strat = make_strategy(p)
        signals = {s: strat.generate(bars[s], regime) for s in bars}
        res = Backtester(cfg).run(bars, signals)
        rows.append({
            "perturbation": i,
            "sharpe": res.metrics["sharpe"],
            "total_return": res.metrics["total_return"],
            "max_drawdown": res.metrics["max_drawdown"],
            "n_trades": res.metrics["n_trades"],
        })
    df = pd.DataFrame(rows)
    return df


# ------------------------------------------------------------------ helpers
def _shocked_config(cfg: BacktestConfig, cost_mult: float = 1.0,
                    slippage_mult: float = 1.0) -> BacktestConfig:
    import copy
    c = copy.deepcopy(cfg)
    c.costs = CostModel(
        commission_per_share=cfg.costs.commission_per_share * cost_mult,
        half_spread_bps=cfg.costs.half_spread_bps * cost_mult * slippage_mult,
        slippage_bps=cfg.costs.slippage_bps * slippage_mult,
        impact_coeff=cfg.costs.impact_coeff * cost_mult,
    )
    return c


def _scale_vol(bars: pd.DataFrame, factor: float) -> pd.DataFrame:
    if factor == 1.0:
        return bars
    b = bars.copy()
    ret = b["close"].pct_change().fillna(0.0)
    shocked_ret = ret * factor
    b["close"] = b["close"].iloc[0] * np.exp(np.cumsum(np.log1p(shocked_ret)))
    # rebuild OHLC crudely from shocked close + original intraday ranges
    rng = (b["high"] - b["low"]) / b["close"].shift(1).replace(0, np.nan)
    rng = rng.fillna(0.01) * factor
    prev_close = b["close"].shift(1).fillna(b["close"])
    b["open"] = prev_close
    b["high"] = np.maximum(b["open"], b["close"]) * (1 + rng.abs() / 2)
    b["low"] = np.minimum(b["open"], b["close"]) * (1 - rng.abs() / 2)
    return b


def _scale_volume(bars: pd.DataFrame, factor: float) -> pd.DataFrame:
    b = bars.copy()
    b["volume"] = b["volume"] * factor
    return b
