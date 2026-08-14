"""Risk Engine — the ultimate authority.

The alpha/meta layers propose; the Risk Engine disposes. It enforces hard
limits and kill switches. By construction nothing in the alpha layer can
loosen a limit here; limits live in RiskLimits and are only ever tightened.

Kill switches: any trip => NO_NEW_TRADES. The drawdown kill and emergency
floor additionally request position liquidation (the engine closes at the
next bar close). Kill switches can be tripped but never un-tripped by the
strategy layer; only an authorized reset procedure can clear them.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .. import constants as C
from ..config import RiskLimits, SizingParams

VOL_TARGET_DEFAULT = 0.15
VOL_FLOOR = 0.25
VOL_CEIL = 1.5


@dataclass
class RiskEngine:
    limits: RiskLimits
    sizing: SizingParams
    vol_target: float = VOL_TARGET_DEFAULT

    kill_switches: dict = field(default_factory=dict)
    kill_reasons: dict = field(default_factory=dict)
    rejections: list = field(default_factory=list)
    trades_executed_today: dict = field(default_factory=dict)
    trades_executed_hour: dict = field(default_factory=dict)
    vol_frac: float = 1.0
    force_exit: bool = False
    start_equity: float = 0.0
    _daily_loss_halted: bool = False
    _weekly_loss_halted: bool = False
    _week_start_equity: tuple = None  # type: ignore[assignment]
    _today_tag: object = None
    _hour_tag: object = None

    def __post_init__(self):
        self.kill_switches = {ks: False for ks in C.ALL_KILL_SWITCHES}
        self.kill_reasons = {}
        self.rejections = []
        self.trades_executed_today = {}
        self.trades_executed_hour = {}
        self.vol_frac = 1.0
        self.force_exit = False
        self.start_equity = 0.0
        self._daily_loss_halted = False
        self._weekly_loss_halted = False
        self._week_start_equity = None
        self._today_tag = None
        self._hour_tag = None

    # ------------------------------------------------------------ kill switch
    def trip(self, ks: str, reason: str) -> None:
        if not self.kill_switches.get(ks, False):
            self.kill_switches[ks] = True
            self.kill_reasons[ks] = reason

    def is_tripped(self) -> bool:
        return any(self.kill_switches.values())

    def new_trades_allowed(self) -> bool:
        if self.is_tripped():
            return False
        if self._daily_loss_halted or self._weekly_loss_halted:
            return False
        return True

    def tripped_switches(self) -> list[str]:
        return [ks for ks, v in self.kill_switches.items() if v]

    # --------------------------------------------------------------- per bar
    def on_bar(
        self,
        t: pd.Timestamp,
        equity: float,
        day_start_equity: float,
        peak_equity: float,
        positions: dict,
        consecutive_losses: int,
        realized_vol: float | None = None,
    ) -> None:
        if self.start_equity <= 0:
            self.start_equity = equity
        self._today_tag = t.normalize()
        self._hour_tag = t.floor("h")

        # daily loss limit
        if day_start_equity > 0:
            day_pnl_pct = (equity - day_start_equity) / day_start_equity
            if day_pnl_pct <= -self.limits.daily_loss_limit_pct / 100.0:
                self._daily_loss_halted = True
                self.trip(C.KS_DRAWDOWN, f"daily loss limit hit ({day_pnl_pct:.2%})")

        # weekly loss limit
        period_time = t.tz_localize(None) if t.tzinfo is not None else t
        week_start = period_time.to_period("W").start_time
        if self._week_start_equity is None or self._week_start_equity[0] != week_start:
            self._week_start_equity = (week_start, equity)
        else:
            week_pnl = (equity - self._week_start_equity[1]) / self._week_start_equity[1]
            if week_pnl <= -self.limits.weekly_loss_limit_pct / 100.0:
                self._weekly_loss_halted = True
                self.trip(C.KS_DRAWDOWN, f"weekly loss limit hit ({week_pnl:.2%})")

        # drawdown kill switch
        if peak_equity > 0:
            dd = (peak_equity - equity) / peak_equity
            if dd >= self.limits.max_portfolio_drawdown_pct / 100.0:
                self.trip(C.KS_DRAWDOWN, f"portfolio drawdown {dd:.2%} >= limit")
                self.force_exit = True

        # emergency equity floor
        if equity <= self.start_equity * self.limits.emergency_equity_floor_frac:
            self.trip(C.KS_DRAWDOWN, "emergency equity floor breached")
            self.force_exit = True

        # consecutive losses
        if consecutive_losses >= self.limits.max_consecutive_losses:
            self.trip(C.KS_DRAWDOWN, f"{consecutive_losses} consecutive losses")

        # volatility kill + vol scaling
        if realized_vol is not None:
            if realized_vol > 1.2:  # annualized > 120%: structurally untradeable
                self.trip(C.KS_VOLATILITY, f"realized vol {realized_vol:.0%} extreme")
                self.force_exit = True
            if realized_vol > 1e-4:
                self.vol_frac = float(np.clip(
                    np.sqrt(self.vol_target / realized_vol), VOL_FLOOR, VOL_CEIL
                ))

        if self.force_exit and not positions:
            self.force_exit = False  # liquidation completed

    # ------------------------------------------------------------- pre-trade
    def check_entry(
        self,
        symbol: str,
        direction: int,
        qty: int,
        entry: float,
        stop: float,
        equity: float,
        positions: dict,
        bar_adv: float | None = None,
    ) -> tuple[bool, str]:
        """The full pre-trade checklist. ANY critical no => no trade."""
        lim = self.limits

        if not self.new_trades_allowed():
            return False, "risk: kill switch or halt active"
        if direction not in (-1, 1) or qty <= 0:
            return False, f"risk: invalid order (dir={direction}, qty={qty})"
        if not np.isfinite(entry) or entry <= 0 or not np.isfinite(stop) or stop <= 0:
            return False, "risk: non-finite or non-positive price"
        if direction > 0 and stop >= entry:
            return False, "risk: long stop above entry"
        if direction < 0 and stop <= entry:
            return False, "risk: short stop below entry"

        notional = entry * qty
        if notional > equity * lim.max_per_symbol_frac:
            return False, (
                f"risk: notional {notional:.0f} > per-symbol cap "
                f"{equity * lim.max_per_symbol_frac:.0f}"
            )

        gross = sum(abs(p.qty * p.entry_price) for p in positions.values()) + notional
        if gross > equity * lim.max_gross_exposure_frac:
            return False, f"risk: gross exposure {gross:.0f} > cap"
        net = sum(p.qty * p.entry_price for p in positions.values()) + direction * notional
        if abs(net) > equity * lim.max_net_exposure_frac:
            return False, f"risk: net exposure {net:.0f} > cap"
        if len(positions) >= lim.max_positions:
            return False, f"risk: at max positions ({lim.max_positions})"
        if symbol in positions:
            return False, f"risk: existing position in {symbol} (conflict policy)"
        if bar_adv is not None and bar_adv > 0 and notional > bar_adv * self.sizing.max_adv_share:
            return False, (
                f"risk: order {notional:.0f} > {self.sizing.max_adv_share:.0%} "
                f"of bar ADV {bar_adv:.0f}"
            )

        if self._today_tag is not None:
            if self.trades_executed_today.get(self._today_tag, 0) >= lim.max_daily_trades:
                return False, "risk: daily trade count limit"
        if self._hour_tag is not None:
            if self.trades_executed_hour.get(self._hour_tag, 0) >= lim.max_trading_freq_per_hour:
                return False, "risk: hourly trade frequency limit"

        return True, "ok"

    def log_rejection(self, symbol: str, t, direction: int, msg: str) -> None:
        self.rejections.append(
            {"time": t, "symbol": symbol, "direction": direction, "reason": msg}
        )

    def on_trade_executed(self, t: pd.Timestamp) -> None:
        day = t.normalize()
        hour = t.floor("h")
        self.trades_executed_today[day] = self.trades_executed_today.get(day, 0) + 1
        self.trades_executed_hour[hour] = self.trades_executed_hour.get(hour, 0) + 1

    def summary(self) -> dict:
        return {
            "tripped": self.tripped_switches(),
            "kill_reasons": dict(self.kill_reasons),
            "rejections": len(self.rejections),
            "vol_frac": round(self.vol_frac, 3),
            "force_exit": self.force_exit,
            "daily_halted": self._daily_loss_halted,
            "weekly_halted": self._weekly_loss_halted,
        }
