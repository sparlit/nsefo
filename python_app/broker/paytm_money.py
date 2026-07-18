import logging
from .base import Broker
from typing import List, Dict, Any, Optional, Callable

try:
    import httpx
    _httpx_available = True
except ImportError:
    _httpx_available = False

try:
    import requests
    _requests_available = True
except ImportError:
    _requests_available = False


class PaytmMoneyProvider(Broker):
    """
    PaytmMoney broker implementation using HTTP REST API.
    Auth: X-Client-Id + X-Client-Secret + Bearer token
    API Base: https://api.paytmmoney.com

    ⚠️ WARNING — F&O (Futures & Options) segment NOT confirmed.
    Paytm Money primarily supports equity delivery/intraday.
    NSE F&O trading may not be available via their API.

    STATUS: Equity only (unverified F&O). For F&O trading use
    Zerodha, AngelOne, Dhan, Fyers, or any other supported broker.

    DEPRECATED = True (F&O unsupported — do not use for options trading).
    """

    DEPRECATED = True

    BASE_URL = "https://api.paytmmoney.com"

    def __init__(
        self,
        client_id: str = "",
        client_secret: str = "",
        access_token: str = "",
        use_httpx: bool = True,
        **kwargs
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = access_token
        self.use_httpx = use_httpx and _httpx_available
        self.verify_ssl = kwargs.get("verify_ssl", True)
        self.logger = logging.getLogger("PaytmMoneyProvider")
        self.logger.warning(
            "PaytmMoneyProvider: F&O segment NOT confirmed. "
            "For options trading use Zerodha, AngelOne, or Dhan."
        )
        self._session = None
        self.authenticated = False

    def _get_session(self):
        """Return a fresh requests/httpx session with auth headers."""
        if self.use_httpx and _httpx_available:
            headers = {
                "X-Client-Id": self.client_id,
                "X-Client-Secret": self.client_secret,
                "Content-Type": "application/json",
            }
            if self.access_token:
                headers["Authorization"] = f"Bearer {self.access_token}"
            return httpx.Client(verify=self.verify_ssl, headers=headers, timeout=15)
        elif _requests_available:
            session = requests.Session()
            session.headers.update({
                "X-Client-Id": self.client_id,
                "X-Client-Secret": self.client_secret,
                "Content-Type": "application/json",
            })
            if self.access_token:
                session.headers["Authorization"] = f"Bearer {self.access_token}"
            return session
        else:
            raise ImportError("Neither httpx nor requests is available")

    def login(self, **kwargs) -> bool:
        """Authenticate with PaytmMoney API using client credentials."""
        try:
            client_id = kwargs.get("client_id", self.client_id)
            client_secret = kwargs.get("client_secret", self.client_secret)
            access_token = kwargs.get("access_token", self.access_token)

            if not client_id or not client_secret:
                self.logger.error("PaytmMoney: client_id and client_secret are required")
                return False

            # Try profile endpoint to validate token / authenticate
            url = f"{self.BASE_URL}/v1/user/profile"
            headers = {
                "X-Client-Id": client_id,
                "X-Client-Secret": client_secret,
                "Content-Type": "application/json",
            }
            if access_token:
                headers["Authorization"] = f"Bearer {access_token}"

            if self.use_httpx and _httpx_available:
                client = httpx.Client(verify=self.verify_ssl, timeout=10)
                response = client.get(url, headers=headers)
            elif _requests_available:
                response = requests.get(url, headers=headers, timeout=10)
            else:
                raise ImportError("Neither httpx nor requests is available")

            if response.status_code in (200, 201):
                self.client_id = client_id
                self.client_secret = client_secret
                self.access_token = access_token or ""
                self.authenticated = True
                self.logger.info("PaytmMoney authentication successful")
                return True
            else:
                self.logger.warning(f"PaytmMoney auth failed: {response.status_code} {response.text}")
                return False

        except ImportError:
            self.logger.error("PaytmMoney: httpx or requests library required but not installed")
            return False
        except Exception as e:
            self.logger.error(f"PaytmMoney Login Error: {e}")
            return False

    def get_market_data(self, symbols: List[Dict[str, str]]) -> Dict[str, Any]:
        """Fetch live market data for given symbols."""
        if not self.authenticated:
            return {"status": "error", "remarks": "Not authenticated"}

        try:
            results = {}
            for sym in symbols:
                exchange = sym.get("exchange", "NSE")
                scrip = sym.get("scrip") or sym.get("symbol") or sym.get("tradingsymbol", "")
                url = f"{self.BASE_URL}/v1/quote"
                params = {"exchange": exchange, "scrip": scrip}

                if self.use_httpx and _httpx_available:
                    client = httpx.Client(verify=self.verify_ssl, timeout=10)
                    client.headers["X-Client-Id"] = self.client_id
                    client.headers["X-Client-Secret"] = self.client_secret
                    if self.access_token:
                        client.headers["Authorization"] = f"Bearer {self.access_token}"
                    response = client.get(url, params=params)
                else:
                    response = requests.get(
                        url,
                        params=params,
                        headers={
                            "X-Client-Id": self.client_id,
                            "X-Client-Secret": self.client_secret,
                            "Authorization": f"Bearer {self.access_token}",
                        },
                        timeout=10,
                    )

                if response.status_code == 200:
                    data = response.json()
                    results[scrip] = data.get("data", data)

            return {"data": results, "status": "success"}

        except ImportError:
            return {"status": "error", "remarks": "httpx or requests not available"}
        except Exception as e:
            self.logger.error(f"PaytmMoney Market Data Error: {e}")
            return {"status": "error", "remarks": str(e)}

    def get_historical_data(
        self, symbol: Dict[str, str], interval: str, from_date: str, to_date: str
    ) -> Any:
        """Fetch historical OHLC data."""
        if not self.authenticated:
            return []
        try:
            exchange = symbol.get("exchange", "NSE")
            scrip = symbol.get("scrip") or symbol.get("symbol") or symbol.get("tradingsymbol", "")
            url = f"{self.BASE_URL}/v1/quote/historical"
            params = {
                "exchange": exchange,
                "scrip": scrip,
                "interval": interval,
                "from_date": from_date,
                "to_date": to_date,
            }

            if self.use_httpx and _httpx_available:
                client = httpx.Client(verify=self.verify_ssl, timeout=15)
                client.headers["X-Client-Id"] = self.client_id
                client.headers["X-Client-Secret"] = self.client_secret
                if self.access_token:
                    client.headers["Authorization"] = f"Bearer {self.access_token}"
                response = client.get(url, params=params)
            else:
                response = requests.get(
                    url,
                    params=params,
                    headers={
                        "X-Client-Id": self.client_id,
                        "X-Client-Secret": self.client_secret,
                        "Authorization": f"Bearer {self.access_token}",
                    },
                    timeout=15,
                )

            if response.status_code == 200:
                data = response.json()
                return data.get("data", [])
            return []

        except ImportError:
            return []
        except Exception as e:
            self.logger.error(f"PaytmMoney Historical Data Error: {e}")
            return []

    def place_order(self, order_details: Dict[str, Any]) -> Dict[str, Any]:
        """Place a new order. Returns {"order_id": str, "status": str, "message": str}."""
        if not self.authenticated:
            return {"order_id": "", "status": "ERROR", "message": "Not authenticated"}
        try:
            url = f"{self.BASE_URL}/v1/orders"
            payload = {
                "exchange": order_details.get("exchange", "NSE"),
                "scrip": order_details.get("scrip") or order_details.get("symbol") or order_details.get("tradingsymbol", ""),
                "transaction_type": order_details.get("side", order_details.get("transaction_type", "BUY")),
                "order_type": order_details.get("order_type", "MARKET"),
                "quantity": order_details.get("quantity", 0),
                "price": order_details.get("price", 0),
                "product_type": order_details.get("product_type", "MARGIN"),
                "validity": order_details.get("validity", "DAY"),
                "trigger_price": order_details.get("trigger_price", 0),
            }

            if self.use_httpx and _httpx_available:
                client = httpx.Client(verify=self.verify_ssl, timeout=15)
                client.headers["X-Client-Id"] = self.client_id
                client.headers["X-Client-Secret"] = self.client_secret
                if self.access_token:
                    client.headers["Authorization"] = f"Bearer {self.access_token}"
                response = client.post(url, json=payload)
            else:
                response = requests.post(
                    url,
                    json=payload,
                    headers={
                        "X-Client-Id": self.client_id,
                        "X-Client-Secret": self.client_secret,
                        "Authorization": f"Bearer {self.access_token}",
                        "Content-Type": "application/json",
                    },
                    timeout=15,
                )

            if response.status_code in (200, 201):
                data = response.json()
                if data.get("status") in ("success", "200", 200):
                    order_id = data.get("data", {}).get("order_id", "")
                    if order_id:
                        return {"order_id": str(order_id), "status": "OPEN", "message": ""}
                return {"order_id": "", "status": "REJECTED", "message": data.get(' remarks') or data.get('message') or "Order rejected"}
            return {"order_id": "", "status": "REJECTED", "message": f"HTTP {response.status_code}"}

        except ImportError:
            self.logger.error("PaytmMoney: httpx or requests not available")
            return {"order_id": "", "status": "ERROR", "message": "httpx/requests not available"}
        except Exception as e:
            self.logger.error(f"PaytmMoney Order Error: {e}")
            return {"order_id": "", "status": "ERROR", "message": str(e)}

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get order status by order ID."""
        if not self.authenticated:
            return {}
        try:
            url = f"{self.BASE_URL}/v1/orders/{order_id}"

            if self.use_httpx and _httpx_available:
                client = httpx.Client(verify=self.verify_ssl, timeout=10)
                client.headers["X-Client-Id"] = self.client_id
                client.headers["X-Client-Secret"] = self.client_secret
                if self.access_token:
                    client.headers["Authorization"] = f"Bearer {self.access_token}"
                response = client.get(url)
            else:
                response = requests.get(
                    url,
                    headers={
                        "X-Client-Id": self.client_id,
                        "X-Client-Secret": self.client_secret,
                        "Authorization": f"Bearer {self.access_token}",
                    },
                    timeout=10,
                )

            if response.status_code == 200:
                data = response.json()
                return data.get("data", data)
            return {}

        except ImportError:
            return {}
        except Exception as e:
            self.logger.error(f"PaytmMoney Order Status Error: {e}")
            return {}

    def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions."""
        if not self.authenticated:
            return []
        try:
            url = f"{self.BASE_URL}/v1/positions"

            if self.use_httpx and _httpx_available:
                client = httpx.Client(verify=self.verify_ssl, timeout=10)
                client.headers["X-Client-Id"] = self.client_id
                client.headers["X-Client-Secret"] = self.client_secret
                if self.access_token:
                    client.headers["Authorization"] = f"Bearer {self.access_token}"
                response = client.get(url)
            else:
                response = requests.get(
                    url,
                    headers={
                        "X-Client-Id": self.client_id,
                        "X-Client-Secret": self.client_secret,
                        "Authorization": f"Bearer {self.access_token}",
                    },
                    timeout=10,
                )

            if response.status_code == 200:
                data = response.json()
                if data.get("status") in ("success", "200", 200):
                    return data.get("data", [])
            return []

        except ImportError:
            return []
        except Exception as e:
            self.logger.error(f"PaytmMoney Positions Error: {e}")
            return []

    def get_holdings(self) -> List[Dict[str, Any]]:
        """Get holdings."""
        if not self.authenticated:
            return []
        try:
            url = f"{self.BASE_URL}/v1/holdings"

            if self.use_httpx and _httpx_available:
                client = httpx.Client(verify=self.verify_ssl, timeout=10)
                client.headers["X-Client-Id"] = self.client_id
                client.headers["X-Client-Secret"] = self.client_secret
                if self.access_token:
                    client.headers["Authorization"] = f"Bearer {self.access_token}"
                response = client.get(url)
            else:
                response = requests.get(
                    url,
                    headers={
                        "X-Client-Id": self.client_id,
                        "X-Client-Secret": self.client_secret,
                        "Authorization": f"Bearer {self.access_token}",
                    },
                    timeout=10,
                )

            if response.status_code == 200:
                data = response.json()
                if data.get("status") in ("success", "200", 200):
                    return data.get("data", [])
            return []

        except ImportError:
            return []
        except Exception as e:
            self.logger.error(f"PaytmMoney Holdings Error: {e}")
            return []

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an existing order."""
        if not self.authenticated:
            return False
        try:
            url = f"{self.BASE_URL}/v1/orders/{order_id}"

            if self.use_httpx and _httpx_available:
                client = httpx.Client(verify=self.verify_ssl, timeout=10)
                client.headers["X-Client-Id"] = self.client_id
                client.headers["X-Client-Secret"] = self.client_secret
                if self.access_token:
                    client.headers["Authorization"] = f"Bearer {self.access_token}"
                response = client.delete(url)
            else:
                response = requests.delete(
                    url,
                    headers={
                        "X-Client-Id": self.client_id,
                        "X-Client-Secret": self.client_secret,
                        "Authorization": f"Bearer {self.access_token}",
                    },
                    timeout=10,
                )

            if response.status_code in (200, 201):
                data = response.json()
                return data.get("status") in ("success", "200", 200)
            return False

        except ImportError:
            return False
        except Exception as e:
            self.logger.error(f"PaytmMoney Cancel Order Error: {e}")
            return False

    def start_data_feed(self, symbols: List[Dict[str, Any]], callback: Callable[[Dict[str, Any]], None]):
        """Start real-time data feed (WebSocket)."""
        self.logger.info("PaytmMoney real-time feed not yet implemented — use WebSocket at wss://api.paytmmoney.com/v1/feed")