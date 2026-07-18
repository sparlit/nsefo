import nsefo_core
import pandas as pd
import logging
from opengreeks.black_scholes import delta as calculate_delta
from typing import List, Dict, Any, Optional

# Magic numbers that were previously hardcoded inline — now explicit and tunable
RSI_PERIOD = 14
SUPERTREND_PERIOD = 10
SUPERTREND_MULTIPLIER = 3.0
VOLATILITY_PERIOD = 20
ATR_PERIOD = 14          # used for stop-loss sizing
RISK_FREE_RATE = 0.0695  # 6.95% 91-day T-bill rate (annualised)
DAYS_TO_EXPIRY = 30      # placeholder TTM in days for delta calculation


class BrainEngine:
    def __init__(self):
        self.logger = logging.getLogger("BrainEngine")

    def analyze_symbol(
        self,
        df: pd.DataFrame,
        strike: Optional[float] = None,
        option_type: str = "CE",
        days_to_expiry: float = DAYS_TO_EXPIRY / 365.0,
    ) -> Dict[str, Any]:
        """
        Synthesizes indicators using Rust performance core and OpenGreeks.

        Args:
            df: DataFrame with at least 'close', 'high', 'low' columns.
                Must have >= 14 rows for RSI, >= 21 for valid annualized vol.
            strike: Option strike price. If None, uses spot (ATM approximation).
            option_type: 'CE' or 'PE'. Defaults to 'CE' (call).
            days_to_expiry: Time to expiry in years. Defaults to ~30 days.
        """
        if df.empty or len(df) < 21:
            # Need 21+ rows: 14 for RSI + 20 for first valid annualized vol
            return {
                "probability": 0.5,
                "signal": "INSUFFICIENT_DATA",
                "brains": {},
            }

        try:
            close = df['close'].astype(float).tolist()
            high = df['high'].astype(float).tolist()
            low  = df['low'].astype(float).tolist()

            spot = close[-1]
            K = strike if strike is not None else spot   # ATM if no strike provided
            flag = 'c' if option_type.upper().startswith('C') else 'p'

            # ── Momentum (Rust) ─────────────────────────────────────────────
            rsi = nsefo_core.get_rsi_list(close, RSI_PERIOD)
            curr_rsi = rsi[-1]

            # ── Trend (Rust) ────────────────────────────────────────────────
            st_values, trends = nsefo_core.get_supertrend(
                high, low, close, SUPERTREND_PERIOD, SUPERTREND_MULTIPLIER
            )
            curr_trend = trends[-1]

            # ── Annualized volatility from log-returns (Rust) ───────────────
            # Previously broken: (std_dev / spot) * sqrt(252) is dimensionally wrong.
            # Correct: std_dev of log returns × √252, computed over a rolling window.
            ann_vol_list = nsefo_core.get_annualized_volatility_list(close, VOLATILITY_PERIOD)
            ann_vol = ann_vol_list[-1]
            avg_vol = sum(ann_vol_list[-(VOLATILITY_PERIOD // 2):]) / (VOLATILITY_PERIOD // 2)

            # ── ATR for stop-loss sizing (Rust) ──────────────────────────────
            atr_list = nsefo_core.get_atr_list(high, low, close, ATR_PERIOD)
            curr_atr = atr_list[-1] if atr_list else 0.0

            # ── Delta via OpenGreeks (correct sigma = ann_vol, correct K) ─────
            d = calculate_delta(flag, spot, K, days_to_expiry, RISK_FREE_RATE, ann_vol)

            # ── Expert Synthesis ────────────────────────────────────────────
            trend_score   = float(curr_trend)
            rsi_score     = 1.0 if curr_rsi < 30 else -1.0 if curr_rsi > 70 else 0.0
            vol_conviction = 1.2 if ann_vol > avg_vol else 0.8

            base_prob  = nsefo_core.calculate_probability([trend_score, rsi_score])
            final_prob = min(1.0, max(0.0, base_prob * vol_conviction))

            signal = (
                "BUY"  if final_prob > 0.8 and curr_trend == 1
                else "SELL" if final_prob < 0.2 and curr_trend == -1
                else "NEUTRAL"
            )

            return {
                "probability": round(final_prob, 3),
                "signal": signal,
                "brains": {
                    "trend":     "UP"   if curr_trend == 1  else "DOWN",
                    "rsi":       round(curr_rsi, 1),
                    "volatility": "HIGH" if ann_vol > avg_vol else "NORMAL",
                    "ann_vol":   round(ann_vol, 4),
                    "delta":     round(d, 4),
                    "atr":       round(curr_atr, 2),
                    "strike":    K,
                    "moneyness": "ITM" if (flag == 'c' and K < spot) or (flag == 'p' and K > spot)
                                 else "OTM" if (flag == 'c' and K > spot) or (flag == 'p' and K < spot)
                                 else "ATM",
                },
            }
        except Exception as e:
            self.logger.error(f"Brain Sync Error: {e}")
            return {"probability": 0.0, "signal": "SYSTEM_ERROR", "brains": {}}
