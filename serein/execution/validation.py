"""Pre-trade order validation (hard gate before any order reaches a broker).

Implements the full checklist from the project mandate (§33). ANY critical
'no' means DO NOT TRADE. This runs independently of the alpha layer and can
never be bypassed by a model.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ..config import RiskLimits, SizingParams

_SYMBOL_RE = re.compile(r"^[A-Za-z0-9._\-]{1,20}$")


@dataclass
class ValidationResult:
    ok: bool
    checks: dict = field(default_factory=dict)

    def failures(self) -> list[str]:
        return [k for k, v in self.checks.items() if v is False]

    def summary(self) -> str:
        if self.ok:
            return "PASS: all pre-trade checks ok"
        return "FAIL: " + "; ".join(self.failures())


class OrderValidator:
    """Deterministic pre-trade gate. No model can modify these checks."""

    def __init__(self, limits: RiskLimits, sizing: SizingParams):
        self.limits = limits
        self.sizing = sizing

    def validate(
        self,
        *,
        symbol: str,
        direction: int,
        qty: int,
        price: float,
        quote: dict | None,
        positions: dict,
        open_orders: list,
        equity: float,
        data_fresh: bool,
        market_open: bool,
        broker_healthy: bool,
        model_approved: bool,
        daily_loss_halted: bool,
        risk_new_trades_allowed: bool,
        bar_volume: float | None = None,
        now: pd.Timestamp | None = None,
        weekly_loss_halted: bool = False,
        strategy_approved: bool = True,
        account_authorized: bool = True,
        quote_required: bool = False,
    ) -> ValidationResult:
        checks: dict[str, bool] = {}
        lim = self.limits

        checks["market_open"] = market_open
        checks["data_fresh"] = data_fresh
        checks["symbol_valid"] = bool(symbol and _SYMBOL_RE.match(str(symbol)))
        checks["price_reasonable"] = (
            np.isfinite(price) and price > 0 and price < 1e6
        )
        checks["qty_valid"] = qty > 0
        checks["direction_valid"] = direction in (-1, 1)

        checks["quote_available"] = quote is not None or not quote_required
        if quote is not None:
            spread = quote.get("spread_bps")
            if spread is None and quote.get("bid") and quote.get("ask"):
                mid = (quote["bid"] + quote["ask"]) / 2
                spread = (quote["ask"] - quote["bid"]) / mid * 10_000 if mid > 0 else np.inf
            checks["spread_acceptable"] = spread is None or spread <= lim.max_spread_bps
            qt = quote.get("time")
            checks["quote_fresh"] = not (now is not None and qt is not None) or qt >= now-pd.Timedelta(seconds=30)
        else:
            checks["spread_acceptable"] = not quote_required
            checks["quote_fresh"] = not quote_required

        notional = price * qty
        checks["size_acceptable"] = notional <= equity * lim.max_per_symbol_frac
        checks["position_limit_ok"] = len(positions) < lim.max_positions
        checks["no_conflict"] = symbol not in positions
        checks["no_dup_order"] = not any(
            o.symbol == symbol and o.status in ("NEW", "PARTIAL")
            for o in open_orders
        )
        checks["daily_loss_ok"] = not daily_loss_halted
        checks["weekly_loss_ok"] = not weekly_loss_halted
        checks["risk_engine_ok"] = risk_new_trades_allowed
        checks["broker_healthy"] = broker_healthy
        checks["strategy_approved"] = strategy_approved
        checks["model_approved"] = model_approved
        checks["account_authorized"] = account_authorized
        checks["leverage_ok"] = (notional / max(equity, 1e-9)) <= lim.max_leverage
        checks["liquidity_acceptable"] = (bar_volume is None or bar_volume <= 0
                                           or qty <= bar_volume*self.sizing.max_adv_share)

        ok = all(checks.values())
        return ValidationResult(ok=ok, checks=checks)
