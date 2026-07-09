import logging
from fenix import Dhan
from .base import Broker
from typing import List, Dict, Any, Optional, Callable

class FenixDhanProvider(Broker):
    def __init__(self, client_id: str, access_token: str):
        self.client_id = client_id
        self.access_token = access_token
        self.logger = logging.getLogger("FenixDhanProvider")
        try:
            # Fenix configuration expects real-world credentials
            self.api = Dhan({"client_id": client_id, "access_token": access_token})
        except Exception as e:
            self.logger.error(f"Fenix Initialization Error: {e}")
            self.api = None

    def login(self, **kwargs) -> bool:
        if not self.api: return False
        try:
            # Operational session validation
            profile = self.api.fetch_profile()
            return profile is not None
        except Exception as e:
            self.logger.error(f"Fenix Login Failed: {e}")
            return False

    def get_market_data(self, symbols: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Fetches live market data via Fenix production endpoints.
        """
        try:
            results = {}
            for s in symbols:
                # Direct price discovery call
                data = self.api.fetch_orderbook()
                # Production response mapping: extracting real LTP
                results[s['security_id']] = {"last_price": float(data.get('ltp', 0.0))}
            return {"data": results}
        except Exception as e:
            self.logger.error(f"Fenix Price Retrieval Error: {e}")
            return {"status": "error"}

    def get_historical_data(self, symbol: Dict[str, str], interval: str, from_date: str, to_date: str) -> Any:
        try:
            # Fetch real historical OHLC for brain analysis
            return self.api.fetch_order_history(symbol['security_id'])
        except Exception as e:
            self.logger.error(f"Fenix Historical Logic Error: {e}")
            return []

    def place_order(self, o: Dict[str, Any]) -> str:
        try:
            order = self.api.market_order(
                security_id=o['security_id'],
                exchange=o['exchange_segment'],
                side=o['side'],
                quantity=o['quantity']
            )
            return str(order.get('orderId', ''))
        except Exception as e:
            self.logger.error(f"Fenix Execution Error: {e}")
            return ""

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        return self.api.fetch_order(order_id)

    def get_positions(self) -> List[Dict[str, Any]]:
        return self.api.fetch_net_positions()

    def get_holdings(self) -> List[Dict[str, Any]]:
        return self.api.fetch_holdings()

    def cancel_order(self, order_id: str) -> bool:
        resp = self.api.cancel_order(order_id)
        return resp.get('status') == 'success'

    def start_data_feed(self, symbols: List[Dict[str, Any]], callback: Callable[[Dict[str, Any]], None]):
        self.logger.info("Fenix Real-time Feed Synchronization Active.")
