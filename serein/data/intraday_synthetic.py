"""Session-aware synthetic intraday universe for engineering validation.

This is deliberately NOT real market data. It supplies exchange-like 5-minute
sessions, overnight gaps, a shared market factor, idiosyncratic returns,
U-shaped volume, and labeled trend/range/shock days. Planted effects allow the
research harness to verify that an intraday state machine can detect known
mechanisms without treating synthetic success as evidence of alpha.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

DAY_REGIMES = ("trend_up", "trend_down", "range", "shock")


def generate_intraday_universe(symbols: list[str], days: int = 300,
                               seed: int = 2026, start: str = "2024-01-02",
                               bars_per_day: int = 78) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    if bars_per_day != 78:
        raise ValueError("only 78-bar US-style 5-minute sessions are supported")
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(start, periods=days)
    intraday = pd.timedelta_range("9h30min", periods=bars_per_day, freq="5min")
    idx = pd.DatetimeIndex([d + dt for d in dates for dt in intraday])

    # Persistent daily regimes make adaptation testable but not trivial.
    regimes = []
    current = "range"
    for _ in dates:
        if rng.random() < .16:
            current = rng.choice(DAY_REGIMES, p=[.30, .25, .38, .07])
        regimes.append(current)
    regime_by_bar = np.repeat(regimes, bars_per_day)

    market_r = np.zeros(len(idx))
    market_gap = np.zeros(days)
    for di, reg in enumerate(regimes):
        sl = slice(di*bars_per_day, (di+1)*bars_per_day)
        sigma = {"trend_up": .00065, "trend_down": .00070,
                 "range": .00045, "shock": .0018}[reg]
        drift = {"trend_up": .00011, "trend_down": -.00011,
                 "range": 0.0, "shock": rng.choice([-.00025, .00025])}[reg]
        gap = rng.normal(drift*5, sigma*2)
        market_gap[di] = gap
        e = rng.normal(0, sigma, bars_per_day)
        r = np.zeros(bars_per_day)
        for j in range(bars_per_day):
            # Trend persistence; range days have short-term reversal.
            phi = .22 if "trend" in reg else (-.30 if reg == "range" else .08)
            r[j] = drift + e[j] + (phi*r[j-1] if j else .18*gap)
        market_r[sl] = r

    out: dict[str, pd.DataFrame] = {}
    for si, sym in enumerate(symbols):
        srng = np.random.default_rng(seed + 100 + si)
        beta = .75 + .12*si
        idio = srng.normal(0, .00035 + .00005*si, len(idx))
        ret = beta*market_r + idio
        close = np.empty(len(idx)); open_ = np.empty(len(idx))
        prev = 100.0 + 25*si
        for di in range(days):
            a = di*bars_per_day; b = a+bars_per_day
            open_[a] = prev*np.exp(beta*market_gap[di] + srng.normal(0, .0003))
            close[a] = open_[a]*np.exp(ret[a])
            for j in range(a+1, b):
                open_[j] = close[j-1]
                close[j] = open_[j]*np.exp(ret[j])
            prev = close[b-1]
        spread = np.abs(srng.normal(.00018, .00008, len(idx)))
        high = np.maximum(open_, close)*(1+spread)
        low = np.minimum(open_, close)*(1-spread)
        minute = np.tile(np.arange(bars_per_day), days)
        u_shape = 1.0 + 1.7*((minute-(bars_per_day-1)/2)/((bars_per_day-1)/2))**2
        regime_mult = np.where(np.array(regime_by_bar) == "shock", 2.5, 1.0)
        volume = 700_000*u_shape*regime_mult*np.exp(srng.normal(0, .28, len(idx)))
        frame = pd.DataFrame({"open": open_, "high": high, "low": low,
                              "close": close, "volume": volume}, index=idx)
        frame.attrs.update(symbol=sym, synthetic=True, session_aware=True, seed=seed)
        out[sym] = frame

    truth = pd.DataFrame({"day_regime": regime_by_bar,
                          "market_return": market_r}, index=idx)
    return out, truth
