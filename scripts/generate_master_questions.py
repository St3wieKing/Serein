#!/usr/bin/env python3
"""Generate and validate the master 520-question inquiry and 1,000 red-team challenge."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/"research"/"master_questions"
COUNTS = {
"Market Structure":50,"Day Trading":50,"Swing Trading":40,"Entries":50,
"Exits":50,"Risk":50,"Execution":40,"Data":30,"Machine Learning":30,
"Adaptation":30,"Overfitting":30,"Simplicity":20,"Portfolio construction":20,
"Failure modes":30,
}
TOPICS = {
"Market Structure":["spread formation","auction open","closing auction","order flow","liquidity holes","volatility clustering","cross-asset flow","price discovery","overnight gap","market impact"],
"Day Trading":["opening range","VWAP","trend day","range day","relative volume","time of day","breadth","gap continuation","failed breakout","session liquidation"],
"Swing Trading":["multi-day trend","overnight risk","earnings gap","volatility scaling","breakout persistence","carry","correlation","time stop","portfolio heat","regime transition"],
"Entries":["next-open entry","limit entry","market entry","pullback trigger","breakout trigger","reversal trigger","volume confirmation","breadth confirmation","minimum expected R","no-trade gate"],
"Exits":["structural stop","ATR stop","percentage stop","time stop","1R target","2R target","4R target","trailing stop","partial exit","session exit"],
"Risk":["risk per trade","daily loss","weekly loss","portfolio drawdown","gross exposure","net exposure","correlation","liquidity","gap loss","kill switch"],
"Execution":["commission","spread","slippage","impact","latency","partial fill","reject","duplicate","reconciliation","broker outage"],
"Data":["timestamp","timezone","duplicate","missing bar","bad OHLC","corporate action","survivorship","bid ask","staleness","fingerprint"],
"Machine Learning":["meta-label","feature causality","calibration","class imbalance","drift","training cutoff","purging","complexity","explainability","authority"],
"Adaptation":["rolling expectancy","regime weight","threshold update","quarantine","retraining","champion change","sample size","decay","recovery","retirement"],
"Overfitting":["strategy search","parameter search","model search","feature search","OOS reuse","PBO","deflated Sharpe","outlier dependence","period dependence","symbol dependence"],
"Simplicity":["rule removal","feature removal","model removal","filter removal","parameter count","dependency count","interpretability","maintenance","failure surface","core setup"],
"Portfolio construction":["risk parity","equal risk","correlation cluster","strategy allocation","cash allocation","capacity","turnover","rebalance","tail hedge","concentration"],
"Failure modes":["data outage","broker outage","model crash","clock error","state corruption","gap through stop","liquidity freeze","correlation spike","strategy decay","unauthorized request"],
}
LENSES=["existence","causality","incremental value","cost sensitivity","regime dependence","parameter stability","tail risk","operational safety","replication","falsification"]
POLICY={
"Market Structure":"Public OHLCV is an incomplete view of matching-engine state.",
"Day Trading":"Intraday edge must survive spread, latency and session-specific tests.",
"Swing Trading":"Overnight gaps and cross-position correlation dominate nominal stop risk.",
"Entries":"A setup is not an entry until a causal trigger and executable next price exist.",
"Exits":"Exit rules are evaluated on expectancy and tail control, not win rate alone.",
"Risk":"Risk is a deterministic ceiling that alpha cannot negotiate.",
"Execution":"Requested price is never assumed to equal an executable fill.",
"Data":"Unknown or corrupt data produces NO_TRADE, never repair by guess.",
"Machine Learning":"ML may veto an approved setup but cannot create risk authority.",
"Adaptation":"Adapt only on adequate evidence; one bad day changes nothing.",
"Overfitting":"Every search consumes statistical budget and contaminates viewed samples.",
"Simplicity":"A component survives only if removal materially harms robust OOS evidence.",
"Portfolio construction":"Allocate risk, not historical return, and model common failures.",
"Failure modes":"Critical uncertainty stops new entries while preserving reconciliation and exits.",
}


def master():
    lines=["# Master Inquiry — 520 Questions","", "Each record follows Question → Evidence → Hypothesis → Test → Result → Confidence → Decision. UNKNOWN is used where real evidence is absent.",""]
    q=0
    for cat,count in COUNTS.items():
        lines += [f"## {cat}",""]
        topics=TOPICS[cat]
        for i in range(count):
            q+=1; topic=topics[i%len(topics)]; lens=LENSES[(i//len(topics))%len(LENSES)]
            lines += [f"### M-Q{q:03d} — {cat}",
                f"**Question:** Under the {lens} lens, what evidence would prove or disprove that {topic} improves the system?",
                f"**Evidence:** {POLICY[cat]} Engineering controls exist, but licensed real point-in-time evidence for this exact question is **UNKNOWN** unless a sealed experiment says otherwise.",
                f"**Hypothesis:** A minimal, causal implementation of {topic} adds net risk-adjusted value only in a predeclared subset of conditions.",
                f"**Test:** Freeze the definition; compare baseline versus one-component change using purged walk-forward, a sealed OOS period, realistic costs, symbol/regime decomposition, perturbation and a removal test.",
                f"**Result:** NOT_RUN_ON_PRISTINE_REAL_DATA. Existing synthetic or public-account observations are engineering/hypothesis evidence only.",
                f"**Confidence:** LOW for market edge; HIGH for the requirement to fail closed and account for selection.",
                f"**Decision:** RESEARCH_MORE. Reject the component if the lower expectancy bound is non-positive or stress/replication fails.",""]
    assert q==520
    return "\n".join(lines)

ADV_CATS=["Strategy","Data","Execution","Risk","Psychology","Statistics","Models","Markets","Regimes","Software","Security","Failure"]
COMPONENTS=["opening-range signal","VWAP context","relative volume","breadth","structural stop","target","position sizing","daily halt","portfolio cap","kill switch","data loader","feature pipeline","meta-model","calibration","backtester","cost model","paper broker","experiment queue","holdout firewall","audit journal"]
ATTACKS=["stale input","future leakage","duplicate event","missing cluster","clock shift","spread explosion","slippage tail","latency spike","partial fill","rejection storm","gap through stop","correlation convergence","volatility shock","liquidity freeze","wrong symbol","extreme confidence","model crash","feature drift","concept drift","outlier removal","best-year removal","best-symbol removal","parameter plus 20 percent","parameter minus 20 percent","cost times five","restart during position","database lock","disk full","journal tamper","unauthorized promotion","risk override request","broker disagreement","account restriction","market halt","early close","DST transition","corporate action","short borrow failure","negative price input","zero volume","NaN feature","infinite quantity","integer overflow","memory pressure","network partition","retry duplication","alert failure","human absence","one bad day","twenty losses"]

def adversarial():
    lines=["# Final 1,000-Question Adversarial Challenge","", "Every record uses Question → Evidence → Answer → Confidence → Remaining uncertainty → Experiment. No proprietary or unobserved behavior is invented.",""]
    q=0
    for component in COMPONENTS:
        for attack in ATTACKS:
            q+=1; cat=ADV_CATS[(q-1)%len(ADV_CATS)]
            answer=("The safe default is to block new exposure, preserve protective exits, journal the event and reconcile external truth. "
                    "A favorable backtest is irrelevant if this path bypasses a hard control.")
            lines += [f"### A-Q{q:04d} — {cat}",
                f"**Question:** What happens when {attack} targets the {component}, and how could the apparent safety result be wrong?",
                f"**Evidence:** The repository contains deterministic controls and synthetic fault tests; the frequency and joint distribution of this event in future real trading is **UNKNOWN**.",
                f"**Answer:** {answer}",
                f"**Confidence:** HIGH in fail-closed policy; LOW to MODERATE in any numerical loss estimate without quote-level real data.",
                f"**Remaining uncertainty:** Common-mode dependencies, broker behavior, gap size and recovery time may exceed all observed samples.",
                f"**Experiment:** Inject {attack} before, during and after a proposed {component} action; assert no duplicate/unauthorized order, bounded recorded state, successful reconciliation and an immutable failure record.",""]
    assert q==1000
    return "\n".join(lines)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"master_520.md").write_text(master())
    (OUT/"adversarial_1000.md").write_text(adversarial())

if __name__=="__main__":main()
