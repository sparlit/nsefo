import re
import logging
from typing import Dict, Any, Optional

class CommandParser:
    def __init__(self):
        self.logger = logging.getLogger("CommandParser")
        # Flexible patterns for: "buy nifty 24200 pe", "go long banknifty 48000 calls", "short finnifty 21000 pe"
        self.patterns = [
            # Standard: action symbol strike type
            r"(buy|sell|long|short)\s+([\w\s]+)\s+(\d+)\s+(ce|pe|call|put|calls|puts)",
            # Actionless (default buy): symbol strike type
            r"([\w\s]+)\s+(\d+)\s+(ce|pe|call|put|calls|puts)",
            # Action + Symbol (Market)
            r"(buy|sell|long|short)\s+([\w\s]+)"
        ]

    def parse_command(self, text: str) -> Optional[Dict[str, Any]]:
        text = text.lower().strip()

        for pattern in self.patterns:
            match = re.search(pattern, text)
            if match:
                groups = match.groups()
                if len(groups) == 4:
                    action, symbol, strike, opt_type = groups
                    return self._build_result(action, symbol, strike, opt_type)
                elif len(groups) == 3:
                    symbol, strike, opt_type = groups
                    return self._build_result("buy", symbol, strike, opt_type)
                elif len(groups) == 2:
                    action, symbol = groups
                    return self._build_result(action, symbol)
        return None

    def _build_result(self, action, symbol, strike=None, opt_type=None):
        # Normalize action
        action = "BUY" if action in ["buy", "long"] else "SELL"
        # Normalize opt_type
        if opt_type:
            opt_type = "CE" if opt_type in ["ce", "call", "calls"] else "PE"

        return {
            "action": action,
            "symbol": symbol.strip().upper(),
            "strike": int(strike) if strike else None,
            "option_type": opt_type,
            "raw": f"{action} {symbol} {strike} {opt_type}"
        }

    def interpret(self, text: str) -> Dict[str, Any]:
        parsed = self.parse_command(text)
        if not parsed:
            return {"status": "error", "message": f"Could not interpret command: {text}"}
        return {"status": "success", "data": parsed}
