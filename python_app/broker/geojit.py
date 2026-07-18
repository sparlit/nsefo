"""
Geojit Broker Implementation (HTTP REST)
Auth: client_id + password + yob (YearOfBirth) → access_token
API Docs: https://api.geojit.com
"""
import logging
from typing import List, Dict, Any, Optional, Callable
from urllib.parse import urlencode

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore

from .base import Broker

BASE_URL = "https://api.geojit.com"


class GeojitProvider(Broker):
    """
    Geojit BNP Paribas broker implementation.
    Login uses client_id + password + YearOfBirth.
    Subsequent calls use Authorization: Bearer {access_token}.
    """

    def __init__(self, client_id: str = "", password: str = "", yob: str = "", access_token: str = "", **kwargs):
        self.client_id = client_id
        self.password = password
        self.yob = yob
        self.access_token = access_token
        self.verify_ssl = kwargs.get("verify_ssl", True)
        self._headers = {
            "Accept": "application/json",
        }
        self.logger = logging.getLogger("GeojitProvider")
        self.authenticated = False
        self._client: Optional[httpx.Client] = None

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(base_url=BASE_URL, verify=self.verify_ssl, timeout=15.0)
        return self._client

    def login(self, **kwargs) -> bool:
        """POST /v1/login — Geojit requires application/x-www-form-urlencoded."""
        if httpx is None:
            self.logger.error("httpx is not installed. Run: pip install httpx")
            return False
        try:
            client_id = kwargs.get("client_id", self.client_id)
            password = kwargs.get("password", self.password)
            yob = kwargs.get("yob", self.yob)

            payload = {
                "client_id": client_id,
                "password": password,
                "yob": yob,
            }
            client = self._get_client()
            headers = {**self._headers, "Content-Type": "application/x-www-form-urlencoded"}
            resp = client.post("/v1/login", content=urlencode(payload), headers=headers)
            resp.raise_for_status()
            data = resp.json()

            # Geojit returns access_token in response body or a session token
            token = data.get("access_token") or data.get("data", {}).get("access_token") or ""
            if not token:
                # Fallback: treat the whole data as token source
                token = data.get("token") or data.get("session_token") or ""

            if token:
                self.access_token = token
                self._headers["Authorization"] = f"Bearer {self.access_token}"
                self.authenticated = True
                self.logger.info("Geojit login successful.")
                return True

            self.logger.warning(f"Geojit login response missing token: {data}")
            return False
        except Exception as e:
            self.logger.error(f"Geojit Login Error: {e}")
            return False

    def get_market_data(self, symbols: List[Dict[str, str]]) -> Dict[str, Any]:
        """GET /v1/quote?exch=NSE&symbol=RELIANCE"""
        if not self.authenticated or httpx is None:
            return {"data": {}}
        try:
            results = {}
            for s in symbols:
                exch = s.get("exchange_segment", "NSE").upper()
                sid = s.get("security_id", "")
                client = self._get_client()
                resp = client.get(
                    "/v1/quote",
                    params={"exch": exch, "symbol": sid},
                    headers=self._headers,
                )
                resp.raise_for_status()
                item = resp.json()
                results[sid] = {
                    "last_price": item.get("lp", item.get("last_price", 0.0)),
                    "change": item.get("ch", item.get("change", 0.0)),
                    "percent_change": item.get("chp", item.get("percent_change", 0.0)),
                    "open": item.get("open", 0.0),
                    "high": item.get("high", 0.0),
                    "low": item.get("low", 0.0),
                    "close": item.get("prev_close", item.get("close", 0.0)),
                }
            return {"data": results}
        except Exception as e:
            self.logger.error(f"Geojit Market Data Error: {e}")
            return {"data": {}}

    def get_historical_data(
        self, symbol: Dict[str, str], interval: str, from_date: str, to_date: str
    ) -> Any:
        """GET /v1/historical?exch=NSE&symbol=RELIANCE&interval=1d&from=...&to=..."""
        if not self.authenticated or httpx is None:
            return []
        try:
            exch = symbol.get("exchange_segment", "NSE").upper()
            sid = symbol.get("security_id", "")
            client = self._get_client()
            resp = client.get(
                "/v1/historical",
                params={"exch": exch, "symbol": sid, "interval": interval, "from_date": from_date, "to": to_date},
                headers=self._headers,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            # Geojit historical response structure — adapt to standard candles list
            candles = data.get("candles", data.get("data", []))
            return candles
        except Exception as e:
            self.logger.error(f"Geojit Historical Data Error: {e}")
            return []

    def place_order(self, order_details: Dict[str, Any]) -> Dict[str, Any]:
        """POST /v1/orders. Returns {"order_id": str, "status": str, "message": str}."""
        if not self.authenticated or httpx is None:
            return {"order_id": "", "status": "ERROR", "message": "Not authenticated or httpx unavailable"}
        try:
            exch = order_details.get("exchange_segment", "NSE").upper()
            sid = order_details.get("security_id", "")
            payload = {
                "exchange": exch,
                "symbol": sid,
                "qty": order_details.get("quantity", 0),
                "type": order_details.get("order_type", 2),
                "side": 1 if order_details.get("side", "BUY") == "BUY" else -1,
                "product_type": order_details.get("product_type", "MARGIN"),
                "price": order_details.get("price", 0),
                "trigger_price": order_details.get("trigger_price", 0),
            }
            client = self._get_client()
            resp = client.post("/v1/orders", json=payload, headers=self._headers)
            resp.raise_for_status()
            data = resp.json()
            order_id = ""
            if isinstance(data, dict):
                order_id = str(data.get("order_id") or data.get("data", {}).get("order_id", ""))
            return {"order_id": order_id, "status": "OPEN" if order_id else "ERROR", "message": "" if order_id else "No order_id in Geojit response"}
        except Exception as e:
            self.logger.error(f"Geojit Place Order Error: {e}")
            return {"order_id": "", "status": "ERROR", "message": str(e)}

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """GET /v1/orders/{order_id}"""
        if not self.authenticated or httpx is None:
            return {}
        try:
            client = self._get_client()
            resp = client.get(f"/v1/orders/{order_id}", headers=self._headers, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            self.logger.error(f"Geojit Order Status Error: {e}")
            return {}

    def get_positions(self) -> List[Dict[str, Any]]:
        """GET /v1/positions"""
        if not self.authenticated or httpx is None:
            return []
        try:
            client = self._get_client()
            resp = client.get("/v1/positions", headers=self._headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict):
                return data.get("data", data.get("positions", []))
            return data if isinstance(data, list) else []
        except Exception as e:
            self.logger.error(f"Geojit Positions Error: {e}")
            return []

    def get_holdings(self) -> List[Dict[str, Any]]:
        """GET /v1/holdings"""
        if not self.authenticated or httpx is None:
            return []
        try:
            client = self._get_client()
            resp = client.get("/v1/holdings", headers=self._headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict):
                return data.get("data", data.get("holdings", []))
            return data if isinstance(data, list) else []
        except Exception as e:
            self.logger.error(f"Geojit Holdings Error: {e}")
            return []

    def cancel_order(self, order_id: str) -> bool:
        """DELETE /v1/orders/{order_id}"""
        if not self.authenticated or httpx is None:
            return False
        try:
            client = self._get_client()
            resp = client.delete(f"/v1/orders/{order_id}", headers=self._headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return data.get("status", False) if isinstance(data, dict) else True
        except Exception as e:
            self.logger.error(f"Geojit Cancel Order Error: {e}")
            return False

    def start_data_feed(
        self, symbols: List[Dict[str, Any]], callback: Callable[[Dict[str, Any]], None]
    ):
        self.logger.warning(
            "Geojit real-time feed via HTTP REST not implemented — use WebSocket for live data."
        )