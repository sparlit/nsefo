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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [ENGINE] - %(levelname)s - %(message)s')

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

        global_state.update_summary(
            capital=self.session.config['risk']['capital'],
            mode=self.session.config['mode']
        )
        global_state.set_scanning(self.watch_list)

    def handle_manual_suggestion(self, command: str):
        self.logger.info(f"Analyzing Instruction: {command}")
        global_state.add_log(f"Manual Input: {command}")
        parsed = self.parser.interpret(command)
        if parsed["status"] == "error": return parsed

        data = parsed["data"]
        sid = self.symbol_map.get(data['symbol'], "13")
        symbol_info = {'security_id': sid, 'exchange_segment': 'NSE_EQ'}

        market_data = self.broker.get_market_data([symbol_info])
        last_price = self._extract_ltp(market_data, sid)

        if last_price <= 0.0:
            self.logger.error("Live price unavailable. Aborting analysis.")
            return {"status": "error", "message": "Live price unavailable"}

        df_context = self._get_context_data(symbol_info, last_price)
        if df_context.empty:
            self.logger.error("Market context unavailable.")
            return {"status": "error", "message": "Market context unavailable"}

        analysis = self.engine.analyze_symbol(df_context)
        prob = analysis['probability']

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
                global_state.add_log(f"Order Success: {order_id}")

        return report

    def _extract_ltp(self, market_data, sid):
        """Extracts LTP from real Dhan/Fenix data structures."""
        try:
            if market_data and 'data' in market_data:
                d = market_data['data']
                if isinstance(d, dict):
                    # Dhan quote_data format
                    return float(d.get(sid, {}).get('last_price', 0.0))
                elif isinstance(d, list) and len(d) > 0:
                    return float(d[0].get('last_price', 0.0))
        except Exception as e:
            self.logger.debug(f"LTP extraction failed: {e}")
        return 0.0

    def _get_context_data(self, symbol_info, last_price):
        """Fetches real historical OHLC for brain processing."""
        now = datetime.now()
        try:
            hist_data = self.broker.get_historical_data(
                symbol_info, "1",
                (now - timedelta(minutes=60)).strftime("%Y-%m-%d %H:%M:%S"),
                now.strftime("%Y-%m-%d %H:%M:%S")
            )
            if hist_data and isinstance(hist_data, list) and len(hist_data) > 14:
                return pd.DataFrame(hist_data)
        except Exception as e:
            self.logger.error(f"Historical fetch failed: {e}")
        return pd.DataFrame()

    def run_market_cycle(self):
        self.running = True
        self.logger.info("Neural Scanning Cycle Started.")
        while self.running:
            try:
                current_prices = {}
                active_list = []
                # Fixed: Creating a copy of keys to avoid modification error
                for order_id in list(self.coordinator.active_trades.keys()):
                    trade = self.coordinator.active_trades[order_id]
                    sid = self.symbol_map.get(trade['symbol'], "13")
                    quote = self.broker.get_market_data([{'security_id': sid, 'exchange_segment': 'NSE_EQ'}])
                    lp = self._extract_ltp(quote, sid)
                    if lp > 0:
                        current_prices[trade['symbol']] = lp
                        active_list.append({"symbol": trade['symbol'], "side": trade['side'], "price": trade['price'], "ltp": lp, "quantity": trade['quantity']})

                self.coordinator.track_trades(current_prices)
                global_state.update_active_trades(active_list)

                for symbol in self.watch_list:
                    sid = self.symbol_map.get(symbol)
                    info = {'security_id': sid, 'exchange_segment': 'NSE_EQ'}
                    quote = self.broker.get_market_data([info])
                    lp = self._extract_ltp(quote, sid)
                    if lp > 0:
                        df = self._get_context_data(info, lp)
                        if not df.empty:
                            analysis = self.engine.analyze_symbol(df)
                            if analysis['probability'] > 0.90:
                                global_state.add_signal({"symbol": symbol, "side": analysis['signal'], "prob": analysis['probability'], "price": lp, "brains": analysis['brains']})
            except Exception as e:
                self.logger.error(f"Cycle Exception: {e}")
            time.sleep(1)

    def start(self):
        self.logger.info("Activating Master Pro Core Loop...")
        self.run_market_cycle()

if __name__ == "__main__":
    app = TradingApp()
    if len(sys.argv) > 1:
        app.handle_manual_suggestion(" ".join(sys.argv[1:]))
    else:
        app.start()
