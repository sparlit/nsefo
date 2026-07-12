"""
Fyers Broker Implementation (HTTP REST)
Auth: client_id + access_token (Fyers API v2 token)
API Docs: https://api.fyers.in/api/v2/
"""
import logging
import requests
from typing import List, Dict, Any, Optional, Callable
from .base import Broker

BASE_URL = "https://api.fyers.in/api/v2"


class FyersProvider(Broker):
    def __init__(self, client_id: str, access_token: str = "", **kwargs):
        self.client_id = client_id
        self.access_token = access_token
        self.fyers_id = kwargs.get("fyers_id", "")
        self.session = requests.Session()
        self.logger = logging.getLogger("FyersProvider")
        self.authenticated = False
        self._headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.access_token:
            self._headers["Authorization"] = f"{self.client_id}:{self.access_token}"
            self.authenticated = True

    def _validate_token(self) -> bool:
        """Validate the access token."""
        if not self.access_token:
            return False
        try:
            resp = self.session.get(
                f"{BASE_URL}/profile",
                headers=self._headers,
                timeout=10,
            )
            return resp.status_code == 200
        except Exception:
            return False

    def login(self, **kwargs) -> bool:
        if not self.access_token:
            return False
        self._headers["Authorization"] = f"{self.client_id}:{self.access_token}"
        self.authenticated = self._validate_token()
        if self.authenticated:
            self.logger.info("Fyers session validated.")
        return self.authenticated

    def get_market_data(self, symbols: List[Dict[str, str]]) -> Dict[str, Any]:
        if not self.authenticated:
            return {"data": {}}
        try:
            symbol_list = []
            for s in symbols:
                exch = s.get("exchange_segment", "NSE").upper()
                sid = s.get("security_id", "")
                symbol_list.append(f"{exch}:{sid}")
            payload = {"symbol": symbol_list, "ohlc": 0}
            resp = self.session.post(
                "https://api.fyers.in/api/v2/market-data",
                json=payload,
                headers=self._headers,
                timeout=15,
            )
            resp.raise_for_status()
            result = resp.json()
            data_map = {}
            for item in result.get("data", []):
                sid = item.get("symbol", "").split(":")[-1]
                data_map[sid] = {
                    "last_price": item.get("lp", 0.0),
                    "change": item.get("ch", 0.0),
                    "percent_change": item.get("chp", 0.0),
                    "open": item.get("open", 0.0),
                    "high": item.get("high", 0.0),
                    "low": item.get("low", 0.0),
                    "close": item.get("prev_close", 0.0),
                }
            return {"data": data_map}
        except Exception as e:
            self.logger.error(f"Fyers Market Data Error: {e}")
            return {"data": {}}

    def get_historical_data(
        self, symbol: Dict[str, str], interval: str, from_date: str, to_date: str
    ) -> Any:
        if not self.authenticated:
            return []
        try:
            exch = symbol.get("exchange_segment", "NSE").upper()
            sid = symbol.get("security_id", "")
            symbol_str = f"{exch}:{sid}"
            payload = {
                "symbol": symbol_str,
                "resolution": interval,
                "from_date": from_date,
                "to": to_date,
            }
            resp = self.session.get(
                "https://api.fyers.in/api/v2/historical",
                params=payload,
                headers=self._headers,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            candles = data.get("candles", data.get("data", []))
            return candles
        except Exception as e:
            self.logger.error(f"Fyers Historical Data Error: {e}")
            return []

    def place_order(self, order_details: Dict[str, Any]) -> str:
        if not self.authenticated:
            return ""
        try:
            exch = order_details.get("exchange_segment", "NSE_FNO").upper()
            sid = order_details.get("security_id", "")
            payload = {
                "symbol": f"{exch}:{sid}",
                "qty": order_details.get("quantity", 0),
                "type": order_details.get("order_type", 2),  # 2= MARKET
                "side": 1 if order_details.get("side", "BUY") == "BUY" else -1,
                "productType": order_details.get("product_type", "MARGIN"),
                "limitPrice": order_details.get("price", 0),
                "stopPrice": order_details.get("trigger_price", 0),
            }
            resp = self.session.post(
                "https://api.fyers.in/api/v2/orders",
                json=[payload],
                headers=self._headers,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("s") == "ok" and data.get("data"):
                return str(data["data"][0].get("orderId", ""))
            return ""
        except Exception as e:
            self.logger.error(f"Fyers Place Order Error: {e}")
            return ""

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        if not self.authenticated:
            return {}
        try:
            resp = self.session.get(
                f"https://api.fyers.in/api/v2/orders/{order_id}",
                headers=self._headers,
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            self.logger.error(f"Fyers Order Status Error: {e}")
            return {}

    def get_positions(self) -> List[Dict[str, Any]]:
        if not self.authenticated:
            return []
        try:
            resp = self.session.get(
                "https://api.fyers.in/api/v2/positions",
                headers=self._headers,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", []) if data.get("s") == "ok" else []
        except Exception as e:
            self.logger.error(f"Fyers Positions Error: {e}")
            return []

    def get_holdings(self) -> List[Dict[str, Any]]:
        if not self.authenticated:
            return []
        try:
            resp = self.session.get(
                "https://api.fyers.in/api/v2/holdings",
                headers=self._headers,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", []) if data.get("s") == "ok" else []
        except Exception as e:
            self.logger.error(f"Fyers Holdings Error: {e}")
            return []

    def cancel_order(self, order_id: str) -> bool:
        if not self.authenticated:
            return False
        try:
            resp = self.session.delete(
                f"https://api.fyers.in/api/v2/orders/{order_id}",
                headers=self._headers,
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("s") == "ok"
        except Exception as e:
            self.logger.error(f"Fyers Cancel Order Error: {e}")
            return False

    def start_data_feed(
        self, symbols: List[Dict[str, Any]], callback: Callable[[Dict[str, Any]], None]
    ):
        self.logger.warning("Fyers real-time feed via HTTP REST not implemented — use WebSocket for live data.")