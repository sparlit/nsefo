from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Callable

class Broker(ABC):
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
