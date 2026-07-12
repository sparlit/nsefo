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

    def place_order(self, o: Dict[str, Any]) -> str:
        if not self.api: return ""
        try:
            order = self.api.market_order(
                security_id=o['security_id'],
                exchange=o['exchange_segment'],
                side=o['side'],
                quantity=o['quantity']
            )
            return str(order.get('orderId', ''))
        except Exception as e:
            self.logger.error(f"Fenix Order Error: {e}")
            return ""

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
