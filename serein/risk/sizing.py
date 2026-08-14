"""Position sizing: risk-budget-based with confidence / drawdown / vol scaling.

Rules (non-negotiable):
  * risk per trade is a fraction of CURRENT equity — never a fixed dollar
    amount that ignores drawdown
  * martingale is structurally impossible: size never depends on prior pnl
  * confidence can only scale size WITHIN the risk budget, never beyond caps
"""

from __future__ import annotations

import math

from ..config import SizingParams


def size_position(
    equity: float,
    entry: float,
    stop_distance: float,
    confidence: float,
    expected_R: float,
    params: SizingParams,
    drawdown_frac: float = 0.0,
    vol_frac: float = 1.0,
    bar_adv: float | None = None,
) -> int:
    """Return number of shares (positive), or 0 for 'no position'.

    Args:
        equity: current account equity
        entry: planned entry price
        stop_distance: per-share distance to stop (entry - stop)
        confidence: model confidence 0..1
        expected_R: expected reward/risk (used only for a small quality gate)
        params: SizingParams
        drawdown_frac: current drawdown from peak (0..1)
        vol_frac: volatility scale from RiskEngine (0.25..1.5)
        bar_adv: bar dollar volume (for liquidity cap)
    """
    if equity <= 0 or entry <= 0 or stop_distance <= 0:
        return 0
    if confidence < params.confidence_floor:
        return 0
    if expected_R <= 0.2:                      # no point risking for pennies
        return 0

    # base risk budget
    risk_budget = equity * (params.risk_per_trade_pct / 100.0)

    # confidence multiplier: linear from floor -> 1.0 at confidence=1
    span = max(1.0 - params.confidence_floor, 1e-9)
    conf_mult = 1.0 + (params.max_confidence_mult - 1.0) * (
        (confidence - params.confidence_floor) / span
    )
    conf_mult = min(max(conf_mult, 1.0), params.max_confidence_mult)

    dd_scale = 1.0
    if params.drawdown_scale_on:
        dd_scale = max(0.0, 1.0 - drawdown_frac)   # linear shrink to zero at 100% DD
    vol_scale = vol_frac if params.vol_scale_on else 1.0

    notional = (risk_budget * conf_mult * dd_scale * vol_scale) / (
        stop_distance / entry
    )

    # hard caps
    notional = min(notional, equity * params.max_notional_frac)
    if bar_adv is not None and bar_adv > 0:
        notional = min(notional, bar_adv * params.max_adv_share)

    if notional < params.min_order_notional:
        return 0

    qty = math.floor(notional / entry / params.lot_size) * params.lot_size
    return qty
