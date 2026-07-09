import nsefo_core
import pandas as pd
import logging
from typing import List, Dict, Any

class BrainEngine:
    def __init__(self):
        self.logger = logging.getLogger("BrainEngine")

    def analyze_symbol(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Coordinates between specialized brains: Trend, Volatility, and Mean Reversion.
        """
        if df.empty or len(df) < 20:
            return {"probability": 0.5, "signal": "NEUTRAL"}

        try:
            close = df['close'].astype(float).tolist()
            high = df['high'].astype(float).tolist()
            low = df['low'].astype(float).tolist()

            # Brain 1: Mean Reversion (RSI)
            rsi = nsefo_core.get_rsi_list(close, 14)
            curr_rsi = rsi[-1]

            # Brain 2: Trend (Supertrend)
            st_values, trends = nsefo_core.get_supertrend(high, low, close, 10, 3.0)
            curr_trend = trends[-1]

            # Brain 3: Volatility (Standard Deviation)
            vol = nsefo_core.get_volatility_list(close, 20)
            curr_vol = vol[-1]
            avg_vol = sum(vol[-10:]) / 10

            # Multi-Brain Synthesis for Probability
            trend_score = float(curr_trend)
            rsi_score = 0.0
            if curr_rsi < 30: rsi_score = 1.0
            elif curr_rsi > 70: rsi_score = -1.0

            # Volatility Score: High volatility increases conviction for trend followers
            vol_multiplier = 1.2 if curr_vol > avg_vol else 0.8

            # Synthesize
            base_prob = nsefo_core.calculate_probability([trend_score, rsi_score])
            final_prob = (base_prob * vol_multiplier).clamp(0.0, 1.0) if hasattr(base_prob, "clamp") else min(1.0, base_prob * vol_multiplier)

            return {
                "probability": round(final_prob, 2),
                "signal": "BUY" if (final_prob > 0.8) else "SELL" if (final_prob < 0.2) else "NEUTRAL",
                "brains": {
                    "trend": "UP" if curr_trend == 1 else "DOWN",
                    "rsi": round(curr_rsi, 1),
                    "volatility": "HIGH" if curr_vol > avg_vol else "NORMAL"
                }
            }
        except Exception as e:
            self.logger.error(f"Multi-brain analysis failed: {e}")
            return {"probability": 0.5, "signal": "ERROR"}
