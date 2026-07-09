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
        results = {}
        for symbol, df in symbols_data.items():
            analysis = self.engine.analyze_symbol(df)
            results[symbol] = analysis
            if analysis['probability'] > 0.85:
                self.logger.info(f"HIGH CONVICTION signal for {symbol}: {analysis['brains']}")
        return results

    def track_trades(self, current_prices: Dict[str, float]):
        """
        Independent brain tracking and maintaining active positions.
        """
        for order_id, trade in list(self.active_trades.items()):
            symbol = trade['symbol']
            price = current_prices.get(symbol)
            if not price: continue
            self.apply_trailing_sl(order_id, trade, price)

    def apply_trailing_sl(self, order_id: str, trade: Dict[str, Any], current_price: float):
        side = trade['side']
        entry = trade['entry_price']
        sl = trade['sl']
        # Dynamic step based on volatility could be added here
        step = trade.get('trailing_step', 1.0)

        if side == 'BUY' and current_price > entry + step:
            # Trailing logic: if price moves up, SL moves up by the same distance
            new_sl = current_price - (entry - sl)
            if new_sl > sl:
                trade['sl'] = new_sl
                self.logger.info(f"Trail SL UP -> {new_sl}")
        elif side == 'SELL' and current_price < entry - step:
            new_sl = current_price + (sl - entry)
            if new_sl < sl:
                trade['sl'] = new_sl
                self.logger.info(f"Trail SL DOWN -> {new_sl}")

    def execute_confirmed_trade(self, proposal: Dict[str, Any]):
        # Expert check: Risk assessment + Coordination check
        risk = self.risk_manager.assess_trade(proposal['price'], proposal['sl'], proposal['quantity'])
        if risk['is_safe']:
            order_id = self.broker.place_order(proposal)
            proposal['order_id'] = order_id
            self.active_trades[order_id] = proposal
            return order_id
        else:
            self.logger.warning(f"Trade rejected by Risk Manager: {risk['recommendation']}")
            return None
