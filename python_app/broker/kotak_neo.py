"""
Kotak Neo Broker Implementation
API Docs: https://api.kotakneo.com/
Authentication: consumer_key + access_token (JWT)
"""

import logging
import requests
from .base import Broker
from typing import List, Dict, Any, Optional, Callable

BASE_URL = "https://api.kotakneo.com"


class KotakNeoProvider(Broker):
    def __init__(self, client_id: str, access_token: str, **kwargs):
        self.client_id = client_id
        self.access_token = access_token
        self.consumer_key = kwargs.get("consumer_key", "")
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
            "X-Client-Id": client_id
        })
        self.logger = logging.getLogger("KotakNeoProvider")
        self._authenticated = False

    def login(self, **kwargs) -> bool:
        """Validate session by calling profile endpoint."""
        try:
            response = self.session.get(
                f"{BASE_URL}/v2/profile",
                timeout=10
            )
            if response.status_code == 200:
                self._authenticated = True
                return True
            self.logger.warning(f"Kotak Neo login failed: {response.status_code}")
            return False
        except Exception as e:
            self.logger.error(f"Kotak Neo Login Error: {e}")
            return False

    def get_market_data(self, symbols: List[Dict[str, str]]) -> Dict[str, Any]:
        """Fetch live market quotes for given symbols."""
        try:
            results = {}
            for sym in symbols:
                security_id = sym.get("security_id")
                exchange = sym.get("exchange_segment", "NSE")
                try:
                    resp = self.session.get(
                        f"{BASE_URL}/v2/quote/{exchange}/{security_id}",
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
                "to_date": to_date,
                "interval": interval
            }
            resp = self.session.get(
                f"{BASE_URL}/v2/historical/{exchange}/{security_id}",
                params=params,
                timeout=15
            )
            if resp.status_code == 200:
                return resp.json()
            return []
        except Exception as e:
            self.logger.error(f"Historical Data Error: {e}")
            return []

    def place_order(self, order_details: Dict[str, Any]) -> str:
        """Place a new order. Returns order_id string."""
        try:
            payload = {
                "exchange": order_details.get("exchange_segment", "NSE"),
                "security_id": str(order_details.get("security_id")),
                "transaction_type": order_details.get("side", "BUY"),
                "quantity": int(order_details.get("quantity", 0)),
                "order_type": order_details.get("order_type", "MARKET"),
                "product_type": order_details.get("product_type", "MARGIN"),
                "price": float(order_details.get("price", 0)),
                "trigger_price": float(order_details.get("trigger_price", 0)),
                "validity": order_details.get("validity", "DAY")
            }
            resp = self.session.post(
                f"{BASE_URL}/v2/orders",
                json=payload,
                timeout=10
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                return str(data.get("order_id", ""))
            self.logger.warning(f"Order failed: {resp.status_code} - {resp.text}")
            return ""
        except Exception as e:
            self.logger.error(f"Order Error: {e}")
            return ""

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get order status by order_id."""
        try:
            resp = self.session.get(
                f"{BASE_URL}/v2/orders/{order_id}",
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
                f"{BASE_URL}/v2/positions",
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
                f"{BASE_URL}/v2/holdings",
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
                f"{BASE_URL}/v2/orders/{order_id}",
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

        token = self.access_token
        ws_url = "wss://streaming.kotakneo.com/stream"

        ws = websocket.WebSocketApp(
            ws_url,
            header={
                "Authorization": f"Bearer {token}",
                "X-Client-Id": self.client_id
            },
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
            on_open=on_open
        )
        thread = threading.Thread(target=ws.run_forever, daemon=True)
        thread.start()