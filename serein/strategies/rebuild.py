"""Serein Strategy v2 research candidates: small, objective, auditable edges.

These are hypotheses, not approved trading systems.  Each candidate translates a
common discretionary idea into causal rules and emits optional structural stop and
target prices.  The backtester executes one bar later and the Risk Engine retains
absolute authority.

The module intentionally exposes only a handful of concepts:
  * trend pullback and continuation;
  * volatility-compression breakout;
  * failed-breakout reversal;
  * session-VWAP reversion.

No order blocks, fair-value gaps, liquidity sweeps, or "smart money" labels are
used unless the idea has an objective price-based definition.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .base import Strategy, empty_signals, validate_signals
from .zoo import _true_range


@dataclass(frozen=True)
class ComponentSpec:
    name: str
    mechanism: str
    rules: int
    parameters: int
    indicators: int
    execution_difficulty: int  # 1 easy .. 5 difficult
    known_failure: str


COMPONENTS = {
    "trend_context": ComponentSpec(
        "trend_context", "Persistent directional imbalance", 2, 2, 2, 1,
        "Whipsaw in ranges and rapid reversals",
    ),
    "pullback": ComponentSpec(
        "pullback", "Enter continuation after temporary countertrend pressure", 2, 2, 1, 2,
        "A pullback may be the start of a reversal",
    ),
    "break_trigger": ComponentSpec(
        "break_trigger", "Require renewed with-trend pressure", 1, 0, 0, 2,
        "Gap or one-bar false break",
    ),
    "volatility_gate": ComponentSpec(
        "volatility_gate", "Avoid abnormal volatility and untradeable stops", 1, 2, 1, 1,
        "Can remove the strongest trends",
    ),
    "volume_filter": ComponentSpec(
        "volume_filter", "Demand activity above the local baseline", 1, 2, 1, 2,
        "Volume is session-dependent and not comparable across venues",
    ),
    "structural_invalidation": ComponentSpec(
        "structural_invalidation", "Exit where the setup thesis is objectively false", 1, 1, 0, 2,
        "Nearby swing levels can be noise",
    ),
}


def simplicity_score(component_names: tuple[str, ...], model_complexity: int = 0) -> float:
    """Transparent 0..100 conceptual simplicity score (higher is simpler).

    It is not a performance metric.  Penalties are declared rather than learned:
    rules 3 points, parameters 4, indicators 4, execution difficulty 2, and
    black-box model complexity 10 per level.
    """
    specs = [COMPONENTS[n] for n in component_names]
    penalty = sum(3*s.rules + 4*s.parameters + 4*s.indicators + 2*s.execution_difficulty
                  for s in specs) + 10*model_complexity
    return float(max(0, 100 - penalty))


def _finish(sig: pd.DataFrame, direction: pd.Series | np.ndarray, confidence,
            expected_r: float, horizon: int, reason: str, stop: pd.Series,
            target_r: float = 2.0, regime_ok=True) -> pd.DataFrame:
    d = pd.Series(direction, index=sig.index).fillna(0).astype(int)
    sig["direction"] = d
    sig["confidence"] = pd.Series(confidence, index=sig.index).fillna(0.0).clip(0, 1)
    sig["expected_R"] = np.where(d != 0, expected_r, 0.0)
    sig["horizon_bars"] = horizon
    sig["regime_ok"] = pd.Series(regime_ok, index=sig.index).fillna(False).astype(bool)
    sig["reason"] = np.where(d != 0, reason, "no_setup")
    sig["stop_price"] = pd.Series(stop, index=sig.index).where(d != 0)
    risk = (sig["close_reference"] - sig["stop_price"]).abs()
    sig["target_price"] = (sig["close_reference"] + d * risk * target_r).where(d != 0)
    sig.drop(columns=["close_reference"], inplace=True)
    validate_signals(sig)
    return sig


class TrendPullbackStrategy(Strategy):
    """Strategy v2.0 candidate: trend -> pullback -> one-bar continuation.

    Optional filters permit controlled smallest-viable-edge experiments.  The
    core trigger is a close through the previous bar's extreme after the prior
    bar touched the fast EMA.  Trend, volatility, and volume are each removable.
    """
    name = "v2_trend_pullback"

    def __init__(self, params=None):
        super().__init__(params)
        p = params or {}
        self.fast = int(p.get("fast", 20))
        self.slow = int(p.get("slow", 60))
        self.swing_n = int(p.get("swing_n", 5))
        self.target_r = float(p.get("target_r", 2.0))
        self.use_trend = bool(p.get("use_trend", True))
        self.use_volatility = bool(p.get("use_volatility", True))
        self.use_volume = bool(p.get("use_volume", False))

    @property
    def components(self) -> tuple[str, ...]:
        out = ["pullback", "break_trigger", "structural_invalidation"]
        if self.use_trend:
            out.append("trend_context")
        if self.use_volatility:
            out.append("volatility_gate")
        if self.use_volume:
            out.append("volume_filter")
        return tuple(out)

    @property
    def simplicity(self) -> float:
        return simplicity_score(self.components)

    def generate(self, bars, regime=None):
        c, h, l = bars["close"], bars["high"], bars["low"]
        fast = c.ewm(span=self.fast, adjust=False, min_periods=self.fast).mean()
        slow = c.ewm(span=self.slow, adjust=False, min_periods=self.slow).mean()
        atr = _true_range(bars).rolling(14, min_periods=14).mean()

        up_context = (fast > slow) & (slow.diff(5) > 0)
        dn_context = (fast < slow) & (slow.diff(5) < 0)
        prior_long_pullback = (l.shift(1) <= fast.shift(1) + 0.25*atr.shift(1)) & (c.shift(1) >= slow.shift(1))
        prior_short_pullback = (h.shift(1) >= fast.shift(1) - 0.25*atr.shift(1)) & (c.shift(1) <= slow.shift(1))
        long_trigger = prior_long_pullback & (c > h.shift(1))
        short_trigger = prior_short_pullback & (c < l.shift(1))

        if not self.use_trend:
            up_context = pd.Series(True, index=c.index)
            dn_context = pd.Series(True, index=c.index)

        vol_rank = (atr/c).rolling(500, min_periods=100).rank(pct=True)
        vol_ok = vol_rank.fillna(0.5).between(0.10, 0.90) if self.use_volatility else pd.Series(True, index=c.index)
        rel_volume = bars["volume"] / bars["volume"].rolling(20, min_periods=20).mean().replace(0, np.nan)
        volume_ok = rel_volume.fillna(0) >= 1.10 if self.use_volume else pd.Series(True, index=c.index)
        allowed = vol_ok & volume_ok

        long = long_trigger & up_context & allowed
        short = short_trigger & dn_context & allowed
        direction = pd.Series(np.where(long, 1, np.where(short, -1, 0)), index=c.index)
        stop_long = l.rolling(self.swing_n, min_periods=self.swing_n).min() - 0.10*atr
        stop_short = h.rolling(self.swing_n, min_periods=self.swing_n).max() + 0.10*atr
        stop = pd.Series(np.where(direction > 0, stop_long, stop_short), index=c.index)
        strength = ((fast-slow).abs()/atr.replace(0, np.nan)).clip(0, 2)
        confidence = (0.55 + 0.15*strength + 0.05*(rel_volume.fillna(1)-1).clip(0, 1)).clip(0, 0.85)

        sig = empty_signals(bars.index)
        sig["close_reference"] = c
        return _finish(sig, direction, confidence, self.target_r, self.slow,
                       "trend_pullback_break", stop, self.target_r, allowed)


class CompressionBreakoutV2Strategy(Strategy):
    """Break the prior range only after trailing range contraction."""
    name = "v2_compression_breakout"

    def __init__(self, params=None):
        super().__init__(params)
        p = params or {}
        self.lookback = int(p.get("lookback", 40))
        self.compression_n = int(p.get("compression_n", 20))
        self.target_r = float(p.get("target_r", 2.5))

    @property
    def simplicity(self):
        return 58.0

    def generate(self, bars, regime=None):
        c = bars["close"]
        atr = _true_range(bars).rolling(14, min_periods=14).mean()
        hi = bars["high"].rolling(self.lookback, min_periods=self.lookback).max().shift(1)
        lo = bars["low"].rolling(self.lookback, min_periods=self.lookback).min().shift(1)
        recent_atr = atr.rolling(self.compression_n, min_periods=self.compression_n).mean()
        baseline = atr.rolling(5*self.compression_n, min_periods=3*self.compression_n).mean()
        compressed = recent_atr < 0.80*baseline
        rv = bars["volume"] / bars["volume"].rolling(20, min_periods=20).mean().replace(0, np.nan)
        active = compressed & (rv > 1.15)
        d = pd.Series(np.where(active & (c > hi), 1, np.where(active & (c < lo), -1, 0)), index=c.index)
        stop = pd.Series(np.where(d > 0, lo, hi), index=c.index)
        sig = empty_signals(bars.index); sig["close_reference"] = c
        return _finish(sig, d, (0.55+0.10*(rv-1).clip(0,2)), self.target_r,
                       self.lookback, "compression_range_break", stop, self.target_r, active)


class FailedBreakoutStrategy(Strategy):
    """Objective sweep/failure: breach a prior range, close back inside, confirm."""
    name = "v2_failed_breakout"

    def __init__(self, params=None):
        super().__init__(params)
        p = params or {}
        self.lookback = int(p.get("lookback", 30))
        self.target_r = float(p.get("target_r", 1.5))

    @property
    def simplicity(self):
        return 68.0

    def generate(self, bars, regime=None):
        c, h, l = bars["close"], bars["high"], bars["low"]
        atr = _true_range(bars).rolling(14, min_periods=14).mean()
        prior_hi = h.rolling(self.lookback, min_periods=self.lookback).max().shift(2)
        prior_lo = l.rolling(self.lookback, min_periods=self.lookback).min().shift(2)
        failed_up = (h.shift(1) > prior_hi) & (c.shift(1) < prior_hi)
        failed_dn = (l.shift(1) < prior_lo) & (c.shift(1) > prior_lo)
        short = failed_up & (c < l.shift(1))
        long = failed_dn & (c > h.shift(1))
        d = pd.Series(np.where(long, 1, np.where(short, -1, 0)), index=c.index)
        stop = pd.Series(np.where(d > 0, l.shift(1)-0.10*atr, h.shift(1)+0.10*atr), index=c.index)
        normal_vol = (atr/c).rolling(300, min_periods=100).rank(pct=True).fillna(0.5) < 0.90
        sig = empty_signals(bars.index); sig["close_reference"] = c
        return _finish(sig, d, 0.62, self.target_r, self.lookback//2,
                       "failed_breakout_reentry", stop, self.target_r, normal_vol)


class VWAPReversionV2Strategy(Strategy):
    """Session VWAP deviation that triggers only after price turns back toward VWAP."""
    name = "v2_vwap_reversion"

    def __init__(self, params=None):
        super().__init__(params)
        p = params or {}
        self.z_entry = float(p.get("z_entry", 2.0))
        self.target_r = float(p.get("target_r", 1.25))

    @property
    def simplicity(self):
        return 64.0

    def generate(self, bars, regime=None):
        c, h, l, v = bars["close"], bars["high"], bars["low"], bars["volume"]
        typical = (h+l+c)/3
        day = pd.Series(bars.index.normalize(), index=bars.index)
        cum_pv = (typical*v).groupby(day).cumsum()
        cum_v = v.groupby(day).cumsum().replace(0, np.nan)
        vwap = cum_pv/cum_v
        atr = _true_range(bars).rolling(14, min_periods=14).mean()
        z = (c-vwap)/atr.replace(0, np.nan)
        long = (z.shift(1) < -self.z_entry) & (c > c.shift(1))
        short = (z.shift(1) > self.z_entry) & (c < c.shift(1))
        d = pd.Series(np.where(long, 1, np.where(short, -1, 0)), index=c.index)
        stop = pd.Series(np.where(d > 0, l.rolling(3).min()-0.1*atr,
                                  h.rolling(3).max()+0.1*atr), index=c.index)
        # Strong trends invalidate a reversion premise.
        trend_strength = c.pct_change(20).abs()/((atr/c)*np.sqrt(20)).replace(0, np.nan)
        range_ok = trend_strength.fillna(99) < 1.5
        sig = empty_signals(bars.index); sig["close_reference"] = c
        return _finish(sig, d, (0.55+0.05*z.abs().clip(0,3)), self.target_r, 12,
                       "vwap_deviation_turn", stop, self.target_r, range_ok)
