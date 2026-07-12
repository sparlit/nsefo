# Migrated from python_app/broker/hdfc.py — DO NOT EDIT HERE
import logging
from typing import List, Dict, Any, Optional, Callable

try:
    import httpx
except ImportError:
    httpx = None

from ..base import Broker


class HDFCSecuritiesProvider(Broker):
    """
    HDFC Securities broker implementation using HTTP REST API.
    Auth: X-Api-Key + X-Client-Code + Authorization: Bearer {access_token}
    API Base: https://api.hdfcsec.com
    """
    BASE_URL = "https://api.hdfcsec.com"

    def __init__(self, client_code: str, api_key: str = "", access_token: str = ""):
        self.client_code = client_code
        self.api_key = api_key
        self.access_token = access_token
        self.logger = logging.getLogger("HDFCSecuritiesProvider")
        self._authenticated = False
        self._client: Optional[httpx.Client] = None

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "X-Api-Key": self.api_key,
            "X-Client-Code": self.client_code,
            "Authorization": f"Bearer {self.access_token}"
        }

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(verify=True, timeout=10.0)
        return self._client

    def login(self, password: str = "", **kwargs) -> bool:
        """Authenticate with HDFC Securities API via POST /api/auth/login."""
        if httpx is None:
            self.logger.error("httpx is not installed. Install it with: pip install httpx")
            return False
        try:
            url = f"{self.BASE_URL}/api/auth/login"
            response = self._get_client().post(
                url,
                headers=self._get_headers(),
                json={"client_code": self.client_code, "password": password},
                timeout=10,
            )
            if response.status_code == 200:
                data = response.json()
                token = data.get("data", {}).get("access_token") or data.get("access_token")
                if token:
                    self.access_token = token
                self._authenticated = True
                self.logger.info("HDFC Securities authentication successful")
                return True
            else:
                self.logger.error(f"HDFC Securities auth failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            self.logger.error(f"HDFC Securities Login Error: {e}")
            return False

    def get_market_data(self, symbols: List[Dict[str, str]]) -> Dict[str, Any]:
        """Fetch live market data for given symbols."""
        if not self._authenticated:
            return {"status": "error", "remarks": "Not authenticated"}
        if httpx is None:
            return {"status": "error", "remarks": "httpx not installed"}
        try:
            results = {}
            for s in symbols:
                symbol = s.get('symbol', '')
                exchange = s.get('exchange', 'NSE')
                url = f"{self.BASE_URL}/api/marketdata/quote?exchange={exchange}&symbol={symbol}"
                response = self._get_client().get(url, headers=self._get_headers(), timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    try:
                        price = float(
                            data.get('last_price')
                            or data.get('data', {}).get('last_price')
                            or data.get('ltp')
                            or 0
                        )
                    except (ValueError, TypeError):
                        price = 0.0
                    results[symbol] = {"last_price": price}
            return {"data": results}
        except Exception as e:
            self.logger.error(f"HDFC Securities Market Data Error: {e}")
            return {"status": "error", "remarks": str(e)}

    def get_historical_data(self, symbol: Dict[str, str], interval: str, from_date: str, to_date: str) -> Any:
        """Fetch historical OHLC data."""
        if not self._authenticated:
            return []
        if httpx is None:
            return []
        try:
            sym = symbol.get('symbol', '')
            exchange = symbol.get('exchange', 'NSE')
            url = f"{self.BASE_URL}/api/marketdata/historical?exchange={exchange}&symbol={sym}"
            params = {"interval": interval, "from_date": from_date, "to": to_date}
            response = self._get_client().get(url, headers=self._get_headers(), params=params, timeout=10)
            if response.status_code == 200:
                return response.json().get('data', [])
            return []
        except Exception as e:
            self.logger.error(f"HDFC Securities Historical Data Error: {e}")
            return []

    def place_order(self, order_details: Dict[str, Any]) -> str:
        """Place a new order."""
        if not self._authenticated:
            return ""
        if httpx is None:
            return ""
        try:
            url = f"{self.BASE_URL}/api/orders"
            payload = {
                "symbol": order_details.get('symbol'),
                "exchange": order_details.get('exchange', 'NSE'),
                "transaction_type": order_details.get('side', 'BUY'),
                "quantity": int(order_details.get('quantity', 0)),
                "order_type": order_details.get('order_type', 'MARKET'),
                "product_type": order_details.get('product_type', 'MARGIN'),
                "price": float(order_details.get('price', 0)),
                "trigger_price": float(order_details.get('trigger_price', 0))
            }
            response = self._get_client().post(url, json=payload, headers=self._get_headers(), timeout=10)
            if response.status_code == 200:
                data = response.json()
                return str(data.get('order_id', ''))
            self.logger.warning(f"HDFC Securities Order Rejected: {response.text}")
            return ""
        except Exception as e:
            self.logger.error(f"HDFC Securities Order Error: {e}")
            return ""

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get order status by order ID."""
        if not self._authenticated:
            return {}
        if httpx is None:
            return {}
        try:
            url = f"{self.BASE_URL}/api/orders/{order_id}"
            response = self._get_client().get(url, headers=self._get_headers(), timeout=10)
            if response.status_code == 200:
                return response.json()
            return {}
        except Exception as e:
            self.logger.error(f"HDFC Securities Order Status Error: {e}")
            return {}

    def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions."""
        if not self._authenticated:
            return []
        if httpx is None:
            return []
        try:
            url = f"{self.BASE_URL}/api/positions"
            response = self._get_client().get(url, headers=self._get_headers(), timeout=10)
            if response.status_code == 200:
                return response.json().get('data', [])
            return []
        except Exception as e:
            self.logger.error(f"HDFC Securities Positions Error: {e}")
            return []

    def get_holdings(self) -> List[Dict[str, Any]]:
        """Get holdings."""
        if not self._authenticated:
            return []
        if httpx is None:
            return []
        try:
            url = f"{self.BASE_URL}/api/holdings"
            response = self._get_client().get(url, headers=self._get_headers(), timeout=10)
            if response.status_code == 200:
                return response.json().get('data', [])
            return []
        except Exception as e:
            self.logger.error(f"HDFC Securities Holdings Error: {e}")
            return []

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an existing order."""
        if not self._authenticated:
            return False
        if httpx is None:
            return False
        try:
            url = f"{self.BASE_URL}/api/orders/{order_id}"
            response = self._get_client().delete(url, headers=self._get_headers(), timeout=10)
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"HDFC Securities Cancel Order Error: {e}")
            return False

    def start_data_feed(self, symbols: List[Dict[str, Any]], callback: Callable[[Dict[str, Any]], None]):
        """Start real-time data feed."""
        self.logger.info("HDFC Securities Real-time Feed - Not implemented (HTTP-only provider)")