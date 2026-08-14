"""Forensic analysis of third-party MT4/MT5 trade exports.

The detector reports observable behavior. It does not claim intent, fraud, or
proprietary strategy knowledge. Results from partial history are labeled partial.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ForensicReport:
    n_trades: int
    start: str | None
    end: str | None
    win_rate: float
    profit_factor: float
    avg_win: float
    avg_loss: float
    payoff_ratio: float
    expectancy: float
    long_fraction: float
    median_duration_minutes: float
    no_visible_sl_fraction: float
    no_visible_tp_fraction: float
    max_simultaneous: int
    clustered_close_fraction: float
    fixed_lot_fraction: float
    loss_followed_by_larger_lot_fraction: float
    grid_evidence: str
    martingale_evidence: str
    limitations: tuple[str, ...]

    def to_dict(self):
        return asdict(self)


def load_trade_export(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    aliases = {
        "open date": "open_time", "close date": "close_time", "action": "action",
        "lots": "lots", "sl": "sl", "tp": "tp", "profit": "profit",
        "duration": "duration", "gain": "gain_pct", "symbol": "symbol",
        "open": "open", "close": "close", "pips": "pips",
    }
    df = df.rename(columns={c: aliases.get(c.strip().lower(), c.strip().lower().replace(" ", "_"))
                            for c in df.columns})
    required = {"open_time", "close_time", "action", "lots", "profit"}
    missing = required - set(df)
    if missing:
        raise ValueError(f"trade export missing columns: {sorted(missing)}")
    for c in ("open_time", "close_time"):
        text = df[c].astype(str)
        # SignalStart displays DD.MM.YYYY; normalized research exports often
        # use ISO YYYY-MM-DD. Select explicitly to avoid ambiguous parsing.
        is_iso = text.str.match(r"^\d{4}-\d{2}-\d{2}").all()
        df[c] = pd.to_datetime(text, dayfirst=not is_iso, errors="coerce")
    for c in ("lots", "profit", "sl", "tp", "open", "close", "pips", "gain_pct"):
        if c in df:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.sort_values("open_time").reset_index(drop=True)


def _max_overlap(df: pd.DataFrame) -> int:
    events = []
    for r in df.itertuples():
        if pd.notna(r.open_time) and pd.notna(r.close_time):
            events.extend([(r.open_time, 1), (r.close_time, -1)])
    # Close before open at equal timestamps avoids a false overlap.
    events.sort(key=lambda x: (x[0], x[1]))
    cur = peak = 0
    for _, change in events:
        cur += change
        peak = max(peak, cur)
    return peak


def analyze_trades(df: pd.DataFrame, *, partial_history: bool = True) -> ForensicReport:
    if len(df) == 0:
        raise ValueError("no trades")
    pnl = df["profit"].fillna(0.0)
    wins, losses = pnl[pnl > 0], pnl[pnl < 0]
    avg_win = float(wins.mean()) if len(wins) else 0.0
    avg_loss = float(losses.mean()) if len(losses) else 0.0
    pf = float(wins.sum()/abs(losses.sum())) if losses.sum() else float("inf")
    payoff = avg_win/abs(avg_loss) if avg_loss else float("inf")
    action = df["action"].astype(str).str.lower()
    duration = (df["close_time"]-df["open_time"]).dt.total_seconds()/60

    sl_missing = df.get("sl", pd.Series(np.nan, index=df.index)).isna()
    tp_missing = df.get("tp", pd.Series(np.nan, index=df.index)).isna()
    close_counts = df["close_time"].value_counts()
    clustered = df["close_time"].map(close_counts).fillna(1) > 1
    lots = df["lots"].astype(float)
    mode_share = float((lots == lots.mode().iloc[0]).mean()) if len(lots.mode()) else np.nan

    prev_loss = pnl.shift(1) < 0
    comparable = prev_loss & lots.shift(1).notna() & lots.notna()
    larger_after_loss = float((lots[comparable] > lots.shift(1)[comparable]).mean()) if comparable.any() else np.nan

    overlap = _max_overlap(df)
    # Grid evidence is based on multiple same-direction overlapping positions
    # and basket-like synchronized exits—not on marketing terminology.
    grid_score = int(overlap >= 3) + int(clustered.mean() >= .20) + int(action.nunique() == 1)
    grid_evidence = ("strong" if grid_score >= 2 else "possible" if grid_score == 1 else "not_detected")
    if np.isnan(larger_after_loss):
        martingale = "inconclusive"
    elif larger_after_loss >= .60:
        martingale = "possible_lot_progression"
    else:
        martingale = "not_detected_in_sample"

    limits = []
    if partial_history:
        limits.append("partial_history")
    if sl_missing.any():
        limits.append("blank_SL_field_does_not_prove_no_internal_or_virtual_stop")
    if len(df) < 200:
        limits.append("small_sample")

    return ForensicReport(
        n_trades=len(df),
        start=str(df.open_time.min()) if df.open_time.notna().any() else None,
        end=str(df.close_time.max()) if df.close_time.notna().any() else None,
        win_rate=float((pnl > 0).mean()), profit_factor=pf,
        avg_win=avg_win, avg_loss=avg_loss, payoff_ratio=payoff,
        expectancy=float(pnl.mean()),
        long_fraction=float(action.str.startswith("buy").mean()),
        median_duration_minutes=float(duration.median()),
        no_visible_sl_fraction=float(sl_missing.mean()),
        no_visible_tp_fraction=float(tp_missing.mean()),
        max_simultaneous=overlap,
        clustered_close_fraction=float(clustered.mean()),
        fixed_lot_fraction=mode_share,
        loss_followed_by_larger_lot_fraction=larger_after_loss,
        grid_evidence=grid_evidence, martingale_evidence=martingale,
        limitations=tuple(limits),
    )
