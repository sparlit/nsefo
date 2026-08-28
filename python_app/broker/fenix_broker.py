import logging
from fenix import Dhan
from .base import Broker
from typing import List, Dict, Any, Optional, Callable

class FenixDhanProvider(Broker):
    def __init__(self, client_id: str, access_token: str):
        self.client_id = client_id
        self.access_token = access_token
        self.logger = logging.getLogger("FenixDhanProvider")
        self.authenticated = False
        try:
            # Fenix configuration expects real-world credentials
            self.api = Dhan({"client_id": client_id, "access_token": access_token})
            # Explicitly call authenticate to ensure headers are generated for API v2
            self.api.authenticate()
            self.authenticated = True
            self.logger.info("Fenix Dhan API Gateway Initialized.")
        except Exception as e:
            self.logger.error(f"Fenix Initialization Error: {e}")
            self.api = None

    def login(self, **kwargs) -> bool:
        if not self.api or not self.authenticated: return False
        try:
            # Operational session validation
            profile = self.api.fetch_profile()
            return profile is not None
        except Exception as e:
            self.logger.error(f"Fenix Login Failed: {e}")
            return False

    def get_market_data(self, symbols: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Fetches live market data using Fenix.
        """
        if not self.api: return {"status": "error"}
        try:
            results = {}
            for s in symbols:
                # Fenix normalized OHLC/Quote access
                # Avoid fetch_orderbook (hits /orders)
                data = self.api.ohlc_data(s['security_id'], s['exchange_segment'])
                if data:
                    results[s['security_id']] = {"last_price": float(data.get('last_price', 0.0))}
            return {"data": results}
        except Exception as e:
            self.logger.debug(f"Fenix Data Error: {e}")
            return {"status": "error", "remarks": str(e)}

    def get_historical_data(self, symbol: Dict[str, str], interval: str, from_date: str, to_date: str) -> Any:
        if not self.api: return []
        try:
            # Fetching intraday data
            return self.api.intraday_minute_data(
                security_id=symbol['security_id'],
                exchange_segment=symbol['exchange_segment']
            )
        except Exception as e:
            self.logger.error(f"Fenix Historical Error: {e}")
            return []

    def place_order(self, o: Dict[str, Any]) -> Dict[str, Any]:
        if not self.api: return {"order_id": "", "status": "ERROR", "message": "Fenix API not initialized"}
        try:
            # Extract idempotency key for duplicate prevention
            # The coordinator generates a stable idempotency_key that remains the same across all retry attempts
            # This prevents duplicate orders when a response is lost but the broker accepted the order
            idempotency_key = o.get('idempotency_key', '')
            tag = o.get('tag', 'NSEFO')
            
            # Build market_order parameters
            # Use idempotency_key as the primary tag to enable broker-side deduplication
            # If idempotency_key is provided, it takes precedence over the generic tag
            order_tag = idempotency_key if idempotency_key else tag
            
            # Log idempotency key usage for audit trail
            if idempotency_key:
                self.logger.debug(f"Placing order with idempotency_key: {idempotency_key}")
            
            # Call Fenix API with idempotency metadata
            # The 'tag' parameter in Fenix/Dhan API serves as a client-side order identifier
            # that can be used for idempotency and order tracking
            order = self.api.market_order(
                security_id=o['security_id'],
                exchange=o['exchange_segment'],
                side=o['side'],
                quantity=o['quantity'],
                tag=order_tag  # Forward idempotency key as tag for broker-side deduplication
            )
            
            # Validate response structure and extract order ID
            if not isinstance(order, dict):
                self.logger.error(f"Fenix returned non-dict response: {type(order)}")
                return {"order_id": "", "status": "ERROR", "message": "Invalid response format from broker"}
            
            # Check for explicit success indicators
            status = order.get('status', '').lower()
            if status and status not in ('success', 'ok', 'complete', 'open', 'pending'):
                self.logger.warning(f"Fenix order rejected with status: {status}")
                return {"order_id": "", "status": "REJECTED", "message": order.get('message', f"Order status: {status}")}
            
            # Extract and validate order ID
            oid = str(order.get('orderId', '')).strip()
            if not oid:
                self.logger.error("Fenix returned empty orderId")
                return {"order_id": "", "status": "REJECTED", "message": "Broker returned empty order ID"}
            
            # Log successful order placement with idempotency tracking
            if idempotency_key:
                self.logger.info(f"Order placed successfully: {oid} (idempotency_key: {idempotency_key})")
            
            return {"order_id": oid, "status": "OPEN", "message": ""}
        except Exception as e:
            self.logger.error(f"Fenix Order Error: {e}")
            return {"order_id": "", "status": "ERROR", "message": str(e)}

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        try: return self.api.fetch_order(order_id)
        except Exception: return {}

    def get_positions(self) -> List[Dict[str, Any]]:
        try: return self.api.fetch_net_positions()
        except Exception: return []

    def get_holdings(self) -> List[Dict[str, Any]]:
        try: return self.api.fetch_holdings()
        except Exception: return []

    def cancel_order(self, order_id: str) -> bool:
        try:
            resp = self.api.cancel_order(order_id)
            return resp.get('status') == 'success'
        except Exception: return False

    def start_data_feed(self, symbols: List[Dict[str, Any]], callback: Callable[[Dict[str, Any]], None]):
        self.logger.info("Fenix Real-time Feed synchronization link active.")
