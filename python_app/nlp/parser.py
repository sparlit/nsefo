import re
from typing import Dict, Any, Optional

class CommandParser:
    def __init__(self):
        # Patterns for: buy nifty 24200 pe, sell banknifty 45000 ce
        self.trade_pattern = re.compile(
            r"(buy|sell)\s+([\w\s]+)\s+(\d+)\s+(ce|pe)", re.IGNORECASE
        )

    def parse_command(self, text: str) -> Optional[Dict[str, Any]]:
        match = self.trade_pattern.search(text)
        if match:
            side, symbol, strike, option_type = match.groups()
            return {
                "action": side.upper(),
                "symbol": symbol.strip().upper(),
                "strike": int(strike),
                "option_type": option_type.upper(),
                "raw": text
            }
        return None

    def interpret(self, text: str) -> Dict[str, Any]:
        parsed = self.parse_command(text)
        if not parsed:
            return {"status": "error", "message": "Could not parse command"}

        # In a real scenario, we'd map 'NIFTY' to its instrument ID
        return {
            "status": "success",
            "data": parsed
        }
