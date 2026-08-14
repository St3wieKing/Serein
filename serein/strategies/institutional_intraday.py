"""Institutional-inspired intraday research strategy.

No claim is made that this is Citadel's strategy. Citadel's exact signals,
datasets, execution stack, and portfolio construction are proprietary and
UNKNOWN. Publicly defensible principles are translated here instead:

* economically grounded, diverse signals rather than indicator confluence;
* regime-specific setup selection;
* cross-sectional market confirmation;
* volatility/liquidity-aware risk;
* next-bar execution, structural invalidation, and no overnight exposure;
* machine learning only as a setup-quality meta-label, never as risk authority.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .base import Strategy, empty_signals, validate_signals
from .zoo import _true_range

META_FEATURES = [
    "f_trend", "f_vwap_z", "f_relvol", "f_vol_rank", "f_breadth",
    "f_market_3", "f_market_12", "f_atr_pct", "f_time_sin", "f_time_cos",
    "f_orb", "f_pullback", "f_reversion",
]


def _minute_of_session(index: pd.DatetimeIndex) -> pd.Series:
    return pd.Series((index.hour*60 + index.minute) - (9*60+30), index=index)


def _session_vwap(b: pd.DataFrame) -> pd.Series:
    day = pd.Series(b.index.normalize(), index=b.index)
    typical = (b.high+b.low+b.close)/3
    return (typical*b.volume).groupby(day).cumsum()/b.volume.groupby(day).cumsum().replace(0, np.nan)


def _same_slot_volume_baseline(volume: pd.Series, slot: pd.Series, days: int = 20) -> pd.Series:
    frame = pd.DataFrame({"v": volume, "slot": slot.to_numpy()}, index=volume.index)
    return frame.groupby("slot")["v"].transform(
        lambda s: s.shift(1).rolling(days, min_periods=5).median()
    )


class InstitutionalIntradayStrategy(Strategy):
    """Regime-routing state machine: OR breakout, trend pullback, range reversion."""
    name = "institutional_intraday_v1"

    def __init__(self, params=None):
        super().__init__(params)
        p = params or {}
        self.fast = int(p.get("fast", 20))
        self.slow = int(p.get("slow", 60))
        self.or_bars = int(p.get("or_bars", 6))
        self.relvol_min = float(p.get("relvol_min", 1.15))
        self.reversion_z = float(p.get("reversion_z", 1.5))
        self.target_r_breakout = float(p.get("target_r_breakout", 2.0))
        self.target_r_pullback = float(p.get("target_r_pullback", 1.8))
        self.target_r_reversion = float(p.get("target_r_reversion", 1.2))

    def generate(self, bars, regime=None):
        # Single-symbol fallback has neutral breadth. Universe generation is
        # preferred because market confirmation is part of the hypothesis.
        return self.generate_universe({"S": bars})["S"]

    def generate_universe(self, bars: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
        symbols = list(bars)
        idx = bars[symbols[0]].index
        ema20 = pd.DataFrame({s: bars[s].close.ewm(span=20, adjust=False,
                                                   min_periods=20).mean() for s in symbols})
        closes = pd.DataFrame({s: bars[s].close for s in symbols})
        breadth = (closes > ema20).mean(axis=1)
        market = closes.pct_change().mean(axis=1)
        market_3 = market.rolling(3).sum()
        market_12 = market.rolling(12).sum()
        return {s: self._one(bars[s], breadth, market_3, market_12) for s in symbols}

    def _one(self, b: pd.DataFrame, breadth: pd.Series,
             market_3: pd.Series, market_12: pd.Series) -> pd.DataFrame:
        c, h, l = b.close, b.high, b.low
        slot = _minute_of_session(b.index)
        day = pd.Series(b.index.normalize(), index=b.index)
        fast = c.ewm(span=self.fast, adjust=False, min_periods=self.fast).mean()
        slow = c.ewm(span=self.slow, adjust=False, min_periods=self.slow).mean()
        atr = _true_range(b).rolling(14, min_periods=14).mean()
        vwap = _session_vwap(b)
        trend = (fast-slow)/atr.replace(0, np.nan)
        z = (c-vwap)/atr.replace(0, np.nan)
        atr_pct = atr/c
        vol_rank = atr_pct.rolling(1500, min_periods=300).rank(pct=True).fillna(.5)
        baseline = _same_slot_volume_baseline(b.volume, slot)
        relvol = (b.volume/baseline.replace(0, np.nan)).clip(0, 10).fillna(0)

        first = slot.between(0, (self.or_bars-1)*5)
        or_hi_raw = h.where(first).groupby(day).transform("max")
        or_lo_raw = l.where(first).groupby(day).transform("min")
        # Levels become tradable only after the opening range is complete.
        or_hi = or_hi_raw.where(slot >= self.or_bars*5)
        or_lo = or_lo_raw.where(slot >= self.or_bars*5)

        active = slot.between(30, 330)  # 10:00 through 15:00
        liquid = relvol >= self.relvol_min
        sane_vol = vol_rank.between(.10, .92)
        up = (trend > .35) & (c > vwap) & (breadth > .55) & (market_12 > 0)
        dn = (trend < -.35) & (c < vwap) & (breadth < .45) & (market_12 < 0)

        orb_long = active & liquid & sane_vol & up & (c > or_hi) & (c.shift(1) <= or_hi.shift(1))
        orb_short = active & liquid & sane_vol & dn & (c < or_lo) & (c.shift(1) >= or_lo.shift(1))

        pb_long = (active & sane_vol & up & (l.shift(1) <= vwap.shift(1)+.15*atr.shift(1))
                   & (c.shift(1) >= slow.shift(1)) & (c > h.shift(1)))
        pb_short = (active & sane_vol & dn & (h.shift(1) >= vwap.shift(1)-.15*atr.shift(1))
                    & (c.shift(1) <= slow.shift(1)) & (c < l.shift(1)))

        range_regime = trend.abs() < .30
        rv_long = (active & sane_vol & range_regime & (z.shift(1) < -self.reversion_z)
                   & (c > c.shift(1)) & (market_3 >= -.0015))
        rv_short = (active & sane_vol & range_regime & (z.shift(1) > self.reversion_z)
                    & (c < c.shift(1)) & (market_3 <= .0015))

        setup = pd.Series("", index=b.index, dtype=object)
        d = pd.Series(0, index=b.index, dtype=int)
        d[rv_long] = 1; d[rv_short] = -1; setup[d != 0] = "vwap_reversion"
        d[pb_long] = 1; d[pb_short] = -1; setup[pb_long | pb_short] = "vwap_pullback"
        d[orb_long] = 1; d[orb_short] = -1; setup[orb_long | orb_short] = "opening_breakout"

        swing_lo = l.rolling(6, min_periods=6).min()-.10*atr
        swing_hi = h.rolling(6, min_periods=6).max()+.10*atr
        stop = pd.Series(np.where(d > 0, swing_lo, swing_hi), index=b.index)
        risk = (c-stop).abs()
        rr = pd.Series(np.where(setup == "opening_breakout", self.target_r_breakout,
                       np.where(setup == "vwap_pullback", self.target_r_pullback,
                                self.target_r_reversion)), index=b.index)
        target = c+d*risk*rr

        # Reversion targets must be achievable before VWAP; cap the fixed-R
        # aspiration at VWAP and reject if reward is less than 0.8R.
        rev = setup == "vwap_reversion"
        target.loc[rev & (d > 0)] = np.minimum(target[rev & (d > 0)], vwap[rev & (d > 0)])
        target.loc[rev & (d < 0)] = np.maximum(target[rev & (d < 0)], vwap[rev & (d < 0)])
        actual_r = ((target-c).abs()/risk.replace(0, np.nan)).fillna(0)
        invalid = (d != 0) & ((risk/c < .001) | (actual_r < .8) | ~np.isfinite(stop))
        d[invalid] = 0; setup[invalid] = ""

        quality = (.54 + .06*trend.abs().clip(0, 2) + .04*(relvol-1).clip(0, 2)
                   + .04*(breadth-.5).abs()*2).clip(.54, .82)
        sig = empty_signals(b.index)
        sig["direction"] = d
        sig["confidence"] = quality.where(d != 0, 0.0)
        sig["expected_R"] = actual_r.where(d != 0, 0.0).clip(0, 3)
        sig["horizon_bars"] = 12
        sig["regime_ok"] = sane_vol & active
        sig["reason"] = setup.where(d != 0, "no_setup")
        sig["stop_price"] = stop.where(d != 0)
        sig["target_price"] = target.where(d != 0)
        sig["force_flat"] = slot >= 385  # 15:55 bar; never hold overnight
        sig["f_trend"] = trend
        sig["f_vwap_z"] = z
        sig["f_relvol"] = relvol
        sig["f_vol_rank"] = vol_rank
        sig["f_breadth"] = breadth
        sig["f_market_3"] = market_3
        sig["f_market_12"] = market_12
        sig["f_atr_pct"] = atr_pct
        angle = 2*np.pi*slot.clip(0, 390)/390
        sig["f_time_sin"] = np.sin(angle); sig["f_time_cos"] = np.cos(angle)
        sig["f_orb"] = (setup == "opening_breakout").astype(float)
        sig["f_pullback"] = (setup == "vwap_pullback").astype(float)
        sig["f_reversion"] = (setup == "vwap_reversion").astype(float)
        validate_signals(sig)
        return sig


class IntradayMetaLabelStrategy(Strategy):
    """Chronologically trained setup-quality filter over deterministic signals."""
    name = "institutional_intraday_meta"

    def __init__(self, params=None):
        super().__init__(params)
        p = params or {}
        if "train_end" not in p:
            raise ValueError("train_end must be predeclared")
        self.train_end = pd.Timestamp(p["train_end"])
        self.family = p.get("family", "logistic")
        self.threshold = float(p.get("threshold", .55))
        self.horizon = int(p.get("horizon", 12))
        self.base_params = p.get("base_params", {})
        self.diagnostics: dict = {}

    def generate(self, bars, regime=None):
        return self.generate_universe({"S": bars})["S"]

    def generate_universe(self, bars: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
        base = InstitutionalIntradayStrategy(self.base_params).generate_universe(bars)
        X, y = [], []
        for sym, sig in base.items():
            b = bars[sym]
            candidates = np.flatnonzero((sig.direction.to_numpy() != 0)
                                        & (sig.index.to_numpy() < np.datetime64(self.train_end)))
            last = -self.horizon
            for i in candidates:
                if i-last < self.horizon or i+self.horizon >= len(b) or sig.index[i+self.horizon] >= self.train_end:
                    continue
                row = sig.iloc[i]
                vals = row[META_FEATURES].astype(float).to_numpy()
                if not np.isfinite(vals).all():
                    continue
                X.append(vals); y.append(self._label(b, row, i)); last = i
        X = pd.DataFrame(np.asarray(X, float), columns=META_FEATURES)
        y = np.asarray(y, int)
        out = {s: frame.copy() for s, frame in base.items()}
        valid_model = len(y) >= 40 and len(np.unique(y)) == 2 and min(np.bincount(y)) >= 10
        self.diagnostics = {"n_train": int(len(y)), "base_rate": float(y.mean()) if len(y) else None,
                            "family": self.family, "valid_model": bool(valid_model)}
        if not valid_model:
            for sig in out.values():
                sig.loc[:, "direction"] = 0; sig.loc[:, "confidence"] = 0.0
                sig.loc[:, "reason"] = "meta_insufficient_training"
            return out
        if self.family == "logistic":
            model = make_pipeline(StandardScaler(), LogisticRegression(
                C=.5, max_iter=5000, class_weight="balanced", random_state=42))
        elif self.family == "gradient_boosting":
            model = GradientBoostingClassifier(n_estimators=80, max_depth=2,
                                                learning_rate=.04, min_samples_leaf=15,
                                                random_state=42)
        else:
            raise ValueError(f"unsupported family: {self.family}")
        model.fit(X, y)
        for sym, sig in out.items():
            eligible = (sig.index >= self.train_end) & (sig.direction != 0)
            feats = sig.loc[eligible, META_FEATURES].astype(float)
            finite = np.isfinite(feats).all(axis=1)
            prob = pd.Series(np.nan, index=feats.index)
            if finite.any():
                prob.loc[finite] = model.predict_proba(feats.loc[finite])[:, 1]
            reject_idx = prob.index[(prob < self.threshold) | prob.isna()]
            sig.loc[sig.index < self.train_end, "direction"] = 0
            sig.loc[sig.index < self.train_end, "confidence"] = 0.0
            sig.loc[reject_idx, "direction"] = 0
            sig.loc[reject_idx, "confidence"] = 0.0
            keep = eligible & (sig.direction != 0)
            sig.loc[keep, "confidence"] = prob.reindex(sig.index[keep]).clip(.52, .85).to_numpy()
            sig.loc[keep, "reason"] = sig.loc[keep, "reason"] + "+meta_" + self.family
            sig.loc[(sig.direction == 0) & (sig.index >= self.train_end), "reason"] = "meta_reject"
            validate_signals(sig)
        return out

    def _label(self, b: pd.DataFrame, row: pd.Series, i: int) -> int:
        d = int(row.direction); stop = float(row.stop_price); target = float(row.target_price)
        future = b.iloc[i+1:i+1+self.horizon]
        for r in future.itertuples():
            stop_hit = r.low <= stop if d > 0 else r.high >= stop
            target_hit = r.high >= target if d > 0 else r.low <= target
            if stop_hit:  # conservative same-bar ordering
                return 0
            if target_hit:
                return 1
        return int(d*(float(future.close.iloc[-1])-float(b.close.iloc[i])) > 0)
