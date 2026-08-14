"""SQLite-backed autonomous research queue and journals."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .types import ExperimentProposal, ExperimentOutcome, ExperimentStatus


def now(): return datetime.now(timezone.utc).isoformat()


class AutonomyStore:
    def __init__(self, path: str | Path):
        self.path = Path(path); self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA foreign_keys=ON")
        self._schema()

    def _schema(self):
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS experiments(
          id TEXT PRIMARY KEY, status TEXT NOT NULL, priority REAL NOT NULL,
          proposal_json TEXT NOT NULL, outcome_json TEXT, created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS failures(
          id INTEGER PRIMARY KEY AUTOINCREMENT, failure_id TEXT UNIQUE NOT NULL,
          component TEXT NOT NULL, description TEXT NOT NULL, impact TEXT NOT NULL,
          root_cause TEXT NOT NULL, detection TEXT NOT NULL, fix TEXT NOT NULL,
          regression_test TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS decisions(
          id INTEGER PRIMARY KEY AUTOINCREMENT, decision_type TEXT NOT NULL,
          payload_json TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS budgets(
          dataset_id TEXT PRIMARY KEY, experiments INTEGER NOT NULL DEFAULT 0,
          parameters INTEGER NOT NULL DEFAULT 0, models INTEGER NOT NULL DEFAULT 0,
          strategies INTEGER NOT NULL DEFAULT 0, updated_at TEXT NOT NULL);
        """)
        self.db.commit()

    def enqueue(self, proposal: ExperimentProposal):
        payload = json.dumps(proposal.to_dict(), sort_keys=True, default=str)
        with self.db:
            self.db.execute("INSERT INTO experiments VALUES(?,?,?,?,?,?,?)",
                            (proposal.experiment_id, ExperimentStatus.QUEUED.value,
                             proposal.priority(), payload, None, now(), now()))
            self.db.execute("""INSERT INTO budgets(dataset_id,experiments,parameters,models,strategies,updated_at)
                VALUES(?,1,?,?,1,?) ON CONFLICT(dataset_id) DO UPDATE SET
                experiments=experiments+1, parameters=parameters+excluded.parameters,
                strategies=strategies+1, updated_at=excluded.updated_at""",
                (proposal.dataset_id, len(proposal.parameters),
                 int(any("model" in c.lower() or "ml" in c.lower() for c in proposal.components)), now()))

    def next(self):
        row = self.db.execute("SELECT * FROM experiments WHERE status=? ORDER BY priority DESC,created_at LIMIT 1",
                              (ExperimentStatus.QUEUED.value,)).fetchone()
        return dict(row) if row else None

    def transition(self, experiment_id: str, status: ExperimentStatus):
        allowed = {
            "QUEUED": {"RUNNING", "DEFERRED", "REJECTED"},
            "RUNNING": {"COMPLETED", "FAILED", "REJECTED"},
            "DEFERRED": {"QUEUED", "REJECTED"},
        }
        row = self.db.execute("SELECT status FROM experiments WHERE id=?", (experiment_id,)).fetchone()
        if not row: raise KeyError(experiment_id)
        if status.value not in allowed.get(row["status"], set()):
            raise ValueError(f"illegal experiment transition {row['status']} -> {status.value}")
        with self.db:
            self.db.execute("UPDATE experiments SET status=?,updated_at=? WHERE id=?",
                            (status.value, now(), experiment_id))

    def record_outcome(self, outcome: ExperimentOutcome):
        row = self.db.execute("SELECT status FROM experiments WHERE id=?", (outcome.experiment_id,)).fetchone()
        if not row: raise KeyError(outcome.experiment_id)
        if row["status"] != ExperimentStatus.RUNNING.value:
            raise ValueError("outcome requires RUNNING experiment")
        with self.db:
            self.db.execute("UPDATE experiments SET status=?,outcome_json=?,updated_at=? WHERE id=?",
                            (outcome.status.value, json.dumps(outcome.to_dict(), sort_keys=True, default=str),
                             now(), outcome.experiment_id))

    def budget(self, dataset_id: str):
        row = self.db.execute("SELECT * FROM budgets WHERE dataset_id=?", (dataset_id,)).fetchone()
        return dict(row) if row else {"dataset_id": dataset_id, "experiments": 0,
                                     "parameters": 0, "models": 0, "strategies": 0}

    def record_failure(self, *, failure_id, component, description, impact,
                       root_cause="UNKNOWN", detection="UNKNOWN", fix="OPEN",
                       regression_test="MISSING"):
        with self.db:
            self.db.execute("INSERT INTO failures(failure_id,component,description,impact,root_cause,detection,fix,regression_test,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                            (failure_id, component, description, impact, root_cause,
                             detection, fix, regression_test, now()))

    def record_decision(self, decision_type: str, payload: dict):
        with self.db:
            self.db.execute("INSERT INTO decisions(decision_type,payload_json,created_at) VALUES(?,?,?)",
                            (decision_type, json.dumps(payload, sort_keys=True, default=str), now()))

    def counts(self):
        return {r["status"]: r["n"] for r in self.db.execute(
            "SELECT status,COUNT(*) n FROM experiments GROUP BY status")}

    def close(self): self.db.close()
