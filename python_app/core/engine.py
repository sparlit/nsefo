import nsefo_core
import pandas as pd
import logging
from typing import List, Dict, Any

class BrainEngine:
    def __init__(self):
        self.logger = logging.getLogger("BrainEngine")

    def analyze_symbol(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyzes a single symbol using real Rust-powered indicators.
        """
        if df.empty or len(df) < 14:
            return {"probability": 0.5, "signal": "NEUTRAL"}

        try:
            close = df['close'].astype(float).tolist()
            high = df['high'].astype(float).tolist()
            low = df['low'].astype(float).tolist()

            # Calculate RSI
            rsi = nsefo_core.get_rsi_list(close, 14)

            # Calculate Supertrend
            # Using standard 10, 3 parameters
            st_values, trends = nsefo_core.get_supertrend(high, low, close, 10, 3.0)

            # Current status from the most recent completed bar
            curr_trend = trends[-1]
            curr_rsi = rsi[-1]

            # Indicators for probability assessment
            trend_score = float(curr_trend)

            rsi_score = 0.0
            if curr_rsi < 30: rsi_score = 1.0
            elif curr_rsi > 70: rsi_score = -1.0

            probability = nsefo_core.calculate_probability([trend_score, rsi_score])

            return {
                "probability": probability,
                "signal": "BUY" if (probability > 0.75 and curr_trend == 1) else "SELL" if (probability < 0.25 and curr_trend == -1) else "NEUTRAL",
                "rsi": round(curr_rsi, 2),
                "trend": "UP" if curr_trend == 1 else "DOWN",
                "st_value": round(st_values[-1], 2)
            }
        except Exception as e:
            self.logger.error(f"Analysis failed: {e}")
            return {"probability": 0.5, "signal": "ERROR"}
