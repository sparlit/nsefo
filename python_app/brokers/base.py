"""
Broker abstract base class.
All broker providers inherit from this.
Copied and enhanced from python_app/broker/base.py
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Callable
import logging

_token_manager = None

def _get_token_manager():
    global _token_manager
    if _token_manager is None:
        try:
            from python_app.auth.browser_login import TokenManager
            _token_manager = TokenManager()
        except ImportError:
            pass
    return _token_manager


class Broker(ABC):
    """
    Abstract broker base class.

    Provides:
      - _handle_auth_error(status_code): call after HTTP calls that may 401
      - get_token(): returns current TokenInfo or None
      - _log_auth_warning(): logs a warning if TokenManager reports expired token
      - provider: the provider_type string (e.g. "zerodha", "icici")
      - DEPRECATED: set to True for brokers no longer functional
    """

    DEPRECATED: bool = False

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        # Subclasses should set self.provider = "<key>" in __init__

    @property
    def provider(self) -> str:
        """Returns the provider key for this broker."""
        return getattr(self, '_provider_key', self.__class__.__name__.replace('Provider', '').lower())

    def get_token(self):
        """Returns the TokenInfo for this broker from TokenManager, or None."""
        tm = _get_token_manager()
        if tm:
            return tm.get_token(self.provider)
        return None

    def _handle_auth_error(self, status_code: int):
        """
        Call this from any HTTP method that receives a 401/403 response.
        Triggers TokenManager to initiate re-login in background.
        """
        if status_code in (401, 403):
            tm = _get_token_manager()
            if tm:
                tm.on_auth_error(self.provider, status_code)

    def _log_auth_warning(self):
        """Log a warning if the current token is expired or missing."""
        token = self.get_token()
        if token and token.is_expired():
            self.logger.warning(
                "Token expired for %s. Auto-relogin will trigger on next 401.",
                self.provider
            )

    # ── Abstract methods ─────────────────────────────────────────────────────

    @abstractmethod
    def login(self, **kwargs) -> bool:
        """Authenticate with the broker API. Returns True on success."""
        raise NotImplementedError

    @abstractmethod
    def get_market_data(self, symbols: List[Dict[str, str]]) -> Dict[str, Any]:
        """Fetch live market data for given symbols."""
        raise NotImplementedError

    @abstractmethod
    def get_historical_data(self, symbol: Dict[str, str], interval: str,
                            from_date: str, to_date: str) -> Any:
        """Fetch historical OHLCV data."""
        raise NotImplementedError

    @abstractmethod
    def place_order(self, order_details: Dict[str, Any]) -> str:
        """Place an order. Returns order_id string."""
        raise NotImplementedError

    @abstractmethod
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get the status of a placed order."""
        raise NotImplementedError

    @abstractmethod
    def get_positions(self) -> List[Dict[str, Any]]:
        """Get current open positions."""
        raise NotImplementedError

    @abstractmethod
    def get_holdings(self) -> List[Dict[str, Any]]:
        """Get holdings / delivery positions."""
        raise NotImplementedError

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order. Returns True on success."""
        raise NotImplementedError

    @abstractmethod
    def start_data_feed(self, symbols: List[Dict[str, Any]],
                        callback: Callable[[Dict[str, Any]], None]):
        """Start a streaming data feed for given symbols."""
        raise NotImplementedError