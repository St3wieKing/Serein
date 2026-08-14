"""Experiment & model registries (append-only JSONL).

Every experiment and every model gets a permanent record. Nothing can be
"deleted" — a bad experiment is marked REJECTED, a bad model QUARANTINED.
This is what makes the research process auditable.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from . import constants as C


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class JsonlRegistry:
    """Minimal append-only JSONL registry."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.touch()

    def append(self, record: dict) -> str:
        rid = record.get("id") or uuid.uuid4().hex[:12]
        record["id"] = rid
        record["recorded_at"] = now_iso()
        with open(self.path, "a") as f:
            f.write(json.dumps(record, default=str) + "\n")
        return rid

    def load(self) -> list[dict]:
        rows = []
        if not self.path.exists():
            return rows
        with open(self.path) as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        return rows

    def get(self, rid: str) -> dict | None:
        for r in self.load():
            if r.get("id") == rid:
                return r
        return None

    def count(self) -> int:
        return len(self.load())

    def status_counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for r in self.load():
            s = r.get("status") or r.get("decision") or "UNKNOWN"
            out[s] = out.get(s, 0) + 1
        return out


class ExperimentRegistry(JsonlRegistry):
    """Experiments: hypothesis -> dataset -> model -> results -> decision."""

    REQUIRED = ("hypothesis", "dataset", "features", "model", "parameters",
                "training_period", "validation_period", "oos_period", "costs",
                "results", "drawdown", "robustness", "failure_cases", "decision")

    def append_experiment(self, exp: dict) -> str:
        missing = [k for k in self.REQUIRED if k not in exp]
        if missing:
            raise ValueError(f"experiment missing required fields: {missing}")
        if exp["decision"] not in (C.DECISION_REJECTED, C.DECISION_DEFERRED,
                                   C.DECISION_RESEARCH_MORE, C.DECISION_PAPER_TEST,
                                   C.DECISION_CHALLENGER, C.DECISION_APPROVED,
                                   C.DECISION_RETIRED):
            raise ValueError(f"invalid decision: {exp['decision']}")
        return self.append(exp)


class ModelRegistry(JsonlRegistry):
    """Models: governance metadata + lifecycle status."""

    def register(self, rec: dict) -> str:
        if rec.get("status") not in (C.STATUS_RESEARCH, C.STATUS_VALIDATION,
                                     C.STATUS_PAPER, C.STATUS_APPROVED,
                                     C.STATUS_DEGRADED, C.STATUS_QUARANTINED,
                                     C.STATUS_RETIRED):
            raise ValueError(f"invalid status: {rec.get('status')}")
        return self.append(rec)

    def transition(self, rid: str, new_status: str, reason: str = "") -> dict | None:
        """Governed status transition with audit trail."""
        allowed = {
            C.STATUS_RESEARCH: {C.STATUS_VALIDATION, C.STATUS_RETIRED},
            C.STATUS_VALIDATION: {C.STATUS_PAPER, C.STATUS_QUARANTINED, C.STATUS_RETIRED},
            C.STATUS_PAPER: {C.STATUS_APPROVED, C.STATUS_DEGRADED, C.STATUS_QUARANTINED, C.STATUS_RETIRED},
            C.STATUS_APPROVED: {C.STATUS_DEGRADED, C.STATUS_QUARANTINED, C.STATUS_RETIRED},
            C.STATUS_DEGRADED: {C.STATUS_QUARANTINED, C.STATUS_RESEARCH, C.STATUS_RETIRED},
            C.STATUS_QUARANTINED: {C.STATUS_RESEARCH, C.STATUS_RETIRED},
            C.STATUS_RETIRED: set(),
        }
        rec = self.get(rid)
        if rec is None:
            return None
        if new_status not in allowed.get(rec.get("status"), set()):
            raise ValueError(
                f"illegal transition {rec.get('status')} -> {new_status} for model {rid}")
        rec["status"] = new_status
        rec.setdefault("audit_trail", []).append({
            "at": now_iso(), "to": new_status, "reason": reason,
        })
        # append a new line with updated status (append-only semantics)
        self.append({k: v for k, v in rec.items() if k != "id"})
        return rec
