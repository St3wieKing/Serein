"""Static HTML dashboard generator (observability).

Generates a self-contained dashboard HTML from run artifacts: equity curve,
drawdown, monthly returns heatmap, trade journal, risk summary, and
strategy decomposition. Charts use matplotlib rendered to base64 PNG.
"""

from __future__ import annotations

import base64
import io
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from .backtest.engine import BacktestResult


def _fig_to_b64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()


def _equity_chart(res: BacktestResult) -> str:
    eq = res.equity_curve["equity"]
    dd = eq / eq.cummax() - 1.0
    fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True,
                             gridspec_kw={"height_ratios": [3, 1]})
    axes[0].plot(eq.index, eq, lw=1.0, color="#1f77b4")
    axes[0].set_title("Equity curve")
    axes[0].grid(alpha=0.3)
    axes[1].fill_between(dd.index, dd * 100, 0, color="#d62728", alpha=0.6)
    axes[1].set_title("Drawdown %")
    axes[1].grid(alpha=0.3)
    fig.tight_layout()
    return _fig_to_b64(fig)


def _monthly_heatmap(res: BacktestResult) -> str:
    eq = res.equity_curve["equity"]
    monthly = eq.resample("ME").last().pct_change().dropna()
    if len(monthly) == 0:
        return ""
    years = monthly.index.year.unique()
    data = np.full((len(years), 12), np.nan)
    for i, y in enumerate(years):
        ym = monthly[monthly.index.year == y]
        for ts, v in ym.items():
            data[i, ts.month - 1] = v * 100
    fig, ax = plt.subplots(figsize=(11, max(2, len(years) * 0.45)))
    im = ax.imshow(data, cmap="RdYlGn", vmin=-max(5, np.nanmax(np.abs(data))),
                   vmax=max(5, np.nanmax(np.abs(data))), aspect="auto")
    ax.set_yticks(range(len(years)))
    ax.set_yticklabels([str(y) for y in years])
    ax.set_xticks(range(12))
    ax.set_xticklabels(["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
    ax.set_title("Monthly returns (%)")
    plt.colorbar(im, ax=ax, shrink=0.6)
    fig.tight_layout()
    return _fig_to_b64(fig)


def _df_to_html(df: pd.DataFrame, max_rows: int = 200) -> str:
    if len(df) == 0:
        return "<p><i>empty</i></p>"
    out = df.head(max_rows).copy()
    for c in out.columns:
        if out[c].dtype.kind in "fc":
            out[c] = out[c].round(4)
    return out.to_html(classes="tbl", border=0)


def generate_dashboard(
    res: BacktestResult,
    out_path: str | Path,
    title: str = "Serein — research dashboard",
    extra_sections: list[tuple[str, str]] | None = None,
    data_label: str = "synthetic — engineering validation only",
) -> Path:
    eq_img = _equity_chart(res)
    heat_img = _monthly_heatmap(res)

    m = res.metrics
    key_metrics = [
        ("Total return", f"{m.get('total_return', 0):.2%}"),
        ("CAGR", f"{m.get('cagr', 0):.2%}"),
        ("Sharpe", f"{m.get('sharpe', 0):.2f}"),
        ("Sortino", f"{m.get('sortino', 0):.2f}"),
        ("Max DD", f"{m.get('max_drawdown', 0):.2%}"),
        ("Trades", f"{m.get('n_trades', 0)}"),
        ("Win rate", f"{m.get('win_rate', 0):.1%}"),
        ("Expectancy", f"{m.get('expectancy_r', 0):.2f}R"),
    ]
    cards = "".join(
        f'<div class="card"><div class="k">{k}</div><div class="v">{v}</div></div>'
        for k, v in key_metrics
    )

    risk = res.risk_summary
    risk_html = (
        f"<p><b>Kill switches tripped:</b> {risk.get('tripped') or 'none'} "
        f"<b>· Rejections:</b> {risk.get('rejections', 0)} "
        f"<b>· Vol scale:</b> {risk.get('vol_frac', 1.0)} "
        f"<b>· Force exit:</b> {risk.get('force_exit')}</p>"
    )

    sections = [
        ("Risk engine", risk_html),
        ("Equity & drawdown", f'<img src="data:image/png;base64,{eq_img}"/>'),
        ("Monthly returns", f'<img src="data:image/png;base64,{heat_img}"/>'),
        ("Trades journal", _df_to_html(res.trades)),
        ("By strategy", _df_to_html(
            pd.DataFrame(res.decompositions.get("by_strategy", {})).T)),
        ("By month", _df_to_html(
            pd.DataFrame(res.decompositions.get("by_month", {})).T)),
        ("By exit reason", _df_to_html(
            pd.DataFrame(res.decompositions.get("by_exit_reason", {})).T)),
    ]
    for s in (extra_sections or []):
        sections.append(s)

    html = [f"<!DOCTYPE html><html><head><meta charset='utf-8'>",
            f"<title>{title}</title>",
            "<style>",
            "body{font-family:system-ui,sans-serif;margin:24px;background:#f6f7f9;color:#222}",
            "h1{font-size:22px}.cards{display:flex;flex-wrap:wrap;gap:10px;margin:14px 0}",
            ".card{background:#fff;border:1px solid #e2e4e8;border-radius:8px;padding:10px 16px;min-width:120px}",
            ".k{font-size:11px;color:#666;text-transform:uppercase}.v{font-size:18px;font-weight:600}",
            "section{background:#fff;border:1px solid #e2e4e8;border-radius:8px;padding:14px 18px;margin:14px 0}",
            "h2{font-size:16px;margin-top:0}.tbl{border-collapse:collapse;font-size:12px}",
            ".tbl th,.tbl td{border:1px solid #e2e4e8;padding:4px 8px;text-align:right}",
            ".tbl th{background:#f0f2f5}img{max-width:100%}",
            "</style></head><body>",
            f"<h1>{title}</h1>",
            f'<p class="meta">Period {m.get("start")} → {m.get("end")} · '
            f'final equity {m.get("final_equity", 0):,.0f} · '
            f'<b>data: {data_label}</b></p>',
            '<div class="cards">' + cards + "</div>",
    ]
    for name, body in sections:
        html.append(f"<section><h2>{name}</h2>{body}</section>")
    html.append("</body></html>")
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(html))
    return out
