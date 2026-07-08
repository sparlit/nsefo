import time
from typing import Dict, Any, List
from .engine import BrainEngine
from ..broker.base import Broker

class Coordinator:
    def __init__(self, broker: Broker, engine: BrainEngine):
        self.broker = broker
        self.engine = engine
        self.active_trades: Dict[str, Dict[str, Any]] = {}
        self.risk_settings = {
            "max_drawdown": 0.05,
            "max_risk_per_trade": 0.02,
            "daily_max_loss": 5000
        }

    def track_trades(self):
        """
        Independent brain tracking orders and trailing SL/TP.
        """
        for order_id, trade in list(self.active_trades.items()):
            status = self.broker.get_order_status(order_id)
            # Update SL/TP logic here
            self.apply_trailing_sl(order_id, trade)

    def apply_trailing_sl(self, order_id: str, trade: Dict[str, Any]):
        # Implementation for trailing SL/TP
        # If price moves in favor, update SL in broker
        pass

    def validate_risk(self, trade_proposal: Dict[str, Any]) -> bool:
        # Check against risk_settings
        return True

    def execute_confirmed_trade(self, trade_proposal: Dict[str, Any]):
        if self.validate_risk(trade_proposal):
            order_id = self.broker.place_order(trade_proposal)
            self.active_trades[order_id] = trade_proposal
            return order_id
        return None

    def update_trailing_stops(self, current_prices: Dict[str, f64]):
        for order_id, trade in self.active_trades.items():
            symbol = trade.get('symbol')
            current_price = current_prices.get(symbol)
            if not current_price:
                continue

            entry_price = trade.get('entry_price')
            sl = trade.get('sl')
            tp = trade.get('tp')
            trailing_step = trade.get('trailing_step', 0)

            if trade['side'] == 'BUY':
                if current_price > entry_price + trailing_step:
                    new_sl = current_price - (entry_price - sl)
                    if new_sl > sl:
                        trade['sl'] = new_sl
                        # self.broker.modify_order(...)
            elif trade['side'] == 'SELL':
                if current_price < entry_price - trailing_step:
                    new_sl = current_price + (sl - entry_price)
                    if new_sl < sl:
                        trade['sl'] = new_sl
