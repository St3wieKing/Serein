#!/usr/bin/env python3
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
pat = re.compile(r"^\*\*R(\d)-Q(\d{3})\.")
all_questions = []
for rnd in (1, 2, 3):
    p = ROOT/"research"/"recursive_review"/f"round_{rnd}_500.md"
    lines = p.read_text().splitlines()
    found = [(int(m.group(1)), int(m.group(2)), i) for i, line in enumerate(lines)
             if (m := pat.match(line))]
    answers = sum(line.startswith("**Answer:**") for line in lines)
    ids = [q for r, q, _ in found]
    assert len(found) == 500, (p, len(found))
    assert ids == list(range(1, 501)), (p, "nonsequential")
    assert answers == 500, (p, answers)
    all_questions.extend(lines[i] for _, _, i in found)
    print(f"round {rnd}: 500 questions, 500 answers, PASS")
assert len(set(all_questions)) == 1500, "questions are not globally unique"
print("TOTAL: 1500 unique questions, 1500 answers, PASS")
