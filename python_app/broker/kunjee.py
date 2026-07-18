"""
Kunjee Broker Implementation — DEPRECATED

DEPRECATED — Kunjee trading API is unverified/inactive.

The base URL https://api.kunjee.in is SSRF-blocked from server environments
and cannot be independently verified. The website kunjee.com is a Pakistani
real estate platform (NOT the trading API).

STATUS: Do NOT use — requires manual API discovery with Kunjee support.
For trading, switch to a supported broker (Zerodha, AngelOne, Dhan, etc.).

Authentication: client_id + api_key or access_token.
"""

import logging
import requests
from .base import Broker
from typing import List, Dict, Any, Optional, Callable

# Default base URL - should be configured via constructor
DEFAULT_BASE_URL = "https://api.kunjee.in"


class KunjeeProvider(Broker):
    def __init__(self, client_id: str, access_token: str, **kwargs):
        self.client_id = client_id
        self.access_token = access_token
        self.api_key = kwargs.get("api_key", access_token)
        self.base_url = kwargs.get("base_url", DEFAULT_BASE_URL)
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "X-Client-Id": client_id,
            "Authorization": f"Bearer {access_token}"
        })
        self.logger = logging.getLogger("KunjeeProvider")
        self._authenticated = False

    def login(self, **kwargs) -> bool:
        """Validate credentials and establish session."""
        try:
            resp = self.session.get(
                f"{self.base_url}/v1/profile",
                timeout=10
            )
            if resp.status_code == 200:
                self._authenticated = True
                return True
            self.logger.warning(f"Kunjee login failed: {resp.status_code}")
            return False
        except Exception as e:
            self.logger.error(f"Kunjee Login Error: {e}")
            return False

    def get_market_data(self, symbols: List[Dict[str, str]]) -> Dict[str, Any]:
        """Fetch live market quotes."""
        try:
            results = {}
            for sym in symbols:
                security_id = sym.get("security_id")
                exchange = sym.get("exchange_segment", "NSE")
                try:
                    resp = self.session.get(
                        f"{self.base_url}/v1/quote/{exchange}/{security_id}",
                        timeout=10
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        results[security_id] = {
                            "last_price": float(data.get("last_price", 0)),
                            "volume": data.get("volume", 0),
                            "change": data.get("change", 0)
                        }
                except Exception as e:
                    self.logger.debug(f"Quote error for {security_id}: {e}")
            return {"data": results}
        except Exception as e:
            self.logger.error(f"Market Data Error: {e}")
            return {"data": {}}

    def get_historical_data(self, symbol: Dict[str, str], interval: str,
                           from_date: str, to_date: str) -> Any:
        """Fetch historical OHLC data."""
        try:
            security_id = symbol.get("security_id")
            exchange = symbol.get("exchange_segment", "NSE")
            params = {
                "from_date": from_date,
                "to": to_date,
                "interval": interval
            }
            resp = self.session.get(
                f"{self.base_url}/v1/historical/{exchange}/{security_id}",
                params=params,
                timeout=15
            )
            if resp.status_code == 200:
                return resp.json()
            return []
        except Exception as e:
            self.logger.error(f"Historical Data Error: {e}")
            return []

    def place_order(self, order_details: Dict[str, Any]) -> Dict[str, Any]:
        """Place a new order. Returns {"order_id": str, "status": str, "message": str}."""
        try:
            payload = {
                "exchange": order_details.get("exchange_segment", "NSE"),
                "security_id": str(order_details.get("security_id")),
                "side": order_details.get("side", "BUY"),
                "quantity": int(order_details.get("quantity", 0)),
                "order_type": order_details.get("order_type", "MARKET"),
                "product_type": order_details.get("product_type", "MARGIN"),
                "price": float(order_details.get("price", 0)),
                "trigger_price": float(order_details.get("trigger_price", 0)),
                "validity": order_details.get("validity", "DAY")
            }
            resp = self.session.post(
                f"{self.base_url}/v1/orders",
                json=payload,
                timeout=10
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                oid = str(data.get("order_id", data.get("orderId", "")))
                return {"order_id": oid, "status": "OPEN", "message": ""}
            return {"order_id": "", "status": "REJECTED", "message": f"HTTP {resp.status_code}"}
        except Exception as e:
            self.logger.error(f"Order Error: {e}")
            return {"order_id": "", "status": "ERROR", "message": str(e)}

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get order status by order_id."""
        try:
            resp = self.session.get(
                f"{self.base_url}/v1/orders/{order_id}",
                timeout=10
            )
            if resp.status_code == 200:
                return resp.json()
            return {}
        except Exception as e:
            self.logger.error(f"Order Status Error: {e}")
            return {}

    def get_positions(self) -> List[Dict[str, Any]]:
        """Get all open positions."""
        try:
            resp = self.session.get(
                f"{self.base_url}/v1/positions",
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("data", data.get("positions", []))
            return []
        except Exception as e:
            self.logger.error(f"Positions Error: {e}")
            return []

    def get_holdings(self) -> List[Dict[str, Any]]:
        """Get portfolio holdings."""
        try:
            resp = self.session.get(
                f"{self.base_url}/v1/holdings",
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("data", data.get("holdings", []))
            return []
        except Exception as e:
            self.logger.error(f"Holdings Error: {e}")
            return []

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an existing order."""
        try:
            resp = self.session.delete(
                f"{self.base_url}/v1/orders/{order_id}",
                timeout=10
            )
            return resp.status_code in (200, 204)
        except Exception as e:
            self.logger.error(f"Cancel Order Error: {e}")
            return False

    def start_data_feed(self, symbols: List[Dict[str, Any]],
                        callback: Callable[[Dict[str, Any]], None]):
        """Start WebSocket data feed for real-time quotes."""
        import threading
        import websocket
        import json

        def on_message(ws, message):
            data = json.loads(message)
            callback(data)

        def on_error(ws, error):
            self.logger.error(f"WebSocket Error: {error}")

        def on_close(ws, close_status_code, close_msg):
            self.logger.info("WebSocket closed")

        def on_open(ws):
            for sym in symbols:
                ws.send(json.dumps({
                    "action": "subscribe",
                    "exchange": sym.get("exchange_segment", "NSE"),
                    "security_id": sym.get("security_id")
                }))

        ws_url = self.base_url.replace("https://", "wss://").replace("http://", "wss://") + "/stream"
        ws = websocket.WebSocketApp(
            ws_url,
            header={"Authorization": f"Bearer {self.access_token}"},
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
            on_open=on_open
        )
        thread = threading.Thread(target=ws.run_forever, daemon=True)
        thread.start()