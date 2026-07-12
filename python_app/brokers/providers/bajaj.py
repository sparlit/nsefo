# Migrated from python_app/broker/bajaj.py — DO NOT EDIT HERE
import logging
import httpx
from ..base import Broker
from typing import List, Dict, Any, Callable

try:
    import certifi
    _HAS_CERTIFI = True
except ImportError:
    _HAS_CERTIFI = False


class BajajFinancialProvider(Broker):
    """
    Bajaj Finserv Securities API integration.
    Auth: X-Api-Key + X-Client-Id + Authorization: Bearer {access_token}.
    Docs: https://api.bajajfinservsecurities.in
    """

    def __init__(self, api_key: str, client_id: str, access_token: str):
        self.api_key = api_key
        self.client_id = client_id
        self.access_token = access_token
        self.base_url = "https://api.bajajfinservsecurities.in"
        self.logger = logging.getLogger("BajajFinancialProvider")
        self.client = None

    def _get_client(self) -> httpx.Client:
        if self.client is None:
            verify = certifi.where() if _HAS_CERTIFI else False
            self.client = httpx.Client(
                base_url=self.base_url,
                headers={
                    "X-Api-Key": self.api_key,
                    "X-Client-Id": self.client_id,
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json",
                },
                verify=verify,
                timeout=30.0,
            )
        return self.client

    def login(self, **kwargs) -> bool:
        try:
            client = self._get_client()
            response = client.get("/api/v1/profile")
            if response.status_code == 200:
                self.logger.info("Bajaj Login Successful.")
                return True
            self.logger.error(f"Bajaj Login Failed: {response.status_code} {response.text}")
            return False
        except Exception as e:
            self.logger.error(f"Bajaj Login Error: {e}")
            return False

    def get_market_data(self, symbols: List[Dict[str, str]]) -> Dict[str, Any]:
        try:
            client = self._get_client()
            results = {}
            for s in symbols:
                exchange = s.get("exchange_segment", "NSE")
                symbol = s.get("security_id", "")
                try:
                    response = client.get(
                        "/api/v1/quote",
                        params={"exchange": exchange, "scrip": symbol},
                    )
                    if response.status_code == 200:
                        data = response.json()
                        results[symbol] = {
                            "last_price": data.get("last_price", 0.0),
                            "exchange": exchange,
                        }
                    else:
                        results[symbol] = {"error": response.text}
                except Exception as e:
                    results[symbol] = {"error": str(e)}
            return {"data": results}
        except Exception as e:
            self.logger.error(f"Bajaj Market Data Error: {e}")
            return {"status": "error", "remarks": str(e)}

    def get_historical_data(self, symbol: Dict[str, str], interval: str, from_date: str, to_date: str) -> Any:
        try:
            client = self._get_client()
            exchange = symbol.get("exchange_segment", "NSE")
            sym = symbol.get("security_id", "")
            response = client.get(
                "/api/v1/historical",
                params={
                    "exchange": exchange,
                    "scrip": sym,
                    "interval": interval,
                    "from_date": from_date,
                    "to": to_date,
                },
            )
            if response.status_code == 200:
                return response.json().get("data", [])
            return []
        except Exception as e:
            self.logger.error(f"Bajaj Historical Data Error: {e}")
            return []

    def place_order(self, order_details: Dict[str, Any]) -> str:
        try:
            client = self._get_client()
            payload = {
                "exchange": order_details.get("exchange_segment", "NSE"),
                "scrip": order_details.get("security_id", ""),
                "side": order_details.get("side", "BUY").upper(),
                "quantity": int(order_details.get("quantity", 1)),
                "order_type": order_details.get("order_type", "MARKET"),
                "price": order_details.get("price", 0),
                "product_type": order_details.get("product_type", "D"),
            }
            response = client.post("/api/v1/orders", json=payload)
            if response.status_code in (200, 201):
                data = response.json()
                return str(data.get("order_id", ""))
            self.logger.error(f"Bajaj Order Failed: {response.status_code} {response.text}")
            return ""
        except Exception as e:
            self.logger.error(f"Bajaj Order Error: {e}")
            return ""

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        try:
            client = self._get_client()
            response = client.get(f"/api/v1/orders/{order_id}")
            if response.status_code == 200:
                return response.json()
            return {}
        except Exception as e:
            self.logger.error(f"Bajaj Order Status Error: {e}")
            return {}

    def get_positions(self) -> List[Dict[str, Any]]:
        try:
            client = self._get_client()
            response = client.get("/api/v1/positions")
            if response.status_code == 200:
                data = response.json()
                return data.get("data", []) if isinstance(data, dict) else data
            return []
        except Exception as e:
            self.logger.error(f"Bajaj Positions Error: {e}")
            return []

    def get_holdings(self) -> List[Dict[str, Any]]:
        try:
            client = self._get_client()
            response = client.get("/api/v1/holdings")
            if response.status_code == 200:
                data = response.json()
                return data.get("data", []) if isinstance(data, dict) else data
            return []
        except Exception as e:
            self.logger.error(f"Bajaj Holdings Error: {e}")
            return []

    def cancel_order(self, order_id: str) -> bool:
        try:
            client = self._get_client()
            response = client.delete(f"/api/v1/orders/{order_id}")
            return response.status_code in (200, 204)
        except Exception as e:
            self.logger.error(f"Bajaj Cancel Order Error: {e}")
            return False

    def start_data_feed(self, symbols: List[Dict[str, Any]], callback: Callable[[Dict[str, Any]], None]):
        self.logger.warning("Bajaj real-time data feed not implemented (requires WebSocket setup).")