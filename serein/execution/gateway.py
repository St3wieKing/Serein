"""Paper-only execution gateway with validation, idempotency and journaling."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math

from .. import PAPER_TRADING_ONLY, LIVE_EXECUTION_ENABLED
from ..audit_journal import HashChainJournal
from .broker import BrokerInterface, Order
from .validation import OrderValidator


@dataclass(frozen=True)
class OrderIntent:
    intent_id: str
    symbol: str
    direction: int
    qty: int
    price: float
    strategy_id: str
    model_id: str | None
    confidence: float
    expected_r: float
    stop: float
    target: float


class PaperExecutionGateway:
    def __init__(self, broker: BrokerInterface, validator: OrderValidator,
                 journal: HashChainJournal, *, approved_strategies: set[str],
                 approved_models: set[str], account_authorized: bool = True):
        if LIVE_EXECUTION_ENABLED or not PAPER_TRADING_ONLY:
            raise RuntimeError("repository safety invariant violated")
        self.broker = broker; self.validator = validator; self.journal = journal
        self.approved_strategies = approved_strategies; self.approved_models = approved_models
        self.account_authorized = account_authorized; self.seen_intents = set()

    def submit(self, intent: OrderIntent, *, quote, equity, data_fresh,
               market_open, broker_healthy, daily_loss_halted,
               weekly_loss_halted, risk_new_trades_allowed, bar_volume=None,
               now=None):
        if intent.intent_id in self.seen_intents:
            self.journal.append("ORDER_DENIED", {"intent_id": intent.intent_id,
                                                 "reason": "duplicate_intent"})
            return None
        self.seen_intents.add(intent.intent_id)
        intent_valid = (intent.direction in (-1, 1) and intent.qty > 0
                        and math.isfinite(intent.confidence) and 0 <= intent.confidence <= 1
                        and math.isfinite(intent.expected_r) and intent.expected_r > 0
                        and math.isfinite(intent.stop) and math.isfinite(intent.target)
                        and (intent.price-intent.stop)*intent.direction > 0
                        and (intent.target-intent.price)*intent.direction > 0)
        if not intent_valid:
            self.journal.append("ORDER_DENIED", {"intent_id": intent.intent_id,
                                                 "reason": "malformed_intent"})
            return None
        strategy_ok = intent.strategy_id in self.approved_strategies
        model_ok = intent.model_id is None or intent.model_id in self.approved_models
        res = self.validator.validate(
            symbol=intent.symbol, direction=intent.direction, qty=intent.qty,
            price=intent.price, quote=quote, positions=self.broker.get_positions(),
            open_orders=self.broker.get_orders(), equity=equity, data_fresh=data_fresh,
            market_open=market_open, broker_healthy=broker_healthy,
            model_approved=model_ok, strategy_approved=strategy_ok,
            account_authorized=self.account_authorized,
            daily_loss_halted=daily_loss_halted, weekly_loss_halted=weekly_loss_halted,
            risk_new_trades_allowed=risk_new_trades_allowed, bar_volume=bar_volume,
            now=now, quote_required=True)
        self.journal.append("PRETRADE_VALIDATION", {"intent": asdict(intent),
                                                    "checks": res.checks, "ok": res.ok})
        if not res.ok: return None
        order = Order(order_id="", symbol=intent.symbol,
                      side="buy" if intent.direction > 0 else "sell", qty=intent.qty,
                      idempotency_key=intent.intent_id)
        filled = self.broker.submit_order(order)
        self.journal.append("PAPER_ORDER_RESULT", {"intent_id": intent.intent_id,
                                                   "order_id": filled.order_id,
                                                   "status": filled.status,
                                                   "reject_reason": filled.reject_reason})
        return filled
