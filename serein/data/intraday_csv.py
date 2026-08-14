"""Strict point-in-time intraday CSV ingestion.

No silent repairs are permitted. Missing bars are reported, duplicates and
invalid OHLC are rejected, and timezone/session conversion is explicit.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

REQUIRED = ("timestamp", "symbol", "open", "high", "low", "close", "volume")


@dataclass(frozen=True)
class IntradayDataReport:
    symbols: tuple[str, ...]
    rows: int
    start: str
    end: str
    source_timezone: str
    market_timezone: str
    out_of_session_removed: int
    missing_session_bars: int
    duplicate_rows: int
    nonfinite_rows: int

    def to_dict(self):
        return asdict(self)


def load_intraday_csv(path: str | Path, *, source_timezone: str,
                      market_timezone: str = "America/New_York",
                      regular_session_only: bool = True,
                      require_complete_sessions: bool = False,
                      expected_freq: str = "5min") -> tuple[dict[str, pd.DataFrame], IntradayDataReport]:
    raw = pd.read_csv(path)
    lower = {c: c.strip().lower() for c in raw.columns}
    raw = raw.rename(columns=lower)
    missing = set(REQUIRED)-set(raw.columns)
    if missing:
        raise ValueError(f"intraday CSV missing columns: {sorted(missing)}")
    raw = raw[list(REQUIRED)].copy()
    ts = pd.to_datetime(raw.timestamp, errors="coerce")
    if ts.isna().any():
        raise ValueError(f"unparseable timestamps: {int(ts.isna().sum())}")
    src = ZoneInfo(source_timezone); dst = ZoneInfo(market_timezone)
    if ts.dt.tz is None:
        ts = ts.dt.tz_localize(src, ambiguous="raise", nonexistent="raise")
    else:
        ts = ts.dt.tz_convert(src)
    raw["timestamp"] = ts.dt.tz_convert(dst)
    for c in ("open", "high", "low", "close", "volume"):
        raw[c] = pd.to_numeric(raw[c], errors="coerce")
    numeric = raw[["open", "high", "low", "close", "volume"]]
    nonfinite = int((~np.isfinite(numeric)).any(axis=1).sum())
    if nonfinite:
        raise ValueError(f"non-finite OHLCV rows: {nonfinite}")
    dup = int(raw.duplicated(["symbol", "timestamp"]).sum())
    if dup:
        raise ValueError(f"duplicate symbol/timestamp rows: {dup}")
    invalid = ((raw.high < raw[["open", "close"]].max(axis=1))
               | (raw.low > raw[["open", "close"]].min(axis=1))
               | (raw.low <= 0) | (raw.volume < 0))
    if invalid.any():
        raise ValueError(f"invalid OHLCV invariants: {int(invalid.sum())}")
    raw = raw.sort_values(["symbol", "timestamp"])
    before = len(raw)
    if regular_session_only:
        mins = raw.timestamp.dt.hour*60+raw.timestamp.dt.minute
        raw = raw[(mins >= 570) & (mins <= 955)]  # 09:30..15:55 bar timestamps
    removed = before-len(raw)

    missing_bars = 0; out = {}
    expected_per_day = int(pd.Timedelta("6h30min")/pd.Timedelta(expected_freq))
    for sym, group in raw.groupby("symbol", sort=True):
        g = group.set_index("timestamp").drop(columns=["symbol"])
        if not g.index.is_monotonic_increasing:
            raise ValueError(f"non-monotonic index for {sym}")
        counts = g.groupby(g.index.normalize()).size()
        missing_bars += int((expected_per_day-counts).clip(lower=0).sum())
        if require_complete_sessions and (counts != expected_per_day).any():
            bad = counts[counts != expected_per_day]
            raise ValueError(f"incomplete sessions for {sym}: {len(bad)} days")
        g.attrs.update(symbol=str(sym), synthetic=False,
                       source_timezone=source_timezone, market_timezone=market_timezone)
        out[str(sym)] = g
    if not out:
        raise ValueError("no in-session data")
    all_idx = raw.timestamp
    report = IntradayDataReport(tuple(out), len(raw), str(all_idx.min()), str(all_idx.max()),
                                source_timezone, market_timezone, removed, missing_bars,
                                dup, nonfinite)
    return out, report
