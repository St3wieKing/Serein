"""Persistent holdout-contamination firewall.

A holdout that has been inspected cannot become pristine again. The ledger is
append-only and hash chained; it records process discipline, not secrecy.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path


def _canonical(x) -> str:
    return json.dumps(x, sort_keys=True, separators=(",", ":"), default=str)


@dataclass(frozen=True)
class HoldoutRecord:
    dataset_id: str
    fingerprint: str
    start: str
    end: str
    purpose: str
    status: str = "SEALED"


class HoldoutFirewall:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _events(self):
        if not self.path.exists():
            return []
        return [json.loads(x) for x in self.path.read_text().splitlines() if x.strip()]

    def _append(self, event: dict):
        events = self._events()
        previous = events[-1]["event_hash"] if events else "GENESIS"
        body = {**event, "recorded_at": datetime.now(timezone.utc).isoformat(),
                "previous_hash": previous}
        body["event_hash"] = hashlib.sha256(_canonical(body).encode()).hexdigest()
        with self.path.open("a") as f:
            f.write(_canonical(body)+"\n")
        return body

    def register(self, record: HoldoutRecord):
        if any(e.get("dataset_id") == record.dataset_id for e in self._events()):
            raise ValueError(f"dataset_id already registered: {record.dataset_id}")
        if record.status != "SEALED":
            raise ValueError("new holdout must be SEALED")
        return self._append({"event": "REGISTER", **asdict(record)})

    def reveal(self, dataset_id: str, *, experiment_id: str, reason: str):
        self.assert_pristine(dataset_id)
        return self._append({"event": "REVEAL", "dataset_id": dataset_id,
                             "experiment_id": experiment_id, "reason": reason,
                             "status": "REVEALED"})

    def retire(self, dataset_id: str, reason: str):
        self._find(dataset_id)
        return self._append({"event": "RETIRE", "dataset_id": dataset_id,
                             "reason": reason, "status": "RETIRED"})

    def _find(self, dataset_id):
        events = [e for e in self._events() if e.get("dataset_id") == dataset_id]
        if not events:
            raise KeyError(dataset_id)
        return events

    def status(self, dataset_id: str) -> str:
        events = self._find(dataset_id)
        for e in reversed(events):
            if "status" in e:
                return e["status"]
        return "UNKNOWN"

    def assert_pristine(self, dataset_id: str):
        status = self.status(dataset_id)
        if status != "SEALED":
            raise RuntimeError(f"holdout {dataset_id} is {status}, not pristine")

    def verify_chain(self) -> bool:
        previous = "GENESIS"
        for event in self._events():
            if event.get("previous_hash") != previous:
                return False
            supplied = event.get("event_hash")
            body = {k: v for k, v in event.items() if k != "event_hash"}
            if hashlib.sha256(_canonical(body).encode()).hexdigest() != supplied:
                return False
            previous = supplied
        return True
