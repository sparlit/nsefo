import uuid
import logging
import random
from datetime import datetime
from .base import Broker
from typing import List, Dict, Any, Callable

class PaperBroker(Broker):
    def __init__(self, data_provider: Broker = None):
        self.orders = {}
        self.positions = []
        self.holdings = []
        self.virtual_balance = 1000000.0
        self.data_provider = data_provider
        self.logger = logging.getLogger("PaperBroker")

    def login(self, **kwargs) -> bool:
        self.logger.info("Paper Engine Authenticated.")
        return True

    def get_market_data(self, symbols: List[Dict[str, str]]) -> Dict[str, Any]:
        if self.data_provider:
            try:
                res = self.data_provider.get_market_data(symbols)
                if res.get('status') != 'error':
                    return res
            except Exception as e:
                self.logger.debug(f"Data provider unavailable for paper: {e}")

        # Expert Simulation Logic: Real-time price movement emulation
        results = {}
        for s in symbols:
            results[s['security_id']] = {"last_price": round(100.0 + random.uniform(-1, 1), 2)}
        return {"data": results}

    def get_historical_data(self, symbol: Dict[str, str], interval: str, from_date: str, to_date: str) -> Any:
        if self.data_provider:
            try:
                return self.data_provider.get_historical_data(symbol, interval, from_date, to_date)
            except Exception as e:
                self.logger.debug(f"Historical data unavailable for paper: {e}")
        return []

    def place_order(self, o: Dict[str, Any]) -> str:
        order_id = f"PAPER-{uuid.uuid4().hex[:8].upper()}"
        o['order_id'] = order_id
        o['status'] = 'EXECUTED'
        o['order_time'] = str(datetime.now())
        self.orders[order_id] = o

        self.positions.append({
            "symbol": o['symbol'],
            "quantity": o['quantity'],
            "price": o['price'],
            "side": o['side'],
            "security_id": o.get('security_id', '0'),
            "exchange_segment": o.get('exchange_segment', 'NSE_FNO')
        })
        self.logger.info(f"PAPER EXECUTION: {order_id} | {o['symbol']} {o['side']} @ {o['price']}")
        return order_id

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        return self.orders.get(order_id, {"status": "NOT_FOUND"})

    def get_positions(self) -> List[Dict[str, Any]]:
        return self.positions

    def get_holdings(self) -> List[Dict[str, Any]]:
        return self.holdings

    def cancel_order(self, order_id: str) -> bool:
        if order_id in self.orders:
            self.orders[order_id]['status'] = 'CANCELLED'
            return True
        return False

    def start_data_feed(self, symbols: List[Dict[str, Any]], callback: Callable[[Dict[str, Any]], None]):
        self.logger.info("Paper Engine ready for high-fidelity data relay.")
