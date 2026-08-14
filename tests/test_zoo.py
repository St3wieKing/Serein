"""Strategy zoo tests: causality, schema, determinism."""

import numpy as np
import pandas as pd
import pytest

from serein.data.synthetic import generate_ohclv
from serein.regimes import RegimeEngine
from serein.strategies.base import validate_signals
from serein.strategies.zoo import (
    TrendSlopeStrategy, ADXTrendStrategy, DualMomentumStrategy,
    IntradayMomentumStrategy, RSI2ReversionStrategy, BollingerReversionStrategy,
    DonchianBreakoutStrategy, NewHighContinuationStrategy,
    OpeningRangeBreakoutStrategy, GapFadeStrategy, VolExpansionFadeStrategy,
    VolumeSurgeStrategy, CandleDojiStrategy, CandleEngulfingStrategy,
    RelativeStrengthStrategy, MLDirectionStrategy, RandomBaselineStrategy,
)

ALL = [
    TrendSlopeStrategy, ADXTrendStrategy, DualMomentumStrategy,
    IntradayMomentumStrategy, RSI2ReversionStrategy, BollingerReversionStrategy,
    DonchianBreakoutStrategy, NewHighContinuationStrategy,
    OpeningRangeBreakoutStrategy, GapFadeStrategy, VolExpansionFadeStrategy,
    VolumeSurgeStrategy, CandleDojiStrategy, CandleEngulfingStrategy,
    RandomBaselineStrategy,
]


@pytest.fixture(scope="module")
def ctx():
    bars, _ = generate_ohclv(2000, seed=7)
    reg = RegimeEngine().classify_series(bars)
    return bars, reg


@pytest.mark.parametrize("cls", ALL, ids=lambda c: c.__name__)
def test_zoo_strategy_schema(ctx, cls):
    bars, reg = ctx
    sig = cls().generate(bars, reg)
    assert len(sig) == len(bars)
    validate_signals(sig)
    assert sig["direction"].isin([-1, 0, 1]).all()


@pytest.mark.parametrize("cls", ALL, ids=lambda c: c.__name__)
def test_zoo_strategy_causal(ctx, cls):
    """Signal at t must be identical when computed on truncated data."""
    bars, reg = ctx
    strat = cls()
    full = strat.generate(bars, reg)
    t = bars.index[1200]
    prefix = strat.generate(bars.loc[:t], reg)
    for col in ("direction", "confidence", "expected_R"):
        assert full.loc[t, col] == pytest.approx(prefix.loc[t, col], nan_ok=True)


def test_zoo_deterministic():
    bars, _ = generate_ohclv(500, seed=3)
    reg = RegimeEngine().classify_series(bars)
    a = RandomBaselineStrategy({"seed": 5}).generate(bars, reg)
    b = RandomBaselineStrategy({"seed": 5}).generate(bars, reg)
    pd.testing.assert_frame_equal(a, b)


def test_rel_strength_universe():
    bars, _ = generate_ohclv(800, seed=11)
    bars2 = bars * 1.5  # strongly trending second symbol
    rs = RelativeStrengthStrategy().generate_universe({"A": bars, "B": bars2})
    assert set(rs) == {"A", "B"}
    for s in rs:
        validate_signals(rs[s])


def test_ml_direction_oos_only():
    bars, _ = generate_ohclv(1200, seed=13)
    reg = RegimeEngine().classify_series(bars)
    sig = MLDirectionStrategy({"family": "logistic", "train_frac": 0.5}).generate(bars, reg)
    cutoff = bars.index[600]
    # no signals before the training cutoff (no in-sample leakage)
    assert (sig.loc[:cutoff, "direction"] == 0).all()
    assert (sig.loc[cutoff:, "direction"] != 0).any()


def test_opening_range_respects_days():
    bars, _ = generate_ohclv(2000, seed=17)
    reg = RegimeEngine().classify_series(bars)
    sig = OpeningRangeBreakoutStrategy({"or_bars": 2}).generate(bars, reg)
    # signals must never fire within the first 2 bars of a day
    df = pd.DataFrame({"day": bars.index.date, "row": range(len(bars))})
    df["row_in_day"] = df.groupby("day").cumcount()
    active = sig["direction"] != 0
    assert (df.loc[active.to_numpy(), "row_in_day"] >= 2).all()
