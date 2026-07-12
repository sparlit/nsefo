import logging
from typing import List, Dict, Any, Optional, Callable

try:
    import httpx
except ImportError:
    httpx = None

from .base import Broker


class ICICIDirectProvider(Broker):
    """
    ICICI Direct broker implementation using HTTP REST API.
    Auth: X-API-Key + X-Client-Id + access_token
    API Base: https://api.icicidirect.com
    """
    BASE_URL = "https://api.icicidirect.com"

    def __init__(self, client_id: str, api_key: str = "", access_token: str = "", **kwargs):
        self.client_id = client_id
        self.api_key = api_key
        self.access_token = access_token
        self.verify_ssl = kwargs.get("verify_ssl", True)
        self.logger = logging.getLogger("ICICIDirectProvider")
        self._authenticated = False
        self._client: Optional[httpx.Client] = None

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key,
            "X-Client-Id": self.client_id,
            "Authorization": f"Bearer {self.access_token}"
        }

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(verify=self.verify_ssl, timeout=10.0)
        return self._client

    def login(self, **kwargs) -> bool:
        """Authenticate with ICICI Direct API."""
        if httpx is None:
            self.logger.error("httpx is not installed. Install it with: pip install httpx")
            return False
        try:
            url = f"{self.BASE_URL}/api/Profile"
            response = self._get_client().get(url, headers=self._get_headers())
            if response.status_code == 200:
                self._authenticated = True
                self.logger.info("ICICI Direct authentication successful")
                return True
            else:
                self.logger.error(f"ICICI Direct auth failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            self.logger.error(f"ICICI Direct Login Error: {e}")
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
                url = f"{self.BASE_URL}/api/GetQuote?Exchange={exchange}&ScripCode={symbol}"
                response = self._get_client().get(url, headers=self._get_headers(), timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    results[symbol] = {"last_price": float(data.get('last_price', 0.0))}
            return {"data": results}
        except Exception as e:
            self.logger.error(f"ICICI Direct Market Data Error: {e}")
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
            url = f"{self.BASE_URL}/api/historical?Exchange={exchange}&ScripCode={sym}"
            params = {"interval": interval, "from_date": from_date, "to": to_date}
            response = self._get_client().get(url, headers=self._get_headers(), params=params, timeout=10)
            if response.status_code == 200:
                return response.json().get('data', [])
            return []
        except Exception as e:
            self.logger.error(f"ICICI Direct Historical Data Error: {e}")
            return []

    def place_order(self, order_details: Dict[str, Any]) -> str:
        """Place a new order."""
        if not self._authenticated:
            return ""
        if httpx is None:
            return ""
        try:
            url = f"{self.BASE_URL}/api/Order"
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
            self.logger.warning(f"ICICI Direct Order Rejected: {response.text}")
            return ""
        except Exception as e:
            self.logger.error(f"ICICI Direct Order Error: {e}")
            return ""

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get order status by order ID."""
        if not self._authenticated:
            return {}
        if httpx is None:
            return {}
        try:
            url = f"{self.BASE_URL}/api/Order/{order_id}"
            response = self._get_client().get(url, headers=self._get_headers(), timeout=10)
            if response.status_code == 200:
                return response.json()
            return {}
        except Exception as e:
            self.logger.error(f"ICICI Direct Order Status Error: {e}")
            return {}

    def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions."""
        if not self._authenticated:
            return []
        if httpx is None:
            return []
        try:
            url = f"{self.BASE_URL}/api/Positions"
            response = self._get_client().get(url, headers=self._get_headers(), timeout=10)
            if response.status_code == 200:
                return response.json().get('data', [])
            return []
        except Exception as e:
            self.logger.error(f"ICICI Direct Positions Error: {e}")
            return []

    def get_holdings(self) -> List[Dict[str, Any]]:
        """Get holdings."""
        if not self._authenticated:
            return []
        if httpx is None:
            return []
        try:
            url = f"{self.BASE_URL}/api/Holdings"
            response = self._get_client().get(url, headers=self._get_headers(), timeout=10)
            if response.status_code == 200:
                return response.json().get('data', [])
            return []
        except Exception as e:
            self.logger.error(f"ICICI Direct Holdings Error: {e}")
            return []

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an existing order."""
        if not self._authenticated:
            return False
        if httpx is None:
            return False
        try:
            url = f"{self.BASE_URL}/api/Order/{order_id}"
            response = self._get_client().delete(url, headers=self._get_headers(), timeout=10)
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"ICICI Direct Cancel Order Error: {e}")
            return False

    def start_data_feed(self, symbols: List[Dict[str, Any]], callback: Callable[[Dict[str, Any]], None]):
        """Start real-time data feed."""
        self.logger.info("ICICI Direct Real-time Feed - Not implemented (HTTP-only provider)")