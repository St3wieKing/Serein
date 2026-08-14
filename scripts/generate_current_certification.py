#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from serein.certification import CertificationEvidence,write_certification
from serein.promotion import IntradayPromotionEvidence,evaluate_intraday_promotion
from serein.reproducibility import code_revision

e=IntradayPromotionEvidence(
 "opening_range_challenger_v1","SYNTHETIC",55,-1.60,-.444,-.0054,
 -.0063,-1.0,-1.0,-1.0,3,4,True,0,1,0)
g=evaluate_intraday_promotion(e)
c=CertificationEvidence(
 "opening_range_challenger_v1","1.0.0-selection-contaminated",None,
 code_revision(),"SYNTH-FRESH-777","SYNTHETIC",
 "Selected after prior synthetic OOS ablation; frozen, then independently retested.",
 "Fresh synthetic return -0.53%, 55 trades, Sharpe -1.60.",
 "Prior walk-forward/seed results mixed.",
 "Mean expectancy -0.21R; 95% interval -0.44R to +0.05R.",
 "2x costs and 5x slippage both negative; multiple attacks not yet executed.",
 "2x cost return -0.63%.","5x slippage return -0.50%.",
 "Fresh synthetic max drawdown -0.53%; consecutive-loss risk halt occurred.",
 "No approved model.","No real live feature stream.","0 weeks.",
 ("fresh replication failed","cost stress failed","slippage stress failed"),
 ("future leakage attack unexecuted","missing cluster unexecuted","drift unexecuted"),
 ("no real NBBO data","selection contamination","no paper feed","no legal/broker authorization"))
write_certification(ROOT/"docs"/"CERTIFICATION_CURRENT.md",c,g)
print("FAILED",g.failures)
