"""Volatility-adjusted trend-following (MA structure).

Hypothesis (to be tested, not assumed): a slow MA structure on log prices,
gated by a volatility-percentile filter, captures persistent trends while
avoiding chop. This is the classic trend family (MOP 2012 time-series
momentum lineage: past trend predicts continuation over multi-week horizons;
the *critique* literature shows the edge is weaker than claimed and regime
dependent — hence the vol gate and the mandatory OOS testing).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .base import Strategy, empty_signals, validate_signals


class TrendStrategy(Strategy):
    name = "trend"

    def __init__(self, params=None):
        super().__init__(params)
        p = params or {}
        self.fast = p.get("trend_fast", 20)
        self.slow = p.get("trend_slow", 60)
        self.atr_mult = p.get("trend_atr_mult", 2.0)
        self.vol_n = p.get("trend_vol_filter_n", 60)
        self.vol_pct = p.get("trend_vol_filter_pct", 0.90)

    def generate(self, bars: pd.DataFrame, regime: pd.DataFrame | None = None) -> pd.DataFrame:
        close = bars["close"]
        ma_fast = close.rolling(self.fast, min_periods=self.fast).mean()
        ma_slow = close.rolling(self.slow, min_periods=self.slow).mean()
        slope = ma_fast - ma_slow

        # volatility gate: refuse when realized vol is in the top decile
        ret = close.pct_change()
        vol = ret.rolling(self.vol_n, min_periods=self.vol_n).std()
        vol_rank = vol.rolling(500, min_periods=200).rank(pct=True)
        vol_ok = vol_rank.fillna(0.5) < self.vol_pct

        sig = empty_signals(bars.index)
        sig["direction"] = np.sign(slope).fillna(0).astype(int)
        # confidence scales with |slope| relative to its own trailing dispersion
        slope_abs = slope.abs()
        slope_rank = slope_abs.rolling(500, min_periods=200).rank(pct=True)
        sig["confidence"] = (0.5 + 0.5 * slope_rank.fillna(0.0)).clip(0, 1)
        # expected R: trend strength in ATR units, capped
        atr = (bars["high"] - bars["low"]).rolling(14).mean()
        trend_r = (slope.abs() / atr.replace(0, np.nan)).clip(0, 3)
        sig["expected_R"] = (trend_r.fillna(0.0) * 1.0).clip(0, 3)
        sig["horizon_bars"] = self.slow
        sig["regime_ok"] = vol_ok.fillna(True)
        sig.loc[sig["regime_ok"] == False, "confidence"] *= 0.5  # noqa: E712
        sig.loc[sig["direction"] == 0, "reason"] = "no_trend"
        sig.loc[sig["direction"] == 1, "reason"] = "ma_structure_up"
        sig.loc[sig["direction"] == -1, "reason"] = "ma_structure_down"
        validate_signals(sig)
        return sig


class MomentumStrategy(Strategy):
    """Time-series momentum (TSMOM-style): sign of past `lookback` return,
    vol-scaled. Direct lineage: Moskowitz, Ooi & Pedersen (2012, JFE)."""

    name = "momentum"

    def __init__(self, params=None):
        super().__init__(params)
        p = params or {}
        self.lookback = p.get("momentum_lookback", 120)
        self.vol_n = p.get("momentum_vol_scale_n", 60)

    def generate(self, bars: pd.DataFrame, regime: pd.DataFrame | None = None) -> pd.DataFrame:
        close = bars["close"]
        past = close.pct_change(self.lookback)
        vol = close.pct_change().rolling(self.vol_n, min_periods=self.vol_n).std()
        vol_target = close.pct_change().rolling(500, min_periods=200).std().quantile(0.5)

        sig = empty_signals(bars.index)
        sig["direction"] = np.sign(past).fillna(0).astype(int)
        # confidence: magnitude of the lookback return relative to vol
        r = (past.abs() / vol.replace(0, np.nan)).fillna(0.0)
        sig["confidence"] = (0.5 * (1 - np.exp(-r))).clip(0, 1) + 0.25
        sig["confidence"] = sig["confidence"].clip(0, 1)
        sig["expected_R"] = (r.clip(0, 3) * 0.8).clip(0, 3)
        sig["horizon_bars"] = int(self.lookback * 0.25)
        sig["regime_ok"] = vol.fillna(0) < (vol_target * 3)  # skip extreme vol
        sig.loc[sig["direction"] == 0, "reason"] = "no_momentum"
        sig.loc[sig["direction"] == 1, "reason"] = f"tsmom_{self.lookback}_up"
        sig.loc[sig["direction"] == -1, "reason"] = f"tsmom_{self.lookback}_down"
        validate_signals(sig)
        return sig


class MeanReversionStrategy(Strategy):
    """Z-score mean reversion with a calm-vol gate.

    Hypothesis: in low/stable volatility regimes, price deviations beyond k
    sigma from the trailing mean revert. The vol gate is essential — reversion
    strategies get destroyed in trending/high-vol regimes."""

    name = "mean_reversion"

    def __init__(self, params=None):
        super().__init__(params)
        p = params or {}
        self.z_n = p.get("reversion_z_n", 60)
        self.z_entry = p.get("reversion_z_entry", 2.0)
        self.z_exit = p.get("reversion_z_exit", 0.0)
        self.atr_pct = p.get("reversion_atr_filter_pct", 0.75)

    def generate(self, bars: pd.DataFrame, regime: pd.DataFrame | None = None) -> pd.DataFrame:
        close = bars["close"]
        mean = close.rolling(self.z_n, min_periods=self.z_n).mean()
        std = close.rolling(self.z_n, min_periods=self.z_n).std()
        z = (close - mean) / std.replace(0, np.nan)

        atr = (bars["high"] - bars["low"]).rolling(14).mean()
        atr_rank = atr.rolling(500, min_periods=200).rank(pct=True)
        calm = atr_rank.fillna(0.5) < self.atr_pct

        sig = empty_signals(bars.index)
        sig["direction"] = np.where(z > self.z_entry, -1, np.where(z < -self.z_entry, 1, 0)).astype(int)
        # confidence grows with |z| beyond entry
        conf = ((z.abs() - self.z_entry) / 1.5).clip(0, 1) * 0.75 + 0.25
        sig["confidence"] = conf.clip(0, 1).fillna(0.0)
        sig["expected_R"] = 1.2  # reversion targets are modest by design
        sig["horizon_bars"] = self.z_n // 2
        sig["regime_ok"] = calm.fillna(True)
        sig.loc[sig["regime_ok"] == False, "confidence"] *= 0.25  # noqa: E712
        sig.loc[sig["direction"] == 0, "reason"] = "no_deviation"
        sig.loc[sig["direction"] == 1, "reason"] = "z_oversold"
        sig.loc[sig["direction"] == -1, "reason"] = "z_overbought"
        validate_signals(sig)
        return sig


class BreakoutStrategy(Strategy):
    """Volatility-compression breakout (Donchian channel).

    Hypothesis: after a period of compression (ATR percentile low), a close
    beyond the trailing range with volume confirmation begins a continuation
    move. Compression breakouts are a staple of the breakout literature;
    their main failure mode is false breakouts in chop, so the signal also
    requires a minimum channel width and volume confirmation."""

    name = "breakout"

    def __init__(self, params=None):
        super().__init__(params)
        p = params or {}
        self.lookback = p.get("breakout_lookback", 120)
        self.comp_n = p.get("breakout_vol_compression_n", 40)
        self.comp_pct = p.get("breakout_compression_pct", 0.6)

    def generate(self, bars: pd.DataFrame, regime: pd.DataFrame | None = None) -> pd.DataFrame:
        hi = bars["high"].rolling(self.lookback, min_periods=self.lookback).max().shift(1)
        lo = bars["low"].rolling(self.lookback, min_periods=self.lookback).min().shift(1)
        atr = (bars["high"] - bars["low"]).rolling(14).mean()
        atr_rank = atr.rolling(500, min_periods=200).rank(pct=True)
        compressed = atr_rank.fillna(0.5) < self.comp_pct
        width_ok = ((hi - lo) / bars["close"]).fillna(0) < 0.15  # sane channel width

        rv = bars["volume"] / bars["volume"].rolling(20, min_periods=20).mean().replace(0, np.nan)
        vol_confirm = rv.fillna(1.0) > 1.2

        sig = empty_signals(bars.index)
        up = (bars["close"] > hi) & compressed & vol_confirm & width_ok
        dn = (bars["close"] < lo) & compressed & vol_confirm & width_ok
        sig["direction"] = np.where(up, 1, np.where(dn, -1, 0)).astype(int)
        sig["confidence"] = np.where(
            sig["direction"] != 0,
            (0.5 + 0.5 * (rv.fillna(1.0) - 1.0).clip(0, 1) * 0.5).clip(0.5, 0.9),
            0.0,
        )
        sig["expected_R"] = np.where(
            sig["direction"] != 0, (1.5 + atr_rank.fillna(0.5) * 1.0).clip(1.2, 2.5), 0.0
        )
        sig["horizon_bars"] = 24
        sig["regime_ok"] = compressed.fillna(True)
        sig.loc[sig["direction"] == 0, "reason"] = "no_breakout"
        sig.loc[sig["direction"] == 1, "reason"] = "compression_breakout_up"
        sig.loc[sig["direction"] == -1, "reason"] = "compression_breakout_down"
        validate_signals(sig)
        return sig
