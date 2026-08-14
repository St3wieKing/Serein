#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from serein.certification import CertificationEvidence,write_certification
from serein.promotion import IntradayPromotionEvidence,evaluate_intraday_promotion
from serein.reproducibility import code_revision

e=IntradayPromotionEvidence(
 "opening_range_challenger_v1","HISTORICAL_PUBLIC_UNVERIFIED",8,-2.08,-1.0,-.0051,
 -.0035,-.0051,-.0041,-.0065,3,1,True,0,0,0)
g=evaluate_intraday_promotion(e)
c=CertificationEvidence(
 "opening_range_challenger_v1","1.0.0-selection-contaminated",None,
 code_revision(),"cc751830f538378815a8c0a3927f83eb3db163daa3c95404517f52efcc6bd2c4","HISTORICAL_PUBLIC_UNVERIFIED",
 "Selected after synthetic OOS ablation; frozen, then failed two sealed public external samples.",
 "Fresh public AAL/AMD/BAC last-40-session holdout: -0.28%, 8 trades, Sharpe -2.08.",
 "Prior synthetic results mixed; both public external samples were negative and insufficient.",
 "Expectancy -0.34R; confidence interval unavailable with eight trades.",
 "2x/5x costs, 2x slippage and one-bar latency all negative.",
 "2x cost return -0.35%.","2x slippage return -0.41%.",
 "Fresh public holdout max drawdown -0.51%.",
 "No approved model.","No real live feature stream.","0 weeks.",
 ("fresh replication failed","cost stress failed","slippage stress failed"),
 ("future leakage attack unexecuted","missing cluster unexecuted","drift unexecuted"),
 ("no real NBBO data","selection contamination","no paper feed","no legal/broker authorization"))
write_certification(ROOT/"docs"/"CERTIFICATION_CURRENT.md",c,g)
print("FAILED",g.failures)
