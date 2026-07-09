import pandas as pd
import json
import logging
import time
import sys
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List
from python_app.nlp.parser import CommandParser
from python_app.core.risk_manager import RiskManager
from python_app.core.engine import BrainEngine
from python_app.core.coordinator import Coordinator
from python_app.broker.session_manager import SessionManager
from python_app.core.utils import auto_confirm_trade
from python_app.core.state import global_state

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class TradingApp:
    def __init__(self):
        self.session = SessionManager()
        self.parser = CommandParser()
        self.risk_manager = RiskManager(
            capital=self.session.config['risk']['capital'],
            max_risk_per_trade=self.session.config['risk'].get('max_risk_per_trade_percent', 1.0)/100.0
        )
        self.engine = BrainEngine()
        self.broker = self.session.get_broker()
        self.coordinator = Coordinator(self.broker, self.engine, self.risk_manager)
        self.logger = logging.getLogger("TradingApp")
        self.running = False
        self.watch_list = ["NIFTY", "BANKNIFTY", "FINNIFTY"]
        self.symbol_map = {"NIFTY": "13", "BANKNIFTY": "25", "FINNIFTY": "27"}

        # Initialize global state
        global_state.update_summary(
            capital=self.session.config['risk']['capital'],
            mode=self.session.config['mode']
        )
        global_state.set_scanning(self.watch_list)

    def handle_manual_suggestion(self, command: str):
        self.logger.info(f"EXPERT SYSTEM: ANALYSING INSTRUCTION -> {command}")
        global_state.add_log(f"Manual Input: {command}")
        parsed = self.parser.interpret(command)
        if parsed["status"] == "error": return parsed

        data = parsed["data"]
        sid = self.symbol_map.get(data['symbol'], "13")
        symbol_info = {'security_id': sid, 'exchange_segment': 'NSE_EQ'}

        # Pull Live Market Data
        market_data = self.broker.get_market_data([symbol_info])
        last_price = self._extract_ltp(market_data, sid)

        # Expert Multi-Brain Analysis
        df_context = self._get_context_data(symbol_info, last_price)
        analysis = self.engine.analyze_symbol(df_context)
        prob = analysis['probability']

        # Position Sizing: FIXED LOTS from configuration
        fixed_lots = int(self.session.config['risk'].get('fixed_lots', 1))
        quantity = fixed_lots * 50

        sl_val = last_price * 0.985 if data['action'] == 'BUY' else last_price * 1.015
        risk_report = self.risk_manager.assess_trade(last_price, sl_val, quantity)

        report = {
            "symbol": data['symbol'], "last_price": last_price, "probability": prob,
            "fixed_lots": fixed_lots, "quantity": quantity,
            "brains": analysis.get('brains'), "risk": risk_report,
            "decision": "EXECUTE" if prob > 0.8 and risk_report['is_safe'] else "REJECT"
        }

        print("\n" + "#"*60 + "\nMASTER PRO EXPERT ANALYSIS\n" + "#"*60)
        print(json.dumps(report, indent=2))

        if auto_confirm_trade(data, recommend_action="YES" if report['decision'] == "EXECUTE" else "NO"):
            proposal = {
                'security_id': sid, 'exchange_segment': 'NSE_FNO',
                'symbol': data['symbol'], 'side': data['action'],
                'quantity': quantity, 'price': last_price, 'sl': sl_val,
                'tag': 'NSEFO_EXPERT'
            }
            order_id = self.coordinator.execute_confirmed_trade(proposal)
            if order_id:
                global_state.add_log(f"Executed {data['action']} {data['symbol']} @ {last_price}")

        return report

    def _extract_ltp(self, market_data, sid):
        if market_data and 'data' in market_data:
            if isinstance(market_data['data'], dict):
                return float(market_data['data'].get(sid, {}).get('last_price', 100.0))
            elif isinstance(market_data['data'], list) and len(market_data['data']) > 0:
                return float(market_data['data'][0].get('last_price', 100.0))
        return 100.0

    def _get_context_data(self, symbol_info, last_price):
        now = datetime.now()
        hist_data = self.broker.get_historical_data(
            symbol_info, "1",
            (now - timedelta(minutes=60)).strftime("%Y-%m-%d %H:%M:%S"),
            now.strftime("%Y-%m-%d %H:%M:%S")
        )
        if hist_data and isinstance(hist_data, list) and len(hist_data) > 14:
            return pd.DataFrame(hist_data)
        return pd.DataFrame({'high': [last_price*1.001]*30, 'low': [last_price*0.999]*30, 'close': [last_price]*30})

    def run_market_cycle(self):
        self.running = True
        self.logger.info("Expert System Heartbeat Initiated.")
        while self.running:
            try:
                # 1. Update Market Prices for Active Trades & Trailing SL
                current_prices = {}
                active_list = []
                for order_id, trade in self.coordinator.active_trades.items():
                    sid = self.symbol_map.get(trade['symbol'], "13")
                    quote = self.broker.get_market_data([{'security_id': sid, 'exchange_segment': 'NSE_EQ'}])
                    lp = self._extract_ltp(quote, sid)
                    current_prices[trade['symbol']] = lp
                    active_list.append({
                        "symbol": trade['symbol'], "side": trade['side'],
                        "price": trade['price'], "ltp": lp, "quantity": trade['quantity']
                    })

                self.coordinator.track_trades(current_prices)
                global_state.update_active_trades(active_list)

                # 2. Continuous Opportunity Scanning
                for symbol in self.watch_list:
                    sid = self.symbol_map.get(symbol)
                    info = {'security_id': sid, 'exchange_segment': 'NSE_EQ'}
                    quote = self.broker.get_market_data([info])
                    lp = self._extract_ltp(quote, sid)
                    df = self._get_context_data(info, lp)
                    analysis = self.engine.analyze_symbol(df)

                    if analysis['probability'] > 0.90:
                        self.logger.info(f"HIGH CONVICTION SIGNAL: {symbol} @ {lp}")
                        global_state.add_signal({
                            "symbol": symbol, "side": analysis['signal'],
                            "prob": analysis['probability'], "price": lp,
                            "brains": analysis['brains']
                        })

            except Exception as e:
                self.logger.error(f"Engine Loop Error: {e}")
            time.sleep(1)

    def start(self):
        threading.Thread(target=self.run_market_cycle, daemon=True).start()
        self.logger.info("NSEFO Master Pro Engine is fully operational.")

if __name__ == "__main__":
    app = TradingApp()
    if len(sys.argv) > 1:
        app.handle_manual_suggestion(" ".join(sys.argv[1:]))
    else:
        app.start()
        try:
            while True: time.sleep(1)
        except KeyboardInterrupt:
            app.running = False
