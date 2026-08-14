"""Market Regime Engine.

Version 0 is deliberately simple and transparent:
  * volatility regime via rolling realized-vol percentile
  * trend regime via normalized MA-slope sign and strength
  * uncertainty flag when change-point detection (CUSUM) fires
  * transition flag when regime identity changes

The module is written so a challenger (e.g. HMM / GARCH-state model) can be
dropped in behind the same RegimeSnapshot interface and tested head-to-head.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

REGIME_STRONG_BULL = "strong_bullish_trend"
REGIME_WEAK_BULL = "weak_bullish_trend"
REGIME_STRONG_BEAR = "strong_bearish_trend"
REGIME_WEAK_BEAR = "weak_bearish_trend"
REGIME_SIDEWAYS = "sideways"
REGIME_HIGH_VOL = "high_volatility"
REGIME_LOW_VOL = "low_volatility"
REGIME_VOL_EXPANSION = "volatility_expansion"
REGIME_VOL_COMPRESSION = "volatility_compression"
REGIME_UNCERTAIN = "uncertain"
REGIME_TRANSITION = "transition"


@dataclass
class RegimeSnapshot:
    regime: str
    trend_score: float            # -1 (strong bear) .. +1 (strong bull)
    vol_score: float              # 0 (calm) .. 1 (extreme)
    vol_percentile: float
    change_point: bool
    transition: bool
    features: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "regime": self.regime,
            "trend_score": round(self.trend_score, 4),
            "vol_score": round(self.vol_score, 4),
            "vol_percentile": round(self.vol_percentile, 4),
            "change_point": self.change_point,
            "transition": self.transition,
        }


def _cusum_changepoint(s: pd.Series, threshold: float = 4.0, min_run: int = 40) -> pd.Series:
    """CUSUM-style change-point flag on a series (returns boolean Series)."""
    if s.isna().all():
        return pd.Series(False, index=s.index)
    z = (s - s.rolling(min_run, min_periods=min_run).mean()).fillna(0.0)
    std = s.rolling(min_run, min_periods=min_run).std().replace(0, np.nan)
    z = z / std.fillna(1.0)
    cusum_pos = np.maximum.accumulate(z.fillna(0.0))
    cusum_neg = -np.minimum.accumulate(z.fillna(0.0))
    flag = (cusum_pos > threshold) | (cusum_neg > threshold)
    return flag


class RegimeEngine:
    """Rule-based regime classifier with CUSUM change-point detection."""

    def __init__(
        self,
        vol_window: int = 60,
        vol_pct_window: int = 500,
        trend_fast: int = 20,
        trend_slow: int = 120,
        cusum_threshold: float = 4.0,
    ):
        self.vol_window = vol_window
        self.vol_pct_window = vol_pct_window
        self.trend_fast = trend_fast
        self.trend_slow = trend_slow
        self.cusum_threshold = cusum_threshold

    def classify_series(self, bars: pd.DataFrame) -> pd.DataFrame:
        """Return per-bar RegimeSnapshot-as-dict frame."""
        close = bars["close"]
        ret = close.pct_change()
        vol = ret.rolling(self.vol_window, min_periods=self.vol_window).std()
        vol_pct = vol.rolling(self.vol_pct_window, min_periods=200).rank(pct=True)

        ma_fast = close.rolling(self.trend_fast, min_periods=self.trend_fast).mean()
        ma_slow = close.rolling(self.trend_slow, min_periods=self.trend_slow).mean()
        slope = (ma_fast - ma_slow) / ma_slow.replace(0, np.nan)
        # normalize slope to [-1, 1] via tanh
        trend_score = np.tanh(slope / 0.005)

        cp = _cusum_changepoint(ret, self.cusum_threshold)

        out = pd.DataFrame(index=bars.index)
        out["trend_score"] = trend_score
        out["vol_percentile"] = vol_pct
        out["vol_score"] = vol_pct.clip(0, 1)
        out["change_point"] = cp
        out["regime_raw"] = "uncertain"

        reg = out["regime_raw"].astype(object)
        vp = out["vol_percentile"].fillna(0.5)
        ts = out["trend_score"].fillna(0.0)

        # volatility dimension first (it vetoes)
        high_vol = vp > 0.85
        low_vol = vp < 0.15
        # trend dimension
        strong_bull = ts > 0.6
        weak_bull = (ts > 0.15) & (ts <= 0.6)
        strong_bear = ts < -0.6
        weak_bear = (ts <= -0.15) & (ts >= -0.6)
        flat = (ts.abs() <= 0.15)

        reg[high_vol] = REGIME_HIGH_VOL
        reg[~high_vol & low_vol & flat] = REGIME_LOW_VOL
        reg[~high_vol & ~low_vol & strong_bull] = REGIME_STRONG_BULL
        reg[~high_vol & ~low_vol & weak_bull] = REGIME_WEAK_BULL
        reg[~high_vol & ~low_vol & strong_bear] = REGIME_STRONG_BEAR
        reg[~high_vol & ~low_vol & weak_bear] = REGIME_WEAK_BEAR
        reg[~high_vol & ~low_vol & flat] = REGIME_SIDEWAYS

        # vol expansion/compression overlays
        vol_ratio = vol / vol.shift(self.vol_window).replace(0, np.nan)
        reg[(reg == REGIME_HIGH_VOL) & (vol_ratio > 1.5)] = REGIME_VOL_EXPANSION
        reg[(reg == REGIME_LOW_VOL) & (vol_ratio < 0.7)] = REGIME_VOL_COMPRESSION

        # transitions: regime changed vs previous non-NaN row
        prev = reg.shift(1)
        transition = (reg != prev) & prev.notna()
        reg[transition] = REGIME_TRANSITION

        out["regime"] = reg
        out["transition"] = transition
        return out

    def snapshot(self, bars: pd.DataFrame, t: pd.Timestamp) -> RegimeSnapshot:
        s = self.classify_series(bars.loc[:t])
        row = s.iloc[-1]
        return RegimeSnapshot(
            regime=row["regime"],
            trend_score=float(row["trend_score"]),
            vol_score=float(row["vol_score"]),
            vol_percentile=float(row["vol_percentile"]),
            change_point=bool(row["change_point"]),
            transition=bool(row["transition"]),
            features={"regime_raw": row["regime_raw"]},
        )
