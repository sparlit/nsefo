"""
mStock (Mirae Asset Capital Markets) broker integration.

Auth: API key + access token via request headers.
BASE_URL: https://trade.mstock.com —VERIFY THIS from browser DevTools F12 → Network tab
    during a live mStock web session before using in production.

Registration: SEBI Stock Broker INZ000163138 | NSE Member ID: 90144 | BSE Member ID: 6681

NOTE: mStock API endpoints are unverified from browser trace. The BASE_URL and all
    endpoint paths below are based on standard Mirae Asset / industry conventions.
    If login/orders fail with 404/401, open browser DevTools → Network tab on
    https://trade.mstock.com, perform a quote lookup, and copy the actual XHR URL.
    Then update BASE_URL accordingly.

Requires: httpx (pip install httpx)
"""
import logging
from typing import Any, Callable, Dict, List, Optional

try:
    import httpx

    _HAS_HTTPX = True
except ImportError:
    _HAS_HTTPX = False
    httpx = None

try:
    import certifi

    _HAS_CERTIFI = True
except ImportError:
    _HAS_CERTIFI = False
    certifi = None

from .base import Broker


class MStockProvider(Broker):
    """
    mStock by Mirae Asset Capital Markets.

    Auth: X-Api-Key (API key from mStock developer portal) + Authorization: Bearer <access_token>

    Endpoints are UNVERIFIED — must be confirmed from browser DevTools Network trace.
    If order placement fails, the BASE_URL or endpoint paths are likely incorrect.
    """

    BASE_URL = "https://trade.mstock.com"

    def __init__(
        self,
        client_id: str = "",
        access_token: str = "",
        api_key: str = "",
        verify_ssl: bool = True,
        **kwargs,
    ):
        self.client_id = client_id
        self.access_token = access_token
        self.api_key = api_key or kwargs.get("api_key", "")
        self.verify_ssl = verify_ssl
        self.logger = logging.getLogger("MStockProvider")
        self._client: Optional[httpx.Client] = None

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            verify = certifi.where() if _HAS_CERTIFI and self.verify_ssl else self.verify_ssl
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            if self.api_key:
                headers["X-Api-Key"] = self.api_key
            if self.access_token:
                headers["Authorization"] = f"Bearer {self.access_token}"
            self._client = httpx.Client(
                base_url=self.BASE_URL,
                headers=headers,
                verify=verify,
                timeout=30.0,
            )
        return self._client

    def login(self, **kwargs) -> bool:
        """
        Verify credentials by calling the profile endpoint.
        Returns True if the API key + access token are valid.
        """
        if not _HAS_HTTPX:
            self.logger.error("httpx not installed. Run: pip install httpx")
            return False
        try:
            resp = self._get_client().get("/api/v1/profile")
            if resp.status_code == 401:
                self._handle_auth_error(401)
                self.logger.warning("mStock token invalid or expired.")
                return False
            if resp.status_code == 404:
                self.logger.warning(
                    "mStock profile endpoint returns 404. BASE_URL may be wrong. "
                    "Verify actual API URL from browser DevTools on https://trade.mstock.com"
                )
                return False
            resp.raise_for_status()
            data = resp.json()
            return data.get("status", "").lower() == "success"
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                self._handle_auth_error(401)
            self.logger.error("mStock login HTTP error: %s", e)
            return False
        except Exception as e:
            self.logger.error("mStock login error: %s", e)
            return False

    def get_market_data(self, symbols: List[Dict[str, str]]) -> Dict[str, Any]:
        """Fetch live market quotes for given symbols."""
        if not _HAS_HTTPX:
            return {"status": "error", "remarks": "httpx not installed"}
        try:
            results = {}
            for s in symbols:
                exchange = s.get("exchange", "NSE")
                token = s.get("token", s.get("security_id", ""))
                resp = self._get_client().get(
                    "/api/v1/quote",
                    params={"exchange": exchange, "token": token},
                )
                resp.raise_for_status()
                results[token] = resp.json()
            return {"status": "success", "data": results}
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                self._handle_auth_error(401)
            self.logger.error("mStock market data HTTP error: %s", e)
            return {"status": "error", "remarks": str(e)}
        except Exception as e:
            self.logger.error("mStock market data error: %s", e)
            return {"status": "error", "remarks": str(e)}

    def get_historical_data(
        self,
        symbol: Dict[str, str],
        interval: str,
        from_date: str,
        to_date: str,
    ) -> Any:
        """Fetch OHLCV historical candles."""
        if not _HAS_HTTPX:
            self.logger.error("httpx not installed")
            return []
        try:
            exchange = symbol.get("exchange", "NSE")
            token = symbol.get("token", symbol.get("security_id", ""))
            resp = self._get_client().get(
                "/api/v1/historical",
                params={
                    "exchange": exchange,
                    "token": token,
                    "interval": interval,
                    "from_date": from_date,
                    "to_date": to_date,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict):
                return data.get("data", [])
            return data if isinstance(data, list) else []
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                self._handle_auth_error(401)
            self.logger.error("mStock historical HTTP error: %s", e)
            return []
        except Exception as e:
            self.logger.error("mStock historical data error: %s", e)
            return []

    def place_order(self, order_details: Dict[str, Any]) -> Dict[str, Any]:
        """Place a new order. Returns {"order_id": str, "status": str, "message": str}."""
        if not _HAS_HTTPX:
            self.logger.error("httpx not installed")
            return {"order_id": "", "status": "ERROR", "message": "httpx not available"}
        try:
            payload = {
                "exchange": order_details.get("exchange_segment", "NSE"),
                "symbol": order_details.get("security_id", order_details.get("symbol", "")),
                "side": order_details.get("side", "BUY").upper(),
                "quantity": int(order_details.get("quantity", 1)),
                "order_type": order_details.get("order_type", "MARKET"),
                "price": float(order_details.get("price", 0)),
                "product_type": order_details.get("product_type", "NRML"),
            }
            resp = self._get_client().post("/api/v1/orders", json=payload)
            if resp.status_code == 401:
                self._handle_auth_error(401)
                self.logger.warning("mStock order rejected — token may be expired.")
                return {"order_id": "", "status": "REJECTED", "message": "Token expired"}
            resp.raise_for_status()
            data = resp.json()
            if data.get("status", "").lower() == "success" or data.get("status_code") == 200:
                order_id = (
                    data.get("data", {}).get("order_id")
                    or data.get("order_id")
                    or data.get("data", {}).get("NSE", {}).get("order_id", "")
                )
                return {"order_id": str(order_id) if order_id else "", "status": "OPEN" if order_id else "ERROR", "message": "" if order_id else "No order_id in mStock response"}
            remarks = data.get("remarks", data.get("message", "Order rejected"))
            self.logger.warning("mStock order rejected: %s", remarks)
            return {"order_id": "", "status": "REJECTED", "message": str(remarks)}
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                self._handle_auth_error(401)
            self.logger.error("mStock order HTTP error: %s", e)
            return {"order_id": "", "status": "ERROR", "message": f"HTTP {e.response.status_code}"}
        except Exception as e:
            self.logger.error("mStock place_order error: %s", e)
            return {"order_id": "", "status": "ERROR", "message": str(e)}

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get status of a placed order."""
        if not _HAS_HTTPX:
            return {}
        try:
            resp = self._get_client().get(f"/api/v1/orders/{order_id}")
            if resp.status_code == 401:
                self._handle_auth_error(401)
                return {}
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            self.logger.error("mStock get_order_status error: %s", e)
            return {}

    def get_positions(self) -> List[Dict[str, Any]]:
        """Get open positions."""
        if not _HAS_HTTPX:
            return []
        try:
            resp = self._get_client().get("/api/v1/positions")
            if resp.status_code == 401:
                self._handle_auth_error(401)
                return []
            resp.raise_for_status()
            data = resp.json()
            if data.get("status", "").lower() == "success":
                return data.get("data", [])
            return []
        except Exception as e:
            self.logger.error("mStock get_positions error: %s", e)
            return []

    def get_holdings(self) -> List[Dict[str, Any]]:
        """Get holdings / collateral."""
        if not _HAS_HTTPX:
            return []
        try:
            resp = self._get_client().get("/api/v1/holdings")
            if resp.status_code == 401:
                self._handle_auth_error(401)
                return []
            resp.raise_for_status()
            data = resp.json()
            if data.get("status", "").lower() == "success":
                return data.get("data", [])
            return []
        except Exception as e:
            self.logger.error("mStock get_holdings error: %s", e)
            return []

    def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order."""
        if not _HAS_HTTPX:
            return False
        try:
            resp = self._get_client().delete(f"/api/v1/orders/{order_id}")
            if resp.status_code == 401:
                self._handle_auth_error(401)
                return False
            resp.raise_for_status()
            data = resp.json()
            return data.get("status", "").lower() == "success"
        except Exception as e:
            self.logger.error("mStock cancel_order error: %s", e)
            return False

    def start_data_feed(
        self, symbols: List[Dict[str, Any]], callback: Callable[[Dict[str, Any]], None]
    ):
        """Real-time data feed via WebSocket. Not implemented — requires mStock WebSocket URL."""
        self.logger.warning(
            "mStock real-time feed not implemented. "
            "Use REST polling (get_market_data) or implement WebSocket using "
            "mStock's wss:// endpoint from their API docs."
        )