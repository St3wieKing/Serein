"""Meta-Decision Engine.

Input: one signal frame per strategy per symbol (the strict schema from
strategies.base). Output: one combined decision frame per symbol.

Logic:
  * weighted vote across strategies (weights = validated strategy health)
  * confidence = |net vote| (disagreement-aware)
  * disagreement penalty: if strategies cancel out, NO_TRADE
  * regime veto: uncertain/transition regimes halve confidence; strategies
    declaring regime_ok=False are excluded
  * minimum edge gate: expected_R below threshold => NO_TRADE
  * reason field records WHICH strategies agreed (for the journal)

NO_TRADE is a first-class output, not a fallback.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .strategies.base import SIGNAL_COLUMNS, validate_signals

ACTION_MAP = {
    # (direction, confidence bucket) -> action
}


def _action_for(direction: int, confidence: float) -> str:
    from . import constants as C
    if direction == 0:
        return C.ACTION_NO_TRADE
    if confidence < 0.55:
        return C.ACTION_WEAK_BUY if direction > 0 else C.ACTION_WEAK_SELL
    if confidence < 0.75:
        return C.ACTION_BUY if direction > 0 else C.ACTION_SELL
    return C.ACTION_STRONG_BUY if direction > 0 else C.ACTION_STRONG_SELL


class MetaEngine:
    def __init__(
        self,
        weights: dict[str, float] | None = None,
        min_confidence: float = 0.50,
        max_disagreement: float = 0.75,
        min_expected_r: float = 0.6,
        veto_regimes: tuple[str, ...] = ("uncertain", "transition"),
        regime_penalty: float = 0.5,
    ):
        self.weights = weights or {}
        self.min_confidence = min_confidence
        self.max_disagreement = max_disagreement
        self.min_expected_r = min_expected_r
        self.veto_regimes = veto_regimes
        self.regime_penalty = regime_penalty

    def combine(
        self,
        strategy_signals: dict[str, pd.DataFrame],
        regime: pd.DataFrame | None = None,
    ) -> pd.DataFrame:
        """Combine per-strategy signal frames (all indexed like the bars).

        strategy_signals: strategy_name -> signals frame.
        regime: optional regime classification frame (indexed like bars).
        Returns one combined signals frame with the standard schema plus
        'n_strategies', 'disagreement', 'action'.
        """
        names = list(strategy_signals)
        if not names:
            raise ValueError("no strategy signals provided")
        first = strategy_signals[names[0]]
        idx = first.index
        for n in names:
            validate_signals(strategy_signals[n])

        w = np.array([self.weights.get(n, 1.0) for n in names])
        w = w / w.sum()

        dirs = np.vstack([strategy_signals[n]["direction"].to_numpy() for n in names])
        confs = np.vstack([strategy_signals[n]["confidence"].to_numpy() for n in names])
        r_vals = np.vstack([strategy_signals[n]["expected_R"].to_numpy() for n in names])
        ok = np.vstack([strategy_signals[n]["regime_ok"].to_numpy() for n in names])

        # weighted vote
        vote = (dirs * confs * ok) * w[:, None]
        net = vote.sum(axis=0)
        total_abs = (np.abs(dirs) * confs * ok * w[:, None]).sum(axis=0)
        disagreement = np.where(total_abs > 0, 1.0 - np.abs(net) / np.maximum(total_abs, 1e-12), 0.0)

        # confidence: |net| normalized by the weight of ACTIVE (non-flat, ok)
        # strategies, then penalized by disagreement. 1.0 = all active
        # strategies fully agree; 0 = cancel out.
        active_w = (w[:, None] * ok).sum(axis=0)
        net_norm = np.abs(net) / np.maximum(active_w, 1e-12)
        confidence = net_norm * (1.0 - disagreement)
        confidence = np.clip(confidence, 0.0, 1.0)

        # expected R: weighted mean of active strategies' R
        active_w = (np.abs(dirs) * ok * w[:, None])
        denom = active_w.sum(axis=0)
        exp_r = np.where(denom > 0, (r_vals * active_w).sum(axis=0) / np.maximum(denom, 1e-12), 0.0)

        direction = np.zeros(len(idx), dtype=int)
        direction[net > 0.05] = 1
        direction[net < -0.05] = -1

        out = pd.DataFrame(
            {
                "direction": direction,
                "confidence": confidence,
                "expected_R": exp_r,
                "horizon_bars": 0,
                "regime_ok": np.ones(len(idx), dtype=bool),
                "reason": "",
                "n_strategies": (np.abs(dirs) * ok).sum(axis=0),
                "disagreement": disagreement,
            },
            index=idx,
        )
        out["horizon_bars"] = int(np.nanmedian(
            np.vstack([strategy_signals[n]["horizon_bars"].to_numpy() for n in names])))

        # regime veto
        if regime is not None:
            reg = regime["regime"].reindex(idx).ffill()
            for rname in self.veto_regimes:
                mask = (reg == rname).to_numpy()
                out.loc[mask, "confidence"] *= self.regime_penalty
                out.loc[mask, "regime_ok"] = False if rname == "uncertain" else True

        # gates: confidence, disagreement, edge
        kill = (
            (out["confidence"] < self.min_confidence)
            | (out["disagreement"] > self.max_disagreement)
            | (out["expected_R"] < self.min_expected_r)
        )
        out.loc[kill, "direction"] = 0
        out.loc[kill, "confidence"] = 0.0

        # reasons: which strategies contributed to the final direction
        for i in range(len(idx)):
            if out["direction"].iloc[i] == 0:
                continue
            contrib = [
                n for n in names
                if strategy_signals[n]["direction"].iloc[i] == out["direction"].iloc[i]
                and strategy_signals[n]["regime_ok"].iloc[i]
            ]
            out.loc[out.index[i], "reason"] = "+".join(contrib) if contrib else "meta"

        out["action"] = [_action_for(int(d), float(c))
                         for d, c in zip(out["direction"], out["confidence"])]
        return out
