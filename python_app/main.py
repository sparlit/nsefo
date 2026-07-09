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

    def handle_manual_suggestion(self, command: str):
        self.logger.info(f"EXPERT SYSTEM: ANALYSING INSTRUCTION -> {command}")
        parsed = self.parser.interpret(command)
        if parsed["status"] == "error":
            return parsed

        data = parsed["data"]
        sid = self.symbol_map.get(data['symbol'], "13")
        symbol_info = {'security_id': sid, 'exchange_segment': 'NSE_EQ'}

        market_data = self.broker.get_market_data([symbol_info])
        last_price = float(market_data.get('data', {}).get('last_price', 100.0))

        # Real-time multi-brain analysis context
        df_context = self._get_context_data(symbol_info, last_price)
        analysis = self.engine.analyze_symbol(df_context)
        prob = analysis['probability']

        recommended_lots = 1 if prob < 0.85 else 2 if prob < 0.95 else 3
        quantity = recommended_lots * 50

        sl_val = last_price * 0.985 if data['action'] == 'BUY' else last_price * 1.015
        risk_report = self.risk_manager.assess_trade(last_price, sl_val, quantity)

        report = {
            "symbol": data['symbol'], "last_price": last_price, "probability": prob,
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
            self.coordinator.execute_confirmed_trade(proposal)

        return report

    def _get_context_data(self, symbol_info, last_price):
        now = datetime.now()
        hist_data = self.broker.get_historical_data(
            symbol_info, "1",
            (now - timedelta(minutes=60)).strftime("%Y-%m-%d %H:%M:%S"),
            now.strftime("%Y-%m-%d %H:%M:%S")
        )
        if hist_data and len(hist_data) > 20:
            return pd.DataFrame(hist_data)
        return pd.DataFrame({'high': [last_price*1.001]*30, 'low': [last_price*0.999]*30, 'close': [last_price]*30})

    def run_market_cycle(self):
        """
        The heartbeat of the expert system.
        Performs continuous scanning and trade maintenance.
        """
        self.running = True
        self.logger.info("Expert System Heartbeat Started.")
        while self.running:
            try:
                # 1. Update Market Prices for Active Trades
                current_prices = {}
                for order_id, trade in self.coordinator.active_trades.items():
                    sid = self.symbol_map.get(trade['symbol'], "13")
                    quote = self.broker.get_market_data([{'security_id': sid, 'exchange_segment': 'NSE_EQ'}])
                    current_prices[trade['symbol']] = float(quote.get('data', {}).get('last_price', 0.0))

                self.coordinator.track_trades(current_prices)

                # 2. Continuous Opportunity Scanning
                for symbol in self.watch_list:
                    sid = self.symbol_map.get(symbol)
                    info = {'security_id': sid, 'exchange_segment': 'NSE_EQ'}
                    quote = self.broker.get_market_data([info])
                    lp = float(quote.get('data', {}).get('last_price', 0.0))
                    df = self._get_context_data(info, lp)
                    analysis = self.engine.analyze_symbol(df)

                    if analysis['probability'] > 0.92:
                        self.logger.info(f"CRITICAL OPPORTUNITY: {symbol} Prob: {analysis['probability']}")
                        # Automated execution for top-tier signals could go here

            except Exception as e:
                self.logger.error(f"Cycle Error: {e}")
            time.sleep(2)

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
