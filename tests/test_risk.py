"""Risk engine + sizing tests: limits, kill switches, no-martingale property."""

import numpy as np
import pandas as pd
import pytest

from serein.config import RiskLimits, SizingParams, BacktestConfig
from serein.risk.engine import RiskEngine
from serein.risk.sizing import size_position
from serein import constants as C


def make_risk(**overrides):
    lim = RiskLimits(**overrides)
    return RiskEngine(lim, SizingParams())


def test_kill_switch_blocks_new_trades():
    r = make_risk()
    assert r.new_trades_allowed()
    r.trip(C.KS_DATA, "stale feed")
    assert not r.new_trades_allowed()
    assert C.KS_DATA in r.tripped_switches()


def test_daily_loss_limit_halts():
    r = make_risk(daily_loss_limit_pct=2.0)
    t = pd.Timestamp("2024-01-02 10:00")
    r.on_bar(t=t, equity=100_000, day_start_equity=100_000, peak_equity=100_000,
             positions={}, consecutive_losses=0)
    assert r.new_trades_allowed()
    r.on_bar(t=t + pd.Timedelta("1h"), equity=97_500, day_start_equity=100_000,
             peak_equity=100_000, positions={}, consecutive_losses=0)
    assert not r.new_trades_allowed()
    assert r._daily_loss_halted


def _dummy_pos(qty=100, price=100.0):
    return type("P", (), {"qty": qty, "entry_price": price})()


def test_drawdown_kill_switch_and_force_exit():
    r = make_risk(max_portfolio_drawdown_pct=10.0)
    t = pd.Timestamp("2024-01-02 10:00")
    positions = {"X": _dummy_pos()}
    r.on_bar(t, equity=100_000, day_start_equity=100_000, peak_equity=100_000,
             positions=positions, consecutive_losses=0)
    r.on_bar(t + pd.Timedelta("1h"), equity=88_000, day_start_equity=100_000,
             peak_equity=100_000, positions=positions, consecutive_losses=0)
    assert C.KS_DRAWDOWN in r.tripped_switches()
    assert r.force_exit


def test_consecutive_losses_trip():
    r = make_risk(max_consecutive_losses=3)
    t = pd.Timestamp("2024-01-02 10:00")
    r.on_bar(t, 100_000, 100_000, 100_000, {}, 3)
    assert not r.new_trades_allowed()


def test_volatility_kill():
    r = make_risk()
    t = pd.Timestamp("2024-01-02 10:00")
    r.on_bar(t, 100_000, 100_000, 100_000, {"X": _dummy_pos()}, 0, realized_vol=1.5)
    assert C.KS_VOLATILITY in r.tripped_switches()
    assert r.force_exit


def test_vol_scaling_reduces_size_in_high_vol():
    r = make_risk()
    t = pd.Timestamp("2024-01-02 10:00")
    r.on_bar(t, 100_000, 100_000, 100_000, {}, 0, realized_vol=0.60)
    assert r.vol_frac < 0.6


def test_check_entry_rejects_bad_orders():
    r = make_risk()
    ok, msg = r.check_entry("X", 1, -5, 100.0, 99.0, 100_000, {})
    assert not ok
    ok, msg = r.check_entry("X", 1, 10, 100.0, 101.0, 100_000, {})  # long stop above
    assert not ok
    ok, msg = r.check_entry("X", -1, 10, 100.0, 99.0, 100_000, {})  # short stop below
    assert not ok


def test_check_entry_enforces_caps():
    r = make_risk(max_per_symbol_frac=0.1)
    # 15% of equity in one symbol must be rejected
    ok, msg = r.check_entry("X", 1, 150, 100.0, 99.0, 100_000, {})
    assert not ok
    ok, msg = r.check_entry("X", 1, 50, 100.0, 99.0, 100_000, {})
    assert ok


def test_check_entry_position_conflict():
    r = make_risk()
    positions = {"X": _dummy_pos()}  # already have something in X
    ok, msg = r.check_entry("X", 1, 10, 100.0, 99.0, 100_000, positions)
    assert not ok


def test_max_positions():
    r = make_risk(max_positions=2)
    positions = {"A": _dummy_pos(), "B": _dummy_pos()}
    ok, msg = r.check_entry("C", 1, 10, 100.0, 99.0, 100_000, positions)
    assert not ok


def test_gross_exposure_cap():
    r = make_risk(max_gross_exposure_frac=1.0, max_per_symbol_frac=1.0,
                  max_net_exposure_frac=1.0)
    positions = {"A": _dummy_pos(qty=500, price=100.0)}  # 50k
    ok, msg = r.check_entry("B", 1, 600, 100.0, 99.0, 100_000, positions)  # +60k = 110k
    assert not ok
    ok, msg = r.check_entry("B", 1, 400, 100.0, 99.0, 100_000, positions)  # 90k
    assert ok


def test_size_position_risk_budget():
    sp = SizingParams(risk_per_trade_pct=1.0)
    qty = size_position(equity=100_000, entry=100.0, stop_distance=1.0,
                        confidence=0.8, expected_R=1.5, params=sp,
                        drawdown_frac=0.0, vol_frac=1.0)
    # risk = qty * 1.0 <= 1000 (1% of equity), confidence multiplier <= 1.5
    assert 0 < qty <= 1500


def test_size_position_confidence_floor():
    sp = SizingParams(confidence_floor=0.6)
    qty = size_position(equity=100_000, entry=100.0, stop_distance=1.0,
                        confidence=0.5, expected_R=1.5, params=sp)
    assert qty == 0


def test_size_position_drawdown_scaling():
    # relax the notional cap so the risk budget (not the cap) binds
    sp = SizingParams(drawdown_scale_on=True, max_notional_frac=1.0)
    q1 = size_position(equity=100_000, entry=100.0, stop_distance=1.0,
                       confidence=0.9, expected_R=1.5, params=sp, drawdown_frac=0.0)
    q2 = size_position(equity=100_000, entry=100.0, stop_distance=1.0,
                       confidence=0.9, expected_R=1.5, params=sp, drawdown_frac=0.5)
    assert q2 < q1
    q3 = size_position(equity=100_000, entry=100.0, stop_distance=1.0,
                       confidence=0.9, expected_R=1.5, params=sp, drawdown_frac=1.0)
    assert q3 == 0


def test_no_martingale_property():
    """Position size must NOT depend on recent wins/losses (no input for it)."""
    sp = SizingParams()
    kwargs = dict(equity=100_000, entry=100.0, stop_distance=1.0,
                  confidence=0.8, expected_R=1.5, params=sp,
                  drawdown_frac=0.0, vol_frac=1.0)
    qty_after_loss = size_position(**kwargs)
    qty_after_win = size_position(**kwargs)
    assert qty_after_loss == qty_after_win  # deterministic: no pnl input exists


def test_size_position_liquidity_cap():
    sp = SizingParams(max_adv_share=0.01)
    qty = size_position(equity=100_000, entry=100.0, stop_distance=1.0,
                        confidence=0.9, expected_R=1.5, params=sp,
                        bar_adv=50_000.0)  # cap: 1% of 50k = 500 notional = 5 shares
    assert qty <= 5


def test_emergency_floor():
    r = make_risk(emergency_equity_floor_frac=0.5)
    t = pd.Timestamp("2024-01-02 10:00")
    r.on_bar(t, 100_000, 100_000, 100_000, {}, 0)
    r.on_bar(t + pd.Timedelta("1h"), 40_000, 100_000, 100_000, {}, 0)
    assert not r.new_trades_allowed()
