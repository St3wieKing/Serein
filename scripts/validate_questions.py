"""Validate the Research Decision Log: question counts per category.

Usage: .venv/bin/python scripts/validate_questions.py
Exits non-zero if any category is below its required minimum.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REQUIREMENTS = {
    "01_market": 40,
    "02_strategy": 50,
    "03_risk": 40,
    "04_machine_learning": 40,
    "05_backtesting": 30,
    "06_execution": 25,
    "07_data": 20,
    "08_architecture": 20,
    "09_adaptation": 20,
    "10_security": 15,
    "11_monitoring": 15,
    "12_failure_modes": 20,
}

Q_RE = re.compile(r"^\*\*Q(\d+)\.\*\*")


def count_questions(path: Path) -> int:
    n = 0
    for line in path.read_text().splitlines():
        m = Q_RE.match(line.strip())
        if m:
            n += 1
    return n


def main() -> int:
    log_dir = Path(__file__).resolve().parent.parent / "research" / "decision_log"
    total = 0
    ok = True
    print(f"{'category':<24}{'found':>6}{'required':>10}  status")
    for name, required in REQUIREMENTS.items():
        path = log_dir / f"{name}.md"
        if not path.exists():
            print(f"{name:<24}{0:>6}{required:>10}  MISSING FILE")
            ok = False
            continue
        n = count_questions(path)
        total += n
        status = "OK" if n >= required else "BELOW MINIMUM"
        if n < required:
            ok = False
        print(f"{name:<24}{n:>6}{required:>10}  {status}")
    print(f"\nTOTAL: {total} questions (required >= {sum(REQUIREMENTS.values())})")
    if total < sum(REQUIREMENTS.values()):
        ok = False
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
