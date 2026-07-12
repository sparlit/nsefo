# Migrated from python_app/broker/iifl.py — DO NOT EDIT HERE
"""
IIFL Broker Implementation (HTTP REST)
Auth: clientId + password + DOB + APIKey
API Docs: https://api-iifl.marketsmania.com/
"""
import logging
import requests
import hashlib
import hmac
import base64
from typing import List, Dict, Any, Optional, Callable
from ..base import Broker

BASE_URL = "https://api-iifl.marketsmania.com"


class IIFLProvider(Broker):
    def __init__(self, client_id: str, access_token: str = "", **kwargs):
        self.client_id = client_id
        self.api_key = kwargs.get("api_key", kwargs.get("APIKey", ""))
        self.password = kwargs.get("password", "")
        self.dob = kwargs.get("dob", "")
        self.access_token = access_token
        self.session = requests.Session()
        self.logger = logging.getLogger("IIFLProvider")
        self.authenticated = False
        self._headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Api-Key": self.api_key,
        }
        if self.access_token:
            self._headers["Authorization"] = f"Bearer {self.access_token}"
            self.authenticated = True

    def _authenticate(self) -> bool:
        """Authenticate using IIFL Open APIV2."""
        try:
            payload = {
                "clientId": self.client_id,
                "password": self.password,
                "DOB": self.dob,
                "APIKey": self.api_key,
            }
            resp = self.session.post(
                f"{BASE_URL}/RestAPP/v2/session/validate",
                json=payload,
                headers=self._headers,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") == "Success" or data.get("token"):
                self.access_token = data.get("token", self.access_token)
                self._headers["Authorization"] = f"Bearer {self.access_token}"
                self.authenticated = True
                self.logger.info("IIFL authentication successful.")
                return True
            self.logger.warning(f"IIFL auth failed: {data}")
            return False
        except Exception as e:
            self.logger.error(f"IIFL Authentication Error: {e}")
            return False

    def login(self, **kwargs) -> bool:
        if not self.access_token:
            return self._authenticate()
        # Validate token
        try:
            resp = self.session.get(
                f"{BASE_URL}/RestAPP/v2/client/login",
                headers=self._headers,
                timeout=10,
            )
            self.authenticated = resp.status_code == 200
            return self.authenticated
        except Exception as e:
            self.logger.error(f"IIFL Login Check Error: {e}")
            return False

    def get_market_data(self, symbols: List[Dict[str, str]]) -> Dict[str, Any]:
        if not self.authenticated:
            return {"data": {}}
        try:
            scrips = []
            for s in symbols:
                scrips.append(
                    {
                        "Exchange": s.get("exchange", "NSE"),
                        "ExchangeType": s.get("exchange_type", "CASH"),
                        "ScripCode": s.get("security_id", ""),
                    }
                )
            payload = {"scrips": scrips}
            resp = self.session.post(
                f"{BASE_URL}/RestAPP/v2/marketdata/getLtp",
                json=payload,
                headers=self._headers,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            data_map = {}
            for item in data.get("data", []):
                sid = item.get("ScripCode", "")
                data_map[sid] = {
                    "last_price": item.get("LastRate", 0.0),
                    "change": item.get("Chg", 0.0),
                    "percent_change": item.get("PerChange", 0.0),
                }
            return {"data": data_map}
        except Exception as e:
            self.logger.error(f"IIFL Market Data Error: {e}")
            return {"data": {}}

    def get_historical_data(
        self, symbol: Dict[str, str], interval: str, from_date: str, to_date: str
    ) -> Any:
        if not self.authenticated:
            return []
        try:
            payload = {
                "exchange": symbol.get("exchange", "NSE"),
                "exchangeType": symbol.get("exchange_type", "CASH"),
                "scripCode": symbol.get("security_id", ""),
                "interval": interval,
                "fromDate": from_date,
                "toDate": to_date,
            }
            resp = self.session.get(
                f"{BASE_URL}/RestAPP/v2/charthistory/getIntraday",
                params=payload,
                headers=self._headers,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", []) if isinstance(data, dict) else data
        except Exception as e:
            self.logger.error(f"IIFL Historical Data Error: {e}")
            return []

    def place_order(self, order_details: Dict[str, Any]) -> str:
        if not self.authenticated:
            return ""
        try:
            payload = {
                "clientId": self.client_id,
                "exchange": order_details.get("exchange", "NSE"),
                "exchangeType": order_details.get("exchange_segment", "CASH"),
                "scripCode": order_details.get("security_id", ""),
                "transactionType": order_details.get("side", "BUY"),
                "quantity": order_details.get("quantity", 0),
                "orderType": order_details.get("order_type", "M"),
                "price": order_details.get("price", 0),
                "triggerPrice": order_details.get("trigger_price", 0),
                "productType": order_details.get("product_type", "CASH"),
            }
            resp = self.session.post(
                f"{BASE_URL}/RestAPP/v2/orders/place",
                json=payload,
                headers=self._headers,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("orderId"):
                return str(data["orderId"])
            return ""
        except Exception as e:
            self.logger.error(f"IIFL Place Order Error: {e}")
            return ""

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        if not self.authenticated:
            return {}
        try:
            resp = self.session.get(
                f"{BASE_URL}/RestAPP/v2/orders/{order_id}",
                headers=self._headers,
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            self.logger.error(f"IIFL Order Status Error: {e}")
            return {}

    def get_positions(self) -> List[Dict[str, Any]]:
        if not self.authenticated:
            return []
        try:
            payload = {"clientId": self.client_id}
            resp = self.session.post(
                f"{BASE_URL}/RestAPP/v2/position/get",
                json=payload,
                headers=self._headers,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", []) if isinstance(data, dict) else data
        except Exception as e:
            self.logger.error(f"IIFL Positions Error: {e}")
            return []

    def get_holdings(self) -> List[Dict[str, Any]]:
        if not self.authenticated:
            return []
        try:
            payload = {"clientId": self.client_id}
            resp = self.session.post(
                f"{BASE_URL}/RestAPP/v2/holding/get",
                json=payload,
                headers=self._headers,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", []) if isinstance(data, dict) else data
        except Exception as e:
            self.logger.error(f"IIFL Holdings Error: {e}")
            return []

    def cancel_order(self, order_id: str) -> bool:
        if not self.authenticated:
            return False
        try:
            payload = {"orderId": order_id, "clientId": self.client_id}
            resp = self.session.post(
                f"{BASE_URL}/RestAPP/v2/orders/cancel",
                json=payload,
                headers=self._headers,
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("status") == "Success" or data.get("result", False)
        except Exception as e:
            self.logger.error(f"IIFL Cancel Order Error: {e}")
            return False

    def start_data_feed(
        self, symbols: List[Dict[str, Any]], callback: Callable[[Dict[str, Any]], None]
    ):
        self.logger.warning("IIFL real-time feed via HTTP REST not implemented — use WebSocket for live data.")