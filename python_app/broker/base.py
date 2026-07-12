from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Callable
import logging

# TokenManager must be imported lazily to avoid circular deps at module load
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

    All broker providers inherit from this. Provides:
    - _handle_auth_error(status_code): call after HTTP calls that may return 401
    - get_token(): returns current TokenInfo or None
    - _log_auth_warning(): logs a warning if TokenManager reports expired token
    """

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def get_token(self):
        """Returns the TokenInfo for this broker from TokenManager, or None."""
        tm = _get_token_manager()
        if tm:
            return tm.get_token(getattr(self, "provider", self.__class__.__name__))
        return None

    def _handle_auth_error(self, status_code: int):
        """
        Call this from any HTTP method that receives a 401/403 response.
        Triggers TokenManager to initiate re-login in background.
        """
        if status_code in (401, 403):
            tm = _get_token_manager()
            if tm:
                tm.on_auth_error(getattr(self, "provider", self.__class__.__name__), status_code)

    def _log_auth_warning(self):
        """Log a warning if the current token is expired or missing."""
        token = self.get_token()
        if token and token.is_expired():
            self.logger.warning(
                "Token expired for %s. Auto-relogin will trigger on next 401.",
                getattr(self, "provider", self.__class__.__name__)
            )

    @abstractmethod
    def login(self, **kwargs) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get_market_data(self, symbols: List[Dict[str, str]]) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def get_historical_data(self, symbol: Dict[str, str], interval: str, from_date: str, to_date: str) -> Any:
        raise NotImplementedError

    @abstractmethod
    def place_order(self, order_details: Dict[str, Any]) -> str:
        raise NotImplementedError

    @abstractmethod
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def get_positions(self) -> List[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_holdings(self) -> List[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def start_data_feed(self, symbols: List[Dict[str, Any]], callback: Callable[[Dict[str, Any]], None]):
        raise NotImplementedError
