"""Event-driven multi-instrument backtesting engine.

Timing convention (critical, tested):
  * signal row at time t = DECISION at close of bar t
  * orders execute at the OPEN of bar t+1 (with slippage)
  * stops/targets are checked intrabar from the entry bar onward
  * if both stop and target are hit in the same bar, STOP is assumed
    (conservative)
  * positions are marked to market at every bar close

The Risk Engine is embedded in the loop: it can reject any entry, force
exits, and trip kill switches. The alpha layer cannot bypass it.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .. import constants as C
from ..config import BacktestConfig
from ..risk.engine import RiskEngine
from ..risk.sizing import size_position
from .costs import cost_of_fill, slippage_adjusted_price

TRADE_COLUMNS = [
    "trade_id", "symbol", "direction", "entry_time", "exit_time",
    "entry_price", "exit_price", "qty", "stop", "target",
    "confidence", "expected_R", "reason", "exit_reason",
    "mfe", "mae", "entry_commission", "entry_slippage",
    "exit_commission", "exit_slippage", "costs_total",
    "pnl", "ret_pct", "bars_held", "equity_at_entry",
]


@dataclass
class Position:
    symbol: str
    qty: int                    # signed: +long / -short
    entry_price: float
    entry_time: pd.Timestamp
    stop: float
    target: float
    entry_risk_per_share: float
    confidence: float
    expected_R: float
    reason: str
    equity_at_entry: float
    trade_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    bars_held: int = 0
    mfe: float = 0.0
    mae: float = 0.0
    entry_commission: float = 0.0
    entry_slippage: float = 0.0
    notional_at_entry: float = 0.0
    last_seen: pd.Timestamp | None = None


@dataclass
class PendingOrder:
    symbol: str
    direction: int
    qty: int
    confidence: float
    expected_R: float
    reason: str
    stop: float
    target: float
    decision_time: pd.Timestamp
    trade_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])


@dataclass
class BacktestResult:
    equity_curve: pd.DataFrame
    trades: pd.DataFrame
    metrics: dict
    decompositions: dict
    signals: dict
    risk_summary: dict
    config: BacktestConfig

    def summary(self) -> str:
        m = self.metrics
        return "\n".join([
            f"Trades: {m.get('n_trades', 0)}   Win rate: {m.get('win_rate', 0):.1%}",
            f"Total return: {m.get('total_return', 0):.1%}   CAGR: {m.get('cagr', 0):.1%}",
            f"Sharpe: {m.get('sharpe', 0):.2f}   Sortino: {m.get('sortino', 0):.2f}   "
            f"Calmar: {m.get('calmar', 0):.2f}",
            f"Max drawdown: {m.get('max_drawdown', 0):.1%}   Profit factor: "
            f"{m.get('profit_factor', 0):.2f}",
            f"Expectancy: {m.get('expectancy_r', 0):.2f}R   Payoff: "
            f"{m.get('payoff_ratio', 0):.2f}",
            f"Fees+slippage: {m.get('costs_total', 0):.0f}   Worst losing streak: "
            f"{m.get('worst_losing_streak', 0)}",
        ])


class Backtester:
    def __init__(self, config: BacktestConfig):
        self.cfg = config
        self.risk = RiskEngine(config.risk, config.sizing)

    # ------------------------------------------------------------------ run
    def run(
        self,
        bars: dict[str, pd.DataFrame],
        signals: dict[str, pd.DataFrame],
    ) -> BacktestResult:
        cfg = self.cfg
        master = _union_index(bars)
        expected_step = _median_step(master)
        bar_map: dict[str, dict] = {
            s: {r.Index: r for r in bars[s].itertuples()} for s in bars
        }
        # precomputed ATR and realized-vol series per symbol (causal)
        atr_map = {s: _atr_series(bars[s], 14) for s in bars}
        vol_map = {
            s: bars[s]["close"].pct_change().rolling(20, min_periods=20).std()
            * np.sqrt(bars_per_year(cfg.freq))
            for s in bars
        }

        cash = cfg.initial_equity
        positions: dict[str, Position] = {}
        trades: list[dict] = []
        equity_hist: list[tuple[pd.Timestamp, float]] = []
        pending: list[PendingOrder] = []
        consecutive_losses = 0
        peak_equity = cfg.initial_equity
        day_start_equity: dict[pd.Timestamp, float] = {}
        last_equity = cfg.initial_equity

        for t in master:
            # ---- 1. execute pending orders at open of bar t ------------------
            if pending:
                still_pending: list[PendingOrder] = []
                for o in pending:
                    row = bar_map[o.symbol].get(t)
                    if row is None:
                        still_pending.append(o)
                        continue
                    if o.symbol in positions:
                        continue  # conflict policy: one position per symbol
                    open_px = float(row.open)
                    bar_adv = float(row.volume) * open_px
                    cost = cost_of_fill(cfg.costs, open_px * o.qty, o.qty, bar_adv)
                    fill = slippage_adjusted_price(open_px, o.direction, cost.cost_bps)
                    if fill <= 0 or not np.isfinite(fill):
                        continue
                    stop_dist = abs(fill - o.stop)
                    if stop_dist / fill <= 0.002:
                        continue  # degenerate stop -> reject silently
                    stop = o.stop if o.direction > 0 else fill + stop_dist
                    target = o.target if o.direction > 0 else fill - stop_dist * cfg.target_rr
                    if stop <= 0 or target <= 0:
                        continue
                    # booking (exact accounting): the fill price embeds
                    # spread+slippage; commissions are separate line items.
                    entry_commission = cost.commission
                    entry_slippage = abs(fill - open_px) * o.qty
                    cash -= o.direction * fill * o.qty + entry_commission
                    pos = Position(
                        symbol=o.symbol, qty=o.qty * o.direction,
                        entry_price=fill, entry_time=t, stop=stop, target=target,
                        entry_risk_per_share=stop_dist, confidence=o.confidence,
                        expected_R=o.expected_R, reason=o.reason,
                        equity_at_entry=last_equity, trade_id=o.trade_id,
                        entry_commission=entry_commission,
                        entry_slippage=entry_slippage,
                        notional_at_entry=open_px * o.qty,
                    )
                    positions[o.symbol] = pos
                    pos.last_seen = t
                    self.risk.on_trade_executed(t)
                pending = still_pending

            # ---- 2. intrabar exits (stop/target/max-hold) --------------------
            for sym in list(positions):
                pos = positions[sym]
                row = bar_map[sym].get(t)
                if row is None:
                    pos.bars_held += 1
                    continue
                hi, lo, cl = float(row.high), float(row.low), float(row.close)
                # gap-through handling: if bars are missing for this symbol,
                # the stop/target may have been crossed during the gap; assume
                # the fill happens at the gap OPEN (conservative for stops).
                if pos.last_seen is not None:
                    gap = (t - pos.last_seen) > expected_step
                    if gap:
                        op = float(row.open)
                        if pos.qty > 0 and op <= pos.stop:
                            cash, trades, consecutive_losses = self._close_position(
                                pos, op, t, C.EXIT_STOP_GAP, cash, trades,
                                consecutive_losses, cfg)
                            del positions[sym]
                            continue
                        if pos.qty > 0 and op >= pos.target:
                            cash, trades, consecutive_losses = self._close_position(
                                pos, op, t, C.EXIT_TARGET_GAP, cash, trades,
                                consecutive_losses, cfg)
                            del positions[sym]
                            continue
                        if pos.qty < 0 and op >= pos.stop:
                            cash, trades, consecutive_losses = self._close_position(
                                pos, op, t, C.EXIT_STOP_GAP, cash, trades,
                                consecutive_losses, cfg)
                            del positions[sym]
                            continue
                        if pos.qty < 0 and op <= pos.target:
                            cash, trades, consecutive_losses = self._close_position(
                                pos, op, t, C.EXIT_TARGET_GAP, cash, trades,
                                consecutive_losses, cfg)
                            del positions[sym]
                            continue
                pos.last_seen = t
                if pos.qty > 0:
                    pos.mfe = max(pos.mfe, hi - pos.entry_price)
                    pos.mae = max(pos.mae, pos.entry_price - lo)
                else:
                    pos.mfe = max(pos.mfe, pos.entry_price - lo)
                    pos.mae = max(pos.mae, hi - pos.entry_price)
                pos.bars_held += 1
                exit_px: float | None = None
                exit_reason: str | None = None
                if pos.qty > 0:
                    if lo <= pos.stop:
                        exit_px, exit_reason = pos.stop, C.EXIT_STOP
                    elif hi >= pos.target:
                        exit_px, exit_reason = pos.target, C.EXIT_TARGET
                else:
                    if hi >= pos.stop:
                        exit_px, exit_reason = pos.stop, C.EXIT_STOP
                    elif lo <= pos.target:
                        exit_px, exit_reason = pos.target, C.EXIT_TARGET
                if exit_px is None and pos.bars_held >= cfg.max_holding_bars:
                    exit_px, exit_reason = cl, C.EXIT_TIME
                if exit_px is not None:
                    cash, trades, consecutive_losses = self._close_position(
                        pos, exit_px, t, exit_reason, cash, trades, consecutive_losses,
                        cfg,
                    )
                    del positions[sym]

            # ---- 3. risk-engine forced liquidation at close ------------------
            if self.risk.force_exit and positions:
                for sym in list(positions):
                    pos = positions[sym]
                    row = bar_map[sym].get(t)
                    if row is None:
                        continue
                    cash, trades, consecutive_losses = self._close_position(
                        pos, float(row.close), t, C.EXIT_RISK, cash, trades,
                        consecutive_losses, cfg,
                    )
                    del positions[sym]

            # ---- 4. mark to market + record equity ---------------------------
            equity = cash
            for sym, pos in positions.items():
                row = bar_map[sym].get(t)
                if row is not None:
                    equity += pos.qty * float(row.close)
            equity_hist.append((t, equity))
            last_equity = equity
            peak_equity = max(peak_equity, equity)

            # ---- 5. risk engine updates --------------------------------------
            day = t.normalize()
            if day not in day_start_equity:
                day_start_equity[day] = equity
            vol_now = None
            for s in vol_map:
                if t in vol_map[s].index:
                    v = vol_map[s].loc[t]
                    if np.isfinite(v):
                        vol_now = float(v) if vol_now is None else max(vol_now, float(v))
            self.risk.on_bar(
                t=t, equity=equity,
                day_start_equity=day_start_equity[day],
                peak_equity=peak_equity,
                positions=positions,
                consecutive_losses=consecutive_losses,
                realized_vol=vol_now,
            )

            # ---- 6. generate entries for next bar ----------------------------
            if self.risk.new_trades_allowed():
                for sym, sig_frame in signals.items():
                    if t not in sig_frame.index:
                        continue
                    s = sig_frame.loc[t]
                    direction = int(s["direction"])
                    if direction == 0 or not bool(s.get("regime_ok", True)):
                        continue
                    if direction < 0 and not cfg.allow_shorts:
                        continue
                    row = bar_map[sym].get(t)
                    if row is None:
                        continue
                    close_px = float(row.close)
                    if not np.isfinite(close_px) or close_px <= 0:
                        continue
                    atr = atr_map[sym].get(t)
                    if atr is None or atr <= 0 or not np.isfinite(atr):
                        continue
                    qty = size_position(
                        equity=equity,
                        entry=close_px,
                        stop_distance=cfg.stop_atr_mult * atr,
                        confidence=float(s["confidence"]),
                        expected_R=float(s["expected_R"]),
                        params=cfg.sizing,
                        drawdown_frac=(peak_equity - equity) / peak_equity if peak_equity > 0 else 0.0,
                        vol_frac=self.risk.vol_frac,
                        bar_adv=float(row.volume) * close_px,
                    )
                    if qty <= 0:
                        continue
                    stop = close_px - direction * cfg.stop_atr_mult * atr
                    target = close_px + direction * cfg.stop_atr_mult * atr * cfg.target_rr
                    ok, msg = self.risk.check_entry(
                        symbol=sym, direction=direction, qty=qty,
                        entry=close_px, stop=stop, equity=equity,
                        positions=positions,
                        bar_adv=float(row.volume) * close_px,
                    )
                    if ok:
                        pending.append(PendingOrder(
                            symbol=sym, direction=direction, qty=qty,
                            confidence=float(s["confidence"]),
                            expected_R=float(s["expected_R"]),
                            reason=str(s["reason"]),
                            stop=stop, target=target, decision_time=t,
                        ))
                    else:
                        self.risk.log_rejection(sym, t, direction, msg)

        # ---- close any remaining positions at the last close -----------------
        last_t = master[-1]
        for sym, pos in list(positions.items()):
            row = bar_map[sym].get(last_t)
            if row is not None:
                cash, trades, consecutive_losses = self._close_position(
                    pos, float(row.close), last_t, C.EXIT_MANUAL, cash, trades,
                    consecutive_losses, cfg,
                )

        eq_df = pd.DataFrame(equity_hist, columns=["time", "equity"]).set_index("time")
        trades_df = pd.DataFrame(trades, columns=TRADE_COLUMNS) if trades else pd.DataFrame(columns=TRADE_COLUMNS)
        from .metrics import compute_metrics, decompose
        metrics = compute_metrics(eq_df, trades_df, cfg)
        decompositions = decompose(trades_df, eq_df, cfg)
        return BacktestResult(
            equity_curve=eq_df, trades=trades_df, metrics=metrics,
            decompositions=decompositions, signals=signals,
            risk_summary=self.risk.summary(), config=cfg,
        )

    # ------------------------------------------------------------- internals
    def _close_position(self, pos, exit_px, t, reason, cash, trades,
                        consecutive_losses, cfg):
        cost = cost_of_fill(cfg.costs, abs(exit_px * pos.qty), abs(pos.qty), None)
        exit_commission = cost.commission
        exit_slippage = abs(exit_px) * cost.cost_bps / 10_000.0 * abs(pos.qty)
        pnl = (pos.qty * (exit_px - pos.entry_price)
               - pos.entry_commission - exit_commission)
        cash += pos.qty * exit_px - exit_commission
        costs_total = (pos.entry_commission + exit_commission
                       + pos.entry_slippage + exit_slippage)
        trades.append({
            "trade_id": pos.trade_id, "symbol": pos.symbol,
            "direction": int(np.sign(pos.qty)),
            "entry_time": pos.entry_time, "exit_time": t,
            "entry_price": pos.entry_price, "exit_price": exit_px,
            "qty": abs(pos.qty), "stop": pos.stop, "target": pos.target,
            "confidence": pos.confidence, "expected_R": pos.expected_R,
            "reason": pos.reason, "exit_reason": reason,
            "mfe": pos.mfe, "mae": pos.mae,
            "entry_commission": pos.entry_commission,
            "entry_slippage": pos.entry_slippage,
            "exit_commission": exit_commission,
            "exit_slippage": exit_slippage,
            "costs_total": costs_total,
            "pnl": pnl,
            "ret_pct": pnl / pos.notional_at_entry if pos.notional_at_entry else 0.0,
            "bars_held": pos.bars_held,
            "equity_at_entry": pos.equity_at_entry,
        })
        if pnl < 0:
            consecutive_losses += 1
        else:
            consecutive_losses = 0
        return cash, trades, consecutive_losses


# ---------------------------------------------------------------- utilities
def _union_index(bars: dict[str, pd.DataFrame]) -> pd.DatetimeIndex:
    idx = bars[list(bars)[0]].index
    for s in bars:
        idx = idx.union(bars[s].index)
    return idx.sort_values()


def _median_step(idx: pd.DatetimeIndex) -> pd.Timedelta:
    if len(idx) < 2:
        return pd.Timedelta("1h")
    diffs = pd.Series(idx).diff().dropna()
    return diffs.median() if len(diffs) else pd.Timedelta("1h")


def _atr_series(bars: pd.DataFrame, n: int = 14) -> pd.Series:
    prev_close = bars["close"].shift(1)
    tr = pd.concat([
        bars["high"] - bars["low"],
        (bars["high"] - prev_close).abs(),
        (bars["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(n, min_periods=n).mean()


def bars_per_year(freq: str) -> float:
    """Approximate bars per calendar year for a pandas offset string."""
    table = {"h": 252 * 6.5, "30min": 252 * 13, "15min": 252 * 26, "5min": 252 * 78,
             "d": 252, "W": 52, "M": 12}
    if freq in table:
        return table[freq]
    return 252.0
