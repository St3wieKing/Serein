"""Robustness analysis: parameter grids, perturbation, PBO (CSCV), ablation.

A strategy is not "good" because its best parameter set backtests well.
It is good if a NEIGHBORHOOD of parameters behaves reasonably, and if the
selection process itself is not overfit (PBO).
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass

import numpy as np
import pandas as pd


# --------------------------------------------------------------------------
# Parameter stability
# --------------------------------------------------------------------------
def parameter_grid(space: dict[str, list]) -> list[dict]:
    """Cartesian product of parameter values."""
    keys = list(space)
    for combo in itertools.product(*[space[k] for k in keys]):
        yield dict(zip(keys, combo))


def run_parameter_sweep(
    make_strategy,
    bars: dict[str, pd.DataFrame],
    regime: pd.DataFrame | None,
    space: dict[str, list],
    backtest_fn,
    metric: str = "sharpe",
) -> pd.DataFrame:
    """Run backtests across a parameter grid; return per-config metrics.

    The resulting matrix feeds PBO analysis: rows = configurations,
    columns = chronological subperiod metrics.
    """
    rows = []
    for params in parameter_grid(space):
        strat = make_strategy(params)
        signals = {s: strat.generate(bars[s], regime) for s in bars}
        res = backtest_fn(signals)
        rows.append({"params": params, "metrics": res.metrics})
    df = pd.DataFrame(rows)
    return df


def stability_summary(sweep: pd.DataFrame, metric: str = "sharpe") -> dict:
    """Report the distribution of the chosen metric across the grid."""
    vals = [r["metrics"].get(metric, np.nan) for _, r in sweep.iterrows()]
    vals = [v for v in vals if v is not None and np.isfinite(v)]
    if not vals:
        return {"n": 0, "median": np.nan, "p25": np.nan, "p75": np.nan,
                "frac_positive": np.nan, "max": np.nan, "min": np.nan}
    return {
        "n": len(vals),
        "median": float(np.median(vals)),
        "p25": float(np.percentile(vals, 25)),
        "p75": float(np.percentile(vals, 75)),
        "frac_positive": float(np.mean([v > 0 for v in vals])),
        "max": float(np.max(vals)),
        "min": float(np.min(vals)),
    }


# --------------------------------------------------------------------------
# Probability of Backtest Overfitting (CSCV)
# --------------------------------------------------------------------------
@dataclass
class PBOResult:
    pbo: float
    logit: float
    n_configs: int
    n_partitions: int
    n_trials: int
    best_in_sample: dict

    def summary(self) -> str:
        verdict = "LOW overfitting risk" if self.pbo < 0.25 else (
            "MODERATE overfitting risk" if self.pbo < 0.5 else "HIGH overfitting risk")
        return (f"PBO = {self.pbo:.2%} ({verdict}); logit = {self.logit:.2f}; "
                f"configs={self.n_configs}, partitions={self.n_partitions}")


def cscv_pbo(
    performance_matrix: pd.DataFrame,
    metric: str = "sharpe",
    n_partitions: int = 6,
    max_trials: int = 2000,
    seed: int = 42,
) -> PBOResult:
    """Combinatorially Symmetric Cross-Validation PBO estimate.

    performance_matrix: rows = strategy configurations, columns =
    chronological subperiods, values = the chosen performance metric.
    Implements Bailey, Borwein, Lopez de Prado & Zhu (2015).

    Returns probability that the config selected as best in-sample would rank
    below the median out-of-sample.
    """
    rng = np.random.default_rng(seed)
    M = performance_matrix.copy()
    T = M.shape[1]
    if T < 4:
        raise ValueError("need >= 4 subperiods for CSCV")
    half = T // 2

    # all combinations of half the columns (sampled if too many)
    combos = list(itertools.combinations(range(T), half))
    if len(combos) > max_trials:
        combos = [combos[i] for i in
                  rng.choice(len(combos), size=max_trials, replace=False)]

    n_configs = M.shape[0]
    worse = 0
    total = 0
    best_in_sample = None
    for combo in combos:
        a_cols = list(combo)
        b_cols = [c for c in range(T) if c not in a_cols]
        A = M.iloc[:, a_cols].mean(axis=1)   # IS performance per config
        B = M.iloc[:, b_cols]                # OOS performance per config
        best_idx = A.idxmax()
        if best_in_sample is None:
            best_in_sample = {"index": str(best_idx),
                              "in_sample_metric": float(A.loc[best_idx])}
        # OOS relative rank of the chosen config (Bailey et al. 2015):
        # omega = (#configs with <= performance) / N  -> 1 = best, 1/N = worst.
        # lambda = mean over OOS subperiods of logit(omega).
        # PBO = P(lambda <= 0): the chosen config lands in the worse half OOS.
        omega = (B <= B.loc[best_idx]).sum(axis=0) / n_configs
        omega = np.clip(omega, 1e-9, 1 - 1e-9)
        lam = np.log(omega / (1.0 - omega)).mean()
        total += 1
        if lam <= 0.0:
            worse += 1

    pbo = worse / total if total else np.nan
    logit = float(np.log(pbo / (1 - pbo))) if 0 < pbo < 1 else (np.inf if pbo == 1 else -np.inf)
    return PBOResult(pbo=pbo, logit=logit, n_configs=M.shape[0],
                     n_partitions=n_partitions, n_trials=len(combos),
                     best_in_sample=best_in_sample or {})


def performance_matrix_from_sweep(sweep: pd.DataFrame, n_subperiods: int = 6,
                                  metric: str = "sharpe") -> pd.DataFrame:
    """Build a CSCV matrix from a sweep result — requires subperiod metrics.

    NOTE: for a proper PBO you need per-subperiod metrics per config. This
    helper is a placeholder for pipelines that only store aggregate metrics;
    prefer building the matrix directly from subperiod backtests.
    """
    raise NotImplementedError(
        "PBO requires per-subperiod performance. Build the matrix by running "
        "each configuration on each subperiod and stacking the metric.")


# --------------------------------------------------------------------------
# Ablation
# --------------------------------------------------------------------------
def ablation(
    feature_sets: list[list[str]],
    fit_evaluate,
    baseline_features: list[str],
    metric: str = "oos_auc",
) -> pd.DataFrame:
    """Measure incremental value of feature groups.

    fit_evaluate(features) -> dict of metrics (must include `metric`).
    feature_sets: list of feature-group names/lists to test.
    Returns per-variant results with delta vs baseline (all features).
    """
    rows = []
    base = fit_evaluate(baseline_features)
    base_val = base.get(metric, np.nan)
    rows.append({"variant": "ALL", "features": len(baseline_features),
                 metric: base_val, "delta": 0.0})
    for fname, feats in feature_sets:
        res = fit_evaluate(feats)
        v = res.get(metric, np.nan)
        rows.append({"variant": f"-{fname}", "features": len(feats),
                     metric: v, "delta": (v - base_val) if np.isfinite(v) and np.isfinite(base_val) else np.nan})
    df = pd.DataFrame(rows)
    df["kept"] = df["delta"].fillna(-np.inf) >= -0.005
    return df


# --------------------------------------------------------------------------
# Parameter perturbation
# --------------------------------------------------------------------------
def perturb_params(params: dict, frac: float = 0.1, seed: int = 7,
                   n: int = 20) -> list[dict]:
    """Generate perturbed parameter sets (multiplicative jitter)."""
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        p = dict(params)
        for k, v in p.items():
            if isinstance(v, (int, float)) and v != 0:
                p[k] = v * (1 + rng.normal(0, frac))
                if isinstance(v, int):
                    p[k] = max(2, int(round(p[k])))
        out.append(p)
    return out
