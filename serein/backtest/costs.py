"""Execution cost model.

Costs are modeled one-way per fill:
    cost_bps = half_spread_bps + slippage_bps + impact_bps(order/ADV)

Baseline parameters are conservative retail assumptions (Schwarz 2025, J.
Finance: retail round-trip equity costs measured 7-46 bps; our baseline is
~11 bps one-way incl. impact, i.e. ~16-22 bps round trip at small size).
"""

from __future__ import annotations

from dataclasses import dataclass

from ..config import CostModel


@dataclass
class FillCost:
    cost_bps: float
    commission: float
    total: float


def cost_of_fill(
    model: CostModel,
    notional: float,
    shares: int,
    bar_volume: float | None,
    multiplier: float = 1.0,
) -> FillCost:
    """Compute the cost of one fill (one side).

    multiplier is used by stress tests (2x, 5x, 10x cost shocks).
    """
    bps = model.one_way_bps(notional, bar_volume) * multiplier
    commission = max(shares * model.commission_per_share, model.min_commission)
    total = notional * bps / 10_000.0 + commission
    return FillCost(cost_bps=bps, commission=commission, total=total)


def slippage_adjusted_price(price: float, direction: int, cost_bps: float) -> float:
    """Fill price after one-way cost: longs buy higher, shorts sell lower."""
    if direction > 0:
        return price * (1.0 + cost_bps / 10_000.0)
    return price * (1.0 - cost_bps / 10_000.0)
