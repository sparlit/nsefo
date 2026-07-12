# Migrated from python_app/broker/moneysukh.py — DO NOT EDIT HERE
"""
Moneysukh Broker Implementation (HTTP REST)
API Base: https://online.moneysukh.com
Auth: X-API-Key header + X-Client-Id header
Docs: https://online.moneysukh.com/
"""
import logging
import requests
from typing import List, Dict, Any, Callable
from ..base import Broker

BASE_URL = "https://online.moneysukh.com"


class MoneysukhProvider(Broker):
    """
    Moneysukh (ONUS Capital) broker integration.

    Auth method: X-API-Key and X-Client-Id as HTTP headers.
    Configure via config.json:
      client_id:  your Moneysukh client ID
      api_key:    your Moneysukh API key
    """

    def __init__(self, client_id: str = "", access_token: str = "", **kwargs):
        self.client_id = client_id
        self.api_key = kwargs.get("api_key", "")
        self.verify_ssl = kwargs.get("verify_ssl", True)
        self.session = requests.Session()
        self.logger = logging.getLogger("MoneysukhProvider")
        self._authenticated = False

    def _headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-API-Key": self.api_key,
            "X-Client-Id": self.client_id,
        }

    def login(self, **kwargs) -> bool:
        """
        Authenticate with Moneysukh API.
        Attempts POST /api/v1/login with credentials first.
        Falls back to GET /api/v1/profile if POST is unavailable.
        The real auth endpoint must be confirmed via browser Network tab inspection.
        """
        try:
            username = kwargs.get("username", "")
            password = kwargs.get("password", "")
            # Try POST login endpoint first (preferred REST auth path)
            if username and password:
                resp = self.session.post(
                    f"{BASE_URL}/api/v1/login",
                    headers={**self._headers(), "Content-Type": "application/json"},
                    json={"username": username, "password": password},
                    timeout=15,
                    verify=self.verify_ssl,
                )
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        token = (
                            data.get("data", {}).get("access_token")
                            or data.get("access_token")
                            or data.get("token")
                        )
                        if token:
                            self.session.headers["Authorization"] = f"Bearer {token}"
                        self._authenticated = True
                        self.logger.info("Moneysukh login OK (POST)")
                        return True
                    except Exception:
                        pass
            # Fallback: validate via GET /api/v1/profile if it returns JSON
            resp = self.session.get(
                f"{BASE_URL}/api/v1/profile",
                headers=self._headers(),
                timeout=15,
                verify=self.verify_ssl,
            )
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    if isinstance(data, dict):
                        self._authenticated = True
                        self.logger.info(
                            f"Moneysukh login OK: {data.get('user_name', data.get('data', {}).get('user_name', 'OK'))}"
                        )
                        return True
                except Exception:
                    pass
            self.logger.warning(
                f"Moneysukh auth check returned {resp.status_code} — response: {resp.text[:200]}"
            )
            return False
        except Exception as e:
            self.logger.error(f"Moneysukh login error: {e}")
            return False

    def get_market_data(self, symbols: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Fetch last price for given symbols.
        Symbol format: {"exchange_segment": "NSE/NFO/BSE", "security_id": "<symbol>"}
        """
        if not self._authenticated:
            return {"data": {}}
        try:
            results = {}
            for sym in symbols:
                seg = sym.get("exchange_segment", "NSE").upper()
                sid = sym.get("security_id", "")
                # Moneysukh likely uses standard /quote endpoint
                resp = self.session.get(
                    f"{BASE_URL}/api/v1/quote",
                    headers=self._headers(),
                    params={"symbol": sid, "exchange": seg},
                    timeout=10,
                    verify=self.verify_ssl,
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
            return {"data": results}
        except Exception as e:
            self.logger.error(f"Moneysukh market data error: {e}")
            return {"data": {}}

    def get_historical_data(
        self, symbol: Dict[str, str], interval: str, from_date: str, to_date: str
    ) -> Any:
        if not self._authenticated:
            return []
        try:
            sid = symbol.get("security_id", "")
            resp = self.session.get(
                f"{BASE_URL}/api/v1/historical",
                headers=self._headers(),
                params={
                    "symbol": sid,
                    "interval": interval,
                    "from_date": from_date,
                    "to": to_date,
                },
                timeout=15,
                verify=self.verify_ssl,
            )
            if resp.status_code == 200:
                return resp.json().get("data", [])
            return []
        except Exception as e:
            self.logger.error(f"Moneysukh historical error: {e}")
            return []

    def place_order(self, order_details: Dict[str, Any]) -> str:
        """
        Place an order.
        order_details keys: exchange_segment, security_id, side, quantity,
                           order_type, price, trigger_price, product_type
        """
        if not self._authenticated:
            return ""
        try:
            payload = {
                "exchange": order_details.get("exchange_segment", "NFO"),
                "symbol": order_details.get("security_id", ""),
                "side": order_details.get("side", "BUY").upper(),
                "quantity": int(order_details.get("quantity", 1)),
                "order_type": order_details.get("order_type", "MARKET").upper(),
                "price": float(order_details.get("price", 0)),
                "trigger_price": float(order_details.get("trigger_price", 0)),
                "product_type": order_details.get("product_type", "MARGIN").upper(),
                "variety": order_details.get("variety", "REGULAR").upper(),
            }
            resp = self.session.post(
                f"{BASE_URL}/api/v1/orders",
                headers=self._headers(),
                json=payload,
                timeout=15,
                verify=self.verify_ssl,
            )
            if resp.status_code == 200:
                data = resp.json()
                return str(
                    data.get("data", {}).get("order_id")
                    or data.get("order_id")
                    or data.get("NSE", {}).get("order_id", "")
                )
            self.logger.warning(f"Moneysukh order failed: {resp.status_code} {resp.text[:200]}")
            return ""
        except Exception as e:
            self.logger.error(f"Moneysukh order error: {e}")
            return ""

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        if not self._authenticated:
            return {}
        try:
            resp = self.session.get(
                f"{BASE_URL}/api/v1/orders/{order_id}",
                headers=self._headers(),
                timeout=10,
                verify=self.verify_ssl,
            )
            return resp.json() if resp.status_code == 200 else {}
        except Exception as e:
            self.logger.error(f"Moneysukh order status error: {e}")
            return {}

    def get_positions(self) -> List[Dict[str, Any]]:
        if not self._authenticated:
            return []
        try:
            resp = self.session.get(
                f"{BASE_URL}/api/v1/positions",
                headers=self._headers(),
                timeout=15,
                verify=self.verify_ssl,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("data", []) or data.get("positions", [])
            return []
        except Exception as e:
            self.logger.error(f"Moneysukh positions error: {e}")
            return []

    def get_holdings(self) -> List[Dict[str, Any]]:
        if not self._authenticated:
            return []
        try:
            resp = self.session.get(
                f"{BASE_URL}/api/v1/holdings",
                headers=self._headers(),
                timeout=15,
                verify=self.verify_ssl,
            )
            if resp.status_code == 200:
                return resp.json().get("data", []) or []
            return []
        except Exception as e:
            self.logger.error(f"Moneysukh holdings error: {e}")
            return []

    def cancel_order(self, order_id: str) -> bool:
        if not self._authenticated:
            return False
        try:
            resp = self.session.delete(
                f"{BASE_URL}/api/v1/orders/{order_id}",
                headers=self._headers(),
                timeout=10,
                verify=self.verify_ssl,
            )
            return resp.status_code == 200
        except Exception as e:
            self.logger.error(f"Moneysukh cancel error: {e}")
            return False

    def start_data_feed(self, symbols: List[Dict[str, Any]], callback: Callable):
        self.logger.warning(
            "Moneysukh WebSocket data feed not yet implemented. "
            "Use get_market_data() for polling."
        )