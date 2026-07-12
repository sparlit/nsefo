# Migrated from python_app/broker/sbi.py — DO NOT EDIT HERE
import logging
import httpx
from ..base import Broker
from typing import List, Dict, Any, Callable

try:
    import certifi
    _HAS_CERTIFI = True
except ImportError:
    _HAS_CERTIFI = False


class SBISecuritiesProvider(Broker):
    """
    SBI Securities API integration.
    Auth: X-APPNAME header + access_token.
    Docs: https://www.sbismart.com

    PRODUCT TYPE NOTE (NSE F&O):
      The NSE F&O segment does NOT support "D" (delivery/equity CNC).
      Valid values for F&O orders are:
        NRML — Normal (carry-forward overnight; recommended for swing/positional)
        MIS  — Margin Intraday Square-off (intraday only; auto-squared at 3:20 PM)
        CO   — Cover Order (F&O with stop-loss embedded)
      "D" will cause order rejection for futures/options contracts.
      Default is NRML (positional/trading) unless overridden.
    """

    # Map generic product types to NSE F&O product types for SBI
    _PRODUCT_TYPE_MAP = {
        "D": "NRML",   # delivery → normal (carry-forward, NOT intraday)
        "CNC": "NRML", # same
        "NRML": "NRML",
        "MIS": "MIS",
        "CO": "CO",
        "MARGIN": "NRML",
    }

    def __init__(self, app_name: str, access_token: str, verify_ssl: bool = True):
        self.app_name = app_name
        self.access_token = access_token
        self.verify_ssl = verify_ssl
        self.base_url = "https://api.sbismart.com"
        self.logger = logging.getLogger("SBISecuritiesProvider")
        self.client = None

    def _get_client(self) -> httpx.Client:
        if self.client is None:
            verify = certifi.where() if _HAS_CERTIFI and self.verify_ssl else self.verify_ssl
            self.client = httpx.Client(
                base_url=self.base_url,
                headers={
                    "X-APPNAME": self.app_name,
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json",
                },
                verify=verify,
                timeout=30.0,
            )
        return self.client

    def _translate_product_type(self, pt: str) -> str:
        """Translate generic product type to NSE F&O product type for SBI."""
        mapped = self._PRODUCT_TYPE_MAP.get(pt, pt)
        if pt != mapped:
            self.logger.debug("SBI product_type '%s' → '%s' for NSE F&O", pt, mapped)
        return mapped

    def login(self, **kwargs) -> bool:
        try:
            client = self._get_client()
            response = client.get("/api/v1/profile")
            if response.status_code == 200:
                self.logger.info("SBI Login Successful.")
                return True
            self.logger.error(f"SBI Login Failed: {response.status_code} {response.text}")
            return False
        except Exception as e:
            self.logger.error(f"SBI Login Error: {e}")
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
                        params={"exch": exchange, "symbol": symbol},
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
            self.logger.error(f"SBI Market Data Error: {e}")
            return {"status": "error", "remarks": str(e)}

    def get_historical_data(self, symbol: Dict[str, str], interval: str, from_date: str, to_date: str) -> Any:
        try:
            client = self._get_client()
            exchange = symbol.get("exchange_segment", "NSE")
            sym = symbol.get("security_id", "")
            response = client.get(
                "/api/v1/historical",
                params={
                    "exch": exchange,
                    "symbol": sym,
                    "interval": interval,
                    "from_date": from_date,
                    "to": to_date,
                },
            )
            if response.status_code == 200:
                return response.json().get("data", [])
            return []
        except Exception as e:
            self.logger.error(f"SBI Historical Data Error: {e}")
            return []

    def place_order(self, order_details: Dict[str, Any]) -> str:
        try:
            client = self._get_client()
            payload = {
                "exch": order_details.get("exchange_segment", "NSE"),
                "symbol": order_details.get("security_id", ""),
                "side": order_details.get("side", "BUY").upper(),
                "qty": int(order_details.get("quantity", 1)),
                "order_type": order_details.get("order_type", "MARKET"),
                "price": order_details.get("price", 0),
                "product_type": self._translate_product_type(
                    order_details.get("product_type", "NRML")
                ),
            }
            response = client.post("/api/v1/orders", json=payload)
            if response.status_code in (200, 201):
                data = response.json()
                return str(data.get("order_id", ""))
            self.logger.error(f"SBI Order Failed: {response.status_code} {response.text}")
            return ""
        except Exception as e:
            self.logger.error(f"SBI Order Error: {e}")
            return ""

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        try:
            client = self._get_client()
            response = client.get(f"/api/v1/orders/{order_id}")
            if response.status_code == 200:
                return response.json()
            return {}
        except Exception as e:
            self.logger.error(f"SBI Order Status Error: {e}")
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
            self.logger.error(f"SBI Positions Error: {e}")
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
            self.logger.error(f"SBI Holdings Error: {e}")
            return []

    def cancel_order(self, order_id: str) -> bool:
        try:
            client = self._get_client()
            response = client.delete(f"/api/v1/orders/{order_id}")
            return response.status_code in (200, 204)
        except Exception as e:
            self.logger.error(f"SBI Cancel Order Error: {e}")
            return False

    def start_data_feed(self, symbols: List[Dict[str, Any]], callback: Callable[[Dict[str, Any]], None]):
        self.logger.warning("SBI real-time data feed not implemented (requires WebSocket setup).")