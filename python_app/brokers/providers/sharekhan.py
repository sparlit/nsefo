# Migrated from python_app/broker/sharekhan.py — DO NOT EDIT HERE
"""
Sharekhan Broker Implementation (HTTP REST)
Auth: sk_app_key + access_token (OAuth flow)
API Docs: https://newtrade.sharekhan.com/sk/api
Note: Sharekhan was acquired by Mirae Asset — Mirae endpoints may be used.
"""
import logging
from typing import List, Dict, Any, Optional, Callable

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore

from ..base import Broker

BASE_URL = "https://newtrade.sharekhan.com/sk/api"


class SharekhanProvider(Broker):
    """
    Sharekhan broker implementation.
    Auth: sk_app_key (API key) + access_token from OAuth.
    Headers: sk_app_key + Authorization: Bearer {access_token}
    """

    def __init__(self, client_id: str = "", sk_app_key: str = "", access_token: str = "", **kwargs):
        self.client_id = client_id
        self.sk_app_key = sk_app_key
        self.access_token = access_token
        self.verify_ssl = kwargs.get("verify_ssl", True)
        self._headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "sk_app_key": sk_app_key,
        }
        self.logger = logging.getLogger("SharekhanProvider")
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
        return headers

    def login(self, **kwargs) -> bool:
        """GET /v1/profile — validates sk_app_key + access_token headers."""
        if httpx is None:
            self.logger.error("httpx is not installed. Run: pip install httpx")
            return False
        try:
            # Allow override via kwargs
            sk_app_key = kwargs.get("sk_app_key", self.sk_app_key)
            access_token = kwargs.get("access_token", self.access_token)

            if not access_token:
                self.logger.error("Sharekhan access_token is required for login.")
                return False

            self.sk_app_key = sk_app_key
            self.access_token = access_token
            self._headers["sk_app_key"] = self.sk_app_key

            client = self._get_client()
            resp = client.get(
                "/v1/profile",
                headers=self._auth_headers(),
                timeout=10,
            )
            if resp.status_code == 200:
                self.authenticated = True
                self.logger.info("Sharekhan session validated.")
                return True

            self.logger.warning(f"Sharekhan login failed with status {resp.status_code}: {resp.text}")
            return False
        except Exception as e:
            self.logger.error(f"Sharekhan Login Error: {e}")
            return False

    def get_market_data(self, symbols: List[Dict[str, str]]) -> Dict[str, Any]:
        """GET /v1/quote?exchange=NSE&script=RELIANCE"""
        if not self.authenticated or httpx is None:
            return {"data": {}}
        try:
            results = {}
            for s in symbols:
                exchange = s.get("exchange_segment", "NSE").upper()
                sid = s.get("security_id", "")
                client = self._get_client()
                resp = client.get(
                    "/v1/quote",
                    params={"exchange": exchange, "script": sid},
                    headers=self._auth_headers(),
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
            self.logger.error(f"Sharekhan Market Data Error: {e}")
            return {"data": {}}

    def get_historical_data(
        self, symbol: Dict[str, str], interval: str, from_date: str, to_date: str
    ) -> Any:
        """GET /v1/historical?exchange=NSE&script=RELIANCE&interval=1d&from=...&to=..."""
        if not self.authenticated or httpx is None:
            return []
        try:
            exchange = symbol.get("exchange_segment", "NSE").upper()
            sid = symbol.get("security_id", "")
            client = self._get_client()
            resp = client.get(
                "/v1/historical",
                params={"exchange": exchange, "script": sid, "interval": interval, "from_date": from_date, "to": to_date},
                headers=self._auth_headers(),
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            candles = data.get("candles", data.get("data", []))
            return candles
        except Exception as e:
            self.logger.error(f"Sharekhan Historical Data Error: {e}")
            return []

    def place_order(self, order_details: Dict[str, Any]) -> str:
        """POST /v1/orders"""
        if not self.authenticated or httpx is None:
            return ""
        try:
            exchange = order_details.get("exchange_segment", "NSE").upper()
            sid = order_details.get("security_id", "")
            payload = {
                "exchange": exchange,
                "script": sid,
                "qty": order_details.get("quantity", 0),
                "type": order_details.get("order_type", 2),  # 2 = MARKET
                "side": 1 if order_details.get("side", "BUY") == "BUY" else -1,
                "product_type": order_details.get("product_type", "MARGIN"),
                "price": order_details.get("price", 0),
                "trigger_price": order_details.get("trigger_price", 0),
            }
            client = self._get_client()
            resp = client.post("/v1/orders", json=payload, headers=self._auth_headers())
            resp.raise_for_status()
            data = resp.json()
            order_id = ""
            if isinstance(data, dict):
                order_id = data.get("order_id") or data.get("data", {}).get("order_id", "")
            return str(order_id)
        except Exception as e:
            self.logger.error(f"Sharekhan Place Order Error: {e}")
            return ""

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """GET /v1/orders/{order_id}"""
        if not self.authenticated or httpx is None:
            return {}
        try:
            client = self._get_client()
            resp = client.get(
                f"/v1/orders/{order_id}",
                headers=self._auth_headers(),
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            self.logger.error(f"Sharekhan Order Status Error: {e}")
            return {}

    def get_positions(self) -> List[Dict[str, Any]]:
        """GET /v1/positions"""
        if not self.authenticated or httpx is None:
            return []
        try:
            client = self._get_client()
            resp = client.get("/v1/positions", headers=self._auth_headers(), timeout=15)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict):
                return data.get("data", data.get("positions", []))
            return data if isinstance(data, list) else []
        except Exception as e:
            self.logger.error(f"Sharekhan Positions Error: {e}")
            return []

    def get_holdings(self) -> List[Dict[str, Any]]:
        """GET /v1/holdings"""
        if not self.authenticated or httpx is None:
            return []
        try:
            client = self._get_client()
            resp = client.get("/v1/holdings", headers=self._auth_headers(), timeout=15)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict):
                return data.get("data", data.get("holdings", []))
            return data if isinstance(data, list) else []
        except Exception as e:
            self.logger.error(f"Sharekhan Holdings Error: {e}")
            return []

    def cancel_order(self, order_id: str) -> bool:
        """DELETE /v1/orders/{order_id}"""
        if not self.authenticated or httpx is None:
            return False
        try:
            client = self._get_client()
            resp = client.delete(
                f"/v1/orders/{order_id}",
                headers=self._auth_headers(),
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("status", False) if isinstance(data, dict) else True
        except Exception as e:
            self.logger.error(f"Sharekhan Cancel Order Error: {e}")
            return False

    def start_data_feed(
        self, symbols: List[Dict[str, Any]], callback: Callable[[Dict[str, Any]], None]
    ):
        self.logger.warning(
            "Sharekhan real-time feed via HTTP REST not implemented — use WebSocket for live data."
        )