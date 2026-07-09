from dataclasses import dataclass, field
from typing import List, Dict, Any
import time

@dataclass
class AppState:
    summary: Dict[str, Any] = field(default_factory=lambda: {
        "capital": 0.0,
        "total_pnl": 0.0,
        "active_trades_count": 0,
        "mode": "paper",
        "last_update": time.time()
    })
    kanban: Dict[str, List[Any]] = field(default_factory=lambda: {
        "SCANNING": [],
        "SIGNAL": [],
        "ACTIVE": [],
        "CLOSED": []
    })
    pnl_history: List[float] = field(default_factory=list)
    system_logs: List[str] = field(default_factory=list)

    def update_summary(self, **kwargs):
        self.summary.update(kwargs)
        self.summary["last_update"] = time.time()

    def add_signal(self, signal: Dict[str, Any]):
        self.kanban["SIGNAL"].append(signal)

    def set_scanning(self, symbols: List[str]):
        self.kanban["SCANNING"] = symbols

    def update_active_trades(self, trades: List[Dict[str, Any]]):
        self.kanban["ACTIVE"] = trades
        self.summary["active_trades_count"] = len(trades)

    def add_log(self, message: str):
        self.system_logs.append(f"[{time.strftime('%H:%M:%S')}] {message}")
        if len(self.system_logs) > 100:
            self.system_logs.pop(0)

# Global singleton for state management
global_state = AppState()
