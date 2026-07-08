import time
import logging
from typing import Dict, Any, List
from .engine import BrainEngine
from .risk_manager import RiskManager
from ..broker.base import Broker

class Coordinator:
    def __init__(self, broker: Broker, engine: BrainEngine, risk_manager: RiskManager):
        self.broker = broker
        self.engine = engine
        self.risk_manager = risk_manager
        self.active_trades: Dict[str, Dict[str, Any]] = {}
        self.logger = logging.getLogger("Coordinator")

    def monitor_market(self, symbols_data: Dict[str, Any]):
        """
        Coordinates between brains to find and confirm trades.
        """
        for symbol, df in symbols_data.items():
            analysis = self.engine.analyze_symbol(df)
            if analysis['probability'] > 0.85:
                # Strong signal found, move to confirmation
                self.logger.info(f"Strong Signal for {symbol}: {analysis}")
                # In real app, this would push to 'awaiting_confirmation' in dashboard

    def track_trades(self, current_prices: Dict[str, float]):
        """
        Independent brain tracking orders and maintaining SL/TP.
        """
        for order_id, trade in list(self.active_trades.items()):
            symbol = trade['symbol']
            price = current_prices.get(symbol)
            if not price: continue

            # Update Trailing SL
            self.apply_trailing_sl(order_id, trade, price)

    def apply_trailing_sl(self, order_id: str, trade: Dict[str, Any], current_price: float):
        side = trade['side']
        entry = trade['entry_price']
        sl = trade['sl']
        step = trade.get('trailing_step', 1.0)

        if side == 'BUY' and current_price > entry + step:
            new_sl = current_price - (entry - sl)
            if new_sl > sl:
                trade['sl'] = new_sl
                self.logger.info(f"Trailing SL Updated for {order_id}: {new_sl}")
        elif side == 'SELL' and current_price < entry - step:
            new_sl = current_price + (sl - entry)
            if new_sl < sl:
                trade['sl'] = new_sl
                self.logger.info(f"Trailing SL Updated for {order_id}: {new_sl}")

    def execute_confirmed_trade(self, proposal: Dict[str, Any]):
        # Final risk check before execution
        risk = self.risk_manager.assess_trade(proposal['price'], proposal['sl'], proposal['quantity'])
        if risk['is_safe']:
            order_id = self.broker.place_order(proposal)
            proposal['order_id'] = order_id
            self.active_trades[order_id] = proposal
            return order_id
        return None
