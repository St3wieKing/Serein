"""Deterministic fingerprints and research-run manifests."""
from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from .config import BacktestConfig, config_to_dict


def frame_fingerprint(frame: pd.DataFrame) -> str:
    """Content fingerprint including index, columns and values."""
    h = hashlib.sha256()
    h.update("|".join(map(str, frame.columns)).encode())
    h.update(pd.util.hash_pandas_object(frame.index, index=True).values.tobytes())
    h.update(pd.util.hash_pandas_object(frame, index=True).values.tobytes())
    return h.hexdigest()


def universe_fingerprint(bars: dict[str, pd.DataFrame]) -> str:
    h = hashlib.sha256()
    for symbol in sorted(bars):
        h.update(symbol.encode()); h.update(frame_fingerprint(bars[symbol]).encode())
    return h.hexdigest()


def code_revision() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True,
                                       stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "UNKNOWN"


def run_manifest(*, run_id: str, bars: dict[str, pd.DataFrame],
                 config: BacktestConfig, strategy_name: str,
                 strategy_params: dict, evidence_class: str) -> dict:
    body = {
        "run_id": run_id, "recorded_at": datetime.now(timezone.utc).isoformat(),
        "code_revision": code_revision(), "python": platform.python_version(),
        "numpy": np.__version__, "pandas": pd.__version__,
        "dataset_fingerprint": universe_fingerprint(bars),
        "symbols": sorted(bars), "rows": {s: len(b) for s, b in bars.items()},
        "config": config_to_dict(config), "strategy_name": strategy_name,
        "strategy_params": strategy_params, "evidence_class": evidence_class,
    }
    body["manifest_hash"] = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()
    return body
