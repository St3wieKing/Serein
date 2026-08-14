#!/usr/bin/env python3
import re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
checks=[("master_520.md",r"^### M-Q\d{3}",520,["Question","Evidence","Hypothesis","Test","Result","Confidence","Decision"]),
        ("adversarial_1000.md",r"^### A-Q\d{4}",1000,["Question","Evidence","Answer","Confidence","Remaining uncertainty","Experiment"])]
for name,pattern,n,fields in checks:
    text=(ROOT/"research"/"master_questions"/name).read_text()
    found=len(re.findall(pattern,text,re.M)); assert found==n,(name,found)
    for field in fields:
        count=text.count(f"**{field}:**"); assert count==n,(name,field,count)
    print(f"{name}: {n} records with complete schema, PASS")
print("TOTAL: 1,520 structured research records, PASS")
