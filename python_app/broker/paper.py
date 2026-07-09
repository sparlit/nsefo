import uuid
import threading
import time
import random
from datetime import datetime
from .base import Broker
from typing import List, Dict, Any, Callable

class PaperBroker(Broker):
    def __init__(self):
        self.orders = {}
        self.positions = []
        self.holdings = []
        self.virtual_balance = 1000000.0
        self.streaming = False

    def login(self, **kwargs):
        return True

    def get_market_data(self, symbols: List[str]) -> Dict[str, Any]:
        return {symbol: {"ltp": 100.0} for symbol in symbols}

    def place_order(self, order_details: Dict[str, Any]) -> str:
        order_id = str(uuid.uuid4())
        order_details['order_id'] = order_id
        order_details['status'] = 'EXECUTED'
        order_details['order_time'] = str(datetime.now())
        self.orders[order_id] = order_details

        self.positions.append({
            "symbol": order_details['symbol'],
            "quantity": order_details['quantity'],
            "average_price": order_details.get('price', 100.0),
            "side": order_details['transaction_type']
        })
        return order_id

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        return self.orders.get(order_id, {"status": "NOT_FOUND"})

    def get_positions(self) -> List[Dict[str, Any]]:
        return self.positions

    def get_holdings(self) -> List[Dict[str, Any]]:
        return self.holdings

    def cancel_order(self, order_id: str):
        if order_id in self.orders:
            self.orders[order_id]['status'] = 'CANCELLED'

    def start_data_feed(self, symbols: List[Dict[str, Any]], callback: Callable[[Dict[str, Any]], None]):
        self.streaming = True
        def simulate_feed():
            prices = {s['security_id']: 100.0 for s in symbols}
            while self.streaming:
                for s in symbols:
                    sid = s['security_id']
                    # Random walk
                    prices[sid] += random.uniform(-0.5, 0.5)
                    tick = {
                        "type": "tick",
                        "security_id": sid,
                        "ltp": round(prices[sid], 2),
                        "timestamp": str(datetime.now())
                    }
                    callback(tick)
                time.sleep(0.5) # Simulating sub-second ticks

        thread = threading.Thread(target=simulate_feed, daemon=True)
        thread.start()

    def stop_data_feed(self):
        self.streaming = False
