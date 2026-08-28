import json
import logging
import os
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Dict, Any, Optional, List

if False:
    from python_app.broker.base import Broker

logger = logging.getLogger(__name__)


@dataclass
class CircuitBreakerState:
    """
    Circuit breaker state with persistent storage across restarts.
    
    State is saved to circuit_breaker_state.json after each trade.
    On initialization, state is restored if it's from the same trading day.
    Automatic reset occurs only when a new trading day is detected.
    """
    consecutive_losses: int = 0
    last_trade_result: Optional[str] = None   # "win" | "loss" | None
    session_pnl: float = 0.0
    session_trades: int = 0
    session_start_time: float = field(default_factory=time.time)
    session_date: str = field(default_factory=lambda: date.today().isoformat())
    # Config (set via RiskManager.__init__)
    max_consecutive_losses: int = 3
    daily_max_loss_pct: float = 0.05          # 5% of capital
    capital: float = 1_000_000.0
    _tripped: bool = False
    _state_file: str = field(default="circuit_breaker_state.json", init=False, repr=False)

    def __post_init__(self):
        """Load persisted state if available and from the same trading day."""
        self._load_state()

    def _load_state(self) -> None:
        """
        Load circuit breaker state from disk if it exists and is from today.
        If state is from a previous day, automatically reset for new session.
        """
        if not os.path.exists(self._state_file):
            logger.info("No persisted circuit breaker state found - starting fresh")
            self._save_state()
            return
        
        try:
            with open(self._state_file, 'r') as f:
                data = json.load(f)
            
            saved_date = data.get('session_date', '')
            today = date.today().isoformat()
            
            if saved_date != today:
                logger.info(
                    f"Circuit breaker state is from {saved_date}, today is {today}. "
                    "Resetting for new trading day."
                )
                self.reset_day()
                return
            
            # Restore state from same trading day
            self.consecutive_losses = data.get('consecutive_losses', 0)
            self.last_trade_result = data.get('last_trade_result')
            self.session_pnl = data.get('session_pnl', 0.0)
            self.session_trades = data.get('session_trades', 0)
            self.session_start_time = data.get('session_start_time', time.time())
            self.session_date = saved_date
            self._tripped = data.get('_tripped', False)
            
            logger.info(
                f"Restored circuit breaker state from {saved_date}: "
                f"{self.consecutive_losses} consecutive losses, "
                f"session P&L: {self.session_pnl:.2f}, "
                f"trades: {self.session_trades}, "
                f"tripped: {self._tripped}"
            )
            
        except Exception as e:
            logger.error(f"Failed to load circuit breaker state: {e}. Starting fresh.")
            self._save_state()

    def _save_state(self) -> None:
        """Persist current circuit breaker state to disk."""
        try:
            state_data = {
                'consecutive_losses': self.consecutive_losses,
                'last_trade_result': self.last_trade_result,
                'session_pnl': self.session_pnl,
                'session_trades': self.session_trades,
                'session_start_time': self.session_start_time,
                'session_date': self.session_date,
                '_tripped': self._tripped,
                'saved_at': datetime.now().isoformat(),
            }
            
            # Atomic write: write to temp file, then rename
            temp_file = f"{self._state_file}.tmp"
            with open(temp_file, 'w') as f:
                json.dump(state_data, f, indent=2)
            os.replace(temp_file, self._state_file)
            
            logger.debug(f"Circuit breaker state saved: {state_data}")
            
        except Exception as e:
            logger.error(f"Failed to save circuit breaker state: {e}")

    def record_trade(self, pnl: float) -> None:
        """Update state after a trade closes and persist to disk."""
        self.session_pnl += pnl
        self.session_trades += 1
        if pnl < 0:
            self.consecutive_losses += 1
            self.last_trade_result = "loss"
        else:
            self.consecutive_losses = 0
            self.last_trade_result = "win"
        
        # Persist state after each trade
        self._save_state()

    @property
    def daily_loss_pct(self) -> float:
        if self.capital == 0:
            return 0.0
        return self.session_pnl / self.capital

    @property
    def trade_count(self) -> int:
        """Alias for session_trades for backward compatibility."""
        return self.session_trades

    def is_tripped(self) -> bool:
        if self._tripped:
            return True
        if self.consecutive_losses >= self.max_consecutive_losses:
            self._tripped = True
            self._save_state()
            return True
        if self.daily_loss_pct <= -self.daily_max_loss_pct:
            self._tripped = True
            self._save_state()
            return True
        return False

    def reset_day(self) -> None:
        """Reset state for a new trading session and persist."""
        self.consecutive_losses = 0
        self.session_pnl = 0.0
        self.session_trades = 0
        self.session_start_time = time.time()
        self.session_date = date.today().isoformat()
        self._tripped = False
        self.last_trade_result = None
        self._save_state()
        logger.info("Circuit breaker state reset for new trading day")


class RiskManager:
    def __init__(
        self,
        capital: float,
        max_risk_per_trade: float = 0.01,
        max_consecutive_losses: int = 3,
        daily_max_loss_pct: float = 0.05,
    ):
        self.capital = capital
        self.max_risk_per_trade = max_risk_per_trade
        self.max_consecutive_losses = max_consecutive_losses
        self.daily_max_loss_pct = daily_max_loss_pct
        self.logger = logging.getLogger("RiskManager")
        self.cb = CircuitBreakerState(
            max_consecutive_losses=max_consecutive_losses,
            daily_max_loss_pct=daily_max_loss_pct,
            capital=capital,
        )

    def assess_trade(self, entry: float, sl: float, quantity: int) -> Dict[str, Any]:
        """
        Expert risk assessment for the proposed trade.
        Also checks circuit breaker.
        """
        # ── Circuit breaker gate ──────────────────────────────────────────
        if self.cb.is_tripped():
            reason = (
                f"CIRCUIT BREAKER TRIPPED: {self.cb.consecutive_losses} consecutive losses"
                if self.cb.consecutive_losses >= self.max_consecutive_losses
                else f"CIRCUIT BREAKER TRIPPED: daily loss {self.cb.daily_loss_pct*100:.1f}% exceeds {self.daily_max_loss_pct*100:.1f}% limit"
            )
            return {
                "risk_amount": 0,
                "risk_percent": 0,
                "is_safe": False,
                "recommendation": reason,
                "circuit_broken": True,
            }

        # ── Stop-loss plausibility gate ──────────────────────────────────
        # Reject if stop-loss is > 50% away from entry — it would need a >50%
        # adverse move to trigger, indicating either bad entry or mis-set SL.
        entry_d = Decimal(str(entry))
        sl_d = Decimal(str(sl))
        sl_distance_pct = float(abs(entry_d - sl_d) / entry_d) if entry_d > 0 else 0
        if sl_distance_pct > 0.50:
            return {
                "risk_amount": 0,
                "risk_percent": 0,
                "is_safe": False,
                "recommendation": f"STOP-LOSS IMPLAUSIBLE: {sl_distance_pct*100:.0f}% distance from entry (max 50%)",
                "circuit_broken": False,
                "sl_distance_pct": round(sl_distance_pct, 4),
            }

        risk_amount_d = abs(entry_d - sl_d) * Decimal(str(quantity))
        capital_d = Decimal(str(self.capital))
        risk_percent_d = risk_amount_d / capital_d * 100
        max_risk_pct_d = Decimal(str(self.max_risk_per_trade)) * 100
        is_safe = risk_percent_d <= max_risk_pct_d

        return {
            "risk_amount": float(risk_amount_d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            "risk_percent": float(risk_percent_d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            "is_safe": is_safe,
            "recommendation": "PROCEED" if is_safe else "REDUCE QUANTITY/SIZE",
            "circuit_broken": False,
            "sl_distance_pct": round(sl_distance_pct, 4),
        }

    def check_margin_requirement(
        self,
        broker: "Broker",
        side: str,
        price: float,
        quantity: int,
        option_type: str = "CE",
    ) -> Dict[str, Any]:
        """
        Verify the broker has sufficient margin to cover a trade.

        NSE F&O margin rules (conservative estimates):
          BUY  (long):  Required = price × qty  (full premium debited upfront)
          SELL (short): Required = span_margin + exposure_margin
                        Span ≈ 1.5–2× option premium (exchange mandate)
                        Exposure ≈ 0.5× option premium
                        Conservative estimate: 2.5 × price × qty

        Args:
            broker: Broker instance with get_fund_limits() method
            side: 'BUY' or 'SELL'
            price: option premium per unit
            quantity: total units (qty × lot_size)
            option_type: 'CE' or 'PE' (affects conservative estimate only)

        Returns:
            dict with keys: sufficient (bool), available_cash (float),
            required_margin (float), shortfall (float), recommendation (str)
        """
        fund_limits = {"available_cash": 0.0, "used_margin": 0.0, "total": 0.0}
        try:
            fund_limits = broker.get_fund_limits()
        except Exception as e:
            self.logger.warning(f"Could not fetch broker fund limits: {e}")

        available_cash = fund_limits.get("available_cash", 0.0)

        if side.upper() == "BUY":
            required_margin = price * quantity
        else:
            required_margin = price * quantity * 2.5

        shortfall = max(0.0, required_margin - available_cash)
        sufficient = available_cash >= required_margin

        self.logger.info(
            f"Margin check: {'PASS' if sufficient else 'FAIL'} | "
            f"avail={available_cash:.2f} | required={required_margin:.2f} | "
            f"side={side} premium={price} qty={quantity}"
        )

        return {
            "sufficient": sufficient,
            "available_cash": round(available_cash, 2),
            "required_margin": round(required_margin, 2),
            "shortfall": round(shortfall, 2),
            "recommendation": "PROCEED" if sufficient else f"INCREASE MARGIN BY {shortfall:.2f}",
        }
