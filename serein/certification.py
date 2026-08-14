"""Trading-system certification report builder (paper gate only)."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from .promotion import GateResult


@dataclass(frozen=True)
class CertificationEvidence:
    strategy_id: str
    strategy_version: str
    model_id: str | None
    code_revision: str
    data_fingerprint: str
    evidence_class: str
    research_history: str
    backtest: str
    walk_forward: str
    oos: str
    stress: str
    costs: str
    slippage: str
    drawdown: str
    calibration: str
    drift: str
    paper: str
    failure_cases: tuple[str, ...]
    red_team_failures: tuple[str, ...]
    known_limitations: tuple[str, ...]


def certification_markdown(e: CertificationEvidence, gate: GateResult) -> str:
    status = "CERTIFIED_FOR_PAPER_CHAMPION_REVIEW" if gate.approved_for_paper_champion else "FAILED"
    rows = asdict(e)
    body = ["# Trading System Certification Report", "",
            f"**Status: {status}**", "",
            f"**Promotion failures:** {', '.join(gate.failures) or 'none'}", ""]
    for key, value in rows.items():
        label = key.replace("_", " ").title()
        if isinstance(value, (tuple, list)):
            value = "\n".join(f"- {x}" for x in value) or "- none"
        body += [f"## {label}", "", str(value), ""]
    body += ["## Authority boundary", "",
             "This report cannot enable live execution. It may only support a governed paper-stage review.", ""]
    return "\n".join(body)


def write_certification(path: str | Path, evidence: CertificationEvidence,
                        gate: GateResult) -> Path:
    p = Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(certification_markdown(evidence, gate)); return p
