"""Data layer tests: synthetic generator, validation, leakage audit."""

import numpy as np
import pandas as pd
import pytest

from serein.data.synthetic import generate_ohclv, generate_universe
from serein.data.validation import validate_bars, anomaly_flags, DataQualityError, drop_anomalous
from serein.data.audit import audit_feature_matrix, assert_no_leakage, LeakageFinding
from serein.features import build_features, make_labels


@pytest.fixture(scope="module")
def bars():
    b, _ = generate_ohclv(1500, seed=7)
    return b


def test_generator_shapes(bars):
    assert list(bars.columns) == ["open", "high", "low", "close", "volume"]
    assert len(bars) == 1500
    assert isinstance(bars.index, pd.DatetimeIndex)
    assert bars.isna().sum().sum() == 0
    assert (bars["high"] >= bars["low"]).all()


def test_generator_reproducible():
    b1, _ = generate_ohclv(500, seed=1)
    b2, _ = generate_ohclv(500, seed=1)
    pd.testing.assert_frame_equal(b1, b2)


def test_generator_regime_chain():
    _, reg = generate_ohclv(1000, seed=3, regime_chain=["bull_trend"] * 1000)
    assert (reg["regime"] == "bull_trend").all()
    # bull chain must drift upward on average
    assert np.mean(reg["drift"]) > 0


def test_universe_alignment():
    uni = generate_universe(["A", "B"], 300, seed=5)
    assert set(uni) == {"A", "B"}
    assert len(uni["A"]) == len(uni["B"]) == 300


def test_validation_clean(bars):
    assert validate_bars(bars) == []


def test_validation_catches_corruption(bars):
    bad = bars.copy()
    bad.loc[bad.index[10], "high"] = bad.loc[bad.index[10], "low"] - 1
    problems = validate_bars(bad)
    assert any("high<low" in p for p in problems)

    bad2 = bars.copy()
    bad2.loc[bad2.index[5], "close"] = np.nan
    assert any("close" in p and "NaN" in p for p in validate_bars(bad2))

    bad3 = bars.copy()
    bad3.loc[bad3.index[0], "open"] = -5.0
    assert any("open" in p for p in validate_bars(bad3))


def test_anomaly_flags(bars):
    flags = anomaly_flags(bars)
    assert flags["any_anomaly"].dtype == bool
    assert flags.index.equals(bars.index)


def test_drop_anomalous_tolerance():
    b, _ = generate_ohclv(500, seed=9)
    vandalized = b.copy()
    vandalized.iloc[:200, 1] = 1e9  # 40% insane highs
    with pytest.raises(DataQualityError):
        drop_anomalous(vandalized, max_frac=0.02)


def test_audit_detects_target_leakage():
    idx = pd.date_range("2020-01-01", periods=500, freq="h")
    y = pd.Series(np.random.default_rng(0).normal(size=500), index=idx)
    X = pd.DataFrame({"leaky": y * 1.0 + 1e-12, "ok": y * 0.1 + 0.5}, index=idx)
    result = audit_feature_matrix(X, y, ["leaky", "ok"])
    assert not result["pass"]
    with pytest.raises(LeakageFinding):
        assert_no_leakage(result)


def test_audit_alignment_error():
    idx = pd.date_range("2020-01-01", periods=500, freq="h")
    X = pd.DataFrame({"a": np.ones(500)}, index=idx)
    y = pd.Series(np.ones(499), index=idx[1:])
    result = audit_feature_matrix(X, y, ["a"])
    assert not result["pass"]


def test_audit_warns_on_horizon_overlap():
    idx = pd.date_range("2020-01-01", periods=500, freq="h")
    X = pd.DataFrame({"a": np.random.default_rng(1).normal(size=500)}, index=idx)
    y = pd.Series(np.random.default_rng(2).normal(size=500), index=idx)
    result = audit_feature_matrix(X, y, ["a"], label_horizon=6)
    assert result["pass"]
    assert any("purged" in w.lower() for w in result["warnings"])


def test_features_are_causal():
    """Feature at time t must not depend on data after t."""
    b, _ = generate_ohclv(800, seed=11)
    full = build_features(b, horizons=(1, 6, 24))
    t = b.index[400]
    prefix = build_features(b.loc[:t], horizons=(1, 6, 24))
    cols = [c for c in full.columns if c not in ("hour", "dow", "month", "session")]
    # values at t computed from full data must equal values computed only on prefix
    for c in cols:
        assert full.loc[t, c] == pytest.approx(prefix.loc[t, c], nan_ok=True)


def test_labels_are_forward():
    b, _ = generate_ohclv(800, seed=13)
    lab = make_labels(b, horizon=6, mode="binary")["label"]
    # label at t must equal sign of close[t+6]/close[t] - 1
    fwd = (b["close"].shift(-6) / b["close"] - 1.0) > 0
    expected = fwd.astype(lab.dtype)
    assert lab.equals(expected)
