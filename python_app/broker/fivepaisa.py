"""
5paisa Broker Implementation (HTTP REST)
Auth: client_id + password + dob (or TOTP) + AppSource
API Docs: https://openapi.5paisa.com/
"""
import logging
import requests
from typing import List, Dict, Any, Optional, Callable
from .base import Broker

BASE_URL = "https://openapi.5paisa.com"
MARTECH_URL = "https://maringate.5paisa.com"


class FivePaisaProvider(Broker):
    def __init__(self, client_id: str, access_token: str = "", **kwargs):
        self.client_id = client_id
        self.password = kwargs.get("password", "")
        self.dob = kwargs.get("dob", "")
        self.app_source = kwargs.get("app_source", kwargs.get("AppSource", ""))
        self.totp = kwargs.get("totp", "")
        self.access_token = access_token
        self.session = requests.Session()
        self.logger = logging.getLogger("FivePaisaProvider")
        self.authenticated = False
        self._headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.access_token:
            self._headers["Authorization"] = f"Bearer {self.access_token}"
            self.authenticated = True

    def _authenticate(self) -> bool:
        """Authenticate using credentials and get JWT token."""
        try:
            payload = {
                "head": {
                    "appSource": self.app_source,
                    "appType": "Web",
                    "localTxnId": "1",
                    "reqRefId": "ref1",
                    "userClientType": "Web",
                },
                "body": {
                    "clientCode": self.client_id,
                    "password": self.password,
                    "dob": self.dob,
                    "totp": self.totp,
                },
            }
            resp = self.session.post(
                f"{BASE_URL}/5pservices/jwtvalidate/v1/authenticationtoken",
                json=payload,
                headers=self._headers,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") == 200 or data.get("token"):
                self.access_token = data.get("token", self.access_token)
                self._headers["Authorization"] = f"Bearer {self.access_token}"
                self.authenticated = True
                self.logger.info("5paisa authentication successful.")
                return True
            self.logger.warning(f"5paisa auth failed: {data}")
            return False
        except Exception as e:
            self.logger.error(f"5paisa Authentication Error: {e}")
            return False

    def login(self, **kwargs) -> bool:
        if not self.access_token:
            return self._authenticate()
        # Validate existing token
        try:
            resp = self.session.get(
                f"{BASE_URL}/5pservices/FifthPersaService/Rest/V1/client/ClientSessionValidity",
                headers=self._headers,
                timeout=10,
            )
            return resp.status_code == 200
        except Exception as e:
            self.logger.error(f"5paisa Login Check Error: {e}")
            return False

    def get_market_data(self, symbols: List[Dict[str, str]]) -> Dict[str, Any]:
        if not self.authenticated:
            return {"data": {}, "status": "error", "remarks": "not authenticated"}
        try:
            scrip_data = []
            for s in symbols:
                scrip_data.append(
                    {
                        "Exchange": s.get("exchange", "NSE"),
                        "ExchangeType": s.get("exchange_type", "CASH"),
                        "ScripCode": s.get("security_id", ""),
                    }
                )
            payload = {
                "head": {
                    "appSource": self.app_source,
                    "appType": "Web",
                    "localTxnId": "2",
                    "reqRefId": "ref2",
                    "userClientType": "Web",
                },
                "body": {"ScripData": scrip_data},
            }
            resp = self.session.post(
                f"{MARTECH_URL}/5pservices/FifthPersaService/Rest/V1/marketWatch/getLtp",
                json=payload,
                headers=self._headers,
                timeout=15,
            )
            resp.raise_for_status()
            result = resp.json()
            data_map = {}
            body = result.get("body", {})
            for item in body.get("data", []):
                sid = item.get("ScripCode", "")
                data_map[sid] = {
                    "last_price": item.get("LastRate", 0.0),
                    "change": item.get("Chg", 0.0),
                    "percent_change": item.get("PerChange", 0.0),
                }
            return {"data": data_map}
        except Exception as e:
            self.logger.error(f"5paisa Market Data Error: {e}")
            return {"data": {}, "status": "error", "remarks": str(e)}

    def get_historical_data(
        self, symbol: Dict[str, str], interval: str, from_date: str, to_date: str
    ) -> Any:
        if not self.authenticated:
            return []
        try:
            payload = {
                "head": {
                    "appSource": self.app_source,
                    "appType": "Web",
                    "localTxnId": "3",
                    "reqRefId": "ref3",
                },
                "body": {
                    "ClientCode": self.client_id,
                    "Exchange": symbol.get("exchange", "NSE"),
                    "ExchangeType": symbol.get("exchange_type", "CASH"),
                    "ScripCode": symbol.get("security_id", ""),
                    "Interval": interval,
                    "FromDate": from_date,
                    "ToDate": to_date,
                },
            }
            resp = self.session.post(
                f"{BASE_URL}/5pservices/FifthPersaService/Rest/V1/chartData/getIntraDay",
                json=payload,
                headers=self._headers,
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json().get("body", {}).get("data", [])
        except Exception as e:
            self.logger.error(f"5paisa Historical Data Error: {e}")
            return []

    def place_order(self, order_details: Dict[str, Any]) -> str:
        if not self.authenticated:
            return ""
        try:
            payload = {
                "head": {
                    "appSource": self.app_source,
                    "appType": "Web",
                    "localTxnId": "4",
                    "reqRefId": "ref4",
                },
                "body": {
                    "ClientCode": self.client_id,
                    "Exchange": order_details.get("exchange", "NSE"),
                    "ExchangeType": order_details.get("exchange_segment", "CASH"),
                    "ScripCode": order_details.get("security_id", ""),
                    "TransactionType": order_details.get("side", "BUY"),
                    "Quantity": str(order_details.get("quantity", "")),
                    "OrderType": order_details.get("order_type", "M"),
                    "Price": str(order_details.get("price", 0)),
                    "TriggerPrice": str(order_details.get("trigger_price", 0)),
                    "ProductType": order_details.get("product_type", "CASH"),
                    "Expiry": order_details.get("expiry", ""),
                    "OrderId": "",
                },
            }
            resp = self.session.post(
                f"{BASE_URL}/5pservices/FifthPersaService/Rest/V1/order/place",
                json=payload,
                headers=self._headers,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("body", {}).get("OrderID"):
                return str(data["body"]["OrderID"])
            return ""
        except Exception as e:
            self.logger.error(f"5paisa Place Order Error: {e}")
            return ""

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        if not self.authenticated:
            return {}
        try:
            payload = {
                "head": {
                    "appSource": self.app_source,
                    "appType": "Web",
                    "localTxnId": "5",
                    "reqRefId": "ref5",
                },
                "body": {"OrderId": order_id, "ClientCode": self.client_id},
            }
            resp = self.session.post(
                f"{BASE_URL}/5pservices/FifthPersaService/Rest/V1/order/status",
                json=payload,
                headers=self._headers,
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json().get("body", {})
        except Exception as e:
            self.logger.error(f"5paisa Order Status Error: {e}")
            return {}

    def get_positions(self) -> List[Dict[str, Any]]:
        if not self.authenticated:
            return []
        try:
            payload = {
                "head": {
                    "appSource": self.app_source,
                    "appType": "Web",
                    "localTxnId": "6",
                    "reqRefId": "ref6",
                },
                "body": {"ClientCode": self.client_id},
            }
            resp = self.session.post(
                f"{BASE_URL}/5pservices/FifthPersaService/Rest/V1/position/get",
                json=payload,
                headers=self._headers,
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json().get("body", {}).get("data", [])
        except Exception as e:
            self.logger.error(f"5paisa Positions Error: {e}")
            return []

    def get_holdings(self) -> List[Dict[str, Any]]:
        if not self.authenticated:
            return []
        try:
            payload = {
                "head": {
                    "appSource": self.app_source,
                    "appType": "Web",
                    "localTxnId": "7",
                    "reqRefId": "ref7",
                },
                "body": {"ClientCode": self.client_id},
            }
            resp = self.session.post(
                f"{BASE_URL}/5pservices/FifthPersaService/Rest/V1/holding/get",
                json=payload,
                headers=self._headers,
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json().get("body", {}).get("data", [])
        except Exception as e:
            self.logger.error(f"5paisa Holdings Error: {e}")
            return []

    def cancel_order(self, order_id: str) -> bool:
        if not self.authenticated:
            return False
        try:
            payload = {
                "head": {
                    "appSource": self.app_source,
                    "appType": "Web",
                    "localTxnId": "8",
                    "reqRefId": "ref8",
                },
                "body": {"OrderId": order_id, "ClientCode": self.client_id},
            }
            resp = self.session.post(
                f"{BASE_URL}/5pservices/FifthPersaService/Rest/V1/order/cancel",
                json=payload,
                headers=self._headers,
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("body", {}).get("result", False)
        except Exception as e:
            self.logger.error(f"5paisa Cancel Order Error: {e}")
            return False

    def start_data_feed(
        self, symbols: List[Dict[str, Any]], callback: Callable[[Dict[str, Any]], None]
    ):
        self.logger.warning("5paisa real-time feed via HTTP REST not implemented — use WebSocket SDK for live data.")