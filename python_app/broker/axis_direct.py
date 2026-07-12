"""
Axis Direct Broker Implementation (HTTP REST)
Auth: X-Api-Key + Authorization: Bearer {access_token}
Base: https://api.axisdirect.in
API Docs: https://api.axisdirect.in
"""
import logging
from typing import List, Dict, Any, Optional, Callable

try:
    import httpx
    _httpx_available = True
except ImportError:
    _httpx_available = False

from .base import Broker

BASE_URL = "https://api.axisdirect.in"


class AxisDirectProvider(Broker):
    def __init__(self, client_id: str, access_token: str = "", api_key: str = "", **kwargs):
        self.client_id = client_id
        self.api_key = api_key
        self.access_token = access_token
        self.verify_ssl = kwargs.get("verify_ssl", True)
        self.logger = logging.getLogger("AxisDirectProvider")
        self.authenticated = False
        self._headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Api-Key": self.api_key,
        }
        if self.access_token:
            self._headers["Authorization"] = f"Bearer {self.access_token}"

    def _get_session(self) -> bool:
        """Validate session / fetch user profile."""
        if not self.access_token:
            return False
        try:
            resp = httpx.get(
                f"{BASE_URL}/api/v1/profile",
                headers=self._headers,
                timeout=10,
                verify=self.verify_ssl,
            )
            self.authenticated = resp.status_code == 200
            return self.authenticated
        except Exception:
            return False

    def login(self, **kwargs) -> bool:
        if not self.access_token:
            return False
        self._headers["Authorization"] = f"Bearer {self.access_token}"
        self.authenticated = self._get_session()
        if self.authenticated:
            self.logger.info("Axis Direct session validated.")
        return self.authenticated

    def get_market_data(self, symbols: List[Dict[str, str]]) -> Dict[str, Any]:
        if not self.authenticated:
            return {"data": {}}
        try:
            data_map = {}
            for s in symbols:
                exchange = s.get("exchange", "NSE")
                scrip = s.get("security_id", s.get("symbol", ""))
                try:
                    resp = httpx.get(
                        f"{BASE_URL}/api/v1/quote",
                        params={"exchange": exchange, "scrip": scrip},
                        headers=self._headers,
                        timeout=15,
                        verify=self.verify_ssl,
                    )
                    resp.raise_for_status()
                    item = resp.json()
                    sid = item.get("instrument_token", item.get("tradingsymbol", scrip))
                    data_map[sid] = {
                        "last_price": item.get("last_price", 0.0),
                        "change": item.get("change", 0.0),
                        "percent_change": item.get("change_percent", 0.0),
                        "open": item.get("ohlc", {}).get("open", 0.0),
                        "high": item.get("ohlc", {}).get("high", 0.0),
                        "low": item.get("ohlc", {}).get("low", 0.0),
                        "close": item.get("ohlc", {}).get("close", 0.0),
                    }
                except Exception as e:
                    self.logger.error(f"Axis Direct Market Data Error for {scrip}: {e}")
            return {"data": data_map}
        except Exception as e:
            self.logger.error(f"Axis Direct Market Data Error: {e}")
            return {"data": {}}

    def get_historical_data(
        self, symbol: Dict[str, str], interval: str, from_date: str, to_date: str
    ) -> Any:
        if not self.authenticated:
            return []
        try:
            params = {
                "exchange": symbol.get("exchange", "NSE"),
                "tradingsymbol": symbol.get("security_id", ""),
                "interval": interval,
                "from_date": from_date,
                "to": to_date,
            }
            resp = httpx.get(
                f"{BASE_URL}/api/v1/historical",
                params=params,
                headers=self._headers,
                timeout=15,
                verify=self.verify_ssl,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", []) if isinstance(data, dict) else data
        except Exception as e:
            self.logger.error(f"Axis Direct Historical Data Error: {e}")
            return []

    def place_order(self, order_details: Dict[str, Any]) -> str:
        if not self.authenticated:
            return ""
        try:
            payload = {
                "exchange": order_details.get("exchange", "NSE"),
                "tradingsymbol": order_details.get("security_id", ""),
                "transaction_type": order_details.get("side", "BUY"),
                "quantity": order_details.get("quantity", 0),
                "order_type": order_details.get("order_type", "MARKET"),
                "product": order_details.get("product_type", "CNC"),
                "price": order_details.get("price", 0),
                "trigger_price": order_details.get("trigger_price", 0),
                "validity": order_details.get("validity", "DAY"),
            }
            resp = httpx.post(
                f"{BASE_URL}/api/v1/orders",
                json=payload,
                headers=self._headers,
                timeout=15,
                verify=self.verify_ssl,
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("order_id"):
                return str(data["order_id"])
            return ""
        except Exception as e:
            self.logger.error(f"Axis Direct Place Order Error: {e}")
            return ""

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        if not self.authenticated:
            return {}
        try:
            resp = httpx.get(
                f"{BASE_URL}/api/v1/orders/{order_id}",
                headers=self._headers,
                timeout=10,
                verify=self.verify_ssl,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            self.logger.error(f"Axis Direct Order Status Error: {e}")
            return {}

    def get_positions(self) -> List[Dict[str, Any]]:
        if not self.authenticated:
            return []
        try:
            resp = httpx.get(
                f"{BASE_URL}/api/v1/positions",
                headers=self._headers,
                timeout=15,
                verify=self.verify_ssl,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", []) if isinstance(data, dict) else data
        except Exception as e:
            self.logger.error(f"Axis Direct Positions Error: {e}")
            return []

    def get_holdings(self) -> List[Dict[str, Any]]:
        if not self.authenticated:
            return []
        try:
            resp = httpx.get(
                f"{BASE_URL}/api/v1/holdings",
                headers=self._headers,
                timeout=15,
                verify=self.verify_ssl,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", []) if isinstance(data, dict) else data
        except Exception as e:
            self.logger.error(f"Axis Direct Holdings Error: {e}")
            return []

    def cancel_order(self, order_id: str) -> bool:
        if not self.authenticated:
            return False
        try:
            resp = httpx.delete(
                f"{BASE_URL}/api/v1/orders/{order_id}",
                headers=self._headers,
                timeout=10,
                verify=self.verify_ssl,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("status") == "success" or data.get("order_id", "") == order_id
        except Exception as e:
            self.logger.error(f"Axis Direct Cancel Order Error: {e}")
            return False

    def start_data_feed(
        self, symbols: List[Dict[str, Any]], callback: Callable[[Dict[str, Any]], None]
    ):
        self.logger.warning("Axis Direct real-time feed via HTTP REST not implemented — use WebSocket for live data.")