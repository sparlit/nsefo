import pandas as pd
import json
import logging
import time
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
        self.risk_manager = RiskManager(capital=100000)
        self.engine = BrainEngine()
        self.broker = self.session.get_broker()
        self.coordinator = Coordinator(self.broker, self.engine, self.risk_manager)
        self.logger = logging.getLogger("TradingApp")

    def handle_manual_suggestion(self, command: str):
        parsed = self.parser.interpret(command)
        if parsed["status"] == "error":
            return parsed

        data = parsed["data"]
        # Simplified for demonstration: assume fixed quantity and mock entry price
        entry_price = 100.0
        sl = 80.0
        quantity = 50

        risk_report = self.risk_manager.assess_trade(entry_price, sl, quantity)

        # Create a real analysis using mock data for context
        df = pd.DataFrame({
            'high': [102.0]*30, 'low': [98.0]*30, 'close': [100.0]*30
        })
        probability_report = self.engine.analyze_symbol(df)

        report = {
            "parsed": data,
            "risk": risk_report,
            "win_probability": probability_report["probability"],
            "recommendation": "STRONG BUY" if probability_report["probability"] > 0.8 and risk_report["is_safe"] else "CAUTION"
        }

        self.logger.info("EXPERT ANALYSIS COMPLETE")
        print(json.dumps(report, indent=2))

        # User input required with 10s timeout
        recommend_action = "YES" if report["recommendation"] == "STRONG BUY" else "NO"
        should_execute = auto_confirm_trade(data, recommend_action=recommend_action)

        if should_execute:
            self.logger.info("Action: EXECUTING TRADE via COORDINATOR...")
            proposal = {
                'symbol': data['symbol'],
                'side': data['action'],
                'quantity': quantity,
                'price': entry_price,
                'sl': sl,
                'exchange_segment': 'NSE_FNO'
            }
            order_id = self.coordinator.execute_confirmed_trade(proposal)
            if order_id:
                self.logger.info(f"Success! Order ID: {order_id}")
        else:
            self.logger.info("Action: TRADE CANCELLED BY USER OR TIMEOUT.")

        return report

    def run_market_cycle(self):
        """
        High-performance cycle to monitor market and track trades.
        """
        self.logger.info("Starting Market Cycle...")
        try:
            while True:
                # 1. Pull market data for symbols (Mock symbols for demo)
                symbols = ["NIFTY", "BANKNIFTY"]
                # In real scenario, self.broker.get_market_data(symbols)

                # 2. Track existing trades
                # mock_prices = {"NIFTY": 105.0, "BANKNIFTY": 48050.0}
                # self.coordinator.track_trades(mock_prices)

                # 3. Analyze for new signals
                # self.coordinator.monitor_market(mock_data_dfs)

                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("Market Cycle Stopped.")

if __name__ == "__main__":
    app = TradingApp()
    print("NSE Options F&O Master Pro Expert Trader Started.")

if __name__ == "__main__":
    import sys
    app = TradingApp()
    if len(sys.argv) > 1:
        command = " ".join(sys.argv[1:])
        app.handle_manual_suggestion(command)
    else:
        print("Usage: python3 python_app/main.py 'buy nifty 24200 pe'")
