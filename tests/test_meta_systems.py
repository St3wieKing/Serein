"""Meta engine, walk-forward, PBO, calibration, drift, execution tests."""

import numpy as np
import pandas as pd
import pytest

from serein.meta import MetaEngine
from serein.strategies.base import empty_signals
from serein.backtest.walkforward import walk_forward_splits, purged_kfold
from serein.backtest.robustness import cscv_pbo, ablation, stability_summary, perturb_params
from serein.ml.calibration import (expected_calibration_error, brier_score,
                                   reliability_curve)
from serein.drift import psi, feature_drift_report, cusum_drift
from serein.execution.broker import PaperBroker, Order
from serein.execution.validation import OrderValidator
from serein.config import RiskLimits, SizingParams, BacktestConfig
from serein.data.synthetic import generate_ohclv


def test_meta_agreement_gives_direction():
    idx = pd.date_range("2024-01-01", periods=10, freq="h")
    sigs = {}
    for name in ("a", "b"):
        s = empty_signals(idx)
        s["direction"] = 1
        s["confidence"] = 0.8
        s["expected_R"] = 1.5
        sigs[name] = s
    out = MetaEngine().combine(sigs)
    assert (out["direction"] == 1).all()
    assert (out["confidence"] > 0.7).all()


def test_meta_disagreement_yields_no_trade():
    idx = pd.date_range("2024-01-01", periods=10, freq="h")
    a = empty_signals(idx)
    a["direction"] = 1
    a["confidence"] = 0.9
    a["expected_R"] = 1.5
    b = empty_signals(idx)
    b["direction"] = -1
    b["confidence"] = 0.9
    b["expected_R"] = 1.5
    out = MetaEngine().combine({"a": a, "b": b})
    assert (out["direction"] == 0).all()


def test_meta_regime_veto():
    idx = pd.date_range("2024-01-01", periods=10, freq="h")
    a = empty_signals(idx)
    a["direction"] = 1
    a["confidence"] = 0.9
    a["expected_R"] = 1.5
    reg = pd.DataFrame({"regime": ["uncertain"] * 5 + ["sideways"] * 5}, index=idx)
    out = MetaEngine().combine({"a": a}, reg)
    # uncertain bars: vetoed (regime_ok False -> excluded from vote -> no trade)
    assert out["direction"].iloc[:5].eq(0).all()
    assert out["direction"].iloc[5:].eq(1).all()


def test_meta_low_edge_no_trade():
    idx = pd.date_range("2024-01-01", periods=10, freq="h")
    a = empty_signals(idx)
    a["direction"] = 1
    a["confidence"] = 0.9
    a["expected_R"] = 0.1
    out = MetaEngine(min_expected_r=0.6).combine({"a": a})
    assert (out["direction"] == 0).all()


def test_walk_forward_splits_chronological():
    splits = walk_forward_splits(10_000, n_splits=4, embargo=24, min_train=1000)
    for tr, te in splits:
        assert tr.max() <= te.min() - 24
        assert len(te) > 10
    # test windows must not overlap
    tes = [te for _, te in splits]
    for i in range(len(tes) - 1):
        assert tes[i].max() < tes[i + 1].min()


def test_purged_kfold_no_overlap():
    splits = purged_kfold(5000, n_splits=5, embargo=20)
    for tr, te in splits:
        overlap = set(tr) & set(te)
        assert len(overlap) == 0
        # embargo respected: no train point within 20 of test edges
        assert not ((tr >= te.min() - 20) & (tr < te.max() + 20)).any()


def test_cscv_pbo_noise_is_high():
    """Selection among pure noise must show PBO near 0.5 (no real selection)."""
    rng = np.random.default_rng(0)
    M = pd.DataFrame(rng.normal(size=(20, 8)))
    result = cscv_pbo(M, n_partitions=8, max_trials=500, seed=1)
    assert 0.3 < result.pbo < 0.8


def test_cscv_pbo_structure_is_low():
    """A config that is best everywhere must show low PBO."""
    rng = np.random.default_rng(1)
    base = rng.normal(size=(15, 8))
    M = pd.DataFrame(base)
    M.iloc[0] += 3.0  # config 0 dominates every subperiod
    result = cscv_pbo(M, n_partitions=8, max_trials=500, seed=1)
    assert result.pbo < 0.25


def test_ablation_delta():
    def fit_eval(features):
        return {"oos_auc": 0.55 if len(features) >= 3 else 0.51}

    df = ablation([("one", ["a"]), ("two", ["a", "b"])], fit_eval,
                  ["a", "b", "c"], metric="oos_auc")
    assert df.loc[df["variant"] == "ALL", "oos_auc"].iloc[0] == 0.55
    assert df.loc[df["variant"] == "-one", "delta"].iloc[0] == pytest.approx(-0.04)


def test_stability_summary():
    df = pd.DataFrame([{"metrics": {"sharpe": 1.0}},
                       {"metrics": {"sharpe": -0.5}},
                       {"metrics": {"sharpe": 2.0}}])
    s = stability_summary(df)
    assert s["median"] == pytest.approx(1.0)
    assert s["frac_positive"] == pytest.approx(2 / 3)


def test_perturb_params():
    out = perturb_params({"fast": 20, "slow": 60}, frac=0.1, n=10, seed=3)
    assert len(out) == 10
    for p in out:
        assert 0.8 * 20 <= p["fast"] <= 1.2 * 20


def test_calibration_ece_perfect():
    y = np.array([0, 1] * 500)
    p = y.astype(float) * 0.9 + (1 - y.astype(float)) * 0.1
    # binning discretization puts 0.1/0.9 predictions at bin edges; a
    # calibrated predictor must stay well below an uncalibrated one
    ece = expected_calibration_error(y, p, bins=10)
    assert ece < 0.15
    assert 0 <= brier_score(y, p) <= 0.25


def test_calibration_ece_miscalibrated():
    y = np.array([0, 1] * 500)
    p = np.full(1000, 0.7)  # predicts 70% for everything
    ece = expected_calibration_error(y, p, bins=10)
    assert ece > 0.15


def test_reliability_curve_shape():
    y = np.array([0, 1] * 100)
    p = np.linspace(0, 1, len(y))
    rc = reliability_curve(y, p, bins=5)
    assert len(rc) == 5
    assert (rc["n"] > 0).all()


def test_psi_same_distribution_low():
    rng = np.random.default_rng(2)
    a = rng.normal(size=1000)
    b = rng.normal(size=1000)
    assert psi(a, b) < 0.1


def test_psi_different_distribution_high():
    rng = np.random.default_rng(3)
    a = rng.normal(size=1000)
    b = rng.normal(size=1000) + 2.0
    assert psi(a, b) > 1.0


def test_feature_drift_report_flags_shift():
    rng = np.random.default_rng(4)
    train = pd.DataFrame({"x": rng.normal(size=500)})
    live = pd.DataFrame({"x": rng.normal(size=500) + 3.0})
    df = feature_drift_report(train, live, alert_threshold=0.25)
    assert bool(df.loc[df["feature"] == "x", "alert"].iloc[0])


def test_cusum_drift_detects_shift():
    s = pd.Series(np.concatenate([np.zeros(100), np.ones(100) * 0.5]))
    flags = cusum_drift(s, threshold=3.0, min_n=30)
    assert flags.any()


def test_paper_broker_fill_and_costs():
    bars, _ = generate_ohclv(500, seed=21)
    cfg = BacktestConfig()
    pb = PaperBroker({"S": bars}, cfg, seed=1)
    pb.set_clock(bars.index[50])
    o = Order(order_id="", symbol="S", side="buy", qty=100)
    filled = pb.submit_order(o)
    assert filled.status == "FILLED"
    assert filled.fill_price is not None
    assert filled.realized_slippage_bps > 0
    assert pb.get_positions() == {"S": 100}


def test_paper_broker_failure_injection():
    bars, _ = generate_ohclv(500, seed=22)
    pb = PaperBroker({"S": bars}, BacktestConfig(), seed=2)
    pb.set_clock(bars.index[50])
    pb.inject_failure(healthy=False)
    o = Order(order_id="", symbol="S", side="buy", qty=10)
    assert pb.submit_order(o).status == "REJECTED"


def test_paper_broker_partial_fill():
    bars, _ = generate_ohclv(500, seed=23)
    pb = PaperBroker({"S": bars}, BacktestConfig(), seed=3)
    pb.set_clock(bars.index[50])
    pb.set_fill_ratio(0.5)
    o = Order(order_id="", symbol="S", side="buy", qty=100)
    filled = pb.submit_order(o)
    assert filled.status == "PARTIAL"
    assert pb.get_positions() == {"S": 50}


def test_order_validator_full_gate():
    v = OrderValidator(RiskLimits(), SizingParams())
    res = v.validate(
        symbol="SPY", direction=1, qty=10, price=500.0, quote=None,
        positions={}, open_orders=[], equity=100_000, data_fresh=True,
        market_open=True, broker_healthy=True, model_approved=True,
        daily_loss_halted=False, risk_new_trades_allowed=True,
    )
    assert res.ok
    assert res.summary().startswith("PASS")


def test_order_validator_rejects_failures():
    v = OrderValidator(RiskLimits(), SizingParams())
    res = v.validate(
        symbol="SPY", direction=1, qty=10, price=500.0, quote=None,
        positions={}, open_orders=[], equity=100_000, data_fresh=False,
        market_open=True, broker_healthy=True, model_approved=True,
        daily_loss_halted=True, risk_new_trades_allowed=False,
    )
    assert not res.ok
    assert "data_fresh" in res.failures()
    assert "risk_engine_ok" in res.failures()
