"""
Thread-safe application state for NSEFO Master Pro.

All reads and writes go through an RLock, so a single trading thread
holding the lock can call any number of state methods without deadlocking
(reentrant = RLock).

Usage:
    from python_app.core.state import global_state
    with global_state._lock:
        summary = global_state.summary
        # ... reads and writes ...
"""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, List


class AppState:
    """
    Thread-safe application state.

    All public methods acquire self._lock before reading or writing any
    shared state. The lock is an RLock (reentrant) so nested calls from
    within the same thread are safe.

    Attributes:
        summary:     Dict with capital, total_pnl, active_trades_count, mode, last_update
        kanban:      Dict with SCANNING / SIGNAL / ACTIVE / CLOSED lists
        pnl_history: Rolling list of realized P&L values
        system_logs: Rolling list of timestamped log messages (max 100)
    """

    def __init__(self):
        self._lock = threading.RLock()
        self.summary: Dict[str, Any] = {
            "capital": 0.0,
            "total_pnl": 0.0,
            "active_trades_count": 0,
            "mode": "paper",
            "last_update": time.time(),
        }
        self.kanban: Dict[str, List[Any]] = {
            "SCANNING": [],
            "SIGNAL": [],
            "ACTIVE": [],
            "CLOSED": [],
        }
        self.pnl_history: List[float] = []
        self.system_logs: List[str] = []
        self.active_symbols: List[str] = []  # Symbols with at least one active trade

    # ── summary ───────────────────────────────────────────────────────────────

    def update_summary(self, **kwargs) -> None:
        """Update one or more summary fields atomically."""
        with self._lock:
            self.summary.update(kwargs)
            self.summary["last_update"] = time.time()

    # ── kanban ───────────────────────────────────────────────────────────────

    def add_signal(self, signal: Dict[str, Any]) -> None:
        """Append a signal to the SIGNAL column."""
        with self._lock:
            self.kanban["SIGNAL"].append(signal)

    def set_scanning(self, symbols: List[str]) -> None:
        """Replace the SCANNING watch list atomically."""
        with self._lock:
            self.kanban["SCANNING"] = list(symbols)

    def update_active_trades(self, trades: List[Dict[str, Any]]) -> None:
        """
        Replace the ACTIVE trades list and update the summary count.
        Call this from the market cycle loop.
        """
        with self._lock:
            self.kanban["ACTIVE"] = list(trades)
            self.summary["active_trades_count"] = len(trades)
            self.summary["last_update"] = time.time()

    def move_to_closed(self, trade: Dict[str, Any]) -> None:
        """Atomically move a trade from ACTIVE to CLOSED."""
        with self._lock:
            self.kanban["ACTIVE"] = [t for t in self.kanban["ACTIVE"] if t.get("order_id") != trade.get("order_id")]
            self.kanban["CLOSED"].append(trade)

    # ── logs ─────────────────────────────────────────────────────────────────

    def add_log(self, message: str) -> None:
        """
        Append a timestamped log message. Keeps last 100 entries atomically.
        """
        with self._lock:
            entry = f"[{time.strftime('%H:%M:%S')}] {message}"
            self.system_logs.append(entry)
            # Trim to 100 entries — pop from the left atomically within the lock
            if len(self.system_logs) > 100:
                del self.system_logs[: len(self.system_logs) - 100]

    # ── P&L ──────────────────────────────────────────────────────────────────

    def add_pnl(self, value: float) -> None:
        """Record a P&L update."""
        with self._lock:
            self.pnl_history.append(value)
            self.summary["total_pnl"] = sum(self.pnl_history)

    # ── bulk reads (return copies for consistency) ─────────────────────────────

    def get_snapshot(self) -> Dict[str, Any]:
        """
        Return a deep-ish snapshot of the entire state (copies the top-level
        containers; callers who need deep copies must copy further).
        """
        with self._lock:
            import copy
            return {
                "summary": dict(self.summary),
                "kanban": {k: list(v) for k, v in self.kanban.items()},
                "pnl_history": list(self.pnl_history),
                "system_logs": list(self.system_logs),
            }


# Global singleton — import this, not AppState directly
global_state = AppState()