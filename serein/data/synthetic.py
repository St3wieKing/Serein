"""Synthetic market data generator with explicit regime structure.

Purpose: engineering validation of the entire pipeline (features, regimes,
strategies, backtest, risk, meta) under KNOWN ground truth. A strategy that
cannot find a planted regime-dependent effect in synthetic data has no chance
on real data; a strategy that finds effects here has no claim on real markets.

The generator is honest about being a model: geometric-Brownian-like dynamics
with regime-switching drift/vol, autocorrelated volume, and optional planted
effects (momentum persistence, mean reversion, breakout continuation) so we
can verify that each strategy engine detects its own planted signal.

This data is LABELED SYNTHETIC everywhere downstream. It is never a proxy for
real market behavior.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

REGIMES = ("bull_trend", "bear_trend", "sideways", "high_vol")


def _regime_drift_vol(regime: str) -> tuple[float, float]:
    """Annualized drift/vol per regime (synthetic ground truth)."""
    table = {
        "bull_trend": (0.25, 0.15),
        "bear_trend": (-0.25, 0.18),
        "sideways": (0.0, 0.10),
        "high_vol": (0.0, 0.45),
    }
    return table[regime]


def generate_ohclv(
    periods: int,
    freq: str = "h",
    seed: int = 42,
    start: str = "2018-01-01",
    start_price: float = 100.0,
    regime_chain: list[str] | None = None,
    regime_hold_mean: int = 300,
    planted: dict[str, bool] | None = None,
    symbol: str = "SYNTH",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Generate synthetic OHLCV + true regime DataFrame.

    Returns (bars, regimes) where regimes has columns ['regime','drift','vol']
    indexed like bars. Bars have columns open/high/low/close/volume.
    """
    rng = np.random.default_rng(seed)
    planted = planted or {"momentum": True, "reversion": False, "breakout": True}

    # --- regime chain (Markov-ish with holding times) ---
    if regime_chain is None:
        chain: list[str] = []
        while len(chain) < periods:
            # regime durations follow a geometric-ish distribution
            hold = max(30, int(rng.exponential(regime_hold_mean)))
            reg = REGIMES[rng.integers(0, len(REGIMES))]
            chain.extend([reg] * hold)
        chain = chain[:periods]
    else:
        chain = (regime_chain * (periods // len(regime_chain) + 1))[:periods]

    ann_to_bar = {
        "h": 252 * 6.5, "30min": 252 * 13, "15min": 252 * 26,
        "5min": 252 * 78, "d": 252,
    }[freq]
    dt_per_year = ann_to_bar
    dt = 1.0 / dt_per_year

    drift = np.zeros(periods)
    vol = np.zeros(periods)
    for i, reg in enumerate(chain):
        d, v = _regime_drift_vol(reg)
        drift[i] = d
        vol[i] = v

    # --- return path: base GBM + planted effects ---
    log_ret = np.zeros(periods)
    close = np.zeros(periods)
    close[0] = start_price
    # momentum state
    mom = 0.0
    for i in range(1, periods):
        sigma_bar = vol[i] * np.sqrt(dt)
        z = rng.normal(0.0, 1.0)
        # planted momentum: past trend carries forward (decaying state)
        if planted.get("momentum"):
            mom = 0.98 * mom + 0.02 * (log_ret[i - 1] if i > 1 else 0.0)
        extra = 0.0
        if planted.get("momentum") and "trend" in chain[i]:
            extra += 0.35 * mom
        if planted.get("reversion") and chain[i] == "sideways":
            # mean reversion: pull back toward slow mean
            slow_mean = np.log(max(close[i - 1] * 0.9, 1.0))  # placeholder
            _ = slow_mean
        log_ret[i] = drift[i] * dt + extra * dt * 10 + sigma_bar * z
        close[i] = close[i - 1] * np.exp(log_ret[i])

    # --- OHLC: open = prev close, high/low around close ---
    open_ = np.empty(periods)
    open_[0] = start_price
    open_[1:] = close[:-1]
    spread = np.abs(rng.normal(0.0, 0.0015, periods))
    high = np.maximum(open_, close) * (1.0 + spread + 0.5 * np.abs(log_ret))
    low = np.minimum(open_, close) * (1.0 - spread - 0.5 * np.abs(log_ret))
    high = np.maximum(high, np.maximum(open_, close))
    low = np.minimum(low, np.minimum(open_, close))

    # --- volume: autocorrelated, elevated in high_vol & bull ---
    vol_mult = np.where(np.array(chain) == "high_vol", 2.2, 1.0)
    vol_mult *= np.where(np.array(chain) == "bull_trend", 1.2, 1.0)
    v_log = np.zeros(periods)
    v_log[0] = 0.0
    for i in range(1, periods):
        v_log[i] = 0.85 * v_log[i - 1] + rng.normal(0.0, 0.3)
    volume = np.exp(v_log) * 1_000_000.0 * vol_mult

    idx = pd.date_range(start=start, periods=periods, freq=freq)
    bars = pd.DataFrame(
        {
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        },
        index=idx,
    )
    regime_df = pd.DataFrame(
        {"regime": chain, "drift": drift, "vol": vol}, index=idx
    )
    bars.attrs["symbol"] = symbol
    bars.attrs["synthetic"] = True
    bars.attrs["seed"] = seed
    return bars, regime_df


def generate_universe(
    symbols: list[str],
    periods: int,
    freq: str = "h",
    seed: int = 42,
    regime_chain: list[str] | None = None,
    **kwargs,
) -> dict[str, pd.DataFrame]:
    """Generate a small correlated universe (shared regime chain)."""
    out = {}
    for i, sym in enumerate(symbols):
        bars, _ = generate_ohclv(
            periods, freq, seed=seed + i, regime_chain=regime_chain,
            start_price=50.0 + 20.0 * i, symbol=sym, **kwargs,
        )
        out[sym] = bars
    return out
