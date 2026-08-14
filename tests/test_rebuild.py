"""Tests for the deliberately small Strategy v2 candidate set."""
import pandas as pd
import pytest

from serein.config import BacktestConfig
from serein.data.synthetic import generate_ohclv
from serein.backtest.engine import Backtester
from serein.strategies.base import validate_signals
from serein.strategies.rebuild import (
    COMPONENTS, CompressionBreakoutV2Strategy, FailedBreakoutStrategy,
    TrendPullbackStrategy, VWAPReversionV2Strategy, simplicity_score,
)

CANDIDATES = [TrendPullbackStrategy, CompressionBreakoutV2Strategy,
              FailedBreakoutStrategy, VWAPReversionV2Strategy]


@pytest.fixture(scope="module")
def bars():
    return generate_ohclv(2400, seed=31)[0]


@pytest.mark.parametrize("cls", CANDIDATES)
def test_rebuild_schema_and_structural_levels(bars, cls):
    sig = cls().generate(bars)
    validate_signals(sig)
    assert {"stop_price", "target_price"}.issubset(sig.columns)
    active = sig.direction != 0
    assert sig.loc[active, "stop_price"].notna().all()
    assert sig.loc[active, "target_price"].notna().all()
    long = sig.direction > 0
    short = sig.direction < 0
    assert (sig.loc[long, "stop_price"] < bars.loc[long, "close"]).all()
    assert (sig.loc[short, "stop_price"] > bars.loc[short, "close"]).all()


@pytest.mark.parametrize("cls", CANDIDATES)
def test_rebuild_is_causal(bars, cls):
    strat = cls()
    full = strat.generate(bars)
    t = bars.index[1800]
    prefix = strat.generate(bars.loc[:t])
    for col in ("direction", "confidence", "expected_R", "stop_price", "target_price"):
        a, b = full.loc[t, col], prefix.loc[t, col]
        if pd.isna(a) and pd.isna(b):
            continue
        assert a == pytest.approx(b)


def test_simplicity_penalizes_extra_filters():
    core = TrendPullbackStrategy({"use_trend": False, "use_volatility": False,
                                  "use_volume": False})
    full = TrendPullbackStrategy({"use_trend": True, "use_volatility": True,
                                  "use_volume": True})
    assert core.simplicity > full.simplicity
    assert set(core.components).issubset(COMPONENTS)
    assert 0 <= simplicity_score(full.components) <= 100


def test_backtester_uses_structural_stops(bars):
    strat = TrendPullbackStrategy({"use_volatility": False})
    sig = strat.generate(bars)
    result = Backtester(BacktestConfig()).run({"X": bars}, {"X": sig})
    # Any executed stop must originate in the decision-time structural series,
    # allowing for exact value matching across potentially repeated prices.
    if len(result.trades):
        planned = set(sig.stop_price.dropna().round(8))
        assert set(result.trades.stop.round(8)).issubset(planned)
