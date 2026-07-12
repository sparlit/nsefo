# Migrated from python_app/broker/anand_rathi.py — DO NOT EDIT HERE
"""
Anand Rathi Broker Implementation (HTTP REST)
Auth: X-Api-Key + X-Client-Id + Authorization: Bearer {access_token}
API Base: https://api.edios.in/apis  (Omnesys NSE API)
NOTE: Anand Rathi uses the Omnesys Notice Board API for trading.
      Browser Login → Extract Token → session_manager. Auth is manual.
"""
import logging

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore

from typing import List, Dict, Any, Optional, Callable
from ..base import Broker

BASE_URL = "https://api.edios.in/apis"


class AnandRathiProvider(Broker):
    """
    Anand Rathi broker integration.

    Auth: X-Api-Key, X-Client-Id, and Authorization: Bearer {access_token} headers.
    """

    def __init__(self, client_id: str = "", access_token: str = "", **kwargs):
        self.client_id = client_id
        self.access_token = access_token
        self.api_key = kwargs.get("api_key", "")
        self._headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        self.logger = logging.getLogger("AnandRathiProvider")
        self.authenticated = False
        self._client: Optional[httpx.Client] = None

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(base_url=BASE_URL, verify=True, timeout=15.0)
        return self._client

    def _auth_headers(self) -> Dict[str, str]:
        headers = dict(self._headers)
        if self.api_key:
            headers["X-Api-Key"] = self.api_key
        if self.client_id:
            headers["X-Client-Id"] = self.client_id
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    def login(self, **kwargs) -> bool:
        """GET /api/v1/profile — validates token and sets authenticated state."""
        if httpx is None:
            self.logger.error("httpx is not installed. Run: pip install httpx")
            return False
        try:
            resp = self._get_client().get(
                "/api/v1/profile",
                headers=self._auth_headers(),
                timeout=15,
            )
            if resp.status_code == 200:
                self.authenticated = True
                self.logger.info("Anand Rathi login OK.")
                return True
            self.logger.warning(f"Anand Rathi login failed: {resp.status_code} {resp.text[:200]}")
            return False
        except Exception as e:
            self.logger.error(f"Anand Rathi login error: {e}")
            return False

    def get_market_data(self, symbols: List[Dict[str, str]]) -> Dict[str, Any]:
        """GET /api/v1/ltp — returns last traded price per symbol (Omnesys NSE)."""
        if not self.authenticated or httpx is None:
            return {"data": {}}
        try:
            results = {}
            for sym in symbols:
                exchange = sym.get("exchange", "NSE").upper()
                sid = sym.get("security_id", sym.get("symbol", ""))
                resp = self._get_client().get(
                    "/api/v1/ltp",
                    headers=self._auth_headers(),
                    params={"exchange": exchange, "symbol": sid},
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
            self.logger.error(f"Anand Rathi market data error: {e}")
            return {"data": {}}

    def get_historical_data(
        self, symbol: Dict[str, str], interval: str, from_date: str, to_date: str
    ) -> Any:
        """GET /api/v1/ohlc — returns OHLCV candles (Omnesys NSE)."""
        if not self.authenticated or httpx is None:
            return []
        try:
            sid = symbol.get("security_id", symbol.get("symbol", ""))
            resp = self._get_client().get(
                "/api/v1/ohlc",
                headers=self._auth_headers(),
                params={
                    "symbol": sid,
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
            self.logger.error(f"Anand Rathi historical data error: {e}")
            return []

    def place_order(self, order_details: Dict[str, Any]) -> str:
        """POST /api/v1/place_order — places a new order (Omnesys NSE)."""
        if not self.authenticated or httpx is None:
            return ""
        try:
            payload = {
                "exchange": order_details.get("exchange", "NSE"),
                "symbol": order_details.get("security_id", ""),
                "side": order_details.get("side", "BUY").upper(),
                "quantity": int(order_details.get("quantity", 1)),
                "order_type": order_details.get("order_type", "MARKET").upper(),
                "price": float(order_details.get("price", 0)),
                "trigger_price": float(order_details.get("trigger_price", 0)),
                "product_type": order_details.get("product_type", "MARGIN").upper(),
            }
            resp = self._get_client().post(
                "/api/v1/place_order",
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
            self.logger.warning(f"Anand Rathi order failed: {resp.status_code} {resp.text[:200]}")
            return ""
        except Exception as e:
            self.logger.error(f"Anand Rathi place_order error: {e}")
            return ""

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """GET /api/v1/orderbook — returns order details (Omnesys NSE)."""
        if not self.authenticated or httpx is None:
            return {}
        try:
            resp = self._get_client().get(
                "/api/v1/orderbook",
                headers=self._auth_headers(),
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                # Omnesys returns orderbook as list — find matching order_id
                orders = data.get("data", []) or []
                for o in orders:
                    if str(o.get("order_id", "")) == str(order_id):
                        return o
                return {}
            return {}
        except Exception as e:
            self.logger.error(f"Anand Rathi order status error: {e}")
            return {}

    def get_positions(self) -> List[Dict[str, Any]]:
        """GET /api/v1/positionbook — returns list of open positions (Omnesys NSE)."""
        if not self.authenticated or httpx is None:
            return []
        try:
            resp = self._get_client().get(
                "/api/v1/positionbook",
                headers=self._auth_headers(),
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("data", []) or data.get("positions", [])
            return []
        except Exception as e:
            self.logger.error(f"Anand Rathi positions error: {e}")
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
            self.logger.error(f"Anand Rathi holdings error: {e}")
            return []

    def cancel_order(self, order_id: str) -> bool:
        """DELETE /api/v1/cancel_order — cancels an existing order (Omnesys NSE)."""
        if not self.authenticated or httpx is None:
            return False
        try:
            resp = self._get_client().post(
                "/api/v1/cancel_order",
                headers=self._auth_headers(),
                json={"order_id": order_id},
                timeout=10,
            )
            return resp.status_code in (200, 204)
        except Exception as e:
            self.logger.error(f"Anand Rathi cancel_order error: {e}")
            return False

    def start_data_feed(
        self, symbols: List[Dict[str, Any]], callback: Callable[[Dict[str, Any]], None]
    ):
        self.logger.warning(
            "Anand Rathi real-time data feed via HTTP REST not implemented. "
            "Use get_market_data() for polling."
        )