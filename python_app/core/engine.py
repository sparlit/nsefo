import nsefo_core
import pandas as pd
import logging
from opengreeks.black_scholes import delta as calculate_delta
from typing import List, Dict, Any

class BrainEngine:
    def __init__(self):
        self.logger = logging.getLogger("BrainEngine")

    def analyze_symbol(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Synthesizes indicators using Rust performance core and OpenGreeks.
        """
        if df.empty or len(df) < 14:
            return {"probability": 0.5, "signal": "INSUFFICIENT_DATA"}

        try:
            close = df['close'].astype(float).tolist()
            high = df['high'].astype(float).tolist()
            low = df['low'].astype(float).tolist()

            # Momentum (Rust)
            rsi = nsefo_core.get_rsi_list(close, 14)
            curr_rsi = rsi[-1]

            # Trend (Rust)
            st_values, trends = nsefo_core.get_supertrend(high, low, close, 10, 3.0)
            curr_trend = trends[-1]

            # Volatility (Rust)
            vol_list = nsefo_core.get_volatility_list(close, 20)
            curr_vol = vol_list[-1]
            avg_vol = sum(vol_list[-10:]) / 10

            # Delta calculation (OpenGreeks)
            # flag='c' (Call), S=Spot, K=Strike, t=Time, r=Rate, sigma=Vol
            # sigma is normalized annual volatility
            sigma = (curr_vol / close[-1]) * (252**0.5)
            d = calculate_delta('c', close[-1], close[-1], 30/365, 0.1, sigma)

            # Experts Synthesis
            trend_score = float(curr_trend)
            rsi_score = 1.0 if curr_rsi < 30 else -1.0 if curr_rsi > 70 else 0.0
            vol_conviction = 1.2 if curr_vol > avg_vol else 0.8

            base_prob = nsefo_core.calculate_probability([trend_score, rsi_score])
            final_prob = min(1.0, max(0.0, base_prob * vol_conviction))

            return {
                "probability": round(final_prob, 3),
                "signal": "BUY" if (final_prob > 0.8 and curr_trend == 1) else "SELL" if (final_prob < 0.2 and curr_trend == -1) else "NEUTRAL",
                "brains": {
                    "trend": "UP" if curr_trend == 1 else "DOWN",
                    "rsi": round(curr_rsi, 1),
                    "volatility": "HIGH" if curr_vol > avg_vol else "NORMAL",
                    "delta": round(d, 3)
                }
            }
        except Exception as e:
            self.logger.error(f"Brain Sync Error: {e}")
            return {"probability": 0.0, "signal": "SYSTEM_ERROR"}
