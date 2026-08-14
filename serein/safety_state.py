"""Atomic persistent safety state for paper-process restart decisions."""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class SafetySnapshot:
    mode: str
    data_healthy: bool
    broker_healthy: bool
    kill_switches: tuple[str, ...]
    open_positions: tuple[str, ...]
    last_reconciled_at: str


class SafetyStateStore:
    def __init__(self, path: str | Path):
        self.path = Path(path); self.path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _checksum(payload):
        return hashlib.sha256(json.dumps(payload, sort_keys=True,
                                         separators=(",", ":")).encode()).hexdigest()

    def save(self, snapshot: SafetySnapshot):
        payload = asdict(snapshot)
        record = {"payload": payload, "checksum": self._checksum(payload),
                  "written_at": datetime.now(timezone.utc).isoformat()}
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=self.path.name+".")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(record, f, sort_keys=True); f.flush(); os.fsync(f.fileno())
            os.replace(tmp, self.path)
        finally:
            if os.path.exists(tmp): os.unlink(tmp)

    def load(self) -> SafetySnapshot:
        try:
            record = json.loads(self.path.read_text())
            payload = record["payload"]
        except Exception as e:
            raise RuntimeError("safety state missing or unreadable") from e
        if record.get("checksum") != self._checksum(payload):
            raise RuntimeError("safety state checksum mismatch")
        payload["kill_switches"] = tuple(payload["kill_switches"])
        payload["open_positions"] = tuple(payload["open_positions"])
        return SafetySnapshot(**payload)

    def startup_action(self) -> str:
        """Only a reconciled, healthy, flat PAPER state can resume entries."""
        try:
            s = self.load()
        except RuntimeError:
            return "HALT_AND_RECONCILE"
        if s.mode != "PAPER" or not s.data_healthy or not s.broker_healthy:
            return "HALT_AND_RECONCILE"
        if s.kill_switches or s.open_positions:
            return "HALT_AND_RECONCILE"
        return "PAPER_ENTRIES_ALLOWED"
