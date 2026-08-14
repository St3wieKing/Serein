"""Drift & performance-degradation detection.

Detects, with statistical discipline:
  * data drift  — input feature distributions change (PSI)
  * performance drift — rolling expectancy / win rate decay (CUSUM-lite)
  * execution drift — realized slippage vs expected

Any drift signal => REDUCE RISK -> INVESTIGATE -> REVALIDATE -> PAPER ->
REDEPLOY. Never "keep trading as usual".
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def psi(expected: np.ndarray, actual: np.ndarray, bins: int = 10) -> float:
    """Population Stability Index between two distributions."""
    expected = np.asarray(expected, dtype=float)
    actual = np.asarray(actual, dtype=float)
    if len(expected) == 0 or len(actual) == 0:
        return np.nan
    edges = np.percentile(expected, np.linspace(0, 100, bins + 1))
    edges[0], edges[-1] = -np.inf, np.inf
    e_hist, _ = np.histogram(expected, bins=edges)
    a_hist, _ = np.histogram(actual, bins=edges)
    e_pct = e_hist / len(expected)
    a_pct = a_hist / len(actual)
    e_pct = np.clip(e_pct, 1e-6, None)
    a_pct = np.clip(a_pct, 1e-6, None)
    return float(np.sum((a_pct - e_pct) * np.log(a_pct / e_pct)))


def feature_drift_report(train_features: pd.DataFrame,
                         live_features: pd.DataFrame,
                         alert_threshold: float = 0.25) -> pd.DataFrame:
    """Per-feature PSI between training and live distributions."""
    rows = []
    for col in train_features.columns:
        if col not in live_features.columns:
            continue
        s_train = train_features[col].dropna()
        s_live = live_features[col].dropna()
        if len(s_train) < 50 or len(s_live) < 50:
            continue
        p = psi(s_train.to_numpy(), s_live.to_numpy())
        rows.append({
            "feature": col,
            "psi": round(p, 4),
            "alert": p > alert_threshold,
        })
    df = pd.DataFrame(rows).sort_values("psi", ascending=False)
    return df


def cusum_drift(series: pd.Series, threshold: float = 3.0,
                min_n: int = 40) -> pd.Series:
    """CUSUM flag: cumulative deviation of `series` from its own rolling mean."""
    s = series.astype(float)
    mean = s.rolling(min_n, min_periods=min_n).mean()
    std = s.rolling(min_n, min_periods=min_n).std().replace(0, np.nan)
    z = ((s - mean) / std.fillna(1.0)).fillna(0.0)
    cp = np.maximum.accumulate(z)
    cn = -np.minimum.accumulate(z)
    return (cp > threshold) | (cn > threshold)


def performance_drift_report(trades: pd.DataFrame, window: int = 50,
                             threshold_z: float = 3.0) -> dict:
    """Rolling expectancy and win-rate drift on the trade journal."""
    if len(trades) < 2 * window:
        return {"status": "INSUFFICIENT_SAMPLE",
                "n_trades": len(trades), "window": window}
    t = trades.sort_values("exit_time").reset_index(drop=True)
    pnl = t["pnl"]
    rolling_exp = pnl.rolling(window).mean()
    rolling_wr = (pnl > 0).rolling(window).mean()
    exp_flag = cusum_drift(rolling_exp.fillna(0), threshold_z)
    wr_flag = cusum_drift(rolling_wr.fillna(0.5), threshold_z)
    worst_exp = float(rolling_exp.min())
    recent_exp = float(rolling_exp.iloc[-1])
    return {
        "status": "OK" if not (exp_flag.any() or wr_flag.any()) else "DRIFT_DETECTED",
        "n_trades": len(trades),
        "window": window,
        "rolling_expectancy_min": worst_exp,
        "rolling_expectancy_recent": recent_exp,
        "exp_drift_detected": bool(exp_flag.any()),
        "wr_drift_detected": bool(wr_flag.any()),
        "drift_bars_ago": int(len(t) - exp_flag[::-1].idxmax() - 1) if exp_flag.any() else None,
    }


def slippage_drift_report(trades: pd.DataFrame, expected_bps: float,
                          alert_bps: float | None = None) -> dict:
    """Compare realized slippage proxy vs expectation (paper/live only)."""
    if "slippage_bps" not in trades.columns or len(trades) < 20:
        return {"status": "INSUFFICIENT_DATA", "n_trades": len(trades)}
    realized = trades["slippage_bps"].dropna()
    median = float(realized.median())
    p90 = float(realized.quantile(0.9))
    alert = alert_bps or max(2 * expected_bps, 10.0)
    return {
        "status": "OK" if median <= alert else "SLIPPAGE_DRIFT",
        "median_bps": median,
        "p90_bps": p90,
        "expected_bps": expected_bps,
    }
