"""Feature engineering library.

Design rule (complexity penalty): a feature only earns its place if an
ablation test shows incremental value. This module provides a broad menu;
feature selection happens per experiment, never by defaulting to everything.

All features are causal: each row uses only data available at that bar's
CLOSE. No centered windows, no future values.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import constants as C


def atr(bars: pd.DataFrame, n: int = 14) -> pd.Series:
    """Wilder-style ATR (approximated with simple mean of true range)."""
    prev_close = bars["close"].shift(1)
    tr = pd.concat(
        [
            bars["high"] - bars["low"],
            (bars["high"] - prev_close).abs(),
            (bars["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(n, min_periods=n).mean()


def realized_vol(bars: pd.DataFrame, n: int = 20) -> pd.Series:
    return bars["close"].pct_change().rolling(n, min_periods=n).std()


def percentile_rank(s: pd.Series, n: int = 250) -> pd.Series:
    """Rolling percentile rank of s within the trailing n observations."""
    return s.rolling(n, min_periods=n).rank(pct=True)


def vwap(bars: pd.DataFrame, n: int = 40) -> pd.Series:
    tp = (bars["high"] + bars["low"] + bars["close"]) / 3.0
    pv = (tp * bars["volume"]).rolling(n, min_periods=n).sum()
    v = bars["volume"].rolling(n, min_periods=n).sum()
    return pv / v.replace(0, np.nan)


def zscore(s: pd.Series, n: int = 60) -> pd.Series:
    mean = s.rolling(n, min_periods=n).mean()
    std = s.rolling(n, min_periods=n).std()
    return (s - mean) / std.replace(0, np.nan)


def build_features(
    bars: pd.DataFrame,
    horizons: tuple[int, ...] = (1, 6, 24),
    include_time: bool = True,
    include_volume: bool = True,
    regime_series: pd.Series | None = None,
) -> pd.DataFrame:
    """Build the causal feature matrix for one symbol.

    Args:
        bars: OHLCV DataFrame (index DatetimeIndex)
        horizons: return horizons in bars
        include_time: add time-of-day / day-of-week / session features
        include_volume: add relative-volume features
        regime_series: optional regime labels aligned to bars.index
                       (used for regime-conditional features)
    """
    close = bars["close"]
    ret = close.pct_change()
    log_ret = np.log(close / close.shift(1))
    f = pd.DataFrame(index=bars.index)

    # --- price / return features ---
    for h in horizons:
        f[f"ret_{h}"] = close.pct_change(h)
    f["log_ret_1"] = log_ret
    f["ret_abs_1"] = log_ret.abs()
    f["rng_1"] = (bars["high"] - bars["low"]) / close
    f["gap_1"] = (bars["open"] - close.shift(1)) / close.shift(1)

    # --- volatility family ---
    for n in (10, 20, 60):
        f[f"vol_{n}"] = realized_vol(bars, n)
        f[f"vol_{n}_pct"] = percentile_rank(f[f"vol_{n}"], 500)
    f["atr_14"] = atr(bars, 14)
    f["atr_14_pct"] = percentile_rank(f["atr_14"], 500)
    f["vol_expansion"] = f["vol_10"] / f["vol_60"].replace(0, np.nan)

    # --- trend / momentum family ---
    for n in (20, 60, 120):
        f[f"ma_{n}"] = close.rolling(n, min_periods=n).mean()
        f[f"dist_ma_{n}"] = (close - f[f"ma_{n}"]) / f[f"ma_{n}"]
    for n in (20, 60, 120):
        f[f"mom_{n}"] = close.pct_change(n)
    f["mom_accel"] = f["mom_20"] - f["mom_20"].shift(5)

    # --- mean reversion family ---
    f["z_close_60"] = zscore(close, 60)
    f["z_close_120"] = zscore(close, 120)
    f["vwap_40"] = vwap(bars, 40)
    f["dist_vwap_40"] = (close - f["vwap_40"]) / f["vwap_40"].replace(0, np.nan)

    # --- volume family ---
    if include_volume:
        v = bars["volume"]
        f["rel_vol_20"] = v / v.rolling(20, min_periods=20).mean().replace(0, np.nan)
        f["rel_vol_60"] = v / v.rolling(60, min_periods=60).mean().replace(0, np.nan)
        f["vol_accel"] = f["rel_vol_20"] - f["rel_vol_20"].shift(5)

    # --- time family ---
    if include_time:
        idx = bars.index
        f["hour"] = idx.hour
        f["dow"] = idx.dayofweek
        f["month"] = idx.month
        f["session"] = _session(idx).astype("category").cat.codes

    # --- regime-conditional features ---
    if regime_series is not None:
        reg = regime_series.reindex(bars.index).ffill()
        for r in ("bull_trend", "bear_trend", "high_vol", "sideways"):
            f[f"regime_{r}"] = (reg == r).astype(float)

    f.attrs["symbol"] = bars.attrs.get("symbol", "")
    return f


def _session(idx: pd.DatetimeIndex) -> pd.Series:
    """Coarse session label by local hour (US-equity-ish calendar)."""
    hour = idx.hour
    s = pd.Series(C.SESSION_MIDDAY, index=idx)
    s[hour < 9] = C.SESSION_PRE
    s[(hour >= 9) & (hour < 10)] = C.SESSION_OPEN
    s[(hour >= 10) & (hour < 14)] = C.SESSION_MIDDAY
    s[(hour >= 14) & (hour < 16)] = C.SESSION_AFTERNOON
    s[(hour >= 16) & (hour < 20)] = C.SESSION_CLOSE
    s[hour >= 20] = C.SESSION_POST
    return s


def make_labels(bars: pd.DataFrame, horizon: int = 6, mode: str = "ternary") -> pd.DataFrame:
    """Causal labels for supervised learning.

    label[t] describes the return from close[t] to close[t+horizon].
    The label at row t is only knowable AFTER time t (shifted by construction:
    we compute forward return and store it at t — the AUDIT verifies this).

    mode:
      'sign'    -> +1 / 0 / -1  (up / flat / down)
      'binary'  -> 1 if fwd return > 0 else 0
      'regression' -> forward return (float)
    """
    fwd = bars["close"].shift(-horizon) / bars["close"] - 1.0
    if mode == "regression":
        return fwd.to_frame(name="fwd_ret")
    if mode == "binary":
        return (fwd > 0).astype(int).to_frame(name="label")
    # ternary
    thr = 0.5 * bars["close"].pct_change(horizon).std()
    lab = pd.Series(0, index=bars.index)
    lab[fwd > thr] = 1
    lab[fwd < -thr] = -1
    return lab.to_frame(name="label")
