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
    
    On initialization, reconciles broker positions with local state to ensure
    positions opened before a restart are monitored for stop-loss and targets.
    """

    def __init__(self, broker: Any, risk_manager: Any = None, reconcile_positions: bool = True):
        self.broker = broker
        self.risk_manager = risk_manager
        # Circuit breaker state is now automatically loaded from disk by CircuitBreakerState.__post_init__
        # No unconditional reset_day() call - state persists across restarts within the same trading day
        self.state = global_state  # used for logging only
        self._exit_requested = threading.Event()
        self._track_thread: Optional[threading.Thread] = None
        
        # Idempotency tracking: maps idempotency_key -> (order_id, timestamp)
        # Prevents duplicate order submissions when retries occur after broker acceptance
        self._submitted_orders: Dict[str, tuple[str, float]] = {}
        self._submitted_orders_lock = threading.Lock()
        
        # Reconcile broker positions on startup to restore monitoring for existing positions
        if reconcile_positions:
            self._reconcile_broker_positions()

    def _reconcile_broker_positions(self) -> None:
        """
        Query broker for open positions and reconcile with local state.
        
        This ensures that positions opened before a restart are added to the
        local monitoring loop for stop-loss and target tracking. Without this,
        a restart would leave existing broker positions unmonitored locally.
        
        Security: Positions are added to ACTIVE only if they don't already exist
        (by order_id or symbol+side combination) to prevent duplicate monitoring.
        """
        try:
            logger.info("Reconciling broker positions with local state...")
            
            # Query broker for current positions
            broker_positions = self.broker.get_positions()
            
            if not broker_positions:
                logger.info("No open positions at broker - reconciliation complete")
                return
            
            with global_state._lock:
                # Get existing active order IDs and symbol+side pairs
                existing_order_ids = {t.get("order_id") for t in global_state.kanban["ACTIVE"]}
                existing_positions = {
                    (t.get("symbol"), t.get("side")) 
                    for t in global_state.kanban["ACTIVE"]
                }
                
                reconciled_count = 0
                for pos in broker_positions:
                    # Extract position details (broker-specific field mapping)
                    symbol = pos.get("symbol") or pos.get("trading_symbol") or pos.get("tradingsymbol")
                    quantity = pos.get("quantity") or pos.get("qty") or pos.get("net_quantity", 0)
                    avg_price = pos.get("average_price") or pos.get("avg_price") or pos.get("buy_avg", 0.0)
                    order_id = pos.get("order_id") or pos.get("tag") or f"reconciled_{symbol}_{int(time.time())}"
                    
                    # Determine side from quantity (positive = BUY, negative = SELL)
                    if quantity == 0:
                        continue  # Skip closed positions
                    
                    side = "BUY" if quantity > 0 else "SELL"
                    abs_quantity = abs(quantity)
                    
                    # Skip if already being monitored
                    if order_id in existing_order_ids:
                        logger.debug(f"Position {symbol} {side} already in ACTIVE (order_id: {order_id})")
                        continue
                    
                    if (symbol, side) in existing_positions:
                        logger.debug(f"Position {symbol} {side} already in ACTIVE (by symbol+side)")
                        continue
                    
                    # Add to ACTIVE for monitoring
                    # Note: We don't have original stop_loss/target from before restart,
                    # so we set conservative defaults based on current price
                    # Users should manually set proper stops after restart if needed
                    if avg_price > 0:
                        # Conservative stop: 2% for BUY, 2% for SELL
                        if side == "BUY":
                            default_sl = avg_price * 0.98
                            default_target = avg_price * 1.05
                        else:
                            default_sl = avg_price * 1.02
                            default_target = avg_price * 0.95
                    else:
                        default_sl = None
                        default_target = None
                    
                    reconciled_trade = {
                        "symbol": symbol,
                        "side": side,
                        "price": avg_price,
                        "quantity": abs_quantity,
                        "order_id": order_id,
                        "entry_time": time.time(),
                        "stop_loss": default_sl,
                        "target": default_target,
                        "reconciled": True,  # Flag to indicate this was restored from broker
                    }
                    
                    global_state.kanban["ACTIVE"].append(reconciled_trade)
                    reconciled_count += 1
                    
                    logger.warning(
                        f"Reconciled position from broker: {side} {abs_quantity} {symbol} @ {avg_price:.2f} "
                        f"(order_id: {order_id}). Default stops applied - verify manually!"
                    )
                
                if reconciled_count > 0:
                    global_state.update_summary(
                        active_trades_count=len(global_state.kanban["ACTIVE"])
                    )
                    global_state.add_log(
                        f"Reconciled {reconciled_count} position(s) from broker on startup. "
                        "Verify stop-loss and target levels manually."
                    )
                    logger.info(
                        f"Position reconciliation complete: {reconciled_count} position(s) added to monitoring"
                    )
                else:
                    logger.info("Position reconciliation complete: all broker positions already monitored")
                    
        except Exception as e:
            logger.error(f"Failed to reconcile broker positions: {e}. Continuing without reconciliation.")
            global_state.add_log(
                f"WARNING: Position reconciliation failed - existing broker positions may not be monitored. "
                f"Error: {e}"
            )

    def execute_confirmed_trade(self, trade: Dict[str, Any]) -> OrderInfo:
        """
        Place a confirmed trade order with idempotency key and fill verification.

        The idempotency key is stable across all retry attempts for the same logical order.
        If a network call fails or times out, the retry uses the SAME key so the broker
        can recognize it as a duplicate and prevent double-fills.

        Before retrying, we reconcile with the broker's orderbook to check if a previous
        attempt succeeded but the response was lost. This prevents duplicate orders when
        the broker accepted the order but the response was dropped due to network issues.

        SECURITY: After order placement, this method polls get_order_status to verify
        the order is actually FILLED before adding it to ACTIVE tracking. This prevents
        exposure mismatches where pending or partially-filled orders are tracked as
        fully-filled positions. Only the actual filled quantity is tracked.

        Idempotency key format: {symbol}_{side}_{uuid4_short}
        
        Returns:
            OrderInfo dict with actual filled quantity and average price
            
        Raises:
            OrderError: If order is rejected, times out, or cannot be confirmed as filled
        """
        symbol = trade["symbol"]
        side = trade["side"]
        # Accept both 'quantity' and 'qty' for backwards compatibility
        qty = trade.get("quantity") or trade.get("qty")
        if not qty:
            raise ValueError("Trade must include 'quantity' or 'qty' field")
        price = trade["price"]

        # ── Build stable idempotency key (same for all retries) ──────────────
        idempotency_key = trade.get("idempotency_key") or f"{symbol}_{side}_{uuid.uuid4().hex[:8]}"

        # ── Check local deduplication cache first ────────────────────────────
        # If we've already submitted this order successfully, return the cached result
        with self._submitted_orders_lock:
            if idempotency_key in self._submitted_orders:
                cached_order_id, submit_time = self._submitted_orders[idempotency_key]
                # Only use cache if submission was recent (within last 60 seconds)
                if time.time() - submit_time < 60:
                    logger.warning(
                        f"Idempotency key {idempotency_key} already submitted recently "
                        f"(order_id: {cached_order_id}). Verifying order status..."
                    )
                    try:
                        # Verify the cached order is actually filled
                        order_status_response = self.broker.get_order_status(cached_order_id)
                        final_status = (order_status_response.get("status") or "").upper()
                        
                        if final_status in ("COMPLETE", "FILLED", "EXECUTED"):
                            # Extract actual filled quantity
                            filled_qty_raw = (
                                order_status_response.get("filled_quantity") or
                                order_status_response.get("filled_qty") or
                                order_status_response.get("quantity") or
                                qty
                            )
                            actual_filled_qty = int(filled_qty_raw) if filled_qty_raw else qty
                            
                            avg_price_raw = (
                                order_status_response.get("average_price") or
                                order_status_response.get("avg_price") or
                                order_status_response.get("price") or
                                price
                            )
                            actual_avg_price = float(avg_price_raw) if avg_price_raw else price
                            
                            logger.info(
                                f"Cached order {cached_order_id} confirmed FILLED: "
                                f"{actual_filled_qty}/{qty} @ {actual_avg_price}. "
                                f"Prevented duplicate submission."
                            )
                            
                            # Register the order with actual filled quantity
                            order_info = {
                                "order_id": cached_order_id,
                                "symbol": symbol,
                                "side": side,
                                "price": actual_avg_price,
                                "qty": actual_filled_qty,
                                "status": "FILLED",
                                "requested_qty": qty,
                            }
                            
                            global_state.kanban["ACTIVE"].append({
                                "symbol": symbol,
                                "side": side,
                                "price": actual_avg_price,
                                "quantity": actual_filled_qty,
                                "order_id": cached_order_id,
                                "entry_time": time.time(),
                                "stop_loss": trade.get("stop_loss"),
                                "target": trade.get("target"),
                                "requested_qty": qty,
                            })
                            global_state.update_summary(
                                active_trades_count=len(global_state.kanban["ACTIVE"])
                            )
                            global_state.add_log(
                                f"Trade confirmed (cached): {side} {actual_filled_qty} {symbol} @ {actual_avg_price} "
                                f"[order_id={cached_order_id}]"
                            )
                            return order_info
                        else:
                            logger.warning(
                                f"Cached order {cached_order_id} is not filled (status: {final_status}). "
                                f"Removing from cache and proceeding with new submission."
                            )
                            del self._submitted_orders[idempotency_key]
                    except Exception as cache_verify_error:
                        logger.warning(
                            f"Failed to verify cached order {cached_order_id}: {cache_verify_error}. "
                            f"Removing from cache and proceeding with new submission."
                        )
                        del self._submitted_orders[idempotency_key]
                else:
                    # Cache entry is stale, remove it
                    logger.debug(f"Removing stale cache entry for {idempotency_key}")
                    del self._submitted_orders[idempotency_key]

        for attempt in range(3):
            # ── Reconciliation: Check if previous attempt succeeded ──────────
            if attempt > 0:
                # Before retrying, check if the order was already placed
                try:
                    logger.info(f"Reconciling orderbook before retry {attempt+1} for {symbol} {side}")
                    
                    # First check local cache again (another thread might have submitted)
                    with self._submitted_orders_lock:
                        if idempotency_key in self._submitted_orders:
                            cached_order_id, submit_time = self._submitted_orders[idempotency_key]
                            if time.time() - submit_time < 60:
                                logger.info(
                                    f"Found order {cached_order_id} in local cache during retry. "
                                    f"Verifying status..."
                                )
                                try:
                                    order_status_response = self.broker.get_order_status(cached_order_id)
                                    final_status = (order_status_response.get("status") or "").upper()
                                    
                                    if final_status in ("COMPLETE", "FILLED", "EXECUTED"):
                                        # Extract actual filled quantity
                                        filled_qty_raw = (
                                            order_status_response.get("filled_quantity") or
                                            order_status_response.get("filled_qty") or
                                            order_status_response.get("quantity") or
                                            qty
                                        )
                                        actual_filled_qty = int(filled_qty_raw) if filled_qty_raw else qty
                                        
                                        avg_price_raw = (
                                            order_status_response.get("average_price") or
                                            order_status_response.get("avg_price") or
                                            order_status_response.get("price") or
                                            price
                                        )
                                        actual_avg_price = float(avg_price_raw) if avg_price_raw else price
                                        
                                        logger.info(
                                            f"Cached order {cached_order_id} confirmed FILLED during retry: "
                                            f"{actual_filled_qty}/{qty} @ {actual_avg_price}"
                                        )
                                        
                                        # Register the order
                                        order_info = {
                                            "order_id": cached_order_id,
                                            "symbol": symbol,
                                            "side": side,
                                            "price": actual_avg_price,
                                            "qty": actual_filled_qty,
                                            "status": "FILLED",
                                            "requested_qty": qty,
                                        }
                                        
                                        global_state.kanban["ACTIVE"].append({
                                            "symbol": symbol,
                                            "side": side,
                                            "price": actual_avg_price,
                                            "quantity": actual_filled_qty,
                                            "order_id": cached_order_id,
                                            "entry_time": time.time(),
                                            "stop_loss": trade.get("stop_loss"),
                                            "target": trade.get("target"),
                                            "requested_qty": qty,
                                        })
                                        global_state.update_summary(
                                            active_trades_count=len(global_state.kanban["ACTIVE"])
                                        )
                                        global_state.add_log(
                                            f"Trade confirmed (retry cache hit): {side} {actual_filled_qty} {symbol} @ {actual_avg_price} "
                                            f"[order_id={cached_order_id}]"
                                        )
                                        return order_info
                                except Exception as e:
                                    logger.warning(f"Failed to verify cached order during retry: {e}")
                    
                    # Check if broker implements get_orderbook (not in base interface)
                    if not hasattr(self.broker, 'get_orderbook'):
                        logger.debug("Broker does not implement get_orderbook, skipping reconciliation")
                        raise AttributeError("get_orderbook not implemented")
                    
                    orderbook = self.broker.get_orderbook()
                    
                    # Look for recent orders matching this trade's characteristics
                    # Check last 10 orders to avoid scanning entire history
                    recent_orders = orderbook[-10:] if isinstance(orderbook, list) else []
                    
                    for existing_order in recent_orders:
                        existing_symbol = existing_order.get("symbol") or existing_order.get("trading_symbol")
                        existing_side = existing_order.get("side") or existing_order.get("transaction_type")
                        existing_qty = existing_order.get("quantity") or existing_order.get("qty")
                        existing_status = (existing_order.get("status") or "").upper()
                        
                        # Match by symbol, side, quantity, and non-rejected status
                        if (existing_symbol == symbol and 
                            existing_side == side and 
                            existing_qty == qty and
                            existing_status not in ("REJECTED", "CANCELLED", "CANCELED")):
                            
                            # Found a matching order from previous attempt
                            order_id = existing_order.get("order_id") or existing_order.get("orderid")
                            if order_id:
                                logger.warning(
                                    f"Reconciliation found existing order {order_id} for {symbol} {side} {qty}. "
                                    f"Previous attempt succeeded but response was lost. Verifying fill status..."
                                )
                                
                                # Verify the reconciled order is actually filled before tracking
                                try:
                                    order_status_response = self.broker.get_order_status(order_id)
                                    final_status = (order_status_response.get("status") or "").upper()
                                    
                                    if final_status not in ("COMPLETE", "FILLED", "EXECUTED"):
                                        logger.warning(
                                            f"Reconciled order {order_id} is not filled (status: {final_status}). "
                                            f"Skipping reconciliation to prevent exposure mismatch."
                                        )
                                        continue  # Try next order in reconciliation
                                    
                                    # Extract actual filled quantity
                                    filled_qty_raw = (
                                        order_status_response.get("filled_quantity") or
                                        order_status_response.get("filled_qty") or
                                        order_status_response.get("quantity") or
                                        qty
                                    )
                                    actual_filled_qty = int(filled_qty_raw) if filled_qty_raw else qty
                                    
                                    avg_price_raw = (
                                        order_status_response.get("average_price") or
                                        order_status_response.get("avg_price") or
                                        order_status_response.get("price") or
                                        price
                                    )
                                    actual_avg_price = float(avg_price_raw) if avg_price_raw else price
                                    
                                    logger.info(
                                        f"Reconciled order {order_id} confirmed FILLED: "
                                        f"{actual_filled_qty}/{qty} @ {actual_avg_price}"
                                    )
                                    
                                    # Cache this order to prevent future duplicates
                                    with self._submitted_orders_lock:
                                        self._submitted_orders[idempotency_key] = (order_id, time.time())
                                    
                                    # Register the reconciled order with actual filled quantity
                                    order_info = {
                                        "order_id": order_id,
                                        "symbol": symbol,
                                        "side": side,
                                        "price": actual_avg_price,
                                        "qty": actual_filled_qty,
                                        "status": "FILLED",
                                        "requested_qty": qty,
                                    }
                                    
                                    global_state.kanban["ACTIVE"].append({
                                        "symbol": symbol,
                                        "side": side,
                                        "price": actual_avg_price,
                                        "quantity": actual_filled_qty,
                                        "order_id": order_id,
                                        "entry_time": time.time(),
                                        "stop_loss": trade.get("stop_loss"),
                                        "target": trade.get("target"),
                                        "requested_qty": qty,
                                    })
                                    global_state.update_summary(
                                        active_trades_count=len(global_state.kanban["ACTIVE"])
                                    )
                                    global_state.add_log(
                                        f"Trade reconciled: {side} {actual_filled_qty} {symbol} @ {actual_avg_price} "
                                        f"[order_id={order_id}]"
                                    )
                                    return order_info
                                    
                                except Exception as verify_error:
                                    logger.warning(
                                        f"Failed to verify reconciled order {order_id}: {verify_error}. "
                                        f"Skipping this order."
                                    )
                                    continue  # Try next order in reconciliation
                                
                except Exception as reconcile_error:
                    logger.warning(f"Reconciliation failed: {reconcile_error}. Proceeding with retry.")
            
            # ── Place order with stable idempotency key ───────────────────────
            order_payload = {
                "symbol": symbol,
                "side": side,
                "quantity": qty,
                "price": price,
                "idempotency_key": idempotency_key,  # Same key for all retries
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

                # Extract order_id and validate it's non-empty
                order_id = result.get("order_id", "").strip()
                if not order_id:
                    raise OrderError(
                        f"Broker returned empty order_id: {result.get('message', 'no order ID provided')}",
                        symbol=symbol, side=side, price=price, qty=qty,
                    )

                # Validate status is a known value
                status = result.get("status", "").upper()
                if status == "REJECTED":
                    raise OrderError(
                        f"Order rejected: {result.get('message', 'unknown')}",
                        symbol=symbol, side=side, price=price, qty=qty,
                    )

                if status == "ERROR":
                    raise OrderError(
                        f"Order failed: {result.get('message', 'broker returned error status')}",
                        symbol=symbol, side=side, price=price, qty=qty,
                    )
                
                # Only accept explicit success statuses
                if status not in ("OPEN", "PENDING", "COMPLETE", "FILLED"):
                    raise OrderError(
                        f"Unknown order status '{status}': {result.get('message', 'unexpected broker response')}",
                        symbol=symbol, side=side, price=price, qty=qty,
                    )
                
                # ── Cache the order_id immediately after broker acceptance ────
                # This prevents duplicate submissions if the response is lost after this point
                with self._submitted_orders_lock:
                    self._submitted_orders[idempotency_key] = (order_id, time.time())
                    logger.debug(f"Cached order {order_id} with idempotency key {idempotency_key}")

                # ── Step 2: Verify order is FILLED before tracking ────────────
                # Poll order status to confirm fill and get actual filled quantity
                # Status "OPEN" means order was accepted, not filled
                fill_confirmed = False
                actual_filled_qty = 0
                actual_avg_price = price
                final_status = status
                
                # If already COMPLETE/FILLED, skip polling
                if status in ("COMPLETE", "FILLED"):
                    fill_confirmed = True
                    actual_filled_qty = qty
                    logger.info(f"Order {order_id} returned as {status} immediately")
                else:
                    # Poll for up to 20 seconds (10 * 2s) to confirm fill
                    for poll_attempt in range(10):
                        try:
                            order_status_response = self.broker.get_order_status(order_id)
                            final_status = (order_status_response.get("status") or "").upper()
                            
                            if final_status in ("COMPLETE", "FILLED", "EXECUTED"):
                                fill_confirmed = True
                                # Extract actual filled quantity (may differ from requested)
                                filled_qty_raw = (
                                    order_status_response.get("filled_quantity") or
                                    order_status_response.get("filled_qty") or
                                    order_status_response.get("quantity") or
                                    qty  # Fallback to requested if not provided
                                )
                                # Ensure it's an integer
                                actual_filled_qty = int(filled_qty_raw) if filled_qty_raw else qty
                                
                                # Use actual average fill price if available
                                avg_price_raw = (
                                    order_status_response.get("average_price") or
                                    order_status_response.get("avg_price") or
                                    order_status_response.get("price") or
                                    price
                                )
                                # Ensure it's a float
                                actual_avg_price = float(avg_price_raw) if avg_price_raw else price
                                
                                logger.info(
                                    f"Order {order_id} confirmed FILLED: {actual_filled_qty}/{qty} @ {actual_avg_price}"
                                )
                                break
                            elif final_status in ("REJECTED", "CANCELLED", "CANCELED"):
                                logger.error(
                                    f"Order {order_id} was {final_status} after placement. "
                                    f"Not adding to ACTIVE tracking."
                                )
                                raise OrderError(
                                    f"Order {final_status} after placement: {order_status_response.get('message', 'no reason provided')}",
                                    symbol=symbol, side=side, price=price, qty=qty,
                                )
                            else:
                                # Order still pending (OPEN, PENDING, etc.)
                                logger.debug(
                                    f"Order {order_id} status: {final_status}, waiting for fill... "
                                    f"(poll {poll_attempt+1}/10)"
                                )
                                time.sleep(2)
                                
                        except Exception as e:
                            logger.warning(
                                f"Error checking order status (poll {poll_attempt+1}/10): {e}"
                            )
                            time.sleep(2)
                    
                    if not fill_confirmed:
                        logger.error(
                            f"Order {order_id} did not fill within 20 seconds (final status: {final_status}). "
                            f"Not adding to ACTIVE tracking to prevent exposure mismatch."
                        )
                        raise OrderError(
                            f"Order timeout: could not confirm fill within 20 seconds (status: {final_status})",
                            symbol=symbol, side=side, price=price, qty=qty,
                        )
                
                # ── Step 3: Handle partial fills ──────────────────────────────
                if actual_filled_qty < qty:
                    logger.warning(
                        f"Partial fill detected: {actual_filled_qty}/{qty} filled for {symbol} {side}. "
                        f"Tracking only filled quantity."
                    )
                    global_state.add_log(
                        f"WARNING: Partial fill - {side} {actual_filled_qty}/{qty} {symbol} @ {actual_avg_price}"
                    )
                
                # ── Step 4: Register in global_state with ACTUAL filled qty ───
                order_info = {
                    "order_id": order_id,
                    "symbol": symbol,
                    "side": side,
                    "price": actual_avg_price,
                    "qty": actual_filled_qty,
                    "status": "FILLED",
                    "requested_qty": qty,  # Track original request for audit
                }

                global_state.kanban["ACTIVE"].append({
                    "symbol": symbol,
                    "side": side,
                    "price": actual_avg_price,
                    "quantity": actual_filled_qty,
                    "order_id": order_id,
                    "entry_time": time.time(),
                    "stop_loss": trade.get("stop_loss"),
                    "target": trade.get("target"),
                    "requested_qty": qty,  # Audit trail
                    "security_id": trade.get("security_id"),  # Store for market data lookups
                    "exchange_segment": trade.get("exchange_segment", "NSE_FNO"),
                })
                global_state.update_summary(
                    active_trades_count=len(global_state.kanban["ACTIVE"])
                )
                global_state.add_log(
                    f"Trade confirmed: {side} {actual_filled_qty} {symbol} @ {actual_avg_price} "
                    f"[order_id={order_id}]"
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
        last_cleanup_time = time.time()
        
        while not self._exit_requested.is_set():
            # Periodically clean up stale order cache entries (every 5 minutes)
            current_time = time.time()
            if current_time - last_cleanup_time > 300:  # 5 minutes
                self._cleanup_stale_order_cache()
                last_cleanup_time = current_time
            
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
                        # Use stored security_id if available, otherwise fall back to symbol
                        # This ensures compatibility with Master Trust and similar brokers that
                        # return market data keyed by security_id, not symbol name
                        security_id = trade_data.get("security_id") or symbol
                        exchange_segment = trade_data.get("exchange_segment", "NSE_FNO")
                        
                        ltp_data = self.broker.get_market_data([{
                            "security_id": security_id,
                            "exchange_segment": exchange_segment
                        }])
                        
                        # Handle both direct format and wrapped format
                        # Master Trust and similar brokers return {"data": {security_id: {...}}}
                        # where security_id is the key used in the request, not the symbol name
                        if "data" in ltp_data and isinstance(ltp_data["data"], dict):
                            # Look up by security_id (the key used in request), not symbol
                            market_price = ltp_data["data"].get(security_id, {}).get("last_price", 0)
                        else:
                            # Fallback for brokers that return flat structure
                            market_price = ltp_data.get(security_id, {}).get("last_price", 0)

                    if not market_price:
                        logger.warning(
                            f"No market price available for {symbol} (order_id: {order_id}). "
                            f"Skipping protective exit checks for this cycle."
                        )
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

    def _cleanup_stale_order_cache(self) -> None:
        """
        Remove stale entries from the order submission cache.
        Called periodically to prevent unbounded memory growth.
        Entries older than 5 minutes are removed.
        """
        with self._submitted_orders_lock:
            current_time = time.time()
            stale_keys = [
                key for key, (order_id, submit_time) in self._submitted_orders.items()
                if current_time - submit_time > 300  # 5 minutes
            ]
            for key in stale_keys:
                del self._submitted_orders[key]
            if stale_keys:
                logger.debug(f"Cleaned up {len(stale_keys)} stale order cache entries")

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
            qty = trade["quantity"]
            stop_loss = trade.get("stop_loss")
            target = trade.get("target")
        
        # ── Step 2: Place exit order at broker FIRST ──────────────────────
        # Exit side is opposite of entry side
        exit_side = "SELL" if side == "BUY" else "BUY"
        
        # Generate stable idempotency key for exit order (same across all retries)
        exit_idempotency_key = f"{order_id}_exit_{uuid.uuid4().hex[:8]}"
        
        # Check local cache first to prevent duplicate exit orders
        with self._submitted_orders_lock:
            if exit_idempotency_key in self._submitted_orders:
                cached_exit_order_id, submit_time = self._submitted_orders[exit_idempotency_key]
                if time.time() - submit_time < 60:
                    logger.warning(
                        f"Exit order for {order_id} already submitted recently "
                        f"(exit_order_id: {cached_exit_order_id}). Using cached order."
                    )
                    exit_order_id = cached_exit_order_id
                else:
                    # Stale cache entry, remove it
                    del self._submitted_orders[exit_idempotency_key]
                    exit_order_id = None
            else:
                exit_order_id = None
        
        exit_order_payload = {
            "symbol": symbol,
            "side": exit_side,
            "quantity": qty,
            "price": current_price,
            "idempotency_key": exit_idempotency_key,  # Stable across retries
            "tag": "EXIT",
        }
        
        if not exit_order_id:  # Only place order if not found in cache
            for attempt in range(3):
                # ── Reconciliation: Check if previous exit attempt succeeded ──────
                if attempt > 0:
                    # Check cache again before reconciliation
                    with self._submitted_orders_lock:
                        if exit_idempotency_key in self._submitted_orders:
                            cached_exit_order_id, submit_time = self._submitted_orders[exit_idempotency_key]
                            if time.time() - submit_time < 60:
                                logger.info(
                                    f"Found exit order {cached_exit_order_id} in cache during retry. "
                                    f"Using cached order."
                                )
                                exit_order_id = cached_exit_order_id
                                break
                    
                    try:
                        logger.info(f"Reconciling orderbook before exit retry {attempt+1} for {order_id}")
                        
                        # Check if broker implements get_orderbook (not in base interface)
                        if not hasattr(self.broker, 'get_orderbook'):
                            logger.debug("Broker does not implement get_orderbook, skipping exit reconciliation")
                            raise AttributeError("get_orderbook not implemented")
                        
                        orderbook = self.broker.get_orderbook()
                        
                        # Look for recent exit orders matching this trade's characteristics
                        recent_orders = orderbook[-10:] if isinstance(orderbook, list) else []
                        
                        for existing_order in recent_orders:
                            existing_symbol = existing_order.get("symbol") or existing_order.get("trading_symbol")
                            existing_side = existing_order.get("side") or existing_order.get("transaction_type")
                            existing_qty = existing_order.get("quantity") or existing_order.get("qty")
                            existing_status = (existing_order.get("status") or "").upper()
                            
                            # Match by symbol, exit side, quantity, and non-rejected status
                            if (existing_symbol == symbol and 
                                existing_side == exit_side and 
                                existing_qty == qty and
                                existing_status not in ("REJECTED", "CANCELLED", "CANCELED")):
                                
                                # Found a matching exit order from previous attempt
                                found_exit_order_id = existing_order.get("order_id") or existing_order.get("orderid")
                                if found_exit_order_id:
                                    logger.warning(
                                        f"Reconciliation found existing exit order {found_exit_order_id} for {order_id}. "
                                        f"Previous exit attempt succeeded but response was lost. Using existing order."
                                    )
                                    exit_order_id = found_exit_order_id
                                    # Cache the reconciled order
                                    with self._submitted_orders_lock:
                                        self._submitted_orders[exit_idempotency_key] = (exit_order_id, time.time())
                                    break
                        
                        if exit_order_id:
                            # Found reconciled exit order, skip to verification
                            logger.info(f"Using reconciled exit order {exit_order_id}, proceeding to fill verification")
                            break
                            
                    except Exception as reconcile_error:
                        logger.warning(f"Exit reconciliation failed: {reconcile_error}. Proceeding with retry.")
                
                # Skip placement if we found a reconciled order
                if exit_order_id:
                    break
                
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
                    
                    # Cache the exit order immediately after broker acceptance
                    with self._submitted_orders_lock:
                        self._submitted_orders[exit_idempotency_key] = (exit_order_id, time.time())
                        logger.debug(f"Cached exit order {exit_order_id} with idempotency key {exit_idempotency_key}")
                    
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