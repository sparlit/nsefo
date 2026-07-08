import nsefo_core
import pandas as pd
from typing import List, Dict, Any

class BrainEngine:
    def __init__(self):
        pass

    def analyze_symbol(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyzes a single symbol using Rust-powered indicators.
        """
        close_data = df['close'].tolist()
        ema_20 = nsefo_core.get_ema_list(close_data, 20)

        # In a real scenario, we'd pass multiple indicators to calculate_probability
        # For now, let's mock it with the last close vs last ema
        indicators = [1.0 if close_data[-1] > ema_20[-1] else -1.0]
        probability = nsefo_core.calculate_probability(indicators)

        return {
            "last_ema": ema_20[-1],
            "probability": probability,
            "signal": "BUY" if probability > 0.7 else "SELL" if probability < 0.3 else "NEUTRAL"
        }

    def batch_analyze(self, data_map: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        results = {}
        for symbol, df in data_map.items():
            results[symbol] = self.analyze_symbol(df)
        return results
