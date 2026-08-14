#!/usr/bin/env python3
"""Run one bounded autonomous offline research cycle on fresh synthetic data."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))

from serein.autonomy.authority import Role, authorized
from serein.autonomy.orchestrator import AutonomousResearchLoop
from serein.autonomy.store import AutonomyStore
from serein.backtest.engine import Backtester
from serein.backtest.stress import stress_costs, stress_slippage
from serein.backtest.uncertainty import trade_expectancy_bootstrap
from serein.data.intraday_synthetic import generate_intraday_universe
from serein.safety_state import SafetyStateStore
from serein.strategies.institutional_intraday import OpeningRangeChallenger
from scripts.run_institutional_intraday import config


def main():
    artifacts=ROOT/"artifacts"; artifacts.mkdir(exist_ok=True)
    db=AutonomyStore(artifacts/"autonomy.db")
    loop=AutonomousResearchLoop(db,max_experiments_per_dataset=20)
    dataset_id="SYNTH-FRESH-777"
    loop.propose_next({"issue":"fresh holdout required","n_trades":0},dataset_id=dataset_id)

    def runner(proposal, attacks):
        bars,_=generate_intraday_universe(["SPY","QQQ","IWM"],days=160,seed=777,start="2023-01-03")
        sig=OpeningRangeChallenger().generate_universe(bars); cfg=config()
        res=Backtester(cfg).run(bars,sig); m=res.metrics
        c=stress_costs(bars,sig,cfg,multipliers=(2,)); s=stress_slippage(bars,sig,cfg,multipliers=(5,))
        ci=trade_expectancy_bootstrap(res.trades,n_boot=1000,seed=7)
        # Only attacks actually exercised here are marked passed. Untested
        # attacks fail rather than receiving optimistic assumptions.
        actual={a.name:False for a in attacks}
        actual["cost_expansion"]=bool(c.total_return.iloc[0]>0)
        actual["slippage_tail"]=bool(s.total_return.iloc[0]>0)
        actual["authority_escalation"]=not authorized(Role.TRADING,"loosen_risk_limit")
        actual["restart_corruption"]=SafetyStateStore(artifacts/"missing-state.json").startup_action()=="HALT_AND_RECONCILE"
        metrics={"oos_trades":m["n_trades"],"return":m["total_return"],
                 "sharpe":m["sharpe"],"max_drawdown":m["max_drawdown"],
                 "expectancy_ci_low":ci.get("ci95",[-1])[0],"confidence":"LOW_SYNTHETIC"}
        robustness={"cost2_return":float(c.total_return.iloc[0]),
                    "slippage5_return":float(s.total_return.iloc[0]),"uncertainty":ci}
        failures=tuple(k for k,v in actual.items() if not v)
        return metrics,robustness,failures,actual

    result=loop.run_one(runner,evidence_class="SYNTHETIC",holdout_pristine=True)
    # Failure initiates the next bounded research queue automatically. It does
    # not mutate or promote a strategy against the same holdout.
    m=result[0].metrics
    followups=loop.propose_next({"weak_setup":"opening_breakout",
                                 "issue":"fresh replication and cost stress failed",
                                 "n_trades":m.get("oos_trades",0)},
                                dataset_id="FRESH-DATASET-REQUIRED")
    payload={"outcome":result[0].to_dict(),"review":result[1].__dict__ if result[1] else None,
             "followup_queue":[p.to_dict() for p in followups],
             "counts":db.counts(),"tested_budget":db.budget(dataset_id),
             "next_dataset_budget":db.budget("FRESH-DATASET-REQUIRED")}
    (artifacts/"autonomous_cycle_report.json").write_text(json.dumps(payload,indent=2,default=str))
    print(json.dumps(payload,indent=2,default=str)); db.close()

if __name__=="__main__":main()
