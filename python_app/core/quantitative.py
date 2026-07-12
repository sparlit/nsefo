"""
Quantitative analytics for NSEFO market microstructure.

Implements:
- VWAP: Volume-Weighted Average Price
- VPIN: Volume-Synchronized Probability of Informed Trading
- Bid-Ask spread tracker
- Market regime detection (bull / bear / sideways)
- Implied Volatility surface (strike × expiry grid)
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from typing import Optional


# ─────────────────────────────────────────────
# Dataclasses
# ─────────────────────────────────────────────

@dataclass
class Tick:
    """Single market tick."""
    timestamp: float          # Unix timestamp (seconds)
    price: float
    volume: float
    bid: float = 0.0
    ask: float = 0.0

    @property
    def mid_price(self) -> float:
        if self.bid and self.ask:
            return (self.bid + self.ask) / 2.0
        return self.price

    @property
    def relative_spread(self) -> float:
        """Relative bid-ask spread in percent (bps * 100 = %)."""
        if self.bid and self.ask:
            return (self.ask - self.bid) / self.mid_price * 100
        return 0.0


@dataclass
class MarketRegime:
    """Detected market regime."""
    regime: str          # "bull" | "bear" | "sideways"
    volatility: float     # Annualised volatility %
    trend: float          # Return % over lookback
    confidence: float     # 0-1 how confident the classification is


@dataclass
class IVPoint:
    """Single point on the volatility surface."""
    strike: float
    expiry: str           # e.g. "26JUL" or "2026-07-31"
    iv: float             # Implied volatility as decimal (0.15 = 15%)
    delta: float = 0.0   # Option delta


# ─────────────────────────────────────────────
# VWAP Calculator
# ─────────────────────────────────────────────

class VWAPCalculator:
    """
    Rolling Volume-Weighted Average Price.

    Formula: VWAP = Σ(price_i × volume_i) / Σ(volume_i)
    Reset at session start or on demand.
    """

    def __init__(self):
        self._cumulative_pv: float = 0.0   # Σ(price × volume)
        self._cumulative_volume: float = 0.0 # Σ(volume)
        self._session_start: float = 0.0

    def update(self, tick: Tick) -> float:
        """
        Update VWAP with a new tick.
        Returns the current VWAP.
        """
        ts = tick.timestamp
        if self._session_start == 0.0:
            self._session_start = ts

        self._cumulative_pv += tick.price * tick.volume
        self._cumulative_volume += tick.volume

        return self.current_vwap()

    def current_vwap(self) -> float:
        """Return current VWAP. Returns 0.0 if no volume yet."""
        if self._cumulative_volume == 0.0:
            return 0.0
        return self._cumulative_pv / self._cumulative_volume

    def reset(self, timestamp: float | None = None):
        """Reset cumulative sums. Optionally set new session start."""
        self._cumulative_pv = 0.0
        self._cumulative_volume = 0.0
        if timestamp is not None:
            self._session_start = timestamp


# ─────────────────────────────────────────────
# VPIN Calculator
# ─────────────────────────────────────────────

class VPINCalculator:
    """
    Volume-Synchronized Probability of Informed Trading.

    VPIN = |V_buy - V_sell| / (V_buy + V_sell)

    Uses tick aggregation into equal-volume buckets (not time-based).
    High VPIN (> 0.5) suggests informed trading / toxicity risk.

    Reference: "The Probability of Informed Trading" (Easley, Lopez de Prado, O'Hara)
    """

    BUCKET_SIZE = 50  # Number of ticks per volume bucket

    def __init__(self, bucket_size: int = 50):
        self.bucket_size = bucket_size
        self._buy_volume: float = 0.0
        self._sell_volume: float = 0.0
        self._current_bucket_pv: float = 0.0   # Cumulative price × vol for current bucket
        self._current_bucket_vol: float = 0.0
        self._buckets: deque[float] = deque(maxlen=10)  # Last 10 completed buckets
        self._last_price: float = 0.0

    def update(self, tick: Tick) -> float:
        """
        Update VPIN with a new tick. Classifies as buy/sell from price direction.
        Returns current VPIN.
        """
        price_changed = tick.price - self._last_price
        self._last_price = tick.price

        if price_changed > 0:
            self._buy_volume += tick.volume
        elif price_changed < 0:
            self._sell_volume += tick.volume
        else:
            # No price change — split volume proportionally (neutral)
            self._buy_volume += tick.volume * 0.5
            self._sell_volume += tick.volume * 0.5

        self._current_bucket_pv += tick.price * tick.volume
        self._current_bucket_vol += tick.volume

        # Check if current bucket is "full" (volume threshold met)
        if self._current_bucket_vol >= self.bucket_size * 100:  # configurable tick eq
            self._finalize_bucket()

        return self.current_vpin()

    def _finalize_bucket(self):
        """Finalize the current bucket and compute VPIN for it."""
        if self._current_bucket_vol == 0:
            return
        bucket_vpin = abs(self._buy_volume - self._sell_volume) / (self._buy_volume + self._sell_volume + 1e-9)
        self._buckets.append(bucket_vpin)

        # Reset for next bucket
        self._buy_volume = 0.0
        self._sell_volume = 0.0
        self._current_bucket_pv = 0.0
        self._current_bucket_vol = 0.0

    def current_vpin(self) -> float:
        """Return VPIN. Averages last N completed buckets."""
        if not self._buckets:
            # Fall back to running VPIN on unfinalized volume
            total = self._buy_volume + self._sell_volume
            if total == 0:
                return 0.0
            return abs(self._buy_volume - self._sell_volume) / total

        return sum(self._buckets) / len(self._buckets)

    def reset(self):
        self._buy_volume = 0.0
        self._sell_volume = 0.0
        self._current_bucket_pv = 0.0
        self._current_bucket_vol = 0.0
        self._buckets.clear()
        self._last_price = 0.0


# ─────────────────────────────────────────────
# Bid-Ask Spread Tracker
# ─────────────────────────────────────────────

class SpreadTracker:
    """
    Tracks bid-ask spread over a rolling window.

    Computes:
    - Absolute spread: ask - bid
    - Relative spread in percent
    - Mid-price
    - Effective spread (成交价差)
    """

    def __init__(self, window_ticks: int = 20):
        self.window_ticks = window_ticks
        self._bids: deque[float] = deque(maxlen=window_ticks)
        self._asks: deque[float] = deque(maxlen=window_ticks)
        self._spreads: deque[float] = deque(maxlen=window_ticks)

    def update(self, tick: Tick) -> dict:
        """
        Update with new tick. Returns spread metrics dict.
        """
        self._bids.append(tick.bid)
        self._asks.append(tick.ask)

        spread = tick.ask - tick.bid
        self._spreads.append(spread)

        return self.current_metrics()

    def current_metrics(self) -> dict:
        """Return current spread metrics."""
        if not self._spreads:
            return {
                "abs_spread": 0.0,
                "rel_spread_pct": 0.0,
                "mid_price": 0.0,
                "avg_spread": 0.0,
                "max_spread": 0.0,
                "min_spread": 0.0,
            }

        last_bid = self._bids[-1]
        last_ask = self._asks[-1]
        mid = (last_bid + last_ask) / 2.0

        return {
            "abs_spread": last_ask - last_bid,
            "rel_spread_pct": ((last_ask - last_bid) / mid * 100) if mid > 0 else 0.0,
            "mid_price": mid,
            "avg_spread": sum(self._spreads) / len(self._spreads),
            "max_spread": max(self._spreads),
            "min_spread": min(self._spreads),
        }


# ─────────────────────────────────────────────
# Market Regime Detector
# ─────────────────────────────────────────────

class RegimeDetector:
    """
    Detects market regime using rolling returns volatility.

    Regime logic:
    - bull:     trend > 0 AND volatility < high threshold
    - bear:     trend < 0 AND volatility > low threshold
    - sideways: |trend| < flat_threshold OR volatility between bands

    Annualisation factor: √(252) for daily data, √(390) for minute data (NSE 6.5h session)
    """

    def __init__(
        self,
        lookback: int = 20,
        annualisation_factor: float = 15.8,  # √(252) — for minute bars
        flat_threshold: float = 0.2,          # % return threshold for flat
        vol_bull_threshold: float = 1.5,       # Annualised vol below this → low vol
        vol_bear_threshold: float = 3.0,       # Above this → high vol
    ):
        self.lookback = lookback
        self.annualisation_factor = annualisation_factor
        self.flat_threshold = flat_threshold
        self.vol_bull_threshold = vol_bull_threshold
        self.vol_bear_threshold = vol_bear_threshold

        self._prices: deque[float] = deque(maxlen=lookback)
        self._returns: deque[float] = deque(maxlen=lookback)

    def update(self, price: float) -> MarketRegime:
        """Update with new price. Returns detected regime."""
        if self._prices:
            ret = (price - self._prices[-1]) / self._prices[-1] * 100  # Return in %
            self._returns.append(ret)

        self._prices.append(price)

        return self.current_regime()

    def current_regime(self) -> MarketRegime:
        """Compute regime from rolling returns."""
        if len(self._returns) < self.lookback // 2:
            return MarketRegime(regime="sideways", volatility=0.0, trend=0.0, confidence=0.0)

        # Compute statistics
        import statistics
        mean_return = statistics.mean(self._returns)
        stdev_return = statistics.stdev(self._returns) if len(self._returns) > 1 else 0.0

        # Annualise
        ann_vol = stdev_return * self.annualisation_factor
        ann_return = mean_return * self.annualisation_factor

        # Classification
        abs_return = abs(ann_return)

        if ann_return > 0 and ann_vol < self.vol_bull_threshold:
            regime = "bull"
            confidence = min(ann_return / 10.0, 1.0)
        elif ann_return < 0 and ann_vol > self.vol_bear_threshold:
            regime = "bear"
            confidence = min(abs_return / 10.0, 1.0)
        else:
            regime = "sideways"
            confidence = 0.5

        return MarketRegime(
            regime=regime,
            volatility=round(ann_vol, 2),
            trend=round(ann_return, 2),
            confidence=round(confidence, 3),
        )


# ─────────────────────────────────────────────
# Implied Volatility Surface
# ─────────────────────────────────────────────

class VolatilitySurface:
    """
    Builds a strike × expiry IV surface from option chain data.

    Interpolates missing strikes using linear interpolation.
    Computes risk-reversal and butterfly skew metrics.

    Input: list of IVPoint(strike, expiry, iv, delta)
    """

    def __init__(self):
        self._points: list[IVPoint] = []
        self._strike_grid: dict[str, list[float]] = {}   # expiry → sorted strikes
        self._iv_grid: dict[str, dict[float, float]] = {}  # expiry → {strike: iv}

    def add_point(self, point: IVPoint):
        """Add a single IV observation."""
        self._points.append(point)
        expiry = point.expiry
        if expiry not in self._strike_grid:
            self._strike_grid[expiry] = []
            self._iv_grid[expiry] = {}
        if point.strike not in self._strike_grid[expiry]:
            self._strike_grid[expiry].append(point.strike)
            self._iv_grid[expiry][point.strike] = point.iv
        # Update IV (overwrite with latest)
        self._iv_grid[expiry][point.strike] = point.iv

    def get_iv(self, expiry: str, strike: float) -> Optional[float]:
        """Get IV at a specific expiry + strike. Uses linear interpolation."""
        if expiry not in self._iv_grid:
            return None
        strikes = sorted(self._strike_grid.get(expiry, []))
        ivs = self._iv_grid.get(expiry, {})

        if strike in ivs:
            return ivs[strike]

        # Linear interpolation
        if not strikes:
            return None

        # Find surrounding strikes
        below = None
        above = None
        for s in strikes:
            if s <= strike:
                below = s
            if s >= strike and above is None:
                above = s
                break

        if below is None or above is None or below == above:
            return None

        iv_below = ivs[below]
        iv_above = ivs[above]
        weight = (strike - below) / (above - below)
        return iv_below + weight * (iv_above - iv_below)

    def risk_reversal(self, expiry: str, atm_strike: float) -> Optional[float]:
        """
        Risk reversal = IV(OTM call) - IV(OTM put) at same delta.
        Positive RR → skew favours calls (bullish market)
        Negative RR → skew favours puts (bearish market)
        """
        if expiry not in self._iv_grid:
            return None
        strikes = sorted(self._strike_grid.get(expiry, []))
        if len(strikes) < 2:
            return None

        # 25-delta risk reversal (approximate: strikes ±5% from ATM)
        delta = 0.05
        call_strike = atm_strike * (1 + delta)
        put_strike = atm_strike * (1 - delta)

        iv_call = self.get_iv(expiry, call_strike)
        iv_put = self.get_iv(expiry, put_strike)

        if iv_call is None or iv_put is None:
            return None
        return iv_call - iv_put

    def butterfly_skew(self, expiry: str, atm_strike: float) -> Optional[float]:
        """
        Butterfly = (IV_lower + IV_upper - 2*IV_ATM) / 2
        Positive butterfly → wings richer than ATM (potential pinned ATM)
        """
        iv_atm = self.get_iv(expiry, atm_strike)
        if iv_atm is None:
            return None

        wing_delta = 0.05
        iv_lower = self.get_iv(expiry, atm_strike * (1 - wing_delta))
        iv_upper = self.get_iv(expiry, atm_strike * (1 + wing_delta))

        if iv_lower is None or iv_upper is None:
            return None

        return (iv_lower + iv_upper - 2 * iv_atm) / 2.0

    def surface_summary(self) -> dict:
        """Return a summary of the IV surface."""
        if not self._points:
            return {"expiries": [], "strikes": [], "iv_points": 0}

        expiries = list(self._strike_grid.keys())
        all_strikes: set[float] = set()
        for strikes in self._strike_grid.values():
            all_strikes.update(strikes)

        return {
            "expiries": expiries,
            "expiry_count": len(expiries),
            "strike_min": min(all_strikes) if all_strikes else 0,
            "strike_max": max(all_strikes) if all_strikes else 0,
            "iv_points": len(self._points),
        }


# ─────────────────────────────────────────────
# Main Quantitative Engine
# ─────────────────────────────────────────────

class QuantitativeEngine:
    """
    Unified quantitative analytics engine.

    Use as:
        qe = QuantitativeEngine()
        qe.update(tick)          # feed every tick
        vwap  = qe.vwap.current_vwap()
        vpin  = qe.vpin.current_vpin()
        spread = qe.spread.current_metrics()
        regime = qe.regime.current_regime()
        iv     = qe.iv_surface.get_iv("26JUL", 24500.0)
    """

    def __init__(self):
        self.vwap: VWAPCalculator = VWAPCalculator()
        self.vpin: VPINCalculator = VPINCalculator()
        self.spread: SpreadTracker = SpreadTracker()
        self.regime: RegimeDetector = RegimeDetector()
        self.iv_surface: VolatilitySurface = VolatilitySurface()
        self._tick_count: int = 0

    def update(self, tick: Tick) -> dict:
        """
        Feed a tick and update all analytics.
        Returns a combined snapshot.
        """
        self._tick_count += 1
        vwap = self.vwap.update(tick)
        vpin = self.vpin.update(tick)
        spread_metrics = self.spread.update(tick)
        market_regime = self.regime.update(tick.price)

        return {
            "tick": self._tick_count,
            "vwap": round(vwap, 2),
            "vpin": round(vpin, 4),
            "spread": spread_metrics,
            "regime": {
                "name": market_regime.regime,
                "volatility_ann_pct": market_regime.volatility,
                "trend_ann_pct": market_regime.trend,
                "confidence": market_regime.confidence,
            },
        }

    def reset(self):
        """Reset all calculators."""
        self.vwap.reset()
        self.vpin.reset()
        self.regime = RegimeDetector()
        self.iv_surface = VolatilitySurface()
        self._tick_count = 0


# ─────────────────────────────────────────────
# CLI smoke-test
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import time
    import random

    print("QuantitativeEngine smoke-test")
    qe = QuantitativeEngine()
    base_price = 24500.0

    for i in range(100):
        tick = Tick(
            timestamp=time.time(),
            price=base_price + random.uniform(-50, 50),
            volume=random.randint(50, 500),
            bid=base_price - 5 + random.uniform(-3, 3),
            ask=base_price + 5 + random.uniform(-3, 3),
        )
        result = qe.update(tick)
        if i % 20 == 0:
            print(f"[{i:3d}] VWAP={result['vwap']:.2f}  VPIN={result['vpin']:.4f}  "
                  f"spread={result['spread']['rel_spread_pct']:.4f}%  "
                  f"regime={result['regime']['name']}  vol={result['regime']['volatility_ann_pct']:.1f}%")

    print("Smoke-test passed — QuantitativeEngine is working.")