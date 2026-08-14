"""Capability separation: no agent has end-to-end strategy/risk/deploy power."""
from enum import Enum


class Role(str, Enum):
    RESEARCH = "RESEARCH"
    EXPERIMENT = "EXPERIMENT"
    RED_TEAM = "RED_TEAM"
    REVIEW = "REVIEW"
    TRADING = "TRADING"
    RISK = "RISK"
    EXECUTION = "EXECUTION"
    ADMIN = "ADMIN"


CAPABILITIES = {
    Role.RESEARCH: {"propose_hypothesis", "read_research"},
    Role.EXPERIMENT: {"run_offline_experiment", "write_experiment_result"},
    Role.RED_TEAM: {"run_offline_attack", "quarantine_recommendation"},
    Role.REVIEW: {"review_evidence", "recommend_gate_review"},
    Role.TRADING: {"scan_market", "propose_order"},
    Role.RISK: {"approve_order", "deny_order", "tighten_limit", "trip_kill_switch"},
    Role.EXECUTION: {"submit_paper_order", "cancel_paper_order", "reconcile_paper"},
    Role.ADMIN: {"authorize_reset", "approve_paper_stage"},
}

PROHIBITED = {"enable_live_execution", "loosen_risk_limit", "erase_audit",
              "mark_revealed_holdout_pristine", "bypass_account_authorization"}


def authorized(role: Role, capability: str) -> bool:
    if capability in PROHIBITED: return False
    return capability in CAPABILITIES[role]


def require(role: Role, capability: str):
    if not authorized(role, capability):
        raise PermissionError(f"{role.value} is not authorized for {capability}")
