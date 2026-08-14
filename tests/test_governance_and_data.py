import json

import pandas as pd
import pytest

from serein.audit_journal import HashChainJournal
from serein.backtest.uncertainty import block_bootstrap_equity, trade_expectancy_bootstrap
from serein.config import BacktestConfig
from serein.data.intraday_csv import load_intraday_csv
from serein.data.intraday_synthetic import generate_intraday_universe
from serein.holdout import HoldoutFirewall, HoldoutRecord
from serein.promotion import IntradayPromotionEvidence, evaluate_intraday_promotion
from serein.reproducibility import frame_fingerprint, run_manifest, universe_fingerprint
from serein.safety_state import SafetySnapshot, SafetyStateStore
from serein.strategies.institutional_intraday import OpeningRangeChallenger


def test_holdout_cannot_become_pristine_after_reveal(tmp_path):
    f = HoldoutFirewall(tmp_path/"holdouts.jsonl")
    f.register(HoldoutRecord("spy-2025", "abc", "2025-01-01", "2025-12-31", "final test"))
    f.assert_pristine("spy-2025")
    f.reveal("spy-2025", experiment_id="exp1", reason="locked evaluation")
    with pytest.raises(RuntimeError): f.assert_pristine("spy-2025")
    with pytest.raises(RuntimeError): f.reveal("spy-2025", experiment_id="exp2", reason="reuse")
    assert f.verify_chain()


def test_hash_journal_detects_tampering(tmp_path):
    p = tmp_path/"audit.jsonl"; j = HashChainJournal(p)
    j.append("SIGNAL", {"direction": 0}); j.append("RISK", {"allowed": False})
    assert j.verify()
    rows = p.read_text().splitlines(); x = json.loads(rows[0]); x["payload"]["direction"] = 1
    rows[0] = json.dumps(x); p.write_text("\n".join(rows)+"\n")
    assert not j.verify()


def test_intraday_csv_timezone_session_and_missing_report(tmp_path):
    idx = pd.date_range("2025-01-02 14:30", periods=78, freq="5min", tz="UTC")
    df = pd.DataFrame({"timestamp": idx, "symbol": "SPY", "open": 100,
                       "high": 101, "low": 99, "close": 100.5, "volume": 1000})
    p = tmp_path/"bars.csv"; df.to_csv(p, index=False)
    bars, report = load_intraday_csv(p, source_timezone="UTC", require_complete_sessions=True)
    assert len(bars["SPY"]) == 78
    assert bars["SPY"].index[0].strftime("%H:%M") == "09:30"
    assert report.missing_session_bars == 0


def test_intraday_csv_rejects_duplicates(tmp_path):
    row = {"timestamp": "2025-01-02 09:30", "symbol": "SPY", "open": 1,
           "high": 2, "low": .5, "close": 1.5, "volume": 10}
    p = tmp_path/"dup.csv"; pd.DataFrame([row, row]).to_csv(p, index=False)
    with pytest.raises(ValueError, match="duplicate"):
        load_intraday_csv(p, source_timezone="America/New_York")


def test_fingerprints_and_manifest_are_content_sensitive():
    bars, _ = generate_intraday_universe(["SPY"], days=2, seed=1)
    a = universe_fingerprint(bars)
    changed = {"SPY": bars["SPY"].copy()}; changed["SPY"].iloc[0, 0] += .01
    assert a != universe_fingerprint(changed)
    m = run_manifest(run_id="r1", bars=bars, config=BacktestConfig(),
                     strategy_name="x", strategy_params={}, evidence_class="SYNTHETIC")
    assert m["dataset_fingerprint"] == a and len(m["manifest_hash"]) == 64


def test_strict_promotion_rejects_synthetic_and_weak_evidence():
    e = IntradayPromotionEvidence("orb", "SYNTHETIC", 57, 4.8, -.1, -.01,
                                  .01, .005, .009, .01, 3, 4, False, 0, 0, 0)
    r = evaluate_intraday_promotion(e)
    assert not r.approved_for_paper_champion
    assert "real_point_in_time_data_required" in r.failures
    assert "contaminated_holdout" in r.failures
    assert "expectancy_confidence_interval" in r.failures


def test_block_bootstrap_reports_insufficient_and_valid():
    short = pd.Series([100, 101], index=pd.date_range("2025-01-01", periods=2))
    assert block_bootstrap_equity(short)["status"] == "INSUFFICIENT"
    idx = pd.date_range("2025-01-01", periods=100)
    eq = pd.Series(100*(1.001**pd.Series(range(100), index=idx)), index=idx)
    result = block_bootstrap_equity(eq, n_boot=100)
    assert result["status"] == "OK"
    assert result["return_ci95"][0] > 0


def test_safety_state_fails_closed_and_detects_corruption(tmp_path):
    p = tmp_path/"safety.json"; store = SafetyStateStore(p)
    assert store.startup_action() == "HALT_AND_RECONCILE"
    good = SafetySnapshot("PAPER", True, True, (), (), "2026-08-14T12:00:00Z")
    store.save(good)
    assert store.startup_action() == "PAPER_ENTRIES_ALLOWED"
    bad = SafetySnapshot("PAPER", True, True, ("DRAWDOWN",), (), "2026-08-14T12:00:00Z")
    store.save(bad)
    assert store.startup_action() == "HALT_AND_RECONCILE"
    text = p.read_text().replace("DRAWDOWN", "NONE")
    p.write_text(text)
    assert store.startup_action() == "HALT_AND_RECONCILE"


def test_opening_range_challenger_is_frozen_and_only_emits_orb():
    with pytest.raises(ValueError): OpeningRangeChallenger({"or_bars": 4})
    bars, _ = generate_intraday_universe(["SPY", "QQQ", "IWM"], days=30, seed=12)
    sigs = OpeningRangeChallenger().generate_universe(bars)
    for sig in sigs.values():
        active = sig.direction != 0
        assert sig.loc[active, "reason"].eq("opening_breakout").all()
