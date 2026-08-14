"""Probability calibration: confidence != certainty.

Implements reliability-curve analysis, Expected Calibration Error (ECE),
Brier score, and two calibration transforms (Platt/sigmoid via sklearn and
isotonic). Every deployed model's probabilities MUST pass a calibration
check before its confidence can drive position sizing.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

try:
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.isotonic import IsotonicRegression
    _HAS_SKLEARN = True
except Exception:  # pragma: no cover
    _HAS_SKLEARN = False


def reliability_curve(y_true: np.ndarray, proba: np.ndarray,
                      bins: int = 10) -> pd.DataFrame:
    """Bin predictions; compare mean predicted vs empirical frequency."""
    df = pd.DataFrame({"y": np.asarray(y_true, dtype=float),
                       "p": np.asarray(proba, dtype=float)})
    df["bin"] = pd.cut(df["p"], bins=np.linspace(0, 1, bins + 1),
                       include_lowest=True)
    out = df.groupby("bin", observed=True).agg(
        n=("p", "size"),
        mean_pred=("p", "mean"),
        mean_actual=("y", "mean"),
    )
    return out


def expected_calibration_error(y_true: np.ndarray, proba: np.ndarray,
                               bins: int = 10) -> float:
    rc = reliability_curve(y_true, proba, bins)
    if len(rc) == 0:
        return np.nan
    total = rc["n"].sum()
    ece = float((rc["n"] / total * (rc["mean_pred"] - rc["mean_actual"]).abs()).sum())
    return ece


def brier_score(y_true: np.ndarray, proba: np.ndarray) -> float:
    y = np.asarray(y_true, dtype=float)
    p = np.asarray(proba, dtype=float)
    return float(np.mean((p - y) ** 2))


def calibrate(estimator, X_train, y_train, X_cal, y_cal, method: str = "sigmoid"):
    """Fit a calibration transform on a HOLD-OUT calibration set and return
    (calibrated_predictor, report_dict)."""
    if not _HAS_SKLEARN:
        raise RuntimeError("sklearn required for calibration")
    cal = CalibratedClassifierCV(estimator, method=method, cv="prefit")
    cal.fit(X_cal, y_cal)
    report = {
        "method": method,
        "ece_pre": expected_calibration_error(y_cal, estimator.predict_proba(X_cal)[:, 1]),
        "ece_post": expected_calibration_error(y_cal, cal.predict_proba(X_cal)[:, 1]),
        "brier_pre": brier_score(y_cal, estimator.predict_proba(X_cal)[:, 1]),
        "brier_post": brier_score(y_cal, cal.predict_proba(X_cal)[:, 1]),
    }
    return cal, report


def reliability_report(y_true, proba, bins: int = 10) -> pd.DataFrame:
    rc = reliability_curve(y_true, proba, bins)
    rc["abs_gap"] = (rc["mean_pred"] - rc["mean_actual"]).abs()
    rc["ece_contribution"] = rc["abs_gap"] * rc["n"] / rc["n"].sum()
    return rc
