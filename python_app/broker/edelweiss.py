"""
Edelweiss Broker Implementation (HTTP REST)
Auth: Authorization: Bearer {access_token} + X-Api-Key
API Base: https://api.edelweiss.in
"""
import logging

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore

from typing import List, Dict, Any, Optional, Callable
from .base import Broker

BASE_URL = "https://api.edelweiss.in"


class EdelweissProvider(Broker):
    """
    Edelweiss broker integration.

    Auth: Authorization: Bearer {access_token} + X-Api-Key headers.
    """

    def __init__(self, client_id: str = "", access_token: str = "", refresh_token: str = "", **kwargs):
        self.client_id = client_id
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.api_key = kwargs.get("api_key", "")
        self.verify_ssl = kwargs.get("verify_ssl", True)
        self._headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        self.logger = logging.getLogger("EdelweissProvider")
        self.authenticated = False
        self._client: Optional[httpx.Client] = None

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(base_url=BASE_URL, verify=self.verify_ssl, timeout=15.0)
        return self._client

    def _auth_headers(self) -> Dict[str, str]:
        headers = dict(self._headers)
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        if self.api_key:
            headers["X-Api-Key"] = self.api_key
        if self.client_id:
            headers["X-Client-Id"] = self.client_id
        return headers

    def login(self, client_secret: str = "", **kwargs) -> bool:
        """
        OAuth2 login for Edelweiss.
        If refresh_token is available and access_token is expired, auto-refreshes.
        Otherwise validates the existing access_token via GET /api/v1/profile.
        """
        if httpx is None:
            self.logger.error("httpx is not installed. Run: pip install httpx")
            return False
        try:
            # Auto-refresh if refresh_token is available and access_token exists
            if self.refresh_token and self.access_token and client_secret:
                refresh_resp = self._get_client().post(
                    "/oauth/token",
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": self.refresh_token,
                        "client_id": self.client_id,
                        "client_secret": client_secret,
                    },
                    timeout=15,
                )
                if refresh_resp.status_code == 200:
                    tokens = refresh_resp.json()
                    self.access_token = tokens.get("access_token", self.access_token)
                    self.refresh_token = tokens.get("refresh_token", self.refresh_token)
                    self.logger.info("Edelweiss token refreshed.")
            resp = self._get_client().get(
                "/api/v1/profile",
                headers=self._auth_headers(),
                timeout=15,
            )
            if resp.status_code == 200:
                self.authenticated = True
                self.logger.info("Edelweiss login OK.")
                return True
            self.logger.warning(f"Edelweiss login failed: {resp.status_code} {resp.text[:200]}")
            return False
        except Exception as e:
            self.logger.error(f"Edelweiss login error: {e}")
            return False

    def get_market_data(self, symbols: List[Dict[str, str]]) -> Dict[str, Any]:
        """GET /api/v1/quote?exchange=NSE&scrip=RELIANCE — returns last price."""
        if not self.authenticated or httpx is None:
            return {"data": {}}
        try:
            results = {}
            for sym in symbols:
                exchange = sym.get("exchange", "NSE").upper()
                sid = sym.get("security_id", sym.get("scrip", ""))
                resp = self._get_client().get(
                    "/api/v1/quote",
                    headers=self._auth_headers(),
                    params={"exchange": exchange, "scrip": sid},
                    timeout=10,
                )
                if resp.status_code == 200:
                    try:
                        d = resp.json()
                        price = (
                            d.get("data", {}).get("last_price")
                            or d.get("last_price")
                            or d.get("ltp")
                            or 0
                        )
                        results[sid] = {"last_price": float(price)}
                    except Exception:
                        results[sid] = {"last_price": 0.0}
                else:
                    results[sid] = {"last_price": 0.0}
            return {"data": results}
        except Exception as e:
            self.logger.error(f"Edelweiss market data error: {e}")
            return {"data": {}}

    def get_historical_data(
        self, symbol: Dict[str, str], interval: str, from_date: str, to_date: str
    ) -> Any:
        """GET /api/v1/historical — returns OHLCV candles."""
        if not self.authenticated or httpx is None:
            return []
        try:
            sid = symbol.get("security_id", symbol.get("scrip", ""))
            resp = self._get_client().get(
                "/api/v1/historical",
                headers=self._auth_headers(),
                params={
                    "scrip": sid,
                    "interval": interval,
                    "from_date": from_date,
                    "to": to_date,
                },
                timeout=15,
            )
            if resp.status_code == 200:
                return resp.json().get("data", [])
            return []
        except Exception as e:
            self.logger.error(f"Edelweiss historical data error: {e}")
            return []

    def place_order(self, order_details: Dict[str, Any]) -> str:
        """POST /api/v1/orders — places a new order, returns order_id string."""
        if not self.authenticated or httpx is None:
            return ""
        try:
            payload = {
                "exchange": order_details.get("exchange", "NSE"),
                "scrip": order_details.get("security_id", ""),
                "side": order_details.get("side", "BUY").upper(),
                "quantity": int(order_details.get("quantity", 1)),
                "order_type": order_details.get("order_type", "MARKET").upper(),
                "price": float(order_details.get("price", 0)),
                "trigger_price": float(order_details.get("trigger_price", 0)),
                "product_type": order_details.get("product_type", "MARGIN").upper(),
            }
            resp = self._get_client().post(
                "/api/v1/orders",
                headers=self._auth_headers(),
                json=payload,
                timeout=15,
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                return str(
                    data.get("data", {}).get("order_id")
                    or data.get("order_id")
                    or ""
                )
            self.logger.warning(f"Edelweiss order failed: {resp.status_code} {resp.text[:200]}")
            return ""
        except Exception as e:
            self.logger.error(f"Edelweiss place_order error: {e}")
            return ""

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """GET /api/v1/orders/{order_id} — returns order details dict."""
        if not self.authenticated or httpx is None:
            return {}
        try:
            resp = self._get_client().get(
                f"/api/v1/orders/{order_id}",
                headers=self._auth_headers(),
                timeout=10,
            )
            if resp.status_code == 200:
                return resp.json().get("data", {})
            return {}
        except Exception as e:
            self.logger.error(f"Edelweiss order status error: {e}")
            return {}

    def get_positions(self) -> List[Dict[str, Any]]:
        """GET /api/v1/positions — returns list of open positions."""
        if not self.authenticated or httpx is None:
            return []
        try:
            resp = self._get_client().get(
                "/api/v1/positions",
                headers=self._auth_headers(),
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("data", []) or data.get("positions", [])
            return []
        except Exception as e:
            self.logger.error(f"Edelweiss positions error: {e}")
            return []

    def get_holdings(self) -> List[Dict[str, Any]]:
        """GET /api/v1/holdings — returns list of holdings."""
        if not self.authenticated or httpx is None:
            return []
        try:
            resp = self._get_client().get(
                "/api/v1/holdings",
                headers=self._auth_headers(),
                timeout=15,
            )
            if resp.status_code == 200:
                return resp.json().get("data", []) or []
            return []
        except Exception as e:
            self.logger.error(f"Edelweiss holdings error: {e}")
            return []

    def cancel_order(self, order_id: str) -> bool:
        """DELETE /api/v1/orders/{order_id} — cancels an existing order."""
        if not self.authenticated or httpx is None:
            return False
        try:
            resp = self._get_client().delete(
                f"/api/v1/orders/{order_id}",
                headers=self._auth_headers(),
                timeout=10,
            )
            return resp.status_code in (200, 204)
        except Exception as e:
            self.logger.error(f"Edelweiss cancel_order error: {e}")
            return False

    def start_data_feed(
        self, symbols: List[Dict[str, Any]], callback: Callable[[Dict[str, Any]], None]
    ):
        self.logger.warning(
            "Edelweiss real-time data feed via HTTP REST not implemented. "
            "Use get_market_data() for polling."
        )