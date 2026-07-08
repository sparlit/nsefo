from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class Broker(ABC):
    @abstractmethod
    def login(self, **kwargs):
        pass

    @abstractmethod
    def get_market_data(self, symbols: List[str]) -> Dict[str, Any]:
        pass

    @abstractmethod
    def place_order(self, order_details: Dict[str, Any]) -> str:
        pass

    @abstractmethod
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_positions(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_holdings(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def cancel_order(self, order_id: str):
        pass
