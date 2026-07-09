import logging
from typing import Dict, Any

class RiskManager:
    def __init__(self, capital: float, max_risk_per_trade: float = 0.01):
        self.capital = capital
        self.max_risk_per_trade = max_risk_per_trade
        self.logger = logging.getLogger("RiskManager")

    def assess_trade(self, entry: float, sl: float, quantity: int) -> Dict[str, Any]:
        """
        Expert risk assessment for the proposed trade.
        """
        risk_amount = abs(entry - sl) * quantity
        risk_percent = (risk_amount / self.capital) * 100
        is_safe = risk_percent <= (self.max_risk_per_trade * 100)

        return {
            "risk_amount": round(risk_amount, 2),
            "risk_percent": round(risk_percent, 2),
            "is_safe": is_safe,
            "recommendation": "PROCEED" if is_safe else "REDUCE QUANTITY/SIZE"
        }
