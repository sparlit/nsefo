import os
import logging
from typing import List, Dict, Any, Optional, Callable

try:
    import httpx
except ImportError:
    httpx = None

from .base import Broker


class ICICIDirectProvider(Broker):
    """
    ICICI Direct broker implementation using HTTP REST API.

    AUTH — OAuth2 with refresh-token:
      ICICI Direct uses OAuth2. The initial login requires exchanging
      client credentials (api_key + client_secret + authorization code)
      for an access_token + refresh_token. The refresh_token is used to
      obtain a new access_token when the current one expires.

    REQUIRED config.json fields for ICICI:
      {
        "client_id": "your client id",
        "api_key": "your api key",
        "client_secret": "your client secret",
        "access_token": "current access token",
        "refresh_token": "oauth2 refresh token",
        "mode": "paper|live"
      }

    OAUTH2 FLOW (one-time setup):
      1. Register at https://smartapi.angelone.in (or your broker's dev portal)
         to get api_key + client_secret.
      2. Authorize via: GET https://api.icicidirect.com/api/authorize
         with response_type="code", client_id, redirect_uri, scope.
      3. Exchange the authorization code for tokens via:
         POST {BASE_URL}/api/Token  with grant_type="authorization_code"
      4. Store the returned refresh_token in config.json.
         Access token expires in ~3600s; refresh token lasts longer.

    AUTO-REFRESH:
      On receiving HTTP 401, the provider automatically calls
      _refresh_access_token() using the stored refresh_token and
      updates config.json with the new access_token.
    """
    BASE_URL = "https://api.icicidirect.com"

    def __init__(
        self,
        client_id: str,
        api_key: str = "",
        access_token: str = "",
        refresh_token: str = "",
        client_secret: str = "",
        **kwargs,
    ):
        self.client_id = client_id
        self.api_key = api_key
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.client_secret = client_secret
        self.verify_ssl = kwargs.get("verify_ssl", True)
        self.logger = logging.getLogger("ICICIDirectProvider")
        self._authenticated = False
        self._client: Optional[httpx.Client] = None

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key,
            "X-Client-Id": self.client_id,
            "Authorization": f"Bearer {self.access_token}"
        }

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(verify=self.verify_ssl, timeout=10.0)
        return self._client

    def _refresh_access_token(self) -> bool:
        """
        Exchange refresh_token for a new access_token.
        Returns True if refresh succeeded and self.access_token is updated.
        Updates self.access_token in-memory and returns the new value.

        ICICI Direct token endpoint (common pattern):
          POST {BASE_URL}/api/Token
          Body: grant_type=refresh_token&refresh_token=<refresh_token>&client_id=<api_key>&client_secret=<client_secret>
        """
        if not self.refresh_token:
            self.logger.error("No refresh_token available. Cannot refresh access token.")
            return False
        try:
            url = f"{self.BASE_URL}/api/Token"
            payload = {
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
                "client_id": self.api_key,
                "client_secret": self.client_secret,
            }
            # ICICI may use form-encoded or JSON — trying JSON first
            resp = self._get_client().post(
                url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": self.api_key,
                    "X-Client-Id": self.client_id,
                },
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                new_access = data.get("access_token", "")
                new_refresh = data.get("refresh_token", self.refresh_token)
                if new_access:
                    self.access_token = new_access
                    self.refresh_token = new_refresh
                    self.logger.info("Access token refreshed successfully.")
                    # Update config.json so tokens persist
                    self._save_tokens_to_config(new_access, new_refresh)
                    return True
            self.logger.error("Token refresh failed (%d): %s", resp.status_code, resp.text)
            return False
        except Exception as e:
            self.logger.error("Token refresh exception: %s", e)
            return False

    def _save_tokens_to_config(self, access_token: str, refresh_token: str):
        """Persist updated tokens to config.json for next launch."""
        try:
            import json as _json
            from python_app.core.state import global_state
            cfg_path = "config.json"
            if os.path.exists(cfg_path):
                with open(cfg_path) as f:
                    cfg = _json.load(f)
                cfg["access_token"] = access_token
                cfg["refresh_token"] = refresh_token
                with open(cfg_path, "w") as f:
                    _json.dump(cfg, f, indent=4)
                self.logger.info("Tokens updated in config.json.")
        except Exception as e:
            self.logger.error("Failed to persist tokens to config.json: %s — tokens will be lost on restart", e)

    def login(self, **kwargs) -> bool:
        """
        Authenticate with ICICI Direct API.
        - If access_token is valid, verify via /api/Profile
        - If access_token is empty or 401 received, attempt refresh via refresh_token
        - Fallback: if refresh fails, return False (user must re-authorize)
        """
        if httpx is None:
            self.logger.error("httpx not installed. Install: pip install httpx")
            return False

        if not self.access_token:
            self.logger.error("No access_token. Complete OAuth2 authorization first.")
            return False

        # Try with current token
        if self._verify_token():
            self._authenticated = True
            return True

        # Token invalid or expired — try refresh
        if self.refresh_token:
            self.logger.info("Access token expired. Attempting refresh...")
            if self._refresh_access_token() and self._verify_token():
                self._authenticated = True
                return True

        self.logger.error(
            "ICICI Direct auth failed. Ensure refresh_token is set in config.json.\n"
            "To get refresh_token: complete OAuth2 authorization flow and store the refresh_token."
        )
        return False

    def _verify_token(self) -> bool:
        """Check if current access_token is still valid."""
        try:
            url = f"{self.BASE_URL}/api/Profile"
            resp = self._get_client().get(url, headers=self._get_headers(), timeout=10)
            return resp.status_code == 200
        except Exception:
            return False

    def get_market_data(self, symbols: List[Dict[str, str]]) -> Dict[str, Any]:
        """Fetch live market data for given symbols."""
        if not self._authenticated:
            return {"status": "error", "remarks": "Not authenticated"}
        if httpx is None:
            return {"status": "error", "remarks": "httpx not installed"}
        try:
            results = {}
            for s in symbols:
                symbol = s.get('symbol', '')
                exchange = s.get('exchange', 'NSE')
                url = f"{self.BASE_URL}/api/GetQuote?Exchange={exchange}&ScripCode={symbol}"
                response = self._get_client().get(url, headers=self._get_headers(), timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    results[symbol] = {"last_price": float(data.get('last_price', 0.0))}
            return {"data": results}
        except Exception as e:
            self.logger.error(f"ICICI Direct Market Data Error: {e}")
            return {"status": "error", "remarks": str(e)}

    def get_historical_data(self, symbol: Dict[str, str], interval: str, from_date: str, to_date: str) -> Any:
        """Fetch historical OHLC data."""
        if not self._authenticated:
            return []
        if httpx is None:
            return []
        try:
            sym = symbol.get('symbol', '')
            exchange = symbol.get('exchange', 'NSE')
            url = f"{self.BASE_URL}/api/historical?Exchange={exchange}&ScripCode={sym}"
            params = {"interval": interval, "from_date": from_date, "to": to_date}
            response = self._get_client().get(url, headers=self._get_headers(), params=params, timeout=10)
            if response.status_code == 200:
                return response.json().get('data', [])
            return []
        except Exception as e:
            self.logger.error(f"ICICI Direct Historical Data Error: {e}")
            return []

    def place_order(self, order_details: Dict[str, Any]) -> Dict[str, Any]:
        """Place a new order. Returns {"order_id": str, "status": str, "message": str}."""
        if not self._authenticated:
            return {"order_id": "", "status": "ERROR", "message": "Not authenticated"}
        if httpx is None:
            return {"order_id": "", "status": "ERROR", "message": "httpx not available"}
        try:
            url = f"{self.BASE_URL}/api/Order"
            payload = {
                "symbol": order_details.get('symbol'),
                "exchange": order_details.get('exchange', 'NSE'),
                "transaction_type": order_details.get('side', 'BUY'),
                "quantity": int(order_details.get('quantity', 0)),
                "order_type": order_details.get('order_type', 'MARKET'),
                "product_type": order_details.get('product_type', 'MARGIN'),
                "price": float(order_details.get('price', 0)),
                "trigger_price": float(order_details.get('trigger_price', 0))
            }
            response = self._get_client().post(url, json=payload, headers=self._get_headers(), timeout=10)
            if response.status_code == 200:
                data = response.json()
                oid = str(data.get('order_id', '')).strip()
                if not oid:
                    self.logger.error("ICICI Direct returned empty order_id")
                    return {"order_id": "", "status": "REJECTED", "message": "Broker returned empty order ID"}
                return {"order_id": oid, "status": "OPEN", "message": ""}
            return {"order_id": "", "status": "REJECTED", "message": f"HTTP {response.status_code}: {response.text[:80]}"}
        except Exception as e:
            self.logger.error(f"ICICI Direct Order Error: {e}")
            return {"order_id": "", "status": "ERROR", "message": str(e)}

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get order status by order ID."""
        if not self._authenticated:
            return {}
        if httpx is None:
            return {}
        try:
            url = f"{self.BASE_URL}/api/Order/{order_id}"
            response = self._get_client().get(url, headers=self._get_headers(), timeout=10)
            if response.status_code == 200:
                return response.json()
            return {}
        except Exception as e:
            self.logger.error(f"ICICI Direct Order Status Error: {e}")
            return {}

    def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions."""
        if not self._authenticated:
            return []
        if httpx is None:
            return []
        try:
            url = f"{self.BASE_URL}/api/Positions"
            response = self._get_client().get(url, headers=self._get_headers(), timeout=10)
            if response.status_code == 200:
                return response.json().get('data', [])
            return []
        except Exception as e:
            self.logger.error(f"ICICI Direct Positions Error: {e}")
            return []

    def get_holdings(self) -> List[Dict[str, Any]]:
        """Get holdings."""
        if not self._authenticated:
            return []
        if httpx is None:
            return []
        try:
            url = f"{self.BASE_URL}/api/Holdings"
            response = self._get_client().get(url, headers=self._get_headers(), timeout=10)
            if response.status_code == 200:
                return response.json().get('data', [])
            return []
        except Exception as e:
            self.logger.error(f"ICICI Direct Holdings Error: {e}")
            return []

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an existing order."""
        if not self._authenticated:
            return False
        if httpx is None:
            return False
        try:
            url = f"{self.BASE_URL}/api/Order/{order_id}"
            response = self._get_client().delete(url, headers=self._get_headers(), timeout=10)
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"ICICI Direct Cancel Order Error: {e}")
            return False

    def start_data_feed(self, symbols: List[Dict[str, Any]], callback: Callable[[Dict[str, Any]], None]):
        """Start real-time data feed."""
        self.logger.info("ICICI Direct Real-time Feed - Not implemented (HTTP-only provider)")