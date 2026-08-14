from serein.strategy_governance import CandidateEvidence, evaluate_challenger


def test_synthetic_candidate_cannot_promote():
    e = CandidateEvidence("pretty_backtest", "2.0", 1000, 3.0, -0.02, 2.0, 2.0)
    d = evaluate_challenger(e)
    assert not d.approved
    assert "real_data_required" in d.failures
    assert "pristine_holdout_required" in d.failures
    assert "paper_observation_required" in d.failures


def test_complete_paper_evidence_can_reach_candidate_stage():
    e = CandidateEvidence("locked", "2.1", 100, 0.8, -0.05, 0.3, 0.2,
                          real_point_in_time_data=True, pristine_holdout=True,
                          paper_weeks=12)
    d = evaluate_challenger(e)
    assert d.approved
    assert d.stage == "paper_champion_candidate"


def test_any_risk_breach_blocks_promotion():
    e = CandidateEvidence("unsafe", "2.1", 100, 0.8, -0.05, 0.3, 0.2,
                          True, True, 12, ("daily_limit",))
    assert not evaluate_challenger(e).approved
