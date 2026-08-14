from pathlib import Path

import pandas as pd
import pytest

from serein.data.synthetic import generate_ohclv
from serein.research.trade_forensics import analyze_trades, load_trade_export
from serein.strategies.athena_observed import QuantumAthenaSafeProxy
from serein.strategies.base import validate_signals

ROOT = Path(__file__).resolve().parents[1]


def test_public_sample_detects_basket_grid_evidence():
    df = load_trade_export(ROOT/"research"/"quantum_athena_public_sample.csv")
    r = analyze_trades(df)
    assert r.n_trades == 10
    assert r.long_fraction == 1.0
    assert r.max_simultaneous >= 4
    assert r.clustered_close_fraction >= 0.4
    assert r.fixed_lot_fraction == 1.0
    assert r.grid_evidence == "strong"
    # Fixed lots in this tiny sample do not support a martingale allegation.
    assert r.martingale_evidence != "possible_lot_progression"
    assert "partial_history" in r.limitations


def test_forensics_requires_core_columns(tmp_path):
    p = tmp_path/"bad.csv"
    pd.DataFrame({"profit": [1]}).to_csv(p, index=False)
    with pytest.raises(ValueError):
        load_trade_export(p)


def test_safe_proxy_schema_and_causality():
    bars, _ = generate_ohclv(2400, seed=73)
    s = QuantumAthenaSafeProxy()
    full = s.generate(bars)
    validate_signals(full)
    t = bars.index[1800]
    prefix = s.generate(bars.loc[:t])
    for c in ("direction", "confidence", "expected_R", "stop_price", "target_price"):
        a, b = full.loc[t,c], prefix.loc[t,c]
        if pd.isna(a) and pd.isna(b):
            continue
        assert a == pytest.approx(b)
    assert (full.direction >= 0).all()  # default matches observed long bias safely
