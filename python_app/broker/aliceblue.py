import logging
import requests
from .base import Broker
from typing import List, Dict, Any, Optional, Callable

class AliceBlueProvider(Broker):
    """
    AliceBlue broker implementation using HTTP REST API.
    Auth: client_id + app_key + access_token
    API Base: https://ant.aliceblue.com
    """
    BASE_URL = "https://ant.aliceblue.com"

    def __init__(self, client_id: str, access_token: str = "", app_key: str = ""):
        self.client_id = client_id
        self.access_token = access_token
        self.app_key = app_key
        self.logger = logging.getLogger("AliceBlueProvider")
        self.session = requests.Session()
        self.authenticated = False
        self.headers = {
            "Content-Type": "application/json",
            "X-ClientId": client_id,
            "X-AppKey": app_key,
            "X-AccessToken": access_token
        }

    def login(self, **kwargs) -> bool:
        """Authenticate with AliceBlue API using access token."""
        try:
            # Test authentication by fetching user profile
            url = f"{self.BASE_URL}/api/session/profile"
            response = self.session.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                self.authenticated = True
                self.logger.info("AliceBlue authentication successful")
                return True
            else:
                self.logger.error(f"AliceBlue auth failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            self.logger.error(f"AliceBlue Login Error: {e}")
            return False

    def get_market_data(self, symbols: List[Dict[str, str]]) -> Dict[str, Any]:
        """Fetch live market data for given symbols."""
        if not self.authenticated:
            return {"status": "error", "remarks": "Not authenticated"}
        try:
            results = {}
            for s in symbols:
                security_id = s.get('security_id')
                exchange = s.get('exchange_segment', 'NSE')
                url = f"{self.BASE_URL}/api/quote/{exchange}/{security_id}"
                response = self.session.get(url, headers=self.headers, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    results[security_id] = {"last_price": float(data.get('last_price', 0.0))}
            return {"data": results}
        except Exception as e:
            self.logger.error(f"AliceBlue Market Data Error: {e}")
            return {"status": "error", "remarks": str(e)}

    def get_historical_data(self, symbol: Dict[str, str], interval: str, from_date: str, to_date: str) -> Any:
        """Fetch historical OHLC data."""
        if not self.authenticated:
            return []
        try:
            security_id = symbol.get('security_id')
            exchange = symbol.get('exchange_segment', 'NSE')
            url = f"{self.BASE_URL}/api/historical/{exchange}/{security_id}"
            params = {"interval": interval, "from_date": from_date, "to": to_date}
            response = self.session.get(url, headers=self.headers, params=params, timeout=10)
            if response.status_code == 200:
                return response.json().get('data', [])
            return []
        except Exception as e:
            self.logger.error(f"AliceBlue Historical Data Error: {e}")
            return []

    def place_order(self, order_details: Dict[str, Any]) -> str:
        """Place a new order."""
        if not self.authenticated:
            return ""
        try:
            url = f"{self.BASE_URL}/api/orders"
            payload = {
                "symbol": order_details.get('security_id'),
                "exchange": order_details.get('exchange_segment', 'NSE'),
                "transaction_type": order_details.get('side', 'BUY'),
                "quantity": int(order_details.get('quantity', 0)),
                "order_type": order_details.get('order_type', 'MARKET'),
                "product_type": order_details.get('product_type', 'MARGIN'),
                "price": float(order_details.get('price', 0)),
                "trigger_price": float(order_details.get('trigger_price', 0))
            }
            response = self.session.post(url, json=payload, headers=self.headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return str(data.get('order_id', ''))
            self.logger.warning(f"AliceBlue Order Rejected: {response.text}")
            return ""
        except Exception as e:
            self.logger.error(f"AliceBlue Order Error: {e}")
            return ""

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get order status by order ID."""
        if not self.authenticated:
            return {}
        try:
            url = f"{self.BASE_URL}/api/orders/{order_id}"
            response = self.session.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                return response.json()
            return {}
        except Exception as e:
            self.logger.error(f"AliceBlue Order Status Error: {e}")
            return {}

    def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions."""
        if not self.authenticated:
            return []
        try:
            url = f"{self.BASE_URL}/api/positions"
            response = self.session.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                return response.json().get('data', [])
            return []
        except Exception as e:
            self.logger.error(f"AliceBlue Positions Error: {e}")
            return []

    def get_holdings(self) -> List[Dict[str, Any]]:
        """Get holdings."""
        if not self.authenticated:
            return []
        try:
            url = f"{self.BASE_URL}/api/holdings"
            response = self.session.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                return response.json().get('data', [])
            return []
        except Exception as e:
            self.logger.error(f"AliceBlue Holdings Error: {e}")
            return []

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an existing order."""
        if not self.authenticated:
            return False
        try:
            url = f"{self.BASE_URL}/api/orders/{order_id}/cancel"
            response = self.session.delete(url, headers=self.headers, timeout=10)
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"AliceBlue Cancel Order Error: {e}")
            return False

    def start_data_feed(self, symbols: List[Dict[str, Any]], callback: Callable[[Dict[str, Any]], None]):
        """Start real-time data feed (websocket-based)."""
        self.logger.info("AliceBlue Real-time Feed - WebSocket connection would be established here.")
        # Note: AliceBlue uses WebSocket for real-time data
        # This would require websocket-client library for full implementation