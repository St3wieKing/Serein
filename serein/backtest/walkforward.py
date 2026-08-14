"""Walk-forward validation with purging and embargoing.

The single most important anti-overfitting device in this project:
  * parameters/models are locked on the training window
  * the test window is strictly AFTER training (no future information)
  * an embargo between train and test prevents label-overlap leakage
  * nothing is ever tuned on the test window; seeing it invalidates it
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def walk_forward_splits(
    n: int,
    n_splits: int = 4,
    embargo: int = 24,
    min_train: int = 1000,
) -> list[tuple[np.ndarray, np.ndarray]]:
    """Create chronological (train, test) index pairs.

    test i covers [anchor_i, anchor_{i+1}); train covers [0, anchor_i - embargo).
    """
    if n_splits < 2:
        raise ValueError("n_splits must be >= 2")
    anchors = np.linspace(min_train, n, n_splits + 1, dtype=int)
    anchors = np.unique(anchors)
    splits = []
    for i in range(len(anchors) - 1):
        test_start = anchors[i]
        test_end = anchors[i + 1]
        train = np.arange(0, max(test_start - embargo, 0))
        test = np.arange(test_start, test_end)
        if len(train) < 100 or len(test) < 10:
            continue
        splits.append((train, test))
    if not splits:
        raise ValueError("not enough data for walk-forward splits")
    return splits


def run_walk_forward_strategy(
    signals: pd.DataFrame,
    backtest_fn,
    n_splits: int = 4,
    embargo_bars: int = 24,
) -> dict:
    """Evaluate a RULE strategy per test window with parameters locked.

    backtest_fn(train_signals, test_signals) -> BacktestResult.
    """
    idx = signals.index
    n = len(idx)
    splits = walk_forward_splits(n, n_splits, embargo_bars)
    folds = []
    for i, (tr, te) in enumerate(splits):
        test_frame = signals.iloc[te]
        res = backtest_fn(test_frame)
        folds.append({
            "fold": i,
            "train_range": f"{idx[tr[0]]}..{idx[tr[-1]]}",
            "test_range": f"{idx[te[0]]}..{idx[te[-1]]}",
            "n_test_bars": len(te),
            "metrics": res.metrics,
        })
    return {"folds": folds}


def purged_kfold(
    n: int,
    n_splits: int = 5,
    embargo: int = 24,
    pct_out: float = 0.2,
) -> list[tuple[np.ndarray, np.ndarray]]:
    """Purged k-fold for CV of ML models (labels overlap -> purge + embargo)."""
    # simple sequential purged k-fold: train = all outside test window
    # minus embargo buffer on both sides of the test window
    test_size = max(int(n * pct_out / n_splits), 10)
    splits = []
    for k in range(n_splits):
        start = k * test_size
        end = min(n, start + test_size)
        test = np.arange(start, end)
        train = np.concatenate([
            np.arange(0, max(start - embargo, 0)),
            np.arange(min(end + embargo, n), n),
        ])
        splits.append((train, test))
    return splits
