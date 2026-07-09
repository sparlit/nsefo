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
        self.risk_manager = RiskManager(capital=1000000) # Default 10L
        self.engine = BrainEngine()
        self.broker = self.session.get_broker()
        self.coordinator = Coordinator(self.broker, self.engine, self.risk_manager)
        self.logger = logging.getLogger("TradingApp")

    def handle_manual_suggestion(self, command: str):
        self.logger.info(f"User Suggestion: {command}")
        parsed = self.parser.interpret(command)
        if parsed["status"] == "error":
            print(f"Error: {parsed['message']}")
            return parsed

        data = parsed["data"]
        # Expert logic: Analyze current context for the suggested trade
        entry_price = 100.0 # Mock LTP
        sl = 85.0

        # Analyze probability using the multi-brain engine
        df_context = pd.DataFrame({
            'high': [102.0]*30, 'low': [98.0]*30, 'close': [100.0]*30
        })
        analysis = self.engine.analyze_symbol(df_context)
        prob = analysis['probability']

        # Position Sizing Suggestion
        recommended_lots = 1
        if prob > 0.9: recommended_lots = 3
        elif prob > 0.8: recommended_lots = 2

        quantity = recommended_lots * 50 # Assuming NIFTY 50 lot size
        risk_report = self.risk_manager.assess_trade(entry_price, sl, quantity)

        report = {
            "strategy_analysis": analysis,
            "risk_assessment": risk_report,
            "position_sizing": {
                "recommended_lots": recommended_lots,
                "total_quantity": quantity,
                "reason": "High conviction multi-brain alignment" if prob > 0.8 else "Standard risk profile"
            },
            "recommendation": "PROCEED" if prob > 0.7 and risk_report['is_safe'] else "CAUTION / REDUCE SIZE"
        }

        print("\n" + "="*40)
        print("MASTER PRO EXPERT ANALYSIS")
        print("="*40)
        print(json.dumps(report, indent=2))
        print("="*40)

        # Timed auto-confirmation
        confirm_default = "YES" if prob > 0.8 else "NO"
        if auto_confirm_trade(data, recommend_action=confirm_default):
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
                self.logger.info(f"EXPERT EXECUTION SUCCESS: {order_id}")
        else:
            self.logger.info("Trade cancelled by user or safety timeout.")

        return report

if __name__ == "__main__":
    import sys
    app = TradingApp()
    if len(sys.argv) > 1:
        app.handle_manual_suggestion(" ".join(sys.argv[1:]))
    else:
        print("NSE Options F&O Master Pro Expert Trader Active.")
