# Migrated from python_app/broker/angelone.py — DO NOT EDIT HERE
import logging
import requests
import pyotp
from ..base import Broker
from typing import List, Dict, Any, Optional, Callable

class AngelOneProvider(Broker):
    """
    AngelOne (SmartAPI) broker implementation using HTTP REST API.
    Auth: client_id + password + TOTP + api_key
    API Base: https://apiconnect.angelone.in/rest
    """
    BASE_URL = "https://apiconnect.angelone.in/rest"

    def __init__(self, client_id: str, access_token: str = "", api_key: str = "", password: str = "", totp_secret: str = ""):
        self.client_id = client_id
        self.access_token = access_token
        self.api_key = api_key
        self.password = password
        self.totp_secret = totp_secret
        self.logger = logging.getLogger("AngelOneProvider")
        self.session = requests.Session()
        self.authenticated = False
        self.feed_token = ""
        self.jwt_token = ""
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
            "X-Api-Key": api_key,
            "X-Client-Type": "android"
        }

    def _generate_totp(self) -> str:
        """Generate TOTP for authentication."""
        if self.totp_secret:
            return pyotp.TOTP(self.totp_secret).now()
        return ""

    def login(self, **kwargs) -> bool:
        """Authenticate with AngelOne SmartAPI using credentials and TOTP."""
        try:
            # Get TOTP if not already generated
            totp = kwargs.get('totp') or self._generate_totp()
            if not totp:
                self.logger.error("TOTP required for AngelOne authentication")
                return False

            url = f"{self.BASE_URL}/smartapi/login"
            payload = {
                "clientCode": self.client_id,
                "password": self.password,
                "totp": totp
            }
            response = self.session.post(url, json=payload, headers=self.headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('status'):
                    self.jwt_token = data.get('data', {}).get('jwtToken', '')
                    self.feed_token = data.get('data', {}).get('feedToken', '')
                    self.authenticated = True
                    # Update auth header with actual JWT
                    self.headers["Authorization"] = f"Bearer {self.jwt_token}"
                    self.logger.info("AngelOne authentication successful")
                    return True
                else:
                    self.logger.error(f"AngelOne auth failed: {data.get('message')}")
            return False
        except Exception as e:
            self.logger.error(f"AngelOne Login Error: {e}")
            return False

    def get_market_data(self, symbols: List[Dict[str, str]]) -> Dict[str, Any]:
        """Fetch live market data for given symbols."""
        if not self.authenticated:
            return {"status": "error", "remarks": "Not authenticated"}
        try:
            results = {}
            for s in symbols:
                security_id = s.get('security_id')
                exchange = s.get('exchange_segment', 'NSE')
                url = f"{self.BASE_URL}/smartapi/quote"
                params = {
                    "exchange": exchange,
                    "symboltoken": security_id,
                    "mode": "LTP"
                }
                response = self.session.get(url, headers=self.headers, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('status'):
                        ltp_data = data.get('data', {}).get('ltp', {})
                        results[security_id] = {"last_price": float(ltp_data.get('last_price', 0.0))}
            return {"data": results}
        except Exception as e:
            self.logger.error(f"AngelOne Market Data Error: {e}")
            return {"status": "error", "remarks": str(e)}

    def get_historical_data(self, symbol: Dict[str, str], interval: str, from_date: str, to_date: str) -> Any:
        """Fetch historical OHLC data."""
        if not self.authenticated:
            return []
        try:
            security_id = symbol.get('security_id')
            exchange = symbol.get('exchange_segment', 'NSE')
            url = f"{self.BASE_URL}/smartapi/candle"
            params = {
                "exchange": exchange,
                "symboltoken": security_id,
                "interval": interval,
                "fromdate": from_date,
                "todate": to_date
            }
            response = self.session.get(url, headers=self.headers, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('status'):
                    return data.get('data', [])
            return []
        except Exception as e:
            self.logger.error(f"AngelOne Historical Data Error: {e}")
            return []

    def place_order(self, order_details: Dict[str, Any]) -> str:
        """Place a new order."""
        if not self.authenticated:
            return ""
        try:
            url = f"{self.BASE_URL}/smartapi/placeorder"
            payload = {
                "variety": order_details.get('variety', 'NORMAL'),
                "tradingsymbol": order_details.get('tradingsymbol', ''),
                "symboltoken": order_details.get('security_id', ''),
                "transactiontype": order_details.get('side', 'BUY'),
                "exchange": order_details.get('exchange_segment', 'NSE'),
                "ordertype": order_details.get('order_type', 'MARKET'),
                "producttype": order_details.get('product_type', 'MARGIN'),
                "duration": order_details.get('duration', 'DAY'),
                "price": str(order_details.get('price', 0)),
                "squareoff": str(order_details.get('squareoff', 0)),
                "stoploss": str(order_details.get('stoploss', 0)),
                "quantity": str(order_details.get('quantity', 0))
            }
            response = self.session.post(url, json=payload, headers=self.headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('status'):
                    return str(data.get('data', {}).get('orderid', ''))
                else:
                    self.logger.warning(f"AngelOne Order Rejected: {data.get('message')}")
            return ""
        except Exception as e:
            self.logger.error(f"AngelOne Order Error: {e}")
            return ""

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get order status by order ID."""
        if not self.authenticated:
            return {}
        try:
            url = f"{self.BASE_URL}/smartapi/orderbook"
            response = self.session.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('status'):
                    orders = data.get('data', [])
                    for order in orders:
                        if order.get('orderid') == order_id:
                            return order
            return {}
        except Exception as e:
            self.logger.error(f"AngelOne Order Status Error: {e}")
            return {}

    def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions."""
        if not self.authenticated:
            return []
        try:
            url = f"{self.BASE_URL}/smartapi/positionbook"
            response = self.session.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('status'):
                    return data.get('data', [])
            return []
        except Exception as e:
            self.logger.error(f"AngelOne Positions Error: {e}")
            return []

    def get_holdings(self) -> List[Dict[str, Any]]:
        """Get holdings."""
        if not self.authenticated:
            return []
        try:
            url = f"{self.BASE_URL}/smartapi/holdings"
            response = self.session.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('status'):
                    return data.get('data', [])
            return []
        except Exception as e:
            self.logger.error(f"AngelOne Holdings Error: {e}")
            return []

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an existing order."""
        if not self.authenticated:
            return False
        try:
            url = f"{self.BASE_URL}/smartapi/cancelorder"
            payload = {
                "variety": "NORMAL",
                "orderid": order_id
            }
            response = self.session.post(url, json=payload, headers=self.headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get('status', False)
            return False
        except Exception as e:
            self.logger.error(f"AngelOne Cancel Order Error: {e}")
            return False

    def start_data_feed(self, symbols: List[Dict[str, Any]], callback: Callable[[Dict[str, Any]], None]):
        """Start real-time data feed using WebSocket."""
        self.logger.info("AngelOne Real-time Feed - SmartWebSocketV2 would be initialized here.")
        # Note: Full implementation would use SmartWebSocketV2 from SmartApi package
        # Requires: SmartApi.smartWebSocketV2 import