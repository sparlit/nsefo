import logging
import requests
import pyotp
from .base import Broker
from typing import List, Dict, Any, Optional, Callable

class FinvasiaProvider(Broker):
    """
    Finvasia (Shoonya) broker implementation using HTTP REST API.
    Auth: userid + password + TOTP + vendor_code + yob
    API Base: https://shoonya.com/api (or equivalent Finvasia endpoint)
    """
    BASE_URL = "https://shoonya.com/api"

    def __init__(self, client_id: str, access_token: str = "", password: str = "", 
                 vendor_code: str = "", yob: str = "", totp_secret: str = ""):
        self.client_id = client_id
        self.access_token = access_token
        self.password = password
        self.vendor_code = vendor_code
        self.yob = yob
        self.totp_secret = totp_secret
        self.logger = logging.getLogger("FinvasiaProvider")
        self.session = requests.Session()
        self.authenticated = False
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}" if access_token else "",
            "X-User-Id": client_id,
            "X-Vendor-Code": vendor_code
        }

    def _generate_totp(self) -> str:
        """Generate TOTP for authentication."""
        if self.totp_secret:
            return pyotp.TOTP(self.totp_secret).now()
        return ""

    def login(self, **kwargs) -> bool:
        """Authenticate with Finvasia Shoonya API."""
        try:
            totp = kwargs.get('totp') or self._generate_totp()
            if not totp:
                self.logger.error("TOTP required for Finvasia authentication")
                return False

            url = f"{self.BASE_URL}/auth/login"
            payload = {
                "userid": self.client_id,
                "password": self.password,
                "totp": totp,
                "vendor_code": self.vendor_code,
                "yob": self.yob
            }
            response = self.session.post(url, json=payload, headers=self.headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') or data.get('success'):
                    self.access_token = data.get('token', data.get('access_token', ''))
                    if self.access_token:
                        self.headers["Authorization"] = f"Bearer {self.access_token}"
                    self.authenticated = True
                    self.logger.info("Finvasia authentication successful")
                    return True
                else:
                    self.logger.error(f"Finvasia auth failed: {data.get('message', data)}")
            return False
        except Exception as e:
            self.logger.error(f"Finvasia Login Error: {e}")
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
                url = f"{self.BASE_URL}/market/quote"
                params = {
                    "exchange": exchange,
                    "token": security_id,
                    "mode": "LTP"
                }
                response = self.session.get(url, headers=self.headers, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('status'):
                        ltp = data.get('data', {}).get('ltp', 0.0)
                        results[security_id] = {"last_price": float(ltp)}
            return {"data": results}
        except Exception as e:
            self.logger.error(f"Finvasia Market Data Error: {e}")
            return {"status": "error", "remarks": str(e)}

    def get_historical_data(self, symbol: Dict[str, str], interval: str, from_date: str, to_date: str) -> Any:
        """Fetch historical OHLC data."""
        if not self.authenticated:
            return []
        try:
            security_id = symbol.get('security_id')
            exchange = symbol.get('exchange_segment', 'NSE')
            url = f"{self.BASE_URL}/market/historical"
            params = {
                "exchange": exchange,
                "token": security_id,
                "interval": interval,
                "from_date": from_date,
                "to": to_date
            }
            response = self.session.get(url, headers=self.headers, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('status'):
                    return data.get('data', [])
            return []
        except Exception as e:
            self.logger.error(f"Finvasia Historical Data Error: {e}")
            return []

    def place_order(self, order_details: Dict[str, Any]) -> Dict[str, Any]:
        """Place a new order. Returns {"order_id": str, "status": str, "message": str}."""
        if not self.authenticated:
            return {"order_id": "", "status": "ERROR", "message": "Not authenticated"}
        try:
            url = f"{self.BASE_URL}/orders/place"
            payload = {
                "exchange": order_details.get('exchange_segment', 'NSE'),
                "token": order_details.get('security_id', ''),
                "transaction_type": order_details.get('side', 'BUY'),
                "quantity": int(order_details.get('quantity', 0)),
                "order_type": order_details.get('order_type', 'MARKET'),
                "product_type": order_details.get('product_type', 'MARGIN'),
                "price": float(order_details.get('price', 0)),
                "trigger_price": float(order_details.get('trigger_price', 0)),
                "variety": order_details.get('variety', 'NORMAL')
            }
            response = self.session.post(url, json=payload, headers=self.headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') or data.get('success'):
                    oid = str(data.get('order_id', data.get('data', {}).get('nsefo', {}).get('order_id', '')))
                    return {"order_id": oid, "status": "OPEN", "message": ""}
                return {"order_id": "", "status": "REJECTED", "message": data.get('message', 'Finvasia rejected order')}
            return {"order_id": "", "status": "ERROR", "message": f"HTTP {response.status_code}"}
        except Exception as e:
            self.logger.error(f"Finvasia Order Error: {e}")
            return {"order_id": "", "status": "ERROR", "message": str(e)}

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get order status by order ID."""
        if not self.authenticated:
            return {}
        try:
            url = f"{self.BASE_URL}/orders/{order_id}"
            response = self.session.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') or data.get('success'):
                    return data.get('data', {})
            return {}
        except Exception as e:
            self.logger.error(f"Finvasia Order Status Error: {e}")
            return {}

    def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions."""
        if not self.authenticated:
            return []
        try:
            url = f"{self.BASE_URL}/portfolio/positions"
            response = self.session.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') or data.get('success'):
                    return data.get('data', [])
            return []
        except Exception as e:
            self.logger.error(f"Finvasia Positions Error: {e}")
            return []

    def get_holdings(self) -> List[Dict[str, Any]]:
        """Get holdings."""
        if not self.authenticated:
            return []
        try:
            url = f"{self.BASE_URL}/portfolio/holdings"
            response = self.session.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') or data.get('success'):
                    return data.get('data', [])
            return []
        except Exception as e:
            self.logger.error(f"Finvasia Holdings Error: {e}")
            return []

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an existing order."""
        if not self.authenticated:
            return False
        try:
            url = f"{self.BASE_URL}/orders/{order_id}/cancel"
            response = self.session.delete(url, headers=self.headers, timeout=10)
            if response.status_code in (200, 204):
                return True
            return False
        except Exception as e:
            self.logger.error(f"Finvasia Cancel Order Error: {e}")
            return False

    def start_data_feed(self, symbols: List[Dict[str, Any]], callback: Callable[[Dict[str, Any]], None]):
        """Start real-time data feed using WebSocket."""
        self.logger.info("Finvasia Real-time Feed - WebSocket connection would be established here.")
        # Note: Finvasia uses WebSocket for real-time market data streaming