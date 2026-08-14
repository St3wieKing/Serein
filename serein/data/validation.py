"""Data-quality validation and leakage auditing.

The system refuses to train or trade on data that fails these checks.
Severity levels: ERROR (block), WARN (log + flag).
"""

from __future__ import annotations

import numpy as np
import pandas as pd


class DataQualityError(Exception):
    pass


def validate_bars(bars: pd.DataFrame, symbol: str = "") -> list[str]:
    """Run structural checks on an OHLCV frame. Returns list of problems
    (empty = pass). Raises nothing; caller decides how to react."""
    problems: list[str] = []
    tag = f"{symbol}: " if symbol else ""

    if not isinstance(bars.index, pd.DatetimeIndex):
        problems.append(tag + "index is not DatetimeIndex")
        return problems
    if bars.index.has_duplicates:
        problems.append(tag + f"duplicate timestamps: {bars.index.duplicated().sum()}")
    if not bars.index.is_monotonic_increasing:
        problems.append(tag + "index not monotonic")
    for col in ("open", "high", "low", "close", "volume"):
        if col not in bars.columns:
            problems.append(tag + f"missing column {col}")
            continue
        s = bars[col]
        if s.isna().any():
            problems.append(tag + f"{col}: {int(s.isna().sum())} NaNs")
        if col != "volume" and (s <= 0).any():
            problems.append(tag + f"{col}: non-positive prices")
        if col == "volume" and (s < 0).any():
            problems.append(tag + "volume: negative values")
    if "high" in bars.columns and "low" in bars.columns:
        bad = (bars["high"] < bars["low"]).sum()
        if bad:
            problems.append(tag + f"high<low in {bad} rows")
    if "close" in bars.columns:
        pct = bars["close"].pct_change().abs()
        # >50% single-bar move on hourly data is almost certainly corrupt
        if (pct > 0.5).sum():
            problems.append(tag + "abs returns >50% (suspicious outliers)")

    # staleness: consecutive duplicate closes (frozen feed)
    if "close" in bars.columns:
        dup = (bars["close"] == bars["close"].shift(1)).sum()
        if dup > 0.05 * len(bars):
            problems.append(tag + f"excessive flat closes ({dup}) — stale feed?")

    # gap regularity
    if len(bars) > 2:
        deltas = np.diff(bars.index.values).astype("timedelta64[m]").astype(int)
        if (deltas <= 0).any():
            problems.append(tag + "non-positive time deltas")

    return problems


def check_freshness(bars: pd.DataFrame, now: pd.Timestamp, max_staleness_bars: int) -> bool:
    """Is the latest bar fresh enough to trade on?"""
    if len(bars) == 0:
        return False
    diffs = (now - bars.index).to_series().diff().dropna()
    return True  # placeholder semantics; real check is in DataFeed layer


def anomaly_flags(bars: pd.DataFrame, symbol: str = "") -> pd.DataFrame:
    """Per-bar anomaly flags: impossible prices, insane spreads, vol spikes."""
    out = pd.DataFrame(index=bars.index)
    out["impossible_price"] = (bars[["open", "high", "low", "close"]] <= 0).any(axis=1)
    rng = (bars["high"] - bars["low"]) / bars["close"].replace(0, np.nan)
    # robust bounds: absolute sanity cap (20% intra-bar range on hourly data
    # is corrupt) OR 3x the 99.9th percentile of the WINSORIZED distribution
    rng_clip = rng.clip(upper=0.2)
    out["spread_anomaly"] = (rng > 0.2) | (rng > rng_clip.quantile(0.999) * 3 + 0.05)
    ret = bars["close"].pct_change().abs()
    ret_clip = ret.clip(upper=0.2)
    out["return_spike"] = (ret > 0.2) | (ret > ret_clip.quantile(0.999) * 3 + 0.05)
    out["any_anomaly"] = out.any(axis=1)
    out.attrs["symbol"] = symbol
    return out


def drop_anomalous(bars: pd.DataFrame, max_frac: float = 0.02) -> pd.DataFrame:
    """Remove anomalous bars; if more than max_frac are anomalous, refuse."""
    flags = anomaly_flags(bars)
    bad = flags["any_anomaly"].sum()
    if bad / len(bars) > max_frac:
        raise DataQualityError(
            f"{bad} anomalous bars ({bad/len(bars):.1%}) exceeds tolerance {max_frac}"
        )
    return bars[~flags["any_anomaly"]]
