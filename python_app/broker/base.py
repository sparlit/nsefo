from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Callable
import logging

from python_app.broker.login_credentials import LoginCredentials

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


def mark_abstract(func):
    """Mark a function as abstract for test compatibility."""
    # Set on the raw function so getattr through @abstractmethod descriptor finds it
    func.__is_abstract__ = True
    # Also set on __func__ if @abstractmethod wrapped it (descriptor protocol)
    if hasattr(func, '__func__'):
        func.__func__.__is_abstract__ = True
    return func


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
                tm.on_auth_error(
                    getattr(self, "provider", self.__class__.__name__), status_code
                )

    def _log_auth_warning(self):
        """Log a warning if the current token is expired or missing."""
        token = self.get_token()
        if token and token.is_expired():
            self.logger.warning(
                "Token expired for %s. Auto-relogin will trigger on next 401.",
                getattr(self, "provider", self.__class__.__name__),
            )

    @mark_abstract
    @abstractmethod
    def login(self, credentials: LoginCredentials=None, **kwargs) -> bool:
        __is_abstract__ = True
        """Authenticate with the broker. Returns True if login succeeded."""
        raise NotImplementedError

    @mark_abstract
    @abstractmethod
    def get_market_data(self, symbols: List[Dict[str, str]]) -> Dict[str, Any]:
        __is_abstract__ = True
        raise NotImplementedError

    @mark_abstract
    @abstractmethod
    def get_historical_data(
        self, symbol: Dict[str, str], interval: str, from_date: str, to_date: str
    ) -> Any:
        __is_abstract__ = True
        raise NotImplementedError

    @mark_abstract
    @abstractmethod
    def place_order(self, order_details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Place an order. Subclasses must override.

        Returns dict:
            {"order_id": str, "status": "OPEN"|"REJECTED"|"ERROR", "message": str}

        Empty string "" is accepted for backwards compatibility but normalised
        by the caller (coordinator) into {"order_id": "", "status": "ERROR", "message": ...}.
        """
        __is_abstract__ = True
        raise NotImplementedError

    @mark_abstract
    @abstractmethod
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        __is_abstract__ = True
        raise NotImplementedError

    @mark_abstract
    @abstractmethod
    def get_positions(self) -> List[Dict[str, Any]]:
        __is_abstract__ = True
        raise NotImplementedError

    @mark_abstract
    @abstractmethod
    def get_holdings(self) -> List[Dict[str, Any]]:
        __is_abstract__ = True
        raise NotImplementedError

    @mark_abstract
    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        __is_abstract__ = True
        raise NotImplementedError

    def get_fund_limits(self) -> Dict[str, float]:
        """
        Returns available broker funds. Override per-broker.
        Default returns zeros — SAFE default that blocks margin-requiring trades
        until a real broker implementation is provided.
        """
        return {"available_cash": 0.0, "used_margin": 0.0, "total": 0.0}

    @mark_abstract
    @abstractmethod
    def start_data_feed(
        self, symbols: List[Dict[str, Any]], callback: Callable[[Dict[str, Any]], None]
    ):
        __is_abstract__ = True
        raise NotImplementedError

    def check_margin_requirement(
        self, broker: "Broker", side: str = "BUY", price: float = 0.0, quantity: int = 0, option_type: str = "CE"
    ) -> Dict[str, Any]:
        """
        Compute margin requirement for a trade.
        This is a default implementation using get_fund_limits().
        Returns {"sufficient": bool, "shortfall": float, "available_cash": float, "required_margin": float}.
        """
        limits = self.get_fund_limits()
        available_cash = limits.get("available_cash", 0.0)
        required_margin = round(price * quantity * 2.5, 2)
        sufficient = available_cash >= required_margin
        shortfall = max(0.0, required_margin - available_cash)
        return {
            "sufficient": sufficient,
            "shortfall": shortfall,
            "available_cash": available_cash,
            "required_margin": required_margin,
        }