from typing import Dict, Any

class RiskManager:
    def __init__(self, capital: float):
        self.capital = capital
        self.max_risk_per_trade = 0.01 # 1%
        self.daily_stop_loss = 0.03 # 3%

    def assess_trade(self, entry: float, sl: float, quantity: int) -> Dict[str, Any]:
        risk_amount = abs(entry - sl) * quantity
        risk_percent = (risk_amount / self.capital) * 100

        is_safe = risk_percent <= (self.max_risk_per_trade * 100)

        return {
            "risk_amount": risk_amount,
            "risk_percent": risk_percent,
            "is_safe": is_safe,
            "recommendation": "PROCEED" if is_safe else "REDUCE QUANTITY"
        }
