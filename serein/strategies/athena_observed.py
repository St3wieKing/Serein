"""Safe, falsifiable proxy for publicly observable Quantum Athena behavior.

This is NOT Quantum Athena and does not contain its proprietary algorithm. Public
sources reveal only: XAUUSD, strongly long-biased, short holding periods, multiple
simultaneous entries, trend-following grid language, and basket-like exits. Exact
six strategies and entry rules are unknown.

Serein will not reproduce the dangerous parts (1:500 leverage, unbounded grid,
blank hard stops). This proxy tests the least-complex causal hypothesis: buy a
dip in an established trend after a short-term reversal trigger, with a hard
structural stop, one position per symbol, and no adding to losers.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .base import Strategy, empty_signals, validate_signals
from .zoo import _true_range


class QuantumAthenaSafeProxy(Strategy):
    name = "quantum_athena_safe_proxy"

    def __init__(self, params=None):
        super().__init__(params)
        p = params or {}
        self.fast = int(p.get("fast", 20))
        self.slow = int(p.get("slow", 100))
        self.dip_atr = float(p.get("dip_atr", 0.45))
        self.target_r = float(p.get("target_r", 1.0))
        self.allow_rare_shorts = bool(p.get("allow_rare_shorts", False))

    def generate(self, bars, regime=None):
        c, h, l = bars.close, bars.high, bars.low
        atr = _true_range(bars).rolling(14, min_periods=14).mean()
        fast = c.ewm(span=self.fast, adjust=False, min_periods=self.fast).mean()
        slow = c.ewm(span=self.slow, adjust=False, min_periods=self.slow).mean()
        up = (fast > slow) & (slow.diff(5) > 0)
        down = (fast < slow) & (slow.diff(5) < 0)

        # Prior bar is a dip below the fast mean; current close confirms a turn.
        long = up & (c.shift(1) < fast.shift(1)-self.dip_atr*atr.shift(1)) & (c > h.shift(1))
        short = down & (c.shift(1) > fast.shift(1)+self.dip_atr*atr.shift(1)) & (c < l.shift(1))
        if not self.allow_rare_shorts:
            short[:] = False
        d = pd.Series(np.where(long, 1, np.where(short, -1, 0)), index=c.index)
        stop_long = l.rolling(5, min_periods=5).min()-0.15*atr
        stop_short = h.rolling(5, min_periods=5).max()+0.15*atr
        stop = pd.Series(np.where(d > 0, stop_long, stop_short), index=c.index)
        risk = (c-stop).abs()
        target = c+d*risk*self.target_r

        # Avoid the most explosive 5% of trailing volatility. The public account
        # does not disclose this filter; it is Serein's safety constraint.
        vol_rank = (atr/c).rolling(500, min_periods=100).rank(pct=True)
        safe = vol_rank.fillna(1.0) < .95
        sig = empty_signals(bars.index)
        sig["direction"] = d
        sig["confidence"] = np.where(d != 0, .60, 0.0)
        sig["expected_R"] = np.where(d != 0, self.target_r, 0.0)
        sig["horizon_bars"] = 12
        sig["regime_ok"] = safe
        sig["reason"] = np.where(d != 0, "public_behavior_safe_proxy", "no_setup")
        sig["stop_price"] = stop.where(d != 0)
        sig["target_price"] = target.where(d != 0)
        validate_signals(sig)
        return sig
