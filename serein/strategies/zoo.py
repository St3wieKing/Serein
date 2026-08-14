"""Strategy Zoo — the expanded strategy ecosystem.

Every family that can be built from OHLCV+volume data, implemented as
causal signal generators. Popularity is NOT evidence — every strategy
here is a candidate to be destroyed by the tournament harness.

Families covered:
  trend (MA variants, slope, ADX) · momentum (TSMOM ladders, dual,
  intraday) · mean reversion (z ladders, RSI2, Bollinger) · breakout
  (Donchian ladders, compression, new-high, opening-range) ·
  volatility (gap fade, expansion fade) · structure/candles (doji,
  engulfing) · cross-sectional relative strength · ML direction ·
  volume surge · random null.

Not covered (and why): order-flow/imbalance and tick microstructure
(need tick/level-2 data), options/IV strategies (need option data),
news sentiment (need timestamped news + event calendar). These are
roadmap items, not silently approximated.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .base import Strategy, empty_signals, validate_signals
from ..features import build_features


# --------------------------------------------------------------------------
# Indicator helpers (vectorized, causal)
# --------------------------------------------------------------------------
def _true_range(bars: pd.DataFrame) -> pd.Series:
    prev_close = bars["close"].shift(1)
    tr = pd.concat([
        bars["high"] - bars["low"],
        (bars["high"] - prev_close).abs(),
        (bars["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr


def _rsi(close: pd.Series, n: int = 2) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.rolling(n, min_periods=n).mean()
    avg_loss = loss.rolling(n, min_periods=n).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100.0 - 100.0 / (1.0 + rs)


def _adx(bars: pd.DataFrame, n: int = 14) -> pd.Series:
    up = bars["high"].diff()
    dn = -bars["low"].diff()
    plus_dm = pd.Series(np.where((up > dn) & (up > 0), up, 0.0), index=bars.index)
    minus_dm = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0), index=bars.index)
    atr = _true_range(bars).rolling(n, min_periods=n).mean()
    pdi = 100.0 * plus_dm.rolling(n, min_periods=n).mean() / atr.replace(0, np.nan)
    mdi = 100.0 * minus_dm.rolling(n, min_periods=n).mean() / atr.replace(0, np.nan)
    dx = 100.0 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    return dx.rolling(n, min_periods=n).mean()


def _macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    macd = close.ewm(span=fast, adjust=False).mean() - close.ewm(span=slow, adjust=False).mean()
    sig = macd.ewm(span=signal, adjust=False).mean()
    return macd, sig, macd - sig


def _bollinger(close: pd.Series, n: int = 20, k: float = 2.0):
    mid = close.rolling(n, min_periods=n).mean()
    std = close.rolling(n, min_periods=n).std()
    return mid, mid - k * std, mid + k * std


def _vol_gate(bars: pd.DataFrame, pct_thr: float = 0.90, n: int = 60) -> pd.Series:
    ret = bars["close"].pct_change()
    vol = ret.rolling(n, min_periods=n).std()
    rank = vol.rolling(500, min_periods=200).rank(pct=True)
    return rank.fillna(0.5) < pct_thr


def _slope_series(s: pd.Series, n: int = 60) -> pd.Series:
    """Rolling OLS slope of s vs time, normalized by |s| mean (vectorized)."""
    y = s.to_numpy()
    w = np.arange(n) - (n - 1) / 2.0
    w2 = float((w ** 2).sum())
    slope = np.full(len(y), np.nan)
    if len(y) >= n:
        # slope_t = sum_i w_i * y_{t-n+1+i} / sum w^2  (valid for the last n rows ending at t)
        conv = np.convolve(y, w[::-1], mode="valid")
        slope[n - 1:] = conv / w2
    out = pd.Series(slope, index=s.index)
    return out


# --------------------------------------------------------------------------
# TREND FAMILY
# --------------------------------------------------------------------------
class TrendSlopeStrategy(Strategy):
    """Rolling regression slope of log-price; sign = direction."""

    name = "trend_slope"

    def __init__(self, params=None):
        super().__init__(params)
        p = params or {}
        self.n = p.get("slope_n", 60)
        self.entry_slope = p.get("entry_slope", 0.0)

    def generate(self, bars, regime=None):
        close = bars["close"]
        slope = _slope_series(np.log(close), self.n)
        slope_pct = slope  # log-price slope ≈ relative slope
        atr = _true_range(bars).rolling(14).mean()
        norm = (slope_pct / (atr / close).replace(0, np.nan)).clip(-3, 3)
        sig = empty_signals(bars.index)
        sig["direction"] = np.where(norm > self.entry_slope, 1,
                                    np.where(norm < -self.entry_slope, -1, 0)).astype(int)
        sig["confidence"] = (np.tanh(norm.abs()) * 0.5 + 0.5).fillna(0.0).clip(0, 1)
        sig["expected_R"] = (norm.abs().clip(0.5, 2.5)).fillna(0.0)
        sig["horizon_bars"] = self.n
        sig["regime_ok"] = _vol_gate(bars)
        sig.loc[sig["direction"] == 0, "reason"] = "no_slope"
        sig.loc[sig["direction"] == 1, "reason"] = f"slope_{self.n}_up"
        sig.loc[sig["direction"] == -1, "reason"] = f"slope_{self.n}_down"
        validate_signals(sig)
        return sig


class ADXTrendStrategy(Strategy):
    """ADX-strength-filtered EMA trend: only trade when trend is strong."""

    name = "adx_trend"

    def __init__(self, params=None):
        super().__init__(params)
        p = params or {}
        self.adx_n = p.get("adx_n", 14)
        self.adx_thr = p.get("adx_thr", 20)
        self.fast = p.get("fast", 20)
        self.slow = p.get("slow", 60)

    def generate(self, bars, regime=None):
        close = bars["close"]
        adx = _adx(bars, self.adx_n)
        ma_f = close.rolling(self.fast, min_periods=self.fast).mean()
        ma_s = close.rolling(self.slow, min_periods=self.slow).mean()
        strong = adx.fillna(0) > self.adx_thr
        sig = empty_signals(bars.index)
        sig["direction"] = np.where(strong & (ma_f > ma_s), 1,
                                    np.where(strong & (ma_f < ma_s), -1, 0)).astype(int)
        sig["confidence"] = ((adx / 60.0).clip(0, 1) * 0.6 + 0.3).fillna(0.0)
        sig["expected_R"] = 1.2
        sig["horizon_bars"] = self.slow
        sig["regime_ok"] = _vol_gate(bars, 0.95)
        sig.loc[sig["direction"] == 0, "reason"] = "no_adx_trend"
        sig.loc[sig["direction"] == 1, "reason"] = "adx_trend_up"
        sig.loc[sig["direction"] == -1, "reason"] = "adx_trend_down"
        validate_signals(sig)
        return sig


# --------------------------------------------------------------------------
# MOMENTUM FAMILY
# --------------------------------------------------------------------------
class DualMomentumStrategy(Strategy):
    """TSMOM with fast+slow agreement (both must point the same way)."""

    name = "dual_momentum"

    def __init__(self, params=None):
        super().__init__(params)
        p = params or {}
        self.fast = p.get("fast", 60)
        self.slow = p.get("slow", 120)

    def generate(self, bars, regime=None):
        close = bars["close"]
        m_f = close.pct_change(self.fast)
        m_s = close.pct_change(self.slow)
        agree_up = (m_f > 0) & (m_s > 0)
        agree_dn = (m_f < 0) & (m_s < 0)
        vol = close.pct_change().rolling(60, min_periods=60).std()
        sig = empty_signals(bars.index)
        sig["direction"] = np.where(agree_up, 1, np.where(agree_dn, -1, 0)).astype(int)
        mag = ((m_f + m_s) / 2.0).abs() / vol.replace(0, np.nan)
        sig["confidence"] = (0.5 * (1 - np.exp(-mag.fillna(0))) + 0.3).clip(0, 1)
        sig["expected_R"] = (mag.clip(0.3, 2.5) * 0.7).fillna(0.0)
        sig["horizon_bars"] = self.slow // 2
        sig["regime_ok"] = vol.fillna(0) < vol.quantile(0.97)
        sig.loc[sig["direction"] == 0, "reason"] = "momentum_disagree"
        sig.loc[sig["direction"] == 1, "reason"] = f"dual_mom_{self.fast}_{self.slow}_up"
        sig.loc[sig["direction"] == -1, "reason"] = f"dual_mom_{self.fast}_{self.slow}_down"
        validate_signals(sig)
        return sig


class IntradayMomentumStrategy(Strategy):
    """Short-horizon continuation (1-3 bar) gated to trading hours."""

    name = "intraday_momentum"

    def __init__(self, params=None):
        super().__init__(params)
        p = params or {}
        self.h = p.get("h", 3)
        self.min_hour = p.get("min_hour", 8)
        self.max_hour = p.get("max_hour", 20)

    def generate(self, bars, regime=None):
        close = bars["close"]
        ret = close.pct_change(self.h)
        vol = close.pct_change().rolling(60, min_periods=60).std()
        z = ret / vol.replace(0, np.nan)
        hour = bars.index.hour
        in_session = (hour >= self.min_hour) & (hour <= self.max_hour)
        sig = empty_signals(bars.index)
        sig["direction"] = np.where(in_session & (z > 0.5), 1,
                                    np.where(in_session & (z < -0.5), -1, 0)).astype(int)
        sig["confidence"] = (np.tanh(z.abs() / 2.0) * 0.4 + 0.3).fillna(0.0)
        sig["expected_R"] = 0.8
        sig["horizon_bars"] = self.h * 4
        sig["regime_ok"] = _vol_gate(bars, 0.95)
        sig.loc[sig["direction"] == 0, "reason"] = "no_intraday_mom"
        sig.loc[sig["direction"] == 1, "reason"] = f"intraday_mom_{self.h}_up"
        sig.loc[sig["direction"] == -1, "reason"] = f"intraday_mom_{self.h}_down"
        validate_signals(sig)
        return sig


# --------------------------------------------------------------------------
# MEAN REVERSION FAMILY
# --------------------------------------------------------------------------
class RSI2ReversionStrategy(Strategy):
    """RSI(2) extremes (Connors-style): RSI<k -> long, RSI>100-k -> short."""

    name = "rsi2_reversion"

    def __init__(self, params=None):
        super().__init__(params)
        p = params or {}
        self.n = p.get("n", 2)
        self.thr = p.get("thr", 5.0)

    def generate(self, bars, regime=None):
        close = bars["close"]
        rsi = _rsi(close, self.n)
        sig = empty_signals(bars.index)
        sig["direction"] = np.where(rsi < self.thr, 1,
                                    np.where(rsi > 100 - self.thr, -1, 0)).astype(int)
        sig["confidence"] = ((50.0 - (rsi - 50).abs()) / 50.0).clip(0, 1).fillna(0.0)
        sig["expected_R"] = 1.5
        sig["horizon_bars"] = 48
        sig["regime_ok"] = _vol_gate(bars, 0.75)   # reversion needs calm vol
        sig.loc[sig["direction"] == 0, "reason"] = "rsi2_in_range"
        sig.loc[sig["direction"] == 1, "reason"] = "rsi2_oversold"
        sig.loc[sig["direction"] == -1, "reason"] = "rsi2_overbought"
        validate_signals(sig)
        return sig


class BollingerReversionStrategy(Strategy):
    """Fade closes beyond k-sigma Bollinger bands."""

    name = "bollinger_reversion"

    def __init__(self, params=None):
        super().__init__(params)
        p = params or {}
        self.n = p.get("n", 20)
        self.k = p.get("k", 2.0)

    def generate(self, bars, regime=None):
        close = bars["close"]
        mid, low, high = _bollinger(close, self.n, self.k)
        z = (close - mid) / (high - mid).replace(0, np.nan)  # -1..+1 approx
        sig = empty_signals(bars.index)
        sig["direction"] = np.where(close > high, -1, np.where(close < low, 1, 0)).astype(int)
        sig["confidence"] = (z.abs().clip(0, 1) * 0.5 + 0.35).fillna(0.0)
        sig["expected_R"] = 1.0
        sig["horizon_bars"] = self.n * 2
        sig["regime_ok"] = _vol_gate(bars, 0.8)
        sig.loc[sig["direction"] == 0, "reason"] = "inside_bands"
        sig.loc[sig["direction"] == 1, "reason"] = "bollinger_lower"
        sig.loc[sig["direction"] == -1, "reason"] = "bollinger_upper"
        validate_signals(sig)
        return sig


# --------------------------------------------------------------------------
# BREAKOUT FAMILY
# --------------------------------------------------------------------------
class DonchianBreakoutStrategy(Strategy):
    """Plain Donchian channel breakout (no compression filter)."""

    name = "donchian"

    def __init__(self, params=None):
        super().__init__(params)
        p = params or {}
        self.lookback = p.get("lookback", 55)

    def generate(self, bars, regime=None):
        hi = bars["high"].rolling(self.lookback, min_periods=self.lookback).max().shift(1)
        lo = bars["low"].rolling(self.lookback, min_periods=self.lookback).min().shift(1)
        close = bars["close"]
        atr = _true_range(bars).rolling(14).mean()
        width = ((hi - lo) / close.replace(0, np.nan)).fillna(0)
        sig = empty_signals(bars.index)
        up = (close > hi) & (width < 0.2)
        dn = (close < lo) & (width < 0.2)
        sig["direction"] = np.where(up, 1, np.where(dn, -1, 0)).astype(int)
        margin = pd.Series(
            np.where(up, (close - hi) / atr.replace(0, np.nan),
                     np.where(dn, (lo - close) / atr.replace(0, np.nan), 0.0)),
            index=bars.index)
        sig["confidence"] = (np.tanh(margin / 2.0) * 0.4 + 0.4).clip(0, 0.95).fillna(0.0)
        sig["expected_R"] = (1.0 + margin.clip(0, 2)).fillna(0.0)
        sig["horizon_bars"] = self.lookback // 2
        sig["regime_ok"] = _vol_gate(bars, 0.92)
        sig.loc[sig["direction"] == 0, "reason"] = "no_donchian_break"
        sig.loc[sig["direction"] == 1, "reason"] = f"donchian_{self.lookback}_up"
        sig.loc[sig["direction"] == -1, "reason"] = f"donchian_{self.lookback}_down"
        validate_signals(sig)
        return sig


class NewHighContinuationStrategy(Strategy):
    """Close at new rolling high -> long (new-high effect)."""

    name = "new_high"

    def __init__(self, params=None):
        super().__init__(params)
        p = params or {}
        self.lookback = p.get("lookback", 250)

    def generate(self, bars, regime=None):
        close = bars["close"]
        prev_max = close.rolling(self.lookback, min_periods=self.lookback).max().shift(1)
        prev_min = close.rolling(self.lookback, min_periods=self.lookback).min().shift(1)
        atr = _true_range(bars).rolling(14).mean()
        sig = empty_signals(bars.index)
        sig["direction"] = np.where(close > prev_max, 1,
                                    np.where(close < prev_min, -1, 0)).astype(int)
        margin = pd.Series(
            np.where(sig["direction"] > 0, (close - prev_max) / atr.replace(0, np.nan),
                     np.where(sig["direction"] < 0, (prev_min - close) / atr.replace(0, np.nan), 0.0)),
            index=bars.index)
        sig["confidence"] = (np.tanh(margin) * 0.35 + 0.45).clip(0, 0.9).fillna(0.0)
        sig["expected_R"] = (1.2 + margin.clip(0, 1.5)).fillna(0.0)
        sig["horizon_bars"] = self.lookback // 4
        sig["regime_ok"] = _vol_gate(bars, 0.93)
        sig.loc[sig["direction"] == 0, "reason"] = "not_new_extreme"
        sig.loc[sig["direction"] == 1, "reason"] = f"new_high_{self.lookback}"
        sig.loc[sig["direction"] == -1, "reason"] = f"new_low_{self.lookback}"
        validate_signals(sig)
        return sig


class OpeningRangeBreakoutStrategy(Strategy):
    """Intraday: break of the day's opening-range (first OR bars)."""

    name = "opening_range"

    def __init__(self, params=None):
        super().__init__(params)
        p = params or {}
        self.or_bars = p.get("or_bars", 2)
        self.min_vol = p.get("min_vol", 1.2)

    def generate(self, bars, regime=None):
        idx = bars.index
        df = pd.DataFrame({
            "day": idx.date,
            "close": bars["close"].to_numpy(),
            "high": bars["high"].to_numpy(),
            "low": bars["low"].to_numpy(),
            "volume": bars["volume"].to_numpy(),
        }, index=idx)
        grp = df.groupby("day")
        df["row"] = grp.cumcount()
        first = grp.head(self.or_bars)
        or_high = first.groupby("day")["high"].max()
        or_low = first.groupby("day")["low"].min()
        df["or_high"] = df["day"].map(or_high)
        df["or_low"] = df["day"].map(or_low)
        rv = df["volume"] / df["volume"].rolling(20, min_periods=20).mean().replace(0, np.nan)
        after = df["row"] >= self.or_bars
        up = after & (df["close"] > df["or_high"]) & (rv.fillna(0) > self.min_vol)
        dn = after & (df["close"] < df["or_low"]) & (rv.fillna(0) > self.min_vol)
        sig = empty_signals(idx)
        sig["direction"] = np.where(up, 1, np.where(dn, -1, 0)).astype(int)
        sig["confidence"] = np.where(sig["direction"] != 0, 0.58, 0.0)
        sig["expected_R"] = np.where(sig["direction"] != 0, 1.0, 0.0)
        sig["horizon_bars"] = 6
        sig["regime_ok"] = _vol_gate(bars, 0.95)
        sig.loc[sig["direction"] == 0, "reason"] = "no_or_break"
        sig.loc[sig["direction"] == 1, "reason"] = f"or_break_{self.or_bars}_up"
        sig.loc[sig["direction"] == -1, "reason"] = f"or_break_{self.or_bars}_down"
        validate_signals(sig)
        return sig


# --------------------------------------------------------------------------
# VOLATILITY FAMILY
# --------------------------------------------------------------------------
class GapFadeStrategy(Strategy):
    """Fade large open gaps (gap-and-fade hypothesis)."""

    name = "gap_fade"

    def __init__(self, params=None):
        super().__init__(params)
        p = params or {}
        self.k = p.get("k", 2.0)

    def generate(self, bars, regime=None):
        gap = (bars["open"] / bars["close"].shift(1) - 1.0).fillna(0.0)
        atr_pct = _true_range(bars).rolling(14).mean() / bars["close"].replace(0, np.nan)
        z = gap / atr_pct.replace(0, np.nan)
        sig = empty_signals(bars.index)
        sig["direction"] = np.where(z > self.k, -1, np.where(z < -self.k, 1, 0)).astype(int)
        sig["confidence"] = (np.tanh(z.abs() / self.k) * 0.4 + 0.35).clip(0, 0.85).fillna(0.0)
        sig["expected_R"] = 1.0
        sig["horizon_bars"] = 12
        sig["regime_ok"] = _vol_gate(bars, 0.9)
        sig.loc[sig["direction"] == 0, "reason"] = "no_big_gap"
        sig.loc[sig["direction"] == 1, "reason"] = "gap_fade_up"
        sig.loc[sig["direction"] == -1, "reason"] = "gap_fade_down"
        validate_signals(sig)
        return sig


class VolExpansionFadeStrategy(Strategy):
    """Fade extreme single-bar moves when volatility is already elevated."""

    name = "vol_expansion_fade"

    def __init__(self, params=None):
        super().__init__(params)
        p = params or {}
        self.k = p.get("k", 3.0)
        self.min_vol_pct = p.get("min_vol_pct", 0.6)

    def generate(self, bars, regime=None):
        close = bars["close"]
        ret = close.pct_change()
        vol = ret.rolling(60, min_periods=60).std()
        z = ret / vol.replace(0, np.nan)
        vol_rank = vol.rolling(500, min_periods=200).rank(pct=True)
        active = vol_rank.fillna(0.5) > self.min_vol_pct
        sig = empty_signals(bars.index)
        sig["direction"] = np.where(active & (z < -self.k), 1,
                                    np.where(active & (z > self.k), -1, 0)).astype(int)
        sig["confidence"] = (np.tanh(z.abs() / self.k) * 0.4 + 0.3).clip(0, 0.8).fillna(0.0)
        sig["expected_R"] = 1.2
        sig["horizon_bars"] = 24
        sig["regime_ok"] = True
        sig.loc[sig["direction"] == 0, "reason"] = "no_extreme_move"
        sig.loc[sig["direction"] == 1, "reason"] = "fade_crash"
        sig.loc[sig["direction"] == -1, "reason"] = "fade_spike"
        validate_signals(sig)
        return sig


class VolumeSurgeStrategy(Strategy):
    """Volume surge + direction -> continuation."""

    name = "volume_surge"

    def __init__(self, params=None):
        super().__init__(params)
        p = params or {}
        self.rv_thr = p.get("rv_thr", 2.0)

    def generate(self, bars, regime=None):
        close = bars["close"]
        v = bars["volume"]
        rv = v / v.rolling(20, min_periods=20).mean().replace(0, np.nan)
        ret = close.pct_change()
        sig = empty_signals(bars.index)
        surge_up = (rv > self.rv_thr) & (ret > 0.003)
        surge_dn = (rv > self.rv_thr) & (ret < -0.003)
        sig["direction"] = np.where(surge_up, 1, np.where(surge_dn, -1, 0)).astype(int)
        sig["confidence"] = (np.tanh((rv.fillna(1) - 1) / 2) * 0.3 + 0.45).clip(0, 0.9).fillna(0.0)
        sig["expected_R"] = 1.0
        sig["horizon_bars"] = 12
        sig["regime_ok"] = _vol_gate(bars, 0.95)
        sig.loc[sig["direction"] == 0, "reason"] = "no_surge"
        sig.loc[sig["direction"] == 1, "reason"] = "volume_surge_up"
        sig.loc[sig["direction"] == -1, "reason"] = "volume_surge_down"
        validate_signals(sig)
        return sig


# --------------------------------------------------------------------------
# CANDLE / STRUCTURE FAMILY
# --------------------------------------------------------------------------
class CandleDojiStrategy(Strategy):
    """Doji at trend extremes -> reversal (classic lore; likely weak)."""

    name = "candle_doji"

    def __init__(self, params=None):
        super().__init__(params)
        p = params or {}
        self.body_frac = p.get("body_frac", 0.1)
        self.trend_n = p.get("trend_n", 60)

    def generate(self, bars, regime=None):
        rng = (bars["high"] - bars["low"]).replace(0, np.nan)
        body = (bars["close"] - bars["open"]).abs()
        doji = body < self.body_frac * rng
        close = bars["close"]
        ma = close.rolling(self.trend_n, min_periods=self.trend_n).mean()
        up_trend = close > ma
        dn_trend = close < ma
        sig = empty_signals(bars.index)
        sig["direction"] = np.where(doji & up_trend, -1,
                                    np.where(doji & dn_trend, 1, 0)).astype(int)
        sig["confidence"] = np.where(sig["direction"] != 0, 0.52, 0.0)
        sig["expected_R"] = np.where(sig["direction"] != 0, 0.8, 0.0)
        sig["horizon_bars"] = 24
        sig["regime_ok"] = _vol_gate(bars, 0.9)
        sig.loc[sig["direction"] == 0, "reason"] = "no_doji_signal"
        sig.loc[sig["direction"] == 1, "reason"] = "doji_reversal_up"
        sig.loc[sig["direction"] == -1, "reason"] = "doji_reversal_down"
        validate_signals(sig)
        return sig


class CandleEngulfingStrategy(Strategy):
    """Bullish/bearish engulfing patterns."""

    name = "candle_engulfing"

    def __init__(self, params=None):
        super().__init__(params)
        p = params or {}
        self.min_vol = p.get("min_vol", 1.0)

    def generate(self, bars, regime=None):
        o, c, h, l = bars["open"], bars["close"], bars["high"], bars["low"]
        prev_body = (c.shift(1) - o.shift(1)).abs()
        body = (c - o).abs()
        bull_engulf = (c > o) & (c.shift(1) < o.shift(1)) & (body > prev_body) & \
                      (c >= o.shift(1)) & (o <= c.shift(1))
        bear_engulf = (c < o) & (c.shift(1) > o.shift(1)) & (body > prev_body) & \
                      (c <= o.shift(1)) & (o >= c.shift(1))
        v = bars["volume"]
        rv = v / v.rolling(20, min_periods=20).mean().replace(0, np.nan)
        sig = empty_signals(bars.index)
        sig["direction"] = np.where(bull_engulf & (rv.fillna(0) > self.min_vol), 1,
                                    np.where(bear_engulf & (rv.fillna(0) > self.min_vol), -1, 0)).astype(int)
        sig["confidence"] = np.where(sig["direction"] != 0, 0.55, 0.0)
        sig["expected_R"] = np.where(sig["direction"] != 0, 0.9, 0.0)
        sig["horizon_bars"] = 24
        sig["regime_ok"] = _vol_gate(bars, 0.92)
        sig.loc[sig["direction"] == 0, "reason"] = "no_engulfing"
        sig.loc[sig["direction"] == 1, "reason"] = "bull_engulfing"
        sig.loc[sig["direction"] == -1, "reason"] = "bear_engulfing"
        validate_signals(sig)
        return sig


# --------------------------------------------------------------------------
# CROSS-SECTIONAL & ML & NULL
# --------------------------------------------------------------------------
class RelativeStrengthStrategy(Strategy):
    """Cross-sectional relative momentum vs the universe (needs universe)."""

    name = "rel_strength"

    def __init__(self, params=None):
        super().__init__(params)
        p = params or {}
        self.lookback = p.get("lookback", 120)
        self.z_thr = p.get("z_thr", 0.75)

    def generate(self, bars, regime=None):
        # single-symbol fallback: no cross-section available -> flat
        return empty_signals(bars.index)

    def generate_universe(self, bars: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
        rets = {s: b["close"].pct_change(self.lookback) for s, b in bars.items()}
        stacked = pd.DataFrame(rets)
        cross_mean = stacked.mean(axis=1)
        cross_std = stacked.std(axis=1).replace(0, np.nan)
        out = {}
        for s in bars:
            z = (stacked[s] - cross_mean) / cross_std
            sig = empty_signals(bars[s].index)
            sig["direction"] = np.where(z > self.z_thr, 1,
                                        np.where(z < -self.z_thr, -1, 0)).astype(int)
            sig["confidence"] = (np.tanh(z.abs() / 2.0) * 0.4 + 0.35).clip(0, 0.9).fillna(0.0)
            sig["expected_R"] = 1.0
            sig["horizon_bars"] = self.lookback // 2
            sig["regime_ok"] = True
            sig.loc[sig["direction"] == 0, "reason"] = "rs_neutral"
            sig.loc[sig["direction"] == 1, "reason"] = f"rs_{self.lookback}_strong"
            sig.loc[sig["direction"] == -1, "reason"] = f"rs_{self.lookback}_weak"
            validate_signals(sig)
            out[s] = sig
        return out


class MLDirectionStrategy(Strategy):
    """Trained classifier direction: train on first `train_frac`, signal after.

    Honest by construction: signals before the training cutoff are zero,
    so the backtest only ever sees out-of-sample predictions.
    """

    name = "ml_direction"

    def __init__(self, params=None):
        super().__init__(params)
        p = params or {}
        self.family = p.get("family", "logistic")
        self.train_frac = p.get("train_frac", 0.5)
        self.horizon = p.get("horizon", 6)
        self.buy_thr = p.get("buy_thr", 0.55)
        self.sell_thr = p.get("sell_thr", 0.45)

    def _fit_predict(self, bars: pd.DataFrame) -> pd.DataFrame:
        from ..ml.models import ModelFactory, build_ml_dataset
        from ..features import make_labels
        feats = build_features(bars, horizons=(1, 6, 24))
        labels = make_labels(bars, horizon=self.horizon, mode="binary")["label"]
        X, y, _ = build_ml_dataset(feats, labels, audit=True)
        cutoff = int(len(X) * self.train_frac)
        rec = ModelFactory(data_version="zoo").build(
            self.family, list(X.columns), str(X.index[0]), str(X.index[cutoff]))
        est = ModelFactory(data_version="zoo").instantiate(rec)
        est.fit(X.iloc[:cutoff], y.iloc[:cutoff])
        p = est.predict_proba(X.iloc[cutoff:])[:, 1]
        sig = empty_signals(bars.index)
        idx = X.index[cutoff:]
        sig.loc[idx, "direction"] = np.where(p > self.buy_thr, 1,
                                             np.where(p < self.sell_thr, -1, 0))
        sig.loc[idx, "confidence"] = np.abs(p - 0.5) * 2.0
        sig.loc[idx, "expected_R"] = 1.0
        sig.loc[idx, "horizon_bars"] = self.horizon * 4
        sig.loc[idx, "regime_ok"] = True
        sig.loc[idx, "reason"] = np.where(sig.loc[idx, "direction"] > 0,
                                          f"ml_{self.family}_buy",
                                          np.where(sig.loc[idx, "direction"] < 0,
                                                   f"ml_{self.family}_sell", "ml_flat"))
        validate_signals(sig)
        return sig

    def generate(self, bars, regime=None):
        return self._fit_predict(bars)


class RandomBaselineStrategy(Strategy):
    """Seeded random entries every k bars — the null hypothesis."""

    name = "random_null"

    def __init__(self, params=None):
        super().__init__(params)
        p = params or {}
        self.every = p.get("every", 24)
        self.seed = p.get("seed", 42)

    def generate(self, bars, regime=None):
        rng = np.random.default_rng(self.seed)
        n = len(bars)
        sig = empty_signals(bars.index)
        idxs = np.arange(0, n, self.every)
        dirs = rng.choice([-1, 1], size=len(idxs))
        sig.iloc[idxs, sig.columns.get_loc("direction")] = dirs
        sig.iloc[idxs, sig.columns.get_loc("confidence")] = 0.55
        sig.iloc[idxs, sig.columns.get_loc("expected_R")] = 1.0
        sig.iloc[idxs, sig.columns.get_loc("horizon_bars")] = 24
        sig.iloc[idxs, sig.columns.get_loc("reason")] = "random_null"
        validate_signals(sig)
        return sig
