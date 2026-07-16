import re
import logging
from typing import Dict, Any, Optional

class CommandParser:
    def __init__(self):
        self.logger = logging.getLogger("CommandParser")
        # Flexible patterns for: "buy nifty 24200 pe", "go long banknifty 48000 calls", "short finnifty 21000 pe"
        # Pattern 3: market order — action + symbol only (2 groups).
        # Use negative lookahead to prevent matching option-type keywords as symbol.
        # (?!\s*(?:ce|pe|call|put|calls|puts)) ensures symbol doesn't contain opt types.
        self.patterns = [
            # Pattern 1: action + symbol + strike + type  (4 groups) — most specific
            r"(buy|sell|long|short)\s+([\w\s]+?)(?=\s+\d)\s+(\d+)\s+(ce|pe|call|put|calls|puts)",
            # Pattern 2: symbolless (3 groups) — symbol inferred from context
            r"([\w\s]+?)(?=\s+\d)\s+(\d+)\s+(ce|pe|call|put|calls|puts)",
            # Pattern 3: market order — action + symbol only (2 groups).
            # Negative lookahead prevents matching:
            #   - option-type keywords (ce/pe/call/put)
            #   - any digit (prevents "Nifty 24500" from matching as market order)
            r"(buy|sell|long|short)\s+(?!.*(?:ce|pe|call|put|calls|puts|\d))([a-zA-Z][a-zA-Z\s]*)",
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

    SYMBOL_ALIASES = {
        "N": "NIFTY",
        "BN": "BANKNIFTY",
        "FN": "FINNIFTY",
        "BANK": "BANKNIFTY",
        "FINN": "FINNIFTY",
    }

    def _build_result(self, action, symbol, strike=None, opt_type=None):
        # Normalize action
        action = "BUY" if action in ["buy", "long"] else "SELL"
        # Normalize opt_type
        if opt_type:
            opt_type = "CE" if opt_type in ["ce", "call", "calls"] else "PE"

        raw_symbol = symbol.strip().upper()
        # Expand aliases
        symbol = self.SYMBOL_ALIASES.get(raw_symbol, raw_symbol)

        return {
            "action": action,
            "symbol": symbol,
            "strike": int(strike) if strike else None,
            "option_type": opt_type,
            "raw": f"{action} {symbol} {strike} {opt_type}"
        }

    def interpret(self, text: str) -> Dict[str, Any]:
        parsed = self.parse_command(text)
        if not parsed:
            return {"status": "error", "message": f"Could not interpret command: {text}"}
        return {"status": "success", "data": parsed}
