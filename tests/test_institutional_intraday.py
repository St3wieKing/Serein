import pandas as pd
import pytest

from serein.backtest.engine import Backtester
from serein.config import BacktestConfig, RiskLimits, SizingParams
from serein.data.intraday_synthetic import generate_intraday_universe
from serein.strategies.base import validate_signals
from serein.strategies.institutional_intraday import (
    InstitutionalIntradayStrategy, IntradayMetaLabelStrategy,
)


@pytest.fixture(scope="module")
def universe():
    return generate_intraday_universe(["SPY", "QQQ", "IWM"], days=90, seed=91)[0]


def test_session_generator_shape_and_hours(universe):
    for b in universe.values():
        assert len(b) == 90*78
        assert set(b.index.hour).issubset(set(range(9, 17)))
        assert b.index[0].strftime("%H:%M") == "09:30"
        assert b.index[77].strftime("%H:%M") == "15:55"
        assert b.attrs["synthetic"] is True


def test_intraday_strategy_schema_levels_and_flat(universe):
    sigs = InstitutionalIntradayStrategy().generate_universe(universe)
    for s, sig in sigs.items():
        validate_signals(sig)
        active = sig.direction != 0
        long = sig.direction > 0; short = sig.direction < 0
        assert (sig.loc[long, "stop_price"] < universe[s].loc[long, "close"]).all()
        assert (sig.loc[short, "stop_price"] > universe[s].loc[short, "close"]).all()
        assert sig.loc[sig.index.strftime("%H:%M") == "15:55", "force_flat"].all()
        assert not sig.loc[sig.index.strftime("%H:%M") == "09:30", "direction"].any()


def test_intraday_strategy_is_causal(universe):
    b = universe["SPY"]
    strat = InstitutionalIntradayStrategy()
    full = strat.generate(b)
    t = b.index[5000]
    prefix = strat.generate(b.loc[:t])
    for c in ("direction", "confidence", "expected_R", "stop_price", "target_price"):
        a, z = full.loc[t, c], prefix.loc[t, c]
        if pd.isna(a) and pd.isna(z):
            continue
        assert a == pytest.approx(z)


def test_meta_model_is_oos_only_and_deterministic(universe):
    split = universe["SPY"].index[60*78]
    p = {"train_end": split, "family": "logistic", "threshold": .50}
    a = IntradayMetaLabelStrategy(p); sa = a.generate_universe(universe)
    b = IntradayMetaLabelStrategy(p); sb = b.generate_universe(universe)
    assert a.diagnostics == b.diagnostics
    for sym in universe:
        assert (sa[sym].loc[sa[sym].index < split, "direction"] == 0).all()
        pd.testing.assert_frame_equal(sa[sym], sb[sym])


def test_backtester_never_holds_overnight(universe):
    cfg = BacktestConfig(freq="5min", max_holding_bars=24,
                         sizing=SizingParams(risk_per_trade_pct=.25),
                         risk=RiskLimits(max_positions=3, max_daily_trades=6,
                                         daily_loss_limit_pct=.75,
                                         weekly_loss_limit_pct=2.0,
                                         max_portfolio_drawdown_pct=6.0))
    sig = InstitutionalIntradayStrategy().generate_universe(universe)
    r = Backtester(cfg).run(universe, sig)
    if len(r.trades):
        assert (r.trades.entry_time.dt.normalize() == r.trades.exit_time.dt.normalize()).all()
        assert (r.trades.exit_time.dt.strftime("%H:%M") <= "15:55").all()
