import logging
import requests
from .base import Broker
from typing import List, Dict, Any, Callable


class VPCProvider(Broker):
    """
    DEPRECATED — VPC Traders API is unverified/inactive.

    VPC (formerly Ventura Securities) previously provided REST APIs,
    but https://www.vpcapis.com returns HTTP 404 for all endpoints.
    Their current trading API base URL is not publicly documented.

    STATUS: Do NOT use — requires manual API discovery with VPC support.
    For trading, switch to a supported broker (Zerodha, AngelOne, Dhan, etc.).

    Auth: client_id + access_token (API key / session token).
    """

    DEPRECATED = True

    def __init__(self, client_id: str = "", access_token: str = "", **kwargs):
        super().__init__()
        self.client_id = client_id
        self.access_token = access_token
        self.logger = logging.getLogger("VPCProvider")
        self.logger.warning(
            "VPCProvider is DEPRECATED. "
            "https://www.vpcapis.com returns 404. "
            "Use a supported broker instead."
        )
        self.base_url = ""  # No verified URL — do not use
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Client-Id": self.client_id
        }

    def _post(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            resp = requests.post(
                f"{self.base_url}{endpoint}",
                json=payload,
                headers=self.headers,
                timeout=15
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            self.logger.error(f"VPC HTTP Error ({endpoint}): {e}")
            return {}

    def _get(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        try:
            resp = requests.get(
                f"{self.base_url}{endpoint}",
                params=params,
                headers=self.headers,
                timeout=15
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            self.logger.error(f"VPC HTTP GET Error ({endpoint}): {e}")
            return {}

    def login(self, **kwargs) -> bool:
        try:
            # Validate session by hitting a profile or funds endpoint
            resp = self._post("/v3/auth/validate", {"client_id": self.client_id})
            return resp.get("status") == "success" or resp.get("Status") == "Success"
        except Exception as e:
            self.logger.error(f"VPC Login Error: {e}")
            return False

    def get_market_data(self, symbols: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        symbols: [{"security_id": "<token>", "exchange_segment": "NSE_FO"}]
        Returns {data: {security_id: {last_price}}}
        """
        try:
            results = {}
            for s in symbols:
                token = s.get("security_id")
                exchange = s.get("exchange_segment", "NSE_FO")
                resp = self._get(
                    "/v3/market/ltp",
                    {"exchange": exchange, "token": token}
                )
                if resp and resp.get("data"):
                    results[token] = {"last_price": float(resp["data"].get("last_price", 0.0))}
                else:
                    results[token] = {"last_price": 0.0}
            return {"data": results}
        except Exception as e:
            self.logger.error(f"VPC Market Data Error: {e}")
            return {"status": "error", "remarks": str(e)}

    def get_historical_data(self, symbol: Dict[str, str], interval: str, from_date: str, to_date: str) -> Any:
        try:
            exchange = symbol.get("exchange_segment", "NSE_FO")
            token = symbol.get("security_id")
            resp = self._get(
                "/v3/market/historical",
                {
                    "exchange": exchange,
                    "token": token,
                    "interval": interval,
                    "from_date": from_date,
                    "to": to_date
                }
            )
            return resp.get("data", []) if resp else []
        except Exception as e:
            self.logger.error(f"VPC Historical Error: {e}")
            return []

    def place_order(self, o: Dict[str, Any]) -> str:
        try:
            payload = {
                "exchange": o.get("exchange_segment", "NSE_FO"),
                "symbol": o.get("security_id"),
                "side": o.get("side", "BUY").upper(),
                "quantity": int(o.get("quantity", 1)),
                "order_type": o.get("order_type", "MARKET"),
                "price": o.get("price", 0),
                "trigger_price": o.get("trigger_price", 0),
                "product_type": o.get("product_type", "D")
            }
            resp = self._post("/v3/orders/place", payload)
            if resp and resp.get("status") == "success":
                return str(resp.get("data", {}).get("order_id", ""))
            return ""
        except Exception as e:
            self.logger.error(f"VPC Order Error: {e}")
            return ""

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        try:
            resp = self._get("/v3/orders/status", {"order_id": order_id})
            return resp if resp else {}
        except Exception as e:
            self.logger.error(f"VPC Order Status Error: {e}")
            return {}

    def get_positions(self) -> List[Dict[str, Any]]:
        try:
            resp = self._get("/v3/portfolio/positions")
            if resp and resp.get("status") == "success":
                return resp.get("data", [])
            return []
        except Exception as e:
            self.logger.error(f"VPC Positions Error: {e}")
            return []

    def get_holdings(self) -> List[Dict[str, Any]]:
        try:
            resp = self._get("/v3/portfolio/holdings")
            if resp and resp.get("status") == "success":
                return resp.get("data", [])
            return []
        except Exception as e:
            self.logger.error(f"VPC Holdings Error: {e}")
            return []

    def cancel_order(self, order_id: str) -> bool:
        try:
            resp = self._post("/v3/orders/cancel", {"order_id": order_id})
            return resp.get("status") == "success"
        except Exception as e:
            self.logger.error(f"VPC Cancel Order Error: {e}")
            return False

    def start_data_feed(self, symbols: List[Dict[str, Any]], callback: Callable[[Dict[str, Any]], None]):
        self.logger.info("VPC Real-time Feed not implemented (requires WebSocket connection).")