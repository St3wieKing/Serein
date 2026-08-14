"""Shared constants: action space, model/strategy statuses, sessions, kill switches."""

from __future__ import annotations

# ---- Action space -----------------------------------------------------------
# Richer than BUY/SELL/NO_TRADE: the system must be able to do nothing,
# reduce, or exit. Actions are the ONLY vocabulary the execution layer accepts.
ACTION_STRONG_BUY = "STRONG_BUY"
ACTION_BUY = "BUY"
ACTION_WEAK_BUY = "WEAK_BUY"
ACTION_NO_TRADE = "NO_TRADE"
ACTION_WEAK_SELL = "WEAK_SELL"
ACTION_SELL = "SELL"
ACTION_STRONG_SELL = "STRONG_SELL"
ACTION_REDUCE = "REDUCE"
ACTION_EXIT = "EXIT"

ACTIONS = {
    ACTION_STRONG_BUY,
    ACTION_BUY,
    ACTION_WEAK_BUY,
    ACTION_NO_TRADE,
    ACTION_WEAK_SELL,
    ACTION_SELL,
    ACTION_STRONG_SELL,
    ACTION_REDUCE,
    ACTION_EXIT,
}

# Actions that open or add exposure (long side)
LONG_ACTIONS = {ACTION_STRONG_BUY, ACTION_BUY, ACTION_WEAK_BUY}
# Actions that open or add exposure (short side)
SHORT_ACTIONS = {ACTION_STRONG_SELL, ACTION_SELL, ACTION_WEAK_SELL}

# ---- Model / strategy lifecycle statuses -----------------------------------
STATUS_RESEARCH = "RESEARCH"
STATUS_VALIDATION = "VALIDATION"
STATUS_PAPER = "PAPER"
STATUS_APPROVED = "APPROVED"
STATUS_DEGRADED = "DEGRADED"
STATUS_QUARANTINED = "QUARANTINED"
STATUS_RETIRED = "RETIRED"

APPROVED_FOR_EXECUTION = {STATUS_APPROVED, STATUS_PAPER}

# ---- Experiment decisions --------------------------------------------------
DECISION_REJECTED = "REJECTED"
DECISION_DEFERRED = "DEFERRED"
DECISION_RESEARCH_MORE = "RESEARCH_MORE"
DECISION_PAPER_TEST = "PAPER_TEST"
DECISION_CHALLENGER = "CHALLENGER"
DECISION_APPROVED = "APPROVED"
DECISION_RETIRED = "RETIRED"

# ---- Kill switches ----------------------------------------------------------
KS_DATA = "DATA_KILL_SWITCH"
KS_EXECUTION = "EXECUTION_KILL_SWITCH"
KS_BROKER = "BROKER_KILL_SWITCH"
KS_MODEL = "MODEL_KILL_SWITCH"
KS_DRAWDOWN = "DRAWDOWN_KILL_SWITCH"
KS_SLIPPAGE = "SLIPPAGE_KILL_SWITCH"
KS_VOLATILITY = "VOLATILITY_KILL_SWITCH"
KS_ANOMALY = "ANOMALY_KILL_SWITCH"
KS_SYSTEM = "SYSTEM_HEALTH_KILL_SWITCH"

ALL_KILL_SWITCHES = (
    KS_DATA,
    KS_EXECUTION,
    KS_BROKER,
    KS_MODEL,
    KS_DRAWDOWN,
    KS_SLIPPAGE,
    KS_VOLATILITY,
    KS_ANOMALY,
    KS_SYSTEM,
)

# ---- Sessions (ET, approximate, for feature engineering) --------------------
SESSION_PRE = "premarket"
SESSION_OPEN = "open"
SESSION_MIDDAY = "midday"
SESSION_AFTERNOON = "afternoon"
SESSION_CLOSE = "close"
SESSION_POST = "postmarket"

# ---- Loss taxonomy (post-trade analysis) ------------------------------------
LOSS_GOOD = "GOOD_LOSS"                 # process followed, model was right to try
LOSS_BAD = "BAD_LOSS"                   # process violated
LOSS_MODEL_FAILURE = "MODEL_FAILURE"
LOSS_EXECUTION_FAILURE = "EXECUTION_FAILURE"
LOSS_RISK_FAILURE = "RISK_FAILURE"
LOSS_DATA_FAILURE = "DATA_FAILURE"
LOSS_UNEXPECTED_REGIME = "UNEXPECTED_REGIME"
LOSS_RANDOM_VARIANCE = "RANDOM_VARIANCE"

# ---- Exit reasons -----------------------------------------------------------
EXIT_STOP = "stop"
EXIT_TARGET = "target"
EXIT_STOP_GAP = "stop_gap"       # price gapped through the stop during missing bars
EXIT_TARGET_GAP = "target_gap"   # price gapped through the target during missing bars
EXIT_TRAIL = "trailing_stop"
EXIT_TIME = "max_holding_bars"
EXIT_SIGNAL = "signal_invalidation"
EXIT_SESSION = "session_close"
EXIT_RISK = "risk_forced"
EXIT_MANUAL = "manual"
