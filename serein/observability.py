"""System-level observability snapshot for research/shadow/paper modes."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from html import escape
from pathlib import Path


@dataclass(frozen=True)
class SystemSnapshot:
    mode: str
    current_strategy: str
    current_regime: str
    positions: dict
    gross_exposure: float
    net_exposure: float
    risk_state: str
    confidence: float | None
    model_id: str | None
    strategy_health: str
    today_trades: int
    today_pnl: float
    rolling_expectancy_r: float | None
    drawdown: float
    realized_slippage_bps: float | None
    data_health: str
    broker_health: str
    model_drift: str
    last_update: str


def snapshot_html(snapshot: SystemSnapshot, out_path: str | Path) -> Path:
    rows = []
    for key, value in asdict(snapshot).items():
        rows.append(f"<tr><th>{escape(key.replace('_',' ').title())}</th><td>{escape(str(value))}</td></tr>")
    status = "OK" if (snapshot.data_health == snapshot.broker_health == "OK"
                      and snapshot.strategy_health == "ACTIVE") else "HALT / REVIEW"
    html = f"""<!doctype html><meta charset='utf-8'><title>Serein system status</title>
<style>body{{font-family:system-ui;margin:2rem;background:#111827;color:#e5e7eb}}
table{{border-collapse:collapse;background:#1f2937}}th,td{{padding:.5rem 1rem;border:1px solid #374151;text-align:left}}
.badge{{display:inline-block;padding:.4rem .8rem;border-radius:.5rem;background:#374151}}</style>
<h1>Serein — {escape(snapshot.mode)}</h1><p class='badge'>{escape(status)}</p>
<table>{''.join(rows)}</table>"""
    p = Path(out_path); p.parent.mkdir(parents=True, exist_ok=True); p.write_text(html); return p
