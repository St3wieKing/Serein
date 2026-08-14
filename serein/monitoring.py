"""Daily and weekly review payloads from immutable journals."""
from __future__ import annotations

import numpy as np
import pandas as pd


def _stats(t: pd.DataFrame) -> dict:
    if len(t) == 0:
        return {"trades": 0, "gross_pnl": 0.0, "net_pnl": 0.0,
                "win_rate": None, "largest_win": None, "largest_loss": None}
    pnl = t.pnl.astype(float)
    return {"trades": int(len(t)), "gross_pnl": float(pnl.sum()+t.get("costs_total", 0).sum()),
            "net_pnl": float(pnl.sum()), "win_rate": float((pnl > 0).mean()),
            "largest_win": float(pnl.max()), "largest_loss": float(pnl.min()),
            "costs": float(t.get("costs_total", pd.Series(0, index=t.index)).sum()),
            "average_r": float((pnl/((t.entry_price-t.stop).abs()*t.qty).replace(0, np.nan)).mean())}


def daily_review(trades: pd.DataFrame, equity: pd.DataFrame, day,
                 *, data_health: str, broker_health: str,
                 slippage_status: str, anomalies: list[str]) -> dict:
    day = pd.Timestamp(day).normalize()
    t = trades[pd.to_datetime(trades.exit_time).dt.normalize() == day] if len(trades) else trades
    eq = equity[equity.index.normalize() == day]
    stats = _stats(t)
    stats.update({"period": str(day.date()), "drawdown": None,
                  "data_health": data_health, "broker_health": broker_health,
                  "slippage_status": slippage_status, "anomalies": list(anomalies)})
    if len(eq): stats["drawdown"] = float((eq.equity/eq.equity.cummax()-1).min())
    if len(t) and "reason" in t:
        stats["strategy_contribution"] = t.groupby("reason").pnl.sum().to_dict()
    return stats


def weekly_review(trades: pd.DataFrame, equity: pd.DataFrame, end,
                  *, model_drift: dict, strategy_health: dict) -> dict:
    end = pd.Timestamp(end); start = end-pd.Timedelta(days=7)
    t = trades[(pd.to_datetime(trades.exit_time) > start)
               & (pd.to_datetime(trades.exit_time) <= end)] if len(trades) else trades
    out = _stats(t); out.update({"start": str(start), "end": str(end),
                                 "model_drift": model_drift,
                                 "strategy_health": strategy_health})
    for field in ("reason", "symbol"):
        if len(t) and field in t: out[f"by_{field}"] = t.groupby(field).pnl.sum().to_dict()
    return out
