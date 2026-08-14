#!/usr/bin/env python3
"""Clean public Alpha-Vantage-derived CSV fragments for research only.

The source repository files contain concatenated monthly CSV responses and API
error JSON. This script accepts only structurally valid rows, aggregates to five
minutes, and retains dates complete for every requested symbol. Source data are
not redistributed and remain unverified/non-production evidence.
"""
from __future__ import annotations
import argparse,csv
from pathlib import Path
import pandas as pd


def clean(path,symbol):
    rows=[]
    with open(path,newline='',errors='ignore') as f:
        for r in csv.reader(f):
            if len(r)==6 and r[0][:4].isdigit(): rows.append(r)
    d=pd.DataFrame(rows,columns=['timestamp','open','high','low','close','volume'])
    d.timestamp=pd.to_datetime(d.timestamp,errors='coerce')
    for c in ['open','high','low','close','volume']: d[c]=pd.to_numeric(d[c],errors='coerce')
    d=d.dropna().drop_duplicates('timestamp').sort_values('timestamp').set_index('timestamp')
    d=d.between_time('09:30','15:59')
    d=d.resample('5min').agg({'open':'first','high':'max','low':'min','close':'last','volume':'sum'}).dropna()
    counts=d.groupby(d.index.normalize()).size(); good=counts[counts==78].index
    d=d[d.index.normalize().isin(good)].copy();d['symbol']=symbol
    return d.reset_index()


def main():
    p=argparse.ArgumentParser();p.add_argument('--input',action='append',required=True,
        help='SYMBOL=path; repeat');p.add_argument('--out',default='artifacts/public_intraday_5min.csv')
    frames=[]
    for item in p.parse_args().input:
        sym,path=item.split('=',1);frames.append(clean(path,sym))
    common=set(frames[0].timestamp.dt.normalize())
    for f in frames[1:]:common &= set(f.timestamp.dt.normalize())
    frames=[f[f.timestamp.dt.normalize().isin(common)] for f in frames]
    out=pd.concat(frames).sort_values(['timestamp','symbol'])
    path=Path(p.parse_args().out);path.parent.mkdir(exist_ok=True);out.to_csv(path,index=False)
    print({'symbols':[x.split('=',1)[0] for x in p.parse_args().input],
           'common_days':len(common),'rows':len(out),'start':str(out.timestamp.min()),
           'end':str(out.timestamp.max()),'out':str(path)})
if __name__=='__main__':main()
