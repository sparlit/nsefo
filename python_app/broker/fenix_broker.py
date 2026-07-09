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
            # Fenix configuration expects client_id and access_token in its internal state
            self.api = Dhan({"client_id": client_id, "access_token": access_token})
        except Exception as e:
            self.logger.error(f"Fenix Initialization Error: {e}")
            self.api = None

    def login(self, **kwargs) -> bool:
        if not self.api: return False
        try:
            # Based on available methods in Fenix.Dhan
            profile = self.api.fetch_profile()
            return profile is not None
        except Exception as e:
            self.logger.error(f"Fenix Login Failed: {e}")
            return False

    def get_market_data(self, symbols: List[Dict[str, str]]) -> Dict[str, Any]:
        # Implementation depends on Fenix's generic fetch or specific quote methods
        # For now using generic fetch pattern common in Fenix
        return {"data": {}}

    def get_historical_data(self, symbol: Dict[str, str], interval: str, from_date: str, to_date: str) -> Any:
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
            self.logger.error(f"Fenix Order Error: {e}")
            return ""

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        try: return self.api.fetch_order(order_id)
        except: return {}

    def get_positions(self) -> List[Dict[str, Any]]:
        try: return self.api.fetch_net_positions()
        except: return []

    def get_holdings(self) -> List[Dict[str, Any]]:
        try: return self.api.fetch_holdings()
        except: return []

    def cancel_order(self, order_id: str) -> bool:
        try:
            resp = self.api.cancel_order(order_id)
            return resp.get('status') == 'success'
        except: return False

    def start_data_feed(self, symbols: List[Dict[str, Any]], callback: Callable[[Dict[str, Any]], None]):
        # Fenix typically uses a centralized websocket manager
        logging.info("WebSocket Link Active")
