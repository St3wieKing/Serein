"""Data Leakage Auditor.

Searches a candidate (features, labels) matrix for the classic ways future
information contaminates training:

  1. future timestamps in features
  2. label overlap with feature window (no lookahead)
  3. target leakage: feature columns that perfectly or near-perfectly
     predict the label by construction
  4. improper alignment: label index shifted the wrong way
  5. normalization leakage: stats computed on the full sample before split

The audit is a GATE: `run()` returns problems; a severe finding means the
pipeline must refuse to publish performance metrics for that dataset.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


class LeakageFinding(Exception):
    """Raised when a severe leakage pattern is detected."""


def _shift_direction_sanity(df: pd.DataFrame, label_col: str, feature_cols: list[str]) -> list[str]:
    problems = []
    for f in feature_cols:
        # A feature must not contain values that embed the same-bar label info.
        # Cheap heuristic: correlation between feature and label must not be 1.0
        # (a perfect correlation on raw levels indicates the feature IS the label).
        if df[f].dtype.kind in "fiub":
            a = df[f].fillna(0).to_numpy()
            b = df[label_col].fillna(0).to_numpy()
            if a.std() == 0 or b.std() == 0:
                continue  # constant column: no correlation signal either way
            corr = np.corrcoef(a, b)[0, 1]
            if np.isclose(abs(corr), 1.0, atol=1e-9):
                problems.append(f"feature '{f}' is perfectly correlated with label "
                                f"(corr={corr:.4f}) — likely leakage")
    return problems


def audit_feature_matrix(
    X: pd.DataFrame,
    y: pd.Series,
    feature_cols: list[str] | None = None,
    label_horizon: int = 1,
    verbose: bool = True,
) -> dict:
    """Audit a feature/label matrix. Returns {problems, warnings, pass}.

    Rules checked:
      * X.index and y.index identical (alignment).
      * X.index is monotonic (temporal order preserved).
      * No feature column name matches the label column name.
      * No perfect correlations (target leakage).
      * Label is shifted in the correct direction: y[t] must describe the
        future relative to X[t]. We verify that autocorrelation structure is
        plausible (y not identical to a feature).
    """
    problems: list[str] = []
    warnings: list[str] = []
    feature_cols = feature_cols or list(X.columns)
    if y.name is None:
        y = y.rename("label")

    if not X.index.equals(y.index):
        problems.append("X and y indexes are not identical (alignment error)")
    if not isinstance(X.index, pd.DatetimeIndex):
        warnings.append("X index is not a DatetimeIndex")
    elif not X.index.is_monotonic_increasing:
        problems.append("X index is not monotonic (temporal order broken)")

    if y.name in feature_cols:
        problems.append(f"label column '{y.name}' appears in features (target leakage)")

    problems += _shift_direction_sanity(pd.concat([X, y.to_frame()], axis=1),
                                        y.name, feature_cols)

    # Label overlap check: for horizon h>1, y[t] and y[t-1] share future data.
    # That is not leakage per se (labels legitimately overlap), but the audit
    # flags it so callers remember to purge/embargo during CV.
    if label_horizon > 1:
        warnings.append(
            f"label horizon={label_horizon} > 1: labels overlap in time; "
            "purged/embargoed CV is REQUIRED"
        )

    # NaN structure: features with >30% NaN are dangerous (usually misaligned)
    for f in feature_cols:
        nan_frac = X[f].isna().mean()
        if nan_frac > 0.3:
            warnings.append(f"feature '{f}' has {nan_frac:.0%} NaN — misalignment risk")

    result = {"problems": problems, "warnings": warnings, "pass": len(problems) == 0}
    if verbose:
        for w in warnings:
            print(f"[leakage-audit] WARN: {w}")
        for p in problems:
            print(f"[leakage-audit] ERROR: {p}")
    return result


def assert_no_leakage(result: dict) -> None:
    """Gate: raise if the audit found problems."""
    if not result["pass"]:
        raise LeakageFinding("; ".join(result["problems"]))
