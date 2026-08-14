"""Configuration: every important number has a rationale entry and lives here.

Rule: NO MAGIC NUMBERS in strategy/risk code. Any threshold that matters is
either (a) a field in one of these dataclasses with a documented rationale, or
(b) a parameter explicitly passed by an experiment.

Rationale strings should point to evidence (see research/decision_log and
research/source_register.md) rather than taste.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any


@dataclass
class CostModel:
    """Execution cost assumptions. Defaults are deliberately CONSERVATIVE for
    a retail-scale equity account (see Schwarz 2025, J. of Finance: retail
    round-trip costs measured 7-46 bps; we use ~16 bps round trip baseline)."""

    commission_per_share: float = 0.003      # per share, per side (e.g. $3/k shares)
    min_commission: float = 0.0              # per order
    half_spread_bps: float = 2.5             # one-way half-spread on liquid names
    slippage_bps: float = 3.0                # one-way stochastic slippage
    impact_coeff: float = 2.0                # impact_bps = coeff * (order_notional / bar_adv)
    borrow_cost_bps_per_day: float = 0.0     # short borrow/financing (0 for synthetic demo)
    # Shocks applied by stress tests are multipliers on the above.

    def one_way_bps(self, order_notional: float, bar_adv: float | None) -> float:
        base = self.half_spread_bps + self.slippage_bps
        impact = 0.0
        if bar_adv and bar_adv > 0:
            impact = self.impact_coeff * (order_notional / bar_adv) * 100.0
        return base + impact

    @property
    def round_trip_bps(self) -> float:
        return 2.0 * (self.half_spread_bps + self.slippage_bps)


@dataclass
class SizingParams:
    """Position sizing: risk-based with confidence / drawdown / vol scaling.

    rationale:
      - risk_per_trade_pct: per-trade risk cap (1% of equity is a common
        institutional per-position risk budget; 0.5% for research mode).
      - confidence_floor: below this model confidence, no position at all.
      - drawdown_scale: exposure shrinks linearly to zero as drawdown
        approaches max_portfolio_drawdown_pct.
    """

    risk_per_trade_pct: float = 0.5
    confidence_floor: float = 0.52
    max_confidence_mult: float = 1.5        # size multiplier at very high confidence
    drawdown_scale_on: bool = True
    vol_scale_on: bool = True
    target_annual_vol_pct: float = 15.0     # vol targeting anchor
    max_notional_frac: float = 0.25         # per-symbol cap, fraction of equity
    max_adv_share: float = 0.02             # never take more than 2% of a bar's volume
    min_order_notional: float = 500.0
    lot_size: int = 1


@dataclass
class RiskLimits:
    """Absolute, non-negotiable ceilings. The Risk Engine can only make these
    TIGHTER, never looser."""

    max_positions: int = 5
    max_gross_exposure_frac: float = 1.0       # gross notional / equity
    max_net_exposure_frac: float = 0.8
    max_per_symbol_frac: float = 0.25
    max_leverage: float = 1.0                  # paper: no leverage
    daily_loss_limit_pct: float = 2.0          # stop new trades for the day
    weekly_loss_limit_pct: float = 4.0
    max_portfolio_drawdown_pct: float = 10.0   # -> drawdown kill switch
    max_consecutive_losses: int = 6
    max_spread_bps: float = 30.0
    max_daily_trades: int = 20
    max_trading_freq_per_hour: int = 6
    emergency_equity_floor_frac: float = 0.8   # fraction of starting equity
    model_confidence_min: float = 0.0          # set by meta engine, floor here
    data_max_staleness: int = 2                # bars
    slippage_realized_alert_bps: float = 25.0  # rolling realized slippage alert


@dataclass
class StrategyParams:
    """Default parameters for baseline strategies. These are STARTING POINTS
    for experiments, not optimized magic numbers."""

    trend_fast: int = 20
    trend_slow: int = 60
    trend_atr_mult: float = 2.0
    trend_vol_filter_n: int = 60               # require vol below percentile cap
    trend_vol_filter_pct: float = 0.90

    momentum_lookback: int = 120               # TSMOM-style: past-`lookback` return sign
    momentum_vol_scale_n: int = 60

    reversion_z_n: int = 60
    reversion_z_entry: float = 2.0
    reversion_z_exit: float = 0.0
    reversion_atr_filter_pct: float = 0.75     # only trade when vol in calm regime

    breakout_lookback: int = 120               # Donchian channel
    breakout_vol_compression_n: int = 40       # require compression before expansion
    breakout_compression_pct: float = 0.6      # ATR percentile below this = compressed


@dataclass
class BacktestConfig:
    start: str = "2018-01-01"
    end: str = "2026-01-01"
    freq: str = "h"
    initial_equity: float = 100_000.0
    horizon_bars: int = 6                      # prediction horizon for ML labels
    max_holding_bars: int = 120
    stop_atr_mult: float = 2.0
    target_rr: float = 2.0                     # target = risk * rr
    allow_shorts: bool = True
    seed: int = 42

    costs: CostModel = field(default_factory=CostModel)
    sizing: SizingParams = field(default_factory=SizingParams)
    risk: RiskLimits = field(default_factory=RiskLimits)
    strategy: StrategyParams = field(default_factory=StrategyParams)


def load_config(path: str | Path) -> BacktestConfig:
    """Load a JSON config (subset overrides) into BacktestConfig."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"config not found: {p}")
    raw: dict[str, Any] = json.loads(p.read_text())

    def _build(cls, data: dict[str, Any]):
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})

    cfg = BacktestConfig()
    for k, v in raw.items():
        if k in ("costs", "sizing", "risk", "strategy") and isinstance(v, dict):
            setattr(cfg, k, _build({"costs": CostModel, "sizing": SizingParams,
                                    "risk": RiskLimits, "strategy": StrategyParams}[k], v))
        elif k in BacktestConfig.__dataclass_fields__:
            setattr(cfg, k, v)
    return cfg


def config_to_dict(cfg: BacktestConfig) -> dict[str, Any]:
    return asdict(cfg)
