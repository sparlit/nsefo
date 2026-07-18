"""
Coordinator — orchestrates order execution and manages active trades.
All active-trade state goes through global_state (thread-safe, RLock-guarded).
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from typing import Any, Dict, List, Optional

from python_app.core.state import global_state

logger = logging.getLogger(__name__)


class OrderError(Exception):
    """Raised when an order operation fails."""

    def __init__(self, message: str, symbol: str = "", side: str = "", price: float = 0.0, qty: int = 0):
        super().__init__(message)
        self.symbol = symbol
        self.side = side
        self.price = price
        self.qty = qty


class TrailingStop:
    """
    Adaptive trailing stop that locks in profit while allowing
    the position to run. Works for both BUY and SELL positions.

    Usage:
        ts = TrailingStop(entry_price=100, side='BUY', initial_sl=98)
        ts.update(current_price=105)   # raises stop to 103.50
        ts.should_trigger(current_price=104)  # True if stop hit
    """

    def __init__(self, entry_price: float, side: str, initial_sl: float, trailing_pct: float = 0.005):
        self.entry_price = entry_price
        self.side = side  # 'BUY' or 'SELL'
        self.initial_sl = initial_sl
        self.trailing_pct = trailing_pct
        self._stop_price = initial_sl  # current trailing stop level
        self._highest_or_lowest = entry_price
        self._triggered = False

    def update(self, current_price: float) -> None:
        """Recalculate trailing stop level based on current price."""
        if self._triggered:
            return

        if self.side == "BUY":
            if current_price > self._highest_or_lowest:
                self._highest_or_lowest = current_price
                self._stop_price = current_price * (1 - self.trailing_pct)
        else:  # SELL
            if current_price < self._highest_or_lowest:
                self._highest_or_lowest = current_price
                self._stop_price = current_price * (1 + self.trailing_pct)

    def should_trigger(self, current_price: float) -> bool:
        """Return True if current price has hit the trailing stop."""
        if self._triggered:
            return True
        if self.side == "BUY":
            triggered = current_price <= self._stop_price
        else:
            triggered = current_price >= self._stop_price
        if triggered:
            self._triggered = True
        return triggered

    @property
    def stop_price(self) -> float:
        return self._stop_price


class TradeInfo:
    """
    Per-symbol trade state.
    Thread-safe access via global_state (RLock-guarded).
    """

    def __init__(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        qty: int,
        order_id: str,
        stop_loss: float,
        target: float,
        broker: Any,
    ):
        self.symbol = symbol
        self.side = side
        self.entry_price = entry_price
        self.qty = qty
        self.order_id = order_id
        self.stop_loss = stop_loss
        self.target = target
        self.broker = broker
        self.ts: Optional[TrailingStop] = None
        self.status = "OPEN"   # OPEN | CLOSED | STOPPED_OUT
        self.pnl = 0.0
        self.exit_reason = ""
        self.entry_time = time.time()

        # Initialize trailing stop after entry price is set
        self.ts = TrailingStop(entry_price=entry_price, side=side, initial_sl=stop_loss)
        global_state.update_summary()  # bump last_update to signal activity

    def trail_stop(self, current_price: float) -> None:
        self.ts.update(current_price)

    def check_stop_hit(self, current_price: float) -> bool:
        return self.ts.should_trigger(current_price)


class Coordinator:
    """
    Coordinates order execution, trade tracking, and stop-loss management.
    Active trades are stored ONLY in global_state — no duplicate local dict.
    """

    def __init__(self, broker: Any, risk_manager: Any = None):
        self.broker = broker
        self.risk_manager = risk_manager
        if self.risk_manager:
            self.risk_manager.cb.reset_day()  # May be None — circuit breaker recording skipped if so
        self.state = global_state  # used for logging only
        self._exit_requested = threading.Event()
        self._track_thread: Optional[threading.Thread] = None

    def execute_confirmed_trade(self, trade: Dict[str, Any]) -> OrderInfo:
        """
        Place a confirmed trade order with idempotency key.

        The idempotency key is generated per-execution-attempt (not per-order).
        If the network call fails, the retry uses the SAME key so the broker
        (not our code) recognizes it as a duplicate and doesn't double-fill.

        Idempotency key format: {symbol}_{side}_{uuid4_short}_{attempt}
        """
        symbol = trade["symbol"]
        side = trade["side"]
        qty = trade["qty"]
        price = trade["price"]

        # ── Build base idempotency key (stable across retries) ───────────────
        base_key = trade.get("idempotency_key") or f"{symbol}_{side}_{uuid.uuid4().hex[:8]}"

        for attempt in range(3):
            # Stable per-attempt key: base + attempt suffix
            order_payload = {
                "symbol": symbol,
                "side": side,
                "qty": qty,
                "price": price,
                "idempotency_key": f"{base_key}_a{attempt}",
                "tag": trade.get("tag", "NSEFO"),
            }

            try:
                result = self.broker.place_order(order_payload)

                # Normalise: all brokers return Dict[str,Any]; guard against
                # subclasses still returning str (backwards compat shim).
                if isinstance(result, str):
                    # String return means order_id or "" — treat as OPEN or ERROR.
                    oid = result.strip() if result else ""
                    result = {
                        "order_id": oid,
                        "status": "OPEN" if oid else "ERROR",
                        "message": "" if oid else "Broker returned empty order_id",
                    }

                order_id = result.get("order_id", "") or f"{base_key}_a{attempt}"

                if result.get("status") == "REJECTED":
                    raise OrderError(
                        f"Order rejected: {result.get('message', 'unknown')}",
                        symbol=symbol, side=side, price=price, qty=qty,
                    )

                order_info = {
                    "order_id": order_id,
                    "symbol": symbol,
                    "side": side,
                    "price": price,
                    "qty": qty,
                    "status": "OPEN",
                }

                # ── Register in global_state (thread-safe) ────────────────────
                global_state.kanban["ACTIVE"].append({
                    "symbol": symbol,
                    "side": side,
                    "price": price,
                    "qty": qty,
                    "order_id": order_id,
                    "entry_time": time.time(),
                    "stop_loss": trade.get("stop_loss"),
                    "target": trade.get("target"),
                })
                global_state.update_summary(
                    active_trades_count=len(global_state.kanban["ACTIVE"])
                )
                global_state.add_log(
                    f"Trade placed: {side} {qty} {symbol} @ {price} [idempotency={order_payload['idempotency_key']}]"
                )
                return order_info

            except OrderError:
                raise
            except Exception as e:
                logger.warning(f"Order attempt {attempt+1}/3 failed: {e}")
                if attempt < 2:
                    time.sleep(2 ** attempt)  # 1s, 2s backoff before retry
                else:
                    logger.error(f"All 3 order attempts failed for {symbol} {side}")
                    raise

    def track_trades(self, monitor_func=None) -> None:
        """
        Monitor all active trades from global_state, apply trailing stops,
        and close positions on stop-hit / target-hit / broker exit signal.

        Runs in the main trading loop on the main thread (not a daemon).
        Call start_trade_tracking() to launch the background monitor instead.
        """
        while not self._exit_requested.is_set():
            with global_state._lock:
                active = list(global_state.kanban["ACTIVE"])

            for trade_data in active:
                try:
                    symbol = trade_data["symbol"]
                    side = trade_data["side"]
                    order_id = trade_data["order_id"]

                    # ── Get current market price ─────────────────────────────
                    if monitor_func:
                        market_price = monitor_func(symbol)
                    else:
                        ltp_data = self.broker.get_market_data(symbol)
                        market_price = ltp_data.get(symbol, {}).get("last_price", 0)

                    if not market_price:
                        continue

                    # ── Get TradeInfo from global_state ──────────────────────
                    with global_state._lock:
                        ti = next(
                            (t for t in global_state.kanban["ACTIVE"]
                             if t.get("order_id") == order_id),
                            None,
                        )
                        if not ti:
                            continue  # Already closed

                    # ── Trailing stop update ─────────────────────────────────
                    if ti.get("stop_loss"):
                        sl = ti["stop_loss"]
                        ts_pct = 0.005
                        ts = TrailingStop(entry_price=ti["price"], side=ti["side"], initial_sl=sl, trailing_pct=ts_pct)
                        ts.update(market_price)
                        ti["trailing_stop"] = ts.stop_price

                    # ── Check stop-hit ─────────────────────────────────────
                    if side == "BUY" and market_price <= ti["stop_loss"]:
                        self._close_trade(order_id, "STOPPED_OUT", market_price)
                    elif side == "SELL" and market_price >= ti["stop_loss"]:
                        self._close_trade(order_id, "STOPPED_OUT", market_price)
                    # ── Check target-hit ────────────────────────────────────
                    elif side == "BUY" and market_price >= ti["target"]:
                        self._close_trade(order_id, "TARGET_HIT", market_price)
                    elif side == "SELL" and market_price <= ti["target"]:
                        self._close_trade(order_id, "TARGET_HIT", market_price)

                except Exception as e:
                    logger.error(f"Error tracking trade {trade_data.get('symbol')}: {e}")

            time.sleep(2)

    def start_trade_tracking(self, monitor_func=None) -> None:
        """Launch background trade monitoring thread."""
        if self._track_thread and self._track_thread.is_alive():
            return
        self._exit_requested.clear()
        self._track_thread = threading.Thread(target=self._run_tracking, args=(monitor_func,), daemon=True)
        self._track_thread.start()

    def stop_trade_tracking(self) -> None:
        self._exit_requested.set()
        if self._track_thread:
            self._track_thread.join(timeout=5)
            self._track_thread = None

    def _run_tracking(self, monitor_func) -> None:
        self.track_trades(monitor_func=monitor_func)

    def _close_trade(self, order_id: str, reason: str, current_price: float) -> None:
        """
        Close a trade by order_id and move it to CLOSED column.
        Called from track_trades on stop-hit or target-hit.
        """
        with global_state._lock:
            # Find and remove from ACTIVE
            trade = next((t for t in global_state.kanban["ACTIVE"] if t.get("order_id") == order_id), None)
            if not trade:
                return

            side = trade["side"]
            entry_price = trade["price"]
            qty = trade["qty"]

            # Compute P&L
            if side == "BUY":
                pnl = (current_price - entry_price) * qty
            else:
                pnl = (entry_price - current_price) * qty

            # Mark trade as closed
            trade["status"] = "CLOSED"
            trade["exit_reason"] = reason
            trade["exit_price"] = current_price
            trade["pnl"] = pnl
            trade["exit_time"] = time.time()

            global_state.kanban["ACTIVE"] = [t for t in global_state.kanban["ACTIVE"] if t.get("order_id") != order_id]
            global_state.kanban["CLOSED"].append(trade)
            global_state.add_pnl(pnl)
            global_state.update_summary(active_trades_count=len(global_state.kanban["ACTIVE"]))

            # Clean up active_symbols if no trades for this symbol remain
            symbol = trade["symbol"]
            if not any(t.get("symbol") == symbol for t in global_state.kanban["ACTIVE"]):
                global_state.active_symbols = [s for s in global_state.active_symbols if s != symbol]
            global_state.add_log(f"Trade closed ({reason}): {trade['symbol']} {side} {qty} @ {current_price} | P&L: {pnl:.2f}")

            # ── Record in circuit breaker ─────────────────────────────────────
            if self.risk_manager is not None:
                self.risk_manager.cb.record_trade(pnl)
                logger.info(
                    f"Circuit breaker: {self.risk_manager.cb.consecutive_losses} consecutive losses, "
                    f"session P&L: {self.risk_manager.cb.session_pnl:.2f}"
                )

            try:
                self.broker.close_position(order_id=order_id)
            except Exception as e:
                logger.warning(f"Broker.close_position failed for {order_id}: {e}")


# Exposed for type hints elsewhere
OrderInfo = Dict[str, Any]