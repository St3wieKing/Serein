"""Report generation (markdown) from real run artifacts.

Every number in a report comes from an actual computation — never hand-filled.
Reports always state the data provenance (synthetic vs real) and the caveats.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from .backtest.engine import BacktestResult
from .config import config_to_dict


def _fmt(v, pct: bool = False, digits: int = 2) -> str:
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return "n/a"
    if pct:
        return f"{v:.{digits}%}"
    if isinstance(v, float):
        return f"{v:,.{digits}f}"
    return str(v)


def metric_table(m: dict) -> str:
    order = [
        ("total_return", "Total return", True),
        ("cagr", "CAGR", True),
        ("annualized_vol", "Annualized volatility", True),
        ("sharpe", "Sharpe ratio", False),
        ("sortino", "Sortino ratio", False),
        ("calmar", "Calmar ratio", False),
        ("max_drawdown", "Maximum drawdown", True),
        ("avg_drawdown", "Average drawdown", True),
        ("max_drawdown_bars", "Max drawdown duration (bars)", False),
        ("recovery_bars", "Recovery from max DD (bars)", False),
        ("n_trades", "Number of trades", False),
        ("win_rate", "Win rate", True),
        ("loss_rate", "Loss rate", True),
        ("profit_factor", "Profit factor", False),
        ("avg_win", "Average winner", False),
        ("avg_loss", "Average loser", False),
        ("payoff_ratio", "Payoff ratio (avg win / |avg loss|)", False),
        ("expectancy_r", "Expectancy (avg R per trade)", False),
        ("avg_pnl", "Average PnL per trade", False),
        ("total_pnl", "Total PnL", False),
        ("avg_bars_held", "Average holding (bars)", False),
        ("largest_win", "Largest win", False),
        ("largest_loss", "Largest loss", False),
        ("costs_total", "Total costs (fees + slippage + impact)", False),
        ("best_winning_streak", "Best winning streak", False),
        ("worst_losing_streak", "Worst losing streak", False),
        ("n_long", "Long trades", False),
        ("n_short", "Short trades", False),
        ("long_pnl", "Long PnL", False),
        ("short_pnl", "Short PnL", False),
        ("weekly_mean", "Mean weekly return", True),
        ("weekly_std", "Weekly return std", True),
        ("worst_week", "Worst week", True),
        ("best_week", "Best week", True),
        ("monthly_mean", "Mean monthly return", True),
        ("worst_month", "Worst month", True),
        ("best_month", "Best month", True),
        ("trade_ret_skew", "Trade return skew", False),
        ("trade_ret_kurtosis", "Trade return kurtosis", False),
        ("turnover_annual", "Annual turnover (notional/equity)", False),
        ("traded_notional_ratio", "Total traded notional / final equity", False),
    ]
    lines = ["| Metric | Value |", "|---|---|"]
    for key, label, pct in order:
        if key in m:
            lines.append(f"| {label} | {_fmt(m[key], pct=pct)} |")
    return "\n".join(lines)


def tail_loss_table(trades: pd.DataFrame) -> str:
    if len(trades) == 0:
        return "_no trades_"
    t = trades.nsmallest(5, "pnl")[["symbol", "direction", "entry_time", "exit_time",
                                    "pnl", "ret_pct", "reason", "exit_reason"]]
    return t.to_markdown(index=False)


def decomposition_section(decompositions: dict) -> str:
    out = []
    for name, groups in decompositions.items():
        out.append(f"\n### {name.replace('_', ' ').title()}\n")
        out.append("| Group | N | PnL | Win rate | Avg PnL |")
        out.append("|---|---|---|---|---|")
        for k, g in groups.items():
            out.append(f"| {k} | {g['n']} | {g['pnl']:,.0f} | "
                       f"{_fmt(g.get('win_rate'), pct=True)} | {g['avg_pnl']:,.0f} |")
    return "\n".join(out)


def stress_section(title: str, df: pd.DataFrame) -> str:
    out = [f"### {title}\n", "| Shock | Total return | Sharpe | Max DD | Trades |",
           "|---|---|---|---|---|"]
    for _, r in df.iterrows():
        out.append(f"| {r['shock']} | {_fmt(r['total_return'], pct=True)} | "
                   f"{_fmt(r['sharpe'])} | {_fmt(r['max_drawdown'], pct=True)} | "
                   f"{int(r['n_trades'])} |")
    return "\n".join(out)


def backtest_report(res: BacktestResult, title: str = "Backtest report") -> str:
    m = res.metrics
    lines = [
        f"# {title}",
        "",
        f"**Period:** {m.get('start')} → {m.get('end')}  ·  "
        f"**Final equity:** {_fmt(m.get('final_equity'))}  ·  "
        f"**Risk summary:** {json.dumps(res.risk_summary, default=str)}",
        "",
        "## Metrics", "",
        metric_table(m),
        "",
        "## Tail losses (worst 5)", "",
        tail_loss_table(res.trades),
        "",
        "## Decomposition", "",
        decomposition_section(res.decompositions),
    ]
    return "\n".join(lines)


def config_section(cfg) -> str:
    d = config_to_dict(cfg)
    return f"```json\n{json.dumps(d, indent=2, default=str)}\n```"
