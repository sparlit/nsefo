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

                if result.get("status") == "ERROR":
                    raise OrderError(
                        f"Order failed: {result.get('message', 'broker returned empty order_id')}",
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
                        ltp_data = self.broker.get_market_data([{"security_id": symbol, "exchange_segment": "NSE_FNO"}])
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
                        # Extract data under lock to avoid use-after-free
                        trade_price = ti["price"]
                        trade_side = ti["side"]
                        trade_sl = ti.get("stop_loss")
                        trade_target = ti.get("target")
                    # Lock released — trade_data is now in local variables

                    # ── Trailing stop update ─────────────────────────────────
                    if trade_sl:
                        ts_pct = 0.005
                        ts = TrailingStop(entry_price=trade_price, side=trade_side, initial_sl=trade_sl, trailing_pct=ts_pct)
                        ts.update(market_price)
                        with global_state._lock:
                            ti["trailing_stop"] = ts.stop_price

                    # ── Check stop-hit ─────────────────────────────────────
                    if trade_side == "BUY" and market_price <= trade_sl:
                        self._close_trade(order_id, "STOPPED_OUT", market_price)
                    elif trade_side == "SELL" and market_price >= trade_sl:
                        self._close_trade(order_id, "STOPPED_OUT", market_price)
                    # ── Check target-hit ────────────────────────────────────
                    elif trade_side == "BUY" and market_price >= trade_target:
                        self._close_trade(order_id, "TARGET_HIT", market_price)
                    elif trade_side == "SELL" and market_price <= trade_target:
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
        
        Security: Places exit order at broker BEFORE updating local state.
        Verifies the exit order is FILLED before marking trade as closed locally.
        If broker operation fails or fill cannot be confirmed, local state 
        remains unchanged and the position continues to be monitored.
        """
        # ── Step 1: Extract trade data under lock ─────────────────────────
        with global_state._lock:
            trade = next((t for t in global_state.kanban["ACTIVE"] if t.get("order_id") == order_id), None)
            if not trade:
                return
            
            # Copy trade data for broker operation (release lock quickly)
            symbol = trade["symbol"]
            side = trade["side"]
            entry_price = trade["price"]
            qty = trade["qty"]
            stop_loss = trade.get("stop_loss")
            target = trade.get("target")
        
        # ── Step 2: Place exit order at broker FIRST ──────────────────────
        # Exit side is opposite of entry side
        exit_side = "SELL" if side == "BUY" else "BUY"
        exit_order_payload = {
            "symbol": symbol,
            "side": exit_side,
            "qty": qty,
            "price": current_price,
            "idempotency_key": f"{order_id}_exit_{uuid.uuid4().hex[:8]}",
            "tag": "EXIT",
        }
        
        exit_order_id = None
        for attempt in range(3):
            try:
                logger.info(f"Attempting broker exit for {order_id} (attempt {attempt+1}/3): {exit_side} {qty} {symbol} @ {current_price}")
                result = self.broker.place_order(exit_order_payload)
                
                # Normalize result (handle string returns for backwards compat)
                if isinstance(result, str):
                    oid = result.strip() if result else ""
                    result = {
                        "order_id": oid,
                        "status": "OPEN" if oid else "ERROR",
                        "message": "" if oid else "Broker returned empty order_id",
                    }
                
                exit_order_id = result.get("order_id", "")
                status = result.get("status", "ERROR")
                
                if status == "REJECTED":
                    logger.error(f"Exit order rejected for {order_id}: {result.get('message', 'unknown')}")
                    if attempt < 2:
                        time.sleep(2 ** attempt)
                        continue
                    else:
                        logger.critical(
                            f"CRITICAL: Failed to close position {order_id} at broker after 3 attempts. "
                            f"Position remains OPEN at broker and will continue monitoring. "
                            f"Manual intervention required: {symbol} {side} {qty}"
                        )
                        return  # Do NOT update local state - keep monitoring
                
                if status == "ERROR" or not exit_order_id:
                    logger.error(f"Exit order failed for {order_id}: {result.get('message', 'broker error')}")
                    if attempt < 2:
                        time.sleep(2 ** attempt)
                        continue
                    else:
                        logger.critical(
                            f"CRITICAL: Failed to close position {order_id} at broker after 3 attempts. "
                            f"Position remains OPEN at broker and will continue monitoring. "
                            f"Manual intervention required: {symbol} {side} {qty}"
                        )
                        return  # Do NOT update local state - keep monitoring
                
                # Exit order placed - now verify it's filled
                logger.info(f"Exit order placed: {exit_order_id} for original order {order_id}, verifying fill...")
                break
                
            except Exception as e:
                logger.error(f"Exception placing exit order for {order_id} (attempt {attempt+1}/3): {e}")
                if attempt < 2:
                    time.sleep(2 ** attempt)
                else:
                    logger.critical(
                        f"CRITICAL: Failed to close position {order_id} at broker after 3 attempts due to exception. "
                        f"Position remains OPEN at broker and will continue monitoring. "
                        f"Manual intervention required: {symbol} {side} {qty}"
                    )
                    return  # Do NOT update local state - keep monitoring
        
        # ── Step 3: Verify exit order is FILLED ────────────────────────────
        # Poll order status to confirm fill before updating local state
        fill_confirmed = False
        actual_exit_price = current_price
        
        for poll_attempt in range(10):  # Poll for up to 20 seconds (10 * 2s)
            try:
                order_status = self.broker.get_order_status(exit_order_id)
                status = order_status.get("status", "").upper()
                
                if status in ("COMPLETE", "FILLED", "EXECUTED"):
                    fill_confirmed = True
                    # Use actual fill price if available
                    actual_exit_price = order_status.get("average_price") or order_status.get("price") or current_price
                    logger.info(f"Exit order {exit_order_id} confirmed FILLED at {actual_exit_price}")
                    break
                elif status in ("REJECTED", "CANCELLED", "CANCELED"):
                    logger.error(
                        f"Exit order {exit_order_id} was {status} after placement. "
                        f"Position {order_id} remains OPEN at broker and will continue monitoring."
                    )
                    return  # Do NOT update local state - keep monitoring
                else:
                    # Order still pending (OPEN, PENDING, etc.)
                    logger.debug(f"Exit order {exit_order_id} status: {status}, waiting... (poll {poll_attempt+1}/10)")
                    time.sleep(2)
                    
            except Exception as e:
                logger.warning(f"Error checking exit order status (poll {poll_attempt+1}/10): {e}")
                time.sleep(2)
        
        if not fill_confirmed:
            logger.critical(
                f"CRITICAL: Could not confirm fill for exit order {exit_order_id} after 20 seconds. "
                f"Position {order_id} remains in ACTIVE for continued monitoring. "
                f"Manual verification required: {symbol} {side} {qty}"
            )
            return  # Do NOT update local state - keep monitoring
        
        # ── Step 4: Update local state ONLY after confirmed fill ──────────
        with global_state._lock:
            # Re-fetch trade to ensure it still exists (may have been closed by another thread)
            trade = next((t for t in global_state.kanban["ACTIVE"] if t.get("order_id") == order_id), None)
            if not trade:
                logger.warning(f"Trade {order_id} already closed by another thread")
                return
            
            # Compute P&L using actual exit price
            if side == "BUY":
                pnl = (actual_exit_price - entry_price) * qty
            else:
                pnl = (entry_price - actual_exit_price) * qty
            
            # Mark trade as closed
            trade["status"] = "CLOSED"
            trade["exit_reason"] = reason
            trade["exit_price"] = actual_exit_price
            trade["exit_order_id"] = exit_order_id
            trade["pnl"] = pnl
            trade["exit_time"] = time.time()
            
            # Move from ACTIVE to CLOSED
            global_state.kanban["ACTIVE"] = [t for t in global_state.kanban["ACTIVE"] if t.get("order_id") != order_id]
            global_state.kanban["CLOSED"].append(trade)
            global_state.add_pnl(pnl)
            global_state.update_summary(active_trades_count=len(global_state.kanban["ACTIVE"]))
            
            # Clean up active_symbols if no trades for this symbol remain
            if not any(t.get("symbol") == symbol for t in global_state.kanban["ACTIVE"]):
                global_state.active_symbols = [s for s in global_state.active_symbols if s != symbol]
            
            global_state.add_log(
                f"Trade closed ({reason}): {symbol} {side} {qty} @ {actual_exit_price} | "
                f"P&L: {pnl:.2f} | Exit order: {exit_order_id}"
            )
            
            # ── Record in circuit breaker ─────────────────────────────────────
            if self.risk_manager is not None:
                self.risk_manager.cb.record_trade(pnl)
                logger.info(
                    f"Circuit breaker: {self.risk_manager.cb.consecutive_losses} consecutive losses, "
                    f"session P&L: {self.risk_manager.cb.session_pnl:.2f}"
                )


# Exposed for type hints elsewhere
OrderInfo = Dict[str, Any]