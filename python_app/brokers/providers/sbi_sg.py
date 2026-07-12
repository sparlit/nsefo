"""SBISG provider stub."""
from ..base import Broker
from typing import List, Dict, Any, Callable
import logging, httpx, certifi, os

try:
    import brotli
    _HAS_BROTLI = True
except ImportError:
    _HAS_BROTLI = False

_HAS_CERTIFI = bool(certifi.where())

class SBISGProvider(Broker):
    DEPRECATED = False

    def __init__(self, client_id: str = "", access_token: str = "", password: str = "",
                 api_key: str = "", client_secret: str = "", refresh_token: str = "",
                 verify_ssl: bool = True, config: dict = None, **kwargs):
        super().__init__()
        self._provider_key = "sbi_sg"
        self.provider = "sbi_sg"
        self.client_id = client_id or kwargs.get("client_id", "")
        self.access_token = access_token or kwargs.get("access_token", "")
        self.password = password or kwargs.get("password", "")
        self.api_key = api_key or kwargs.get("api_key", "")
        self.client_secret = client_secret or kwargs.get("client_secret", "")
        self.refresh_token = refresh_token or kwargs.get("refresh_token", "")
        self.verify_ssl = verify_ssl
        self.config = config or {}
        self.BASE_URL = "https://sbisdm.motilaloswal.com"
        self.logger = logging.getLogger("SBISGProvider")
        self._has_brotli = _HAS_BROTLI
        self._has_certifi = _HAS_CERTIFI
        self._session = None

    def _get_client(self) -> httpx.Client:
        verify = certifi.where() if self._has_certifi and self.verify_ssl else self.verify_ssl
        headers = {"User-Agent": "NseFO/1.0"}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        if self.client_id:
            headers["X-Client-Id"] = self.client_id
        if self.api_key:
            headers["X-Api-Key"] = self.api_key
        return httpx.Client(verify=verify, headers=headers, timeout=30.0)

    def login(self, **kwargs) -> bool:
        self.logger.warning("sbi_sg: BASE_URL=%s — not verified from live trace", self.BASE_URL)
        return False  # STUB: needs API verification

    def get_market_data(self, symbols: List[Dict[str, str]]) -> Dict[str, Any]:
        return {}

    def get_historical_data(self, symbol: Dict[str, str], interval: str,
                            from_date: str, to_date: str) -> Any:
        return []

    def place_order(self, order_details: Dict[str, Any]) -> str:
        raise NotImplementedError("BASE_URL not verified — cannot place orders")

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        return {}

    def get_positions(self) -> List[Dict[str, Any]]:
        return []

    def get_holdings(self) -> List[Dict[str, Any]]:
        return []

    def cancel_order(self, order_id: str) -> bool:
        raise NotImplementedError("BASE_URL not verified — cannot cancel orders")

    def start_data_feed(self, symbols: List[Dict[str, Any]],
                        callback: Callable[[Dict[str, Any]], None]):
        self.logger.info("start_data_feed called — stub implementation")