"""Broker abstraction layer.

The system is broker-agnostic: research and strategy code depend only on
this interface. The ONLY implementation provided is a PaperBroker — there is
no live adapter in this repository, by design (PAPER_TRADING_ONLY).

PaperBroker simulates fills from historical bars with the cost model,
so paper results are comparable to backtests (and differences are honest
signals, not noise).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ..config import BacktestConfig
from ..backtest.costs import cost_of_fill, slippage_adjusted_price


@dataclass
class Order:
    order_id: str
    symbol: str
    side: str                 # "buy" | "sell"
    qty: int
    order_type: str = "market"
    status: str = "NEW"
    submitted_at: pd.Timestamp | None = None
    filled_at: pd.Timestamp | None = None
    fill_price: float | None = None
    realized_slippage_bps: float | None = None
    reject_reason: str = ""


@dataclass
class Account:
    cash: float
    equity: float
    positions: dict = field(default_factory=dict)   # symbol -> qty (signed)
    orders: list = field(default_factory=list)
    trades: list = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "cash": round(self.cash, 2),
            "equity": round(self.equity, 2),
            "positions": dict(self.positions),
            "open_orders": sum(1 for o in self.orders if o.status in ("NEW", "PARTIAL")),
        }


class BrokerInterface(ABC):
    """The only vocabulary the execution layer knows."""

    @abstractmethod
    def get_account(self) -> Account: ...
    @abstractmethod
    def get_positions(self) -> dict: ...
    @abstractmethod
    def get_quotes(self, symbols: list[str]) -> dict: ...
    @abstractmethod
    def submit_order(self, order: Order) -> Order: ...
    @abstractmethod
    def cancel_order(self, order_id: str) -> bool: ...
    @abstractmethod
    def modify_order(self, order_id: str, qty: int | None = None,
                     price: float | None = None) -> Order | None: ...
    @abstractmethod
    def get_order_status(self, order_id: str) -> Order | None: ...
    @abstractmethod
    def get_trade_history(self, since: pd.Timestamp | None = None) -> list: ...


class PaperBroker(BrokerInterface):
    """Simulated broker: fills against a bar feed with the cost model."""

    def __init__(self, bars: dict[str, pd.DataFrame], cfg: BacktestConfig,
                 seed: int = 11):
        self.bars = bars
        self.cfg = cfg
        self.rng = np.random.default_rng(seed)
        self.account = Account(cash=cfg.initial_equity, equity=cfg.initial_equity)
        self._order_seq = 0
        self._clock: pd.Timestamp | None = None
        self._healthy = True
        self._fill_ratio = 1.0          # 1.0 = always full fill; <1 simulates partial

    # ------------------------------------------------------------ interface
    def get_account(self) -> Account:
        return self.account

    def get_positions(self) -> dict:
        return dict(self.account.positions)

    def get_quotes(self, symbols: list[str]) -> dict:
        out = {}
        for s in symbols:
            if self._clock is None:
                continue
            b = self.bars[s]
            if self._clock not in b.index:
                continue
            close = float(b.loc[self._clock, "close"])
            spread = self.cfg.costs.half_spread_bps * 2 / 1e4
            out[s] = {"bid": close * (1 - spread / 2),
                      "ask": close * (1 + spread / 2),
                      "time": self._clock}
        return out

    def submit_order(self, order: Order) -> Order:
        self._order_seq += 1
        if not self._healthy:
            order.status = "REJECTED"
            order.reject_reason = "broker unhealthy (injected failure)"
            self.account.orders.append(order)
            return order
        if order.qty <= 0:
            order.status = "REJECTED"
            order.reject_reason = "non-positive quantity"
            self.account.orders.append(order)
            return order
        order.order_id = f"P{self._order_seq:06d}"
        order.submitted_at = self._clock
        # simulate fill at next available bar (market order)
        next_t = self._next_bar_time(order.symbol)
        if next_t is None:
            order.status = "REJECTED"
            order.reject_reason = "no market data"
            self.account.orders.append(order)
            return order
        row = self.bars[order.symbol].loc[next_t]
        fill_px = float(row["open"])
        cost = cost_of_fill(self.cfg.costs, fill_px * order.qty, order.qty,
                            float(row["volume"]) * fill_px)
        side = 1 if order.side == "buy" else -1
        fill = slippage_adjusted_price(fill_px, side, cost.cost_bps)
        order.fill_price = fill
        order.filled_at = next_t
        order.realized_slippage_bps = cost.cost_bps
        # partial fills
        qty_filled = int(order.qty * self._fill_ratio)
        if qty_filled <= 0:
            order.status = "REJECTED"
            order.reject_reason = "no fill (partial fill ratio 0)"
            self.account.orders.append(order)
            return order
        self.account.cash -= side * fill * qty_filled
        self.account.positions[order.symbol] = (
            self.account.positions.get(order.symbol, 0) + side * qty_filled
        )
        order.status = "FILLED" if qty_filled == order.qty else "PARTIAL"
        self.account.orders.append(order)
        self.account.trades.append({
            "order_id": order.order_id, "symbol": order.symbol, "side": order.side,
            "qty": qty_filled, "fill_price": fill, "filled_at": next_t,
            "slippage_bps": cost.cost_bps,
        })
        return order

    def cancel_order(self, order_id: str) -> bool:
        for o in self.account.orders:
            if o.order_id == order_id and o.status in ("NEW", "PARTIAL"):
                o.status = "CANCELLED"
                return True
        return False

    def modify_order(self, order_id: str, qty: int | None = None,
                     price: float | None = None) -> Order | None:
        for o in self.account.orders:
            if o.order_id == order_id and o.status == "NEW":
                if qty is not None:
                    o.qty = qty
                return o
        return None

    def get_order_status(self, order_id: str) -> Order | None:
        for o in self.account.orders:
            if o.order_id == order_id:
                return o
        return None

    def get_trade_history(self, since: pd.Timestamp | None = None) -> list:
        if since is None:
            return list(self.account.trades)
        return [t for t in self.account.trades if t["filled_at"] >= since]

    # ------------------------------------------------------------- control
    def set_clock(self, t: pd.Timestamp) -> None:
        self._clock = t
        # mark to market
        eq = self.account.cash
        for s, qty in self.account.positions.items():
            if s in self.bars and t in self.bars[s].index:
                eq += qty * float(self.bars[s].loc[t, "close"])
            else:
                eq += qty * self._last_price(s, t)
        self.account.equity = eq

    def inject_failure(self, healthy: bool = False) -> None:
        """Failure injection: broker rejects everything while unhealthy."""
        self._healthy = healthy

    def set_fill_ratio(self, ratio: float) -> None:
        self._fill_ratio = float(np.clip(ratio, 0.0, 1.0))

    def _next_bar_time(self, symbol: str) -> pd.Timestamp | None:
        idx = self.bars[symbol].index
        if self._clock is None:
            return idx[0]
        after = idx[idx > self._clock]
        return after[0] if len(after) else None

    def _last_price(self, symbol: str, t: pd.Timestamp) -> float:
        past = self.bars[symbol].loc[:t]
        return float(past["close"].iloc[-1]) if len(past) else 0.0
