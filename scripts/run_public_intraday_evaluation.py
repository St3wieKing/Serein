#!/usr/bin/env python3
"""One-shot sealed evaluation on public, unverified real intraday bars."""
from pathlib import Path
import argparse,json,sys
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from serein.backtest.engine import Backtester
from serein.backtest.stress import stress_costs,stress_slippage,stress_latency
from serein.backtest.uncertainty import trade_expectancy_bootstrap
from serein.data.intraday_csv import load_intraday_csv
from serein.holdout import HoldoutFirewall,HoldoutRecord
from serein.reproducibility import universe_fingerprint
from serein.strategies.institutional_intraday import OpeningRangeChallenger
from scripts.run_institutional_intraday import config


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--path',default='artifacts/public_intraday_5min.csv')
    ap.add_argument('--dataset-id',default='PUBLIC-UNVERIFIED-2020-21-LAST40')
    ap.add_argument('--doc',default='docs/PUBLIC_INTRADAY_EVALUATION.md')
    args=ap.parse_args()
    artifacts=ROOT/'artifacts'; path=ROOT/args.path
    bars,quality=load_intraday_csv(path,source_timezone='America/New_York',
                                   require_complete_sessions=True)
    dates=pd.DatetimeIndex(sorted(next(iter(bars.values())).index.normalize().unique()))
    test_dates=dates[-40:]; start=test_dates[0]
    hold_bars={s:b[b.index>=start] for s,b in bars.items()}
    fp=universe_fingerprint(hold_bars); ledger=artifacts/f'{args.dataset_id}-holdout.jsonl'
    if ledger.exists(): ledger.unlink() # one-shot script artifact recreation
    fw=HoldoutFirewall(ledger); fw.register(HoldoutRecord(args.dataset_id,fp,
        str(start),str(dates[-1]),'external frozen OR evaluation'))
    sig=OpeningRangeChallenger().generate_universe(bars)
    fw.reveal(args.dataset_id,experiment_id=f'{args.dataset_id}-ORB',reason='one final evaluation')
    cfg=config(); result=Backtester(cfg).run(hold_bars,sig);m=result.metrics
    c=stress_costs(hold_bars,sig,cfg,multipliers=(1,2,5));s=stress_slippage(hold_bars,sig,cfg,multipliers=(1,2));l=stress_latency(hold_bars,sig,cfg,delays=(0,1))
    unc=trade_expectancy_bootstrap(result.trades,n_boot=5000,seed=9)
    decision='REJECTED'
    reasons=[]
    if m['n_trades']<100:reasons.append('fewer than 100 OOS trades')
    if m['profit_factor']<=1.1:reasons.append('profit factor gate')
    if unc.get('ci95',[-1])[0]<=0:reasons.append('expectancy lower bound not positive')
    if c.loc[c.shock=='costs x2','total_return'].iloc[0]<=0:reasons.append('2x costs failed')
    if s.loc[s.shock=='slippage x2','total_return'].iloc[0]<=0:reasons.append('2x slippage failed')
    reasons += ['public source is unverified/revised and has no bid-ask quotes','no paper-forward evidence']
    report=f"""# Public Intraday External Evaluation

**Evidence:** real historical trade bars from a public GitHub repository that
states Alpha Vantage provenance; source files were malformed concatenations and
were strictly cleaned. Source: `chemicoPy/SP500-data` on GitHub. The repository
does not establish institutional data quality or NBBO provenance. This is
UNVERIFIED research data, not licensed NBBO.

**Holdout:** last 40 common complete sessions, sealed then revealed once.  
**Fingerprint:** `{fp}`  
**Ledger valid:** {fw.verify_chain()}  
**Decision:** **{decision}** — {', '.join(reasons)}.

## Data report

```json
{json.dumps(quality.to_dict(),indent=2)}
```

## Baseline result

- Symbols: {', '.join(bars)}
- Trades: {m['n_trades']}
- Return: {m['total_return']:.2%}
- Sharpe: {m['sharpe']:.2f}
- Profit factor: {m['profit_factor']:.2f}
- Expectancy: {m['expectancy_r']:.2f}R
- Max drawdown: {m['max_drawdown']:.2%}
- Costs: ${m['costs_total']:.2f}

## Uncertainty

```json
{json.dumps(unc,indent=2)}
```

## Cost stress

{c.to_markdown(index=False)}

## Slippage stress

{s.to_markdown(index=False)}

## Latency stress

{l.to_markdown(index=False)}

This holdout is now contaminated and cannot be reused for tuning.
"""
    (artifacts/f'{args.dataset_id}-report.md').write_text(report)
    (ROOT/args.doc).write_text(report)
    print(report)
if __name__=='__main__':main()
