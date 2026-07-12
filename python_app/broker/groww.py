import logging

try:
    import httpx
    _HAS_HTTPX = True
except ImportError:
    _HAS_HTTPX = False
    httpx = None

from .base import Broker
from typing import List, Dict, Any, Optional, Callable


class GrowwProvider(Broker):
    """
    Groww API integration.
    Auth: apiKey + accessToken via request headers.
    Docs: https://api.groww.in
    """

    BASE_URL = "https://api.groww.in/v1"

    def __init__(self, api_key: str, access_token: str):
        self.api_key = api_key
        self.access_token = access_token
        self.logger = logging.getLogger("GrowwProvider")
        self._client: Optional[httpx.Client] = None

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.BASE_URL,
                headers={
                    "apiKey": self.api_key,
                    "Authorization": f"Bearer {self.access_token}",
                },
                verify=True,
                timeout=30.0,
            )
        return self._client

    def login(self, **kwargs) -> bool:
        if not _HAS_HTTPX:
            self.logger.error("httpx not installed. Run: pip install httpx")
            return False
        try:
            resp = self._get_client().get("/user/profile")
            resp.raise_for_status()
            data = resp.json()
            return data.get("status", "").lower() == "success"
        except Exception as e:
            self.logger.error(f"Groww Login Error: {e}")
            return False

    def get_market_data(self, symbols: List[Dict[str, str]]) -> Dict[str, Any]:
        if not _HAS_HTTPX:
            return {"status": "error", "remarks": "httpx not installed"}
        try:
            results = {}
            for s in symbols:
                exchange = s.get("exchange", "NSE")
                symbol = s.get("symbol", s.get("security_id", ""))
                resp = self._get_client().get("/quote", params={"exchange": exchange, "symbol": symbol})
                resp.raise_for_status()
                results[symbol] = resp.json()
            return {"data": results}
        except Exception as e:
            self.logger.error(f"Market Data Error: {e}")
            return {"status": "error", "remarks": str(e)}

    def get_historical_data(
        self, symbol: Dict[str, str], interval: str, from_date: str, to_date: str
    ) -> Any:
        if not _HAS_HTTPX:
            self.logger.error("httpx not installed")
            return []
        try:
            exchange = symbol.get("exchange", "NSE")
            sym = symbol.get("symbol", symbol.get("security_id", ""))
            resp = self._get_client().get(
                "/historical",
                params={"exchange": exchange, "symbol": sym, "interval": interval, "from_date": from_date, "to": to_date},
            )
            resp.raise_for_status()
            return resp.json().get("data", [])
        except Exception as e:
            self.logger.error(f"Historical Data Error: {e}")
            return []

    def place_order(self, order_details: Dict[str, Any]) -> str:
        if not _HAS_HTTPX:
            self.logger.error("httpx not installed")
            return ""
        try:
            resp = self._get_client().post("/orders", json=order_details)
            resp.raise_for_status()
            data = resp.json()
            if data.get("status", "").lower() == "success":
                return str(data.get("data", {}).get("order_id", ""))
            self.logger.warning(f"Order Rejected: {data.get('remarks', '')}")
            return ""
        except Exception as e:
            self.logger.error(f"Order failure: {e}")
            return ""

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        if not _HAS_HTTPX:
            return {}
        try:
            resp = self._get_client().get(f"/orders/{order_id}")
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            self.logger.error(f"Order Status Error: {e}")
            return {}

    def get_positions(self) -> List[Dict[str, Any]]:
        if not _HAS_HTTPX:
            return []
        try:
            resp = self._get_client().get("/positions")
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", []) if data.get("status", "").lower() == "success" else []
        except Exception as e:
            self.logger.error(f"Positions Error: {e}")
            return []

    def get_holdings(self) -> List[Dict[str, Any]]:
        if not _HAS_HTTPX:
            return []
        try:
            resp = self._get_client().get("/holdings")
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", []) if data.get("status", "").lower() == "success" else []
        except Exception as e:
            self.logger.error(f"Holdings Error: {e}")
            return []

    def cancel_order(self, order_id: str) -> bool:
        if not _HAS_HTTPX:
            return False
        try:
            resp = self._get_client().delete(f"/orders/{order_id}")
            resp.raise_for_status()
            return resp.json().get("status", "").lower() == "success"
        except Exception as e:
            self.logger.error(f"Cancel Order Error: {e}")
            return False

    def start_data_feed(
        self, symbols: List[Dict[str, Any]], callback: Callable[[Dict[str, Any]], None]
    ):
        self.logger.warning("Groww real-time feed not implemented (requires WebSocket setup).")