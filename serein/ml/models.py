"""Supervised models for the research pipeline.

Every model carries governance metadata (model_id, training window, features,
hyperparameters, data version) — a model without metadata cannot be deployed.
Champion/challenger discipline lives in registry.py.

Baseline-first philosophy: logistic regression is the mandatory baseline;
a fancier model must beat it OUT OF SAMPLE after costs to earn its place.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ..data.audit import audit_feature_matrix, assert_no_leakage

try:
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    _HAS_SKLEARN = True
except Exception:  # pragma: no cover
    _HAS_SKLEARN = False


@dataclass
class ModelRecord:
    model_id: str
    family: str                    # "logistic" | "random_forest" | "gradient_boosting"
    features: list[str]
    hyperparameters: dict
    training_start: str
    training_end: str
    data_version: str
    status: str = "RESEARCH"       # RESEARCH -> VALIDATION -> PAPER -> APPROVED -> ...
    oos_metrics: dict = field(default_factory=dict)
    calibration: dict = field(default_factory=dict)
    approved_by: str = ""
    deployment_date: str = ""
    note: str = ""

    def content_hash(self) -> str:
        h = hashlib.sha256()
        for part in (self.family, repr(self.features), repr(self.hyperparameters),
                     self.training_start, self.training_end, self.data_version):
            h.update(part.encode())
        return h.hexdigest()[:16]

    def to_dict(self) -> dict:
        d = dict(self.__dict__)
        d["content_hash"] = self.content_hash()
        return d


class ModelFactory:
    """Builds sklearn models with governance metadata."""

    FAMILIES = ("logistic", "random_forest", "gradient_boosting")

    def __init__(self, data_version: str = "v0"):
        self.data_version = data_version

    def build(self, family: str, features: list[str],
              train_start: str, train_end: str,
              hyperparameters: dict | None = None) -> ModelRecord:
        if not _HAS_SKLEARN:
            raise RuntimeError("sklearn is required for ML models")
        if family not in self.FAMILIES:
            raise ValueError(f"unknown family {family}; use {self.FAMILIES}")
        hp = hyperparameters or {}
        if family == "logistic":
            hp = {"C": hp.get("C", 1.0), "max_iter": hp.get("max_iter", 10000),
                  "class_weight": hp.get("class_weight", "balanced")}
        elif family == "random_forest":
            hp = {"n_estimators": hp.get("n_estimators", 300),
                  "max_depth": hp.get("max_depth", 4),
                  "min_samples_leaf": hp.get("min_samples_leaf", 50)}
        elif family == "gradient_boosting":
            hp = {"n_estimators": hp.get("n_estimators", 200),
                  "max_depth": hp.get("max_depth", 2),
                  "learning_rate": hp.get("learning_rate", 0.05)}
        rec = ModelRecord(
            model_id=uuid.uuid4().hex[:12],
            family=family, features=list(features),
            hyperparameters=hp,
            training_start=train_start, training_end=train_end,
            data_version=self.data_version,
        )
        return rec

    def instantiate(self, rec: ModelRecord):
        if rec.family == "logistic":
            return LogisticRegression(**rec.hyperparameters)
        if rec.family == "random_forest":
            return RandomForestClassifier(**rec.hyperparameters, random_state=42,
                                          n_jobs=-1)
        if rec.family == "gradient_boosting":
            return GradientBoostingClassifier(**rec.hyperparameters, random_state=42)
        raise ValueError(f"unknown family {rec.family}")


def build_ml_dataset(
    features: pd.DataFrame,
    labels: pd.Series,
    drop_na: bool = True,
    audit: bool = True,
) -> tuple[pd.DataFrame, pd.Series, dict]:
    """Align features and labels, run the leakage audit, drop NaN rows.

    Returns (X, y, audit_result). Raises LeakageFinding on severe issues.
    """
    aligned = pd.concat([features, labels.to_frame()], axis=1).dropna(
        subset=[labels.name]
    )
    X = aligned[features.columns]
    y = aligned[labels.name]
    if drop_na:
        mask = X.notna().all(axis=1)
        X, y = X[mask], y[mask]
    if audit:
        result = audit_feature_matrix(X, y, list(features.columns),
                                      label_horizon=1)
        assert_no_leakage(result)
    else:
        result = {"problems": [], "warnings": [], "pass": True}
    return X, y, result


def walk_forward_ml(
    X: pd.DataFrame,
    y: pd.Series,
    rec: ModelRecord,
    n_splits: int = 4,
    embargo_bars: int = 24,
    min_train: int = 2000,
    calibrate: bool = True,
    seed: int = 42,
) -> dict:
    """Purged/embargoed walk-forward evaluation of one model record.

    Returns fold-by-fold OOS predictions + aggregate metrics.
    """
    from ..backtest.walkforward import walk_forward_splits

    splits = walk_forward_splits(len(X), n_splits=n_splits, embargo=embargo_bars,
                                 min_train=min_train)
    factory = ModelFactory(data_version=rec.data_version)
    oos_pred, oos_true, fold_reports = [], [], []
    for i, (tr, te) in enumerate(splits):
        est = factory.instantiate(rec)
        est.fit(X.iloc[tr], y.iloc[tr])
        p = est.predict_proba(X.iloc[te])[:, 1]
        oos_pred.append(p)
        oos_true.append(y.iloc[te].to_numpy())
        fold_reports.append({"fold": i, "n_train": len(tr), "n_test": len(te)})
    oos_pred = np.concatenate(oos_pred)
    oos_true = np.concatenate(oos_true)

    from .calibration import (expected_calibration_error, brier_score,
                              reliability_report)
    result = {
        "model_id": rec.model_id,
        "family": rec.family,
        "n_splits": n_splits,
        "embargo_bars": embargo_bars,
        "oos_accuracy": float(((oos_pred > 0.5) == (oos_true == 1)).mean()),
        "oos_auc": _auc(oos_true, oos_pred),
        "ece": expected_calibration_error(oos_true, oos_pred),
        "brier": brier_score(oos_true, oos_pred),
        "base_rate": float(oos_true.mean()),
        "n_oos": int(len(oos_true)),
        "fold_reports": fold_reports,
        "reliability": reliability_report(oos_true, oos_pred),
        "oos_true": oos_true.tolist(),
        "oos_pred": oos_pred.tolist(),
    }
    rec.oos_metrics = {k: v for k, v in result.items()
                       if k not in ("oos_true", "oos_pred", "reliability")}
    return result


def _auc(y_true, y_score) -> float:
    """ROC AUC via rank statistic (no sklearn dependency)."""
    y = np.asarray(y_true, dtype=float)
    s = np.asarray(y_score, dtype=float)
    n_pos = (y == 1).sum()
    n_neg = (y == 0).sum()
    if n_pos == 0 or n_neg == 0:
        return np.nan
    order = np.argsort(s, kind="mergesort")
    ranks = np.empty(len(s))
    ranks[order] = np.arange(1, len(s) + 1)
    return float((ranks[y == 1].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))
