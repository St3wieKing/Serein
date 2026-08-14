"""Tamper-evident append-only decision journal."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def canonical_json(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


class HashChainJournal:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def read(self):
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text().splitlines() if line.strip()]

    def append(self, event_type: str, payload: dict):
        records = self.read()
        prev = records[-1]["hash"] if records else "GENESIS"
        body = {"sequence": len(records), "timestamp": datetime.now(timezone.utc).isoformat(),
                "event_type": event_type, "payload": payload, "previous_hash": prev}
        body["hash"] = hashlib.sha256(canonical_json(body).encode()).hexdigest()
        with self.path.open("a") as f:
            f.write(canonical_json(body)+"\n")
        return body

    def verify(self):
        prev = "GENESIS"
        for i, record in enumerate(self.read()):
            if record.get("sequence") != i or record.get("previous_hash") != prev:
                return False
            supplied = record.get("hash")
            body = {k: v for k, v in record.items() if k != "hash"}
            if hashlib.sha256(canonical_json(body).encode()).hexdigest() != supplied:
                return False
            prev = supplied
        return True
