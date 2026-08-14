"""Strategy interface and signal contract.

Every strategy engine emits a SIGNALS frame (one row per bar) with a strict
schema. The Meta-Decision Engine consumes ONLY this schema — never raw
indicators — which keeps the alpha layer and the decision layer decoupled.

Schema:
  direction     int   -1 / 0 / +1
  confidence    float 0..1   (calibrated-ish confidence, NOT certainty)
  expected_R    float       expected reward in units of planned risk
  horizon_bars  int         expected holding period in bars
  regime_ok     bool        strategy's own regime gate
  reason        str         short human-readable reason (for the journal)

Optional execution fields:
  stop_price    float       objective thesis invalidation known at decision time
  target_price  float       realistic objective known at decision time
If absent, the backtester uses the locked ATR stop and R-multiple target.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np
import pandas as pd

SIGNAL_COLUMNS = ["direction", "confidence", "expected_R", "horizon_bars", "regime_ok", "reason"]


def empty_signals(index: pd.DatetimeIndex) -> pd.DataFrame:
    df = pd.DataFrame(
        {
            "direction": 0,
            "confidence": 0.0,
            "expected_R": 0.0,
            "horizon_bars": 0,
            "regime_ok": True,
            "reason": "",
        },
        index=index,
    )
    return df


def validate_signals(df: pd.DataFrame) -> None:
    missing = [c for c in SIGNAL_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"signal frame missing columns: {missing}")
    if df["direction"].isin([-1, 0, 1]).all() is False:
        raise ValueError("direction must be in {-1, 0, 1}")
    if ((df["confidence"] < 0) | (df["confidence"] > 1)).any():
        raise ValueError("confidence must be in [0, 1]")


class Strategy(ABC):
    """Base class. Strategies are stateless signal generators: same input
    bars -> same output signals. All statefulness lives in the backtester."""

    name: str = "base"

    def __init__(self, params=None):
        self.params = params

    @abstractmethod
    def generate(self, bars: pd.DataFrame, regime: pd.DataFrame | None = None) -> pd.DataFrame:
        """Return a validated signals frame indexed like bars."""

    def __repr__(self) -> str:
        return f"<Strategy {self.name}>"
