"""
Kotak Broker Implementation (HTTP REST)
Auth: client_id + consumer_key + access_token (Kotak Securities OAuth flow)
Uses Kite Connect protocol but with Kotak-specific API keys.
Package (if available): kiteconnect (KiteConnect)
API Docs: https://api.kotaksecurities.com/
"""
import logging
import requests
from typing import List, Dict, Any, Optional, Callable
from .base import Broker

BASE_URL = "https://api.kotaksecurities.com"


class KotakProvider(Broker):
    def __init__(self, client_id: str, access_token: str = "", **kwargs):
        self.client_id = client_id
        self.consumer_key = kwargs.get("consumer_key", "")
        self.access_token = access_token
        self.session = requests.Session()
        self.logger = logging.getLogger("KotakProvider")
        self.authenticated = False
        self._headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Kotak-Api-Key": self.consumer_key,
        }
        if self.access_token:
            self._headers["Authorization"] = f"Bearer {self.access_token}"
            self.authenticated = True

    def _get_session(self) -> bool:
        """Validate session / fetch user profile."""
        if not self.access_token:
            return False
        try:
            resp = self.session.get(
                f"{BASE_URL}/api/v1/profile",
                headers=self._headers,
                timeout=10,
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
            self.logger.info("Kotak session validated.")
        return self.authenticated

    def get_market_data(self, symbols: List[Dict[str, str]]) -> Dict[str, Any]:
        if not self.authenticated:
            return {"data": {}}
        try:
            instruments = []
            for s in symbols:
                instruments.append({
                    "exchange_token": s.get("security_id", ""),
                    "exchange": s.get("exchange", "NSE"),
                    "product_type": s.get("product", "CASH"),
                })
            resp = self.session.post(
                f"{BASE_URL}/api/v1/quote",
                json={"instruments": instruments},
                headers=self._headers,
                timeout=15,
            )
            resp.raise_for_status()
            result = resp.json()
            data_map = {}
            for item in result.get("data", []):
                sid = item.get("instrument_token", item.get("tradingsymbol", ""))
                data_map[sid] = {
                    "last_price": item.get("last_price", 0.0),
                    "change": item.get("change", 0.0),
                    "percent_change": item.get("change_percent", 0.0),
                    "open": item.get("ohlc", {}).get("open", 0.0),
                    "high": item.get("ohlc", {}).get("high", 0.0),
                    "low": item.get("ohlc", {}).get("low", 0.0),
                    "close": item.get("ohlc", {}).get("close", 0.0),
                }
            return {"data": data_map}
        except Exception as e:
            self.logger.error(f"Kotak Market Data Error: {e}")
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
            resp = self.session.get(
                f"{BASE_URL}/api/v1/historical",
                params=params,
                headers=self._headers,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", []) if isinstance(data, dict) else data
        except Exception as e:
            self.logger.error(f"Kotak Historical Data Error: {e}")
            return []

    def place_order(self, order_details: Dict[str, Any]) -> Dict[str, Any]:
        """Returns {"order_id": str, "status": str, "message": str}."""
        if not self.authenticated:
            return {"order_id": "", "status": "ERROR", "message": "Not authenticated"}
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
            resp = self.session.post(
                f"{BASE_URL}/api/v1/orders",
                json=payload,
                headers=self._headers,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("order_id"):
                return {"order_id": str(data["order_id"]), "status": "OPEN", "message": ""}
            return {"order_id": "", "status": "ERROR", "message": "No order_id in Kotak response"}
        except Exception as e:
            self.logger.error(f"Kotak Place Order Error: {e}")
            return {"order_id": "", "status": "ERROR", "message": str(e)}

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        if not self.authenticated:
            return {}
        try:
            resp = self.session.get(
                f"{BASE_URL}/api/v1/orders/{order_id}",
                headers=self._headers,
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            self.logger.error(f"Kotak Order Status Error: {e}")
            return {}

    def get_positions(self) -> List[Dict[str, Any]]:
        if not self.authenticated:
            return []
        try:
            resp = self.session.get(
                f"{BASE_URL}/api/v1/positions",
                headers=self._headers,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", []) if isinstance(data, dict) else data
        except Exception as e:
            self.logger.error(f"Kotak Positions Error: {e}")
            return []

    def get_holdings(self) -> List[Dict[str, Any]]:
        if not self.authenticated:
            return []
        try:
            resp = self.session.get(
                f"{BASE_URL}/api/v1/holdings",
                headers=self._headers,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", []) if isinstance(data, dict) else data
        except Exception as e:
            self.logger.error(f"Kotak Holdings Error: {e}")
            return []

    def cancel_order(self, order_id: str) -> bool:
        if not self.authenticated:
            return False
        try:
            resp = self.session.delete(
                f"{BASE_URL}/api/v1/orders/{order_id}",
                headers=self._headers,
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("status") == "success" or data.get("order_id", "") == order_id
        except Exception as e:
            self.logger.error(f"Kotak Cancel Order Error: {e}")
            return False

    def start_data_feed(
        self, symbols: List[Dict[str, Any]], callback: Callable[[Dict[str, Any]], None]
    ):
        self.logger.warning("Kotak real-time feed via HTTP REST not implemented — use WebSocket for live data.")