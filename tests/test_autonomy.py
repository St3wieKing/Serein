import json

import pytest

from serein import LIVE_EXECUTION_ENABLED, PAPER_TRADING_ONLY
from serein.audit_journal import HashChainJournal
from serein.autonomy.agents import ResearchAgent, RedTeamAgent, ReviewAgent
from serein.autonomy.authority import Role, authorized, require, CAPABILITIES, PROHIBITED
from serein.autonomy.factory import StrategyFactory, CandidateSpec
from serein.autonomy.orchestrator import AutonomousResearchLoop
from serein.autonomy.store import AutonomyStore
from serein.autonomy.types import ExperimentOutcome, ExperimentStatus
from serein.config import BacktestConfig
from serein.certification import CertificationEvidence, certification_markdown
from serein.monitoring import daily_review, weekly_review
from serein.promotion import GateResult
from serein.data.synthetic import generate_ohclv
from serein.execution.broker import PaperBroker
from serein.execution.gateway import OrderIntent, PaperExecutionGateway
from serein.execution.validation import OrderValidator
from serein.health import HealthEvidence, HealthSupervisor, assess_health
from serein.opportunity import Opportunity, OpportunityRanker
from serein.observability import SystemSnapshot, snapshot_html
from serein.journal_schema import TradeJournalRecord


def test_live_execution_is_structurally_disabled():
    assert PAPER_TRADING_ONLY and not LIVE_EXECUTION_ENABLED
    for role in Role:
        for capability in PROHIBITED:
            assert not authorized(role, capability)
    with pytest.raises(PermissionError): require(Role.RESEARCH, "approve_order")
    # No role can both propose alpha, approve risk and submit execution.
    for caps in CAPABILITIES.values():
        assert not {"propose_order", "approve_order", "submit_paper_order"} <= caps


def test_research_redteam_review_agents():
    proposals = ResearchAgent().propose({"weak_setup": "pullback", "issue": "cost failure",
                                         "n_trades": 20}, dataset_id="D1")
    assert proposals and proposals[0].priority() > 0
    attacks = RedTeamAgent().attacks(proposals[0].to_dict())
    assert len(attacks) >= 10 and any(a.name == "authority_escalation" for a in attacks)
    review = ReviewAgent().review(outcome={"oos_trades": 20, "expectancy_ci_low": -.1},
                                  red_team_results={a.name: True for a in attacks},
                                  evidence_class="SYNTHETIC", holdout_pristine=False)
    assert review.decision == "NOT_APPROVED"
    assert "real point-in-time data" in review.missing_evidence


def test_autonomy_store_queue_budget_and_cycle(tmp_path):
    store = AutonomyStore(tmp_path/"autonomy.db")
    loop = AutonomousResearchLoop(store, max_experiments_per_dataset=5)
    queued = loop.propose_next({"weak_setup": "reversion", "issue": "small sample",
                                "n_trades": 12}, dataset_id="D")
    assert queued and store.budget("D")["experiments"] == len(queued)

    def runner(proposal, attacks):
        results = {a.name: a.name not in ("slippage_tail",) for a in attacks}
        return ({"oos_trades": 80, "expectancy_ci_low": .05, "confidence": "LOW"},
                {"cost2": 0.01}, ("slippage_tail",), results)

    outcome, review = loop.run_one(runner, evidence_class="SYNTHETIC", holdout_pristine=True)
    assert outcome.status == ExperimentStatus.COMPLETED
    assert outcome.decision == "REJECTED"
    assert review.decision == "NOT_APPROVED"
    assert store.counts()["COMPLETED"] == 1
    store.close()


def test_factory_is_constrained_and_budgeted():
    f = StrategyFactory(max_candidates=1, max_filters=1)
    bad = CandidateSpec("trend", "opening_breakout", "range_break",
                        "structural_atr", "fixed_r")
    with pytest.raises(ValueError): f.build(bad)
    good = CandidateSpec("opening_session", "opening_breakout", "range_break",
                         "structural_atr", "session_close", ("relative_volume",))
    assert f.build(good) is not None
    with pytest.raises(RuntimeError): f.build(good)


def test_opportunity_ranking_uses_post_cost_ev_and_approval():
    good = Opportunity("SPY", "approved", "orb", 1, .6, 2, 1, .05, .05,
                       .9, .9, .9, .8, strategy_approved=True)
    negative = Opportunity("QQQ", "approved", "orb", 1, .4, 1, 2, .2, .2,
                           .9, .9, .9, .8, strategy_approved=True)
    unapproved = Opportunity("IWM", "research", "orb", 1, .8, 2, 1, 0, 0,
                             1, 1, 1, 1, strategy_approved=False)
    ranked = OpportunityRanker(min_quality=20).rank([negative, unapproved, good])
    assert ranked == [good]
    assert good.expected_r > 0 and negative.expected_r < 0


def test_health_does_not_adapt_to_small_sample_and_quarantines_joint_failure():
    small = HealthEvidence(10, -.5, .2, -5, -.01, 1, 0, .02)
    assert assess_health(small).action == "MONITOR_NO_ADAPTATION"
    bad = HealthEvidence(100, -.2, .2, -4, -.02, 2.5, 4, .2)
    d = assess_health(bad)
    assert d.state == "QUARANTINED" and d.action == "STOP_AND_REVALIDATE"
    supervisor = HealthSupervisor()
    assert supervisor.update("s1", bad).state == "QUARANTINED"
    assert not supervisor.can_trade("s1")


def test_paper_gateway_checks_approval_quote_and_duplicates(tmp_path):
    bars, _ = generate_ohclv(100, seed=4)
    cfg = BacktestConfig()
    broker = PaperBroker({"SPY": bars}, cfg)
    broker.set_clock(bars.index[20])
    journal = HashChainJournal(tmp_path/"orders.jsonl")
    gate = PaperExecutionGateway(broker, OrderValidator(cfg.risk, cfg.sizing), journal,
                                 approved_strategies={"orb-v1"}, approved_models=set())
    q = broker.get_quotes(["SPY"])["SPY"]
    intent = OrderIntent("i-1", "SPY", 1, 10, q["ask"], "orb-v1", None,
                         .7, 1.2, q["ask"]*.99, q["ask"]*1.02)
    filled = gate.submit(intent, quote=q, equity=100_000, data_fresh=True,
                         market_open=True, broker_healthy=True,
                         daily_loss_halted=False, weekly_loss_halted=False,
                         risk_new_trades_allowed=True, bar_volume=1_000_000,
                         now=bars.index[20])
    assert filled is not None and filled.status == "FILLED"
    assert gate.submit(intent, quote=q, equity=100_000, data_fresh=True,
                       market_open=True, broker_healthy=True,
                       daily_loss_halted=False, weekly_loss_halted=False,
                       risk_new_trades_allowed=True, now=bars.index[20]) is None
    assert journal.verify()
    order_ids = {o.order_id for o in broker.get_orders() if o.order_id}
    assert broker.reconcile(broker.get_positions(), order_ids)["ok"]


def test_gateway_denies_unapproved_strategy(tmp_path):
    bars, _ = generate_ohclv(50, seed=5); cfg = BacktestConfig()
    b = PaperBroker({"SPY": bars}, cfg); b.set_clock(bars.index[10])
    g = PaperExecutionGateway(b, OrderValidator(cfg.risk, cfg.sizing),
                              HashChainJournal(tmp_path/"j.jsonl"),
                              approved_strategies=set(), approved_models=set())
    q = b.get_quotes(["SPY"])["SPY"]
    i = OrderIntent("x", "SPY", 1, 1, q["ask"], "bad", None, .9, 2,
                    q["ask"]*.99, q["ask"]*1.02)
    assert g.submit(i, quote=q, equity=100_000, data_fresh=True, market_open=True,
                    broker_healthy=True, daily_loss_halted=False,
                    weekly_loss_halted=False, risk_new_trades_allowed=True,
                    now=bars.index[10]) is None


def test_gateway_denies_malformed_extreme_confidence(tmp_path):
    bars, _ = generate_ohclv(50, seed=6); cfg = BacktestConfig()
    b = PaperBroker({"SPY": bars}, cfg); b.set_clock(bars.index[10])
    j = HashChainJournal(tmp_path/"malformed.jsonl")
    g = PaperExecutionGateway(b, OrderValidator(cfg.risk, cfg.sizing), j,
                              approved_strategies={"ok"}, approved_models=set())
    q = b.get_quotes(["SPY"])["SPY"]
    i = OrderIntent("bad-conf", "SPY", 1, 1, q["ask"], "ok", None, 1000, 2,
                    q["ask"]*.99, q["ask"]*1.02)
    assert g.submit(i, quote=q, equity=100_000, data_fresh=True, market_open=True,
                    broker_healthy=True, daily_loss_halted=False,
                    weekly_loss_halted=False, risk_new_trades_allowed=True,
                    now=bars.index[10]) is None
    assert any(r["payload"].get("reason") == "malformed_intent" for r in j.read())


def test_certification_is_explicitly_failed_and_cannot_enable_live():
    e = CertificationEvidence("orb", "1", None, "abc", "data", "SYNTHETIC",
                              "research", "backtest", "wfa", "oos", "stress",
                              "costs", "slippage", "dd", "n/a", "n/a", "none",
                              ("5x costs",), ("slippage",), ("real data missing",))
    text = certification_markdown(e, GateResult(False, ("real_data_required",)))
    assert "**Status: FAILED**" in text
    assert "cannot enable live execution" in text


def test_daily_weekly_review_payloads():
    import pandas as pd
    t = pd.DataFrame({"exit_time": pd.to_datetime(["2026-08-14 10:00"]),
                      "entry_price": [100.], "stop": [99.], "qty": [10],
                      "pnl": [25.], "costs_total": [2.], "reason": ["orb"],
                      "symbol": ["SPY"]})
    idx = pd.date_range("2026-08-14 09:30", periods=3, freq="5min")
    eq = pd.DataFrame({"equity": [100000, 99990, 100025]}, index=idx)
    d = daily_review(t, eq, "2026-08-14", data_health="OK", broker_health="OK",
                     slippage_status="OK", anomalies=[])
    w = weekly_review(t, eq, "2026-08-14 16:00", model_drift={}, strategy_health={})
    assert d["trades"] == 1 and d["net_pnl"] == 25
    assert w["by_symbol"]["SPY"] == 25


def test_observability_and_complete_trade_schema(tmp_path):
    snap = SystemSnapshot("PAPER", "orb", "trend", {}, 0, 0, "OK", .7, None,
                          "ACTIVE", 0, 0, None, 0, None, "OK", "OK", "OK",
                          "2026-08-14T12:00:00Z")
    p = snapshot_html(snap, tmp_path/"status.html")
    assert p.exists() and "Serein" in p.read_text()
    rec = TradeJournalRecord("t", "SPY", "orb", "opening", "trend", "up", 1,
                             100, 99, 102, 2, .7, .2, 10, 10, {}, None, None,
                             None, None, "PENDING", "OPEN", "data", "code", "cfg")
    assert rec.to_dict()["instrument"] == "SPY"
