"""Performance metrics & decomposition.

Every backtest reports the FULL suite — never just total return. No metric
is "good" without context; the report always shows drawdown, streaks, tail
losses, costs, and decomposition together.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..config import BacktestConfig
from .engine import bars_per_year


def compute_metrics(eq_df: pd.DataFrame, trades_df: pd.DataFrame,
                    cfg: BacktestConfig) -> dict:
    eq = eq_df["equity"]
    rets = eq.pct_change().dropna()
    bpy = bars_per_year(cfg.freq)
    m: dict = {}

    # ---- returns ------------------------------------------------------------
    m["total_return"] = float(eq.iloc[-1] / eq.iloc[0] - 1.0)
    years = len(eq) / bpy
    m["cagr"] = float((eq.iloc[-1] / eq.iloc[0]) ** (1.0 / years) - 1.0) if years > 0 else np.nan
    m["annualized_vol"] = float(rets.std() * np.sqrt(bpy)) if len(rets) > 2 else np.nan
    m["sharpe"] = float(rets.mean() / rets.std() * np.sqrt(bpy)) if rets.std() > 0 and len(rets) > 2 else np.nan
    downside = rets[rets < 0]
    m["sortino"] = float(rets.mean() / downside.std() * np.sqrt(bpy)) if len(downside) > 2 and downside.std() > 0 else np.nan

    # ---- drawdowns ------------------------------------------------------------
    peak = eq.cummax()
    dd = eq / peak - 1.0
    m["max_drawdown"] = float(dd.min())
    m["avg_drawdown"] = float(dd[dd < 0].mean()) if (dd < 0).any() else 0.0
    # duration: longest time underwater
    underwater = dd < 0
    dur = 0
    max_dur = 0
    for u in underwater:
        if u:
            dur += 1
            max_dur = max(max_dur, dur)
        else:
            dur = 0
    m["max_drawdown_bars"] = int(max_dur)
    # recovery time from max drawdown (bars from trough to new peak)
    trough_loc = dd.idxmin()
    m["recovery_bars"] = None
    if trough_loc is not None and not pd.isna(trough_loc):
        pre_peak = eq.loc[:trough_loc].max()
        after = eq.loc[eq.index > trough_loc]
        recovered = after >= pre_peak
        if recovered.any():
            pos1 = eq.index.get_loc(trough_loc)
            pos2 = eq.index.get_loc(recovered.idxmax())
            m["recovery_bars"] = int(pos2 - pos1)
    m["calmar"] = float(m["cagr"] / abs(m["max_drawdown"])) if m["max_drawdown"] < 0 and np.isfinite(m["cagr"]) else np.nan

    # ---- trade statistics -----------------------------------------------------
    if len(trades_df) > 0:
        pnl = trades_df["pnl"]
        wins = pnl[pnl > 0]
        losses = pnl[pnl < 0]
        m["n_trades"] = int(len(trades_df))
        m["win_rate"] = float(len(wins) / len(pnl))
        m["loss_rate"] = float(len(losses) / len(pnl))
        m["avg_win"] = float(wins.mean()) if len(wins) else 0.0
        m["avg_loss"] = float(losses.mean()) if len(losses) else 0.0
        m["payoff_ratio"] = float(wins.mean() / abs(losses.mean())) if len(wins) and len(losses) and losses.mean() != 0 else np.nan
        m["profit_factor"] = float(wins.sum() / abs(losses.sum())) if losses.sum() != 0 else np.inf
        m["avg_pnl"] = float(pnl.mean())
        m["total_pnl"] = float(pnl.sum())
        # expectancy in R units
        risk_r = (trades_df["entry_price"] - trades_df["stop"]).abs() * trades_df["qty"]
        risk_r = risk_r.replace(0, np.nan)
        m["expectancy_r"] = float((pnl / risk_r).mean()) if risk_r.notna().any() else np.nan
        m["avg_bars_held"] = float(trades_df["bars_held"].mean())
        m["largest_win"] = float(pnl.max())
        m["largest_loss"] = float(pnl.min())
        m["costs_total"] = float(trades_df["costs_total"].sum())
        # streaks
        signs = np.sign(pnl)
        cur = 1
        best_win_streak = worst_loss_streak = 0
        win_streak = loss_streak = 0
        for s in signs:
            if s > 0:
                win_streak += 1
                loss_streak = 0
                best_win_streak = max(best_win_streak, win_streak)
            elif s < 0:
                loss_streak += 1
                win_streak = 0
                worst_loss_streak = max(worst_loss_streak, loss_streak)
        m["best_winning_streak"] = int(best_win_streak)
        m["worst_losing_streak"] = int(worst_loss_streak)
        # tail losses
        m["tail_losses_top5"] = [round(x, 2) for x in sorted(pnl)[:5]]
        # trade return distribution
        tr = trades_df["ret_pct"].dropna()
        if len(tr) > 3:
            m["trade_ret_skew"] = float(tr.skew())
            m["trade_ret_kurtosis"] = float(tr.kurt())
        m["n_long"] = int((trades_df["direction"] > 0).sum())
        m["n_short"] = int((trades_df["direction"] < 0).sum())
        m["long_pnl"] = float(trades_df.loc[trades_df["direction"] > 0, "pnl"].sum())
        m["short_pnl"] = float(trades_df.loc[trades_df["direction"] < 0, "pnl"].sum())
    else:
        m["n_trades"] = 0
        for k in ("win_rate", "loss_rate", "avg_win", "avg_loss", "payoff_ratio",
                  "profit_factor", "avg_pnl", "total_pnl", "expectancy_r",
                  "avg_bars_held", "largest_win", "largest_loss", "costs_total",
                  "best_winning_streak", "worst_losing_streak", "n_long", "n_short",
                  "long_pnl", "short_pnl"):
            m[k] = 0.0 if k not in ("best_winning_streak", "worst_losing_streak", "n_trades", "n_long", "n_short") else 0
        m["tail_losses_top5"] = []
        m["trade_ret_skew"] = np.nan
        m["trade_ret_kurtosis"] = np.nan

    # ---- exposure / turnover ---------------------------------------------------
    m["final_equity"] = float(eq.iloc[-1])
    traded_notional = float((trades_df["qty"] * trades_df["entry_price"]).sum()) if len(trades_df) else 0.0
    m["traded_notional_ratio"] = traded_notional / max(m["final_equity"], 1.0)
    notional_per_year = traded_notional / max(years, 1e-9)
    m["turnover_annual"] = notional_per_year / max(m["final_equity"], 1.0)

    # ---- weekly / monthly distributions ----------------------------------------
    if len(rets) > 0:
        eq_s = eq
        weekly = eq_s.resample("W").last().pct_change().dropna()
        monthly = eq_s.resample("ME").last().pct_change().dropna()
        m["weekly_mean"] = float(weekly.mean()) if len(weekly) else np.nan
        m["weekly_std"] = float(weekly.std()) if len(weekly) else np.nan
        m["monthly_mean"] = float(monthly.mean()) if len(monthly) else np.nan
        m["monthly_std"] = float(monthly.std()) if len(monthly) else np.nan
        m["worst_week"] = float(weekly.min()) if len(weekly) else np.nan
        m["worst_month"] = float(monthly.min()) if len(monthly) else np.nan
        m["best_week"] = float(weekly.max()) if len(weekly) else np.nan
        m["best_month"] = float(monthly.max()) if len(monthly) else np.nan
        m["weekly_returns"] = [round(x, 6) for x in weekly.tolist()]
        m["monthly_returns"] = [round(x, 6) for x in monthly.tolist()]
        # daily return tail
        m["daily_ret_skew"] = float(rets.skew()) if len(rets) > 3 else np.nan
        m["daily_ret_kurtosis"] = float(rets.kurt()) if len(rets) > 3 else np.nan

    m["start"] = str(eq.index[0])
    m["end"] = str(eq.index[-1])
    return m


def decompose(trades_df: pd.DataFrame, eq_df: pd.DataFrame,
              cfg: BacktestConfig) -> dict:
    """Break performance down by strategy, direction, exit reason, month, year."""
    out: dict = {}
    if len(trades_df) == 0:
        return out

    def group_stats(df: pd.DataFrame) -> dict:
        if len(df) == 0:
            return {"n": 0, "pnl": 0.0, "win_rate": np.nan}
        pnl = df["pnl"]
        return {
            "n": int(len(df)),
            "pnl": round(float(pnl.sum()), 2),
            "win_rate": round(float((pnl > 0).mean()), 4),
            "avg_pnl": round(float(pnl.mean()), 2),
        }

    # by strategy (reason field encodes the contributing engines)
    strat = trades_df["reason"].fillna("unknown")
    out["by_strategy"] = {k: group_stats(g) for k, g in trades_df.groupby(strat)}

    out["by_direction"] = {
        str(k): group_stats(g) for k, g in trades_df.groupby(trades_df["direction"])
    }
    out["by_exit_reason"] = {
        str(k): group_stats(g) for k, g in trades_df.groupby(trades_df["exit_reason"])
    }
    out["by_month"] = {
        str(k): group_stats(g)
        for k, g in trades_df.groupby(trades_df["exit_time"].dt.to_period("M"))
    }
    out["by_year"] = {
        str(k): group_stats(g)
        for k, g in trades_df.groupby(trades_df["exit_time"].dt.year)
    }
    out["by_symbol"] = {
        str(k): group_stats(g) for k, g in trades_df.groupby(trades_df["symbol"])
    }
    conf = pd.cut(trades_df["confidence"], bins=[0, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
                  labels=["<0.5", "0.5-0.6", "0.6-0.7", "0.7-0.8", "0.8-0.9", "0.9+"])
    out["by_confidence"] = {
        str(k): group_stats(g) for k, g in trades_df.groupby(conf, observed=True)
    }
    hold = pd.cut(trades_df["bars_held"], bins=[0, 6, 24, 72, 240, 10000],
                  labels=["<6", "6-24", "24-72", "72-240", "240+"])
    out["by_holding"] = {
        str(k): group_stats(g) for k, g in trades_df.groupby(hold, observed=True)
    }
    return out
