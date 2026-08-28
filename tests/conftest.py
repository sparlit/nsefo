"""
Shared pytest fixtures for NSEFO test suite.

All fixtures are unit-test only (no broker API, no network).
Use `@pytest.mark.integration` for tests that require live broker connectivity.
"""

import sys
from unittest.mock import MagicMock

import pytest


# ── Broker fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def mock_broker():
    """Minimal mock broker that returns safe-zero fund limits and dict responses."""
    broker = MagicMock()
    broker.get_fund_limits.return_value = {
        "available_cash": 0.0,
        "used_margin": 0.0,
        "total": 0.0,
    }
    broker.get_positions.return_value = []
    broker.get_holdings.return_value = []
    broker.place_order.return_value = {"order_id": "ORDER123", "status": "OPEN"}
    return broker


@pytest.fixture
def mock_broker_with_cash():
    """Mock broker with sufficient cash for margin checks."""
    broker = MagicMock()
    broker.get_fund_limits.return_value = {
        "available_cash": 1_000_000.0,
        "used_margin": 0.0,
        "total": 1_000_000.0,
    }
    broker.get_positions.return_value = []
    broker.get_holdings.return_value = []
    broker.place_order.return_value = {"order_id": "ORDER123", "status": "OPEN"}
    return broker


@pytest.fixture
def mock_broker_with_position():
    """Mock broker carrying one open LONG position."""
    broker = MagicMock()
    broker.get_fund_limits.return_value = {
        "available_cash": 800_000.0,
        "used_margin": 200_000.0,
        "total": 1_000_000.0,
    }
    broker.get_positions.return_value = [
        {
            "symbol": "NIFTY",
            "side": "BUY",
            "qty": 50,
            "entry_price": 24500.0,
            "current_price": 24550.0,
            "unrealized_pnl": 2500.0,
        }
    ]
    broker.get_holdings.return_value = []
    broker.place_order.return_value = {"order_id": "ORDER123", "status": "OPEN"}
    return broker


# ── RiskManager fixtures ─────────────────────────────────────────────────────

@pytest.fixture
def risk_manager_defaults(mock_broker, tmp_path):
    """RiskManager with conservative test defaults and isolated state file."""
    from python_app.core.risk_manager import RiskManager
    import os

    rm = RiskManager(
        capital=1_000_000.0,
        max_risk_per_trade=0.02,
        max_consecutive_losses=3,
        daily_max_loss_pct=0.05,
    )
    # Use isolated state file for tests
    test_state_file = str(tmp_path / "test_cb_defaults.json")
    rm.cb._state_file = test_state_file
    if os.path.exists(test_state_file):
        os.remove(test_state_file)
    rm.cb._save_state()
    
    yield rm
    
    # Cleanup
    if os.path.exists(test_state_file):
        os.remove(test_state_file)


@pytest.fixture
def risk_manager_aggressive(mock_broker_with_cash, tmp_path):
    """RiskManager with aggressive (5%) risk settings for edge-case tests."""
    from python_app.core.risk_manager import RiskManager
    import os

    rm = RiskManager(
        capital=1_000_000.0,
        max_risk_per_trade=0.05,
        max_consecutive_losses=5,
        daily_max_loss_pct=0.10,
    )
    # Use isolated state file for tests
    test_state_file = str(tmp_path / "test_cb_aggressive.json")
    rm.cb._state_file = test_state_file
    if os.path.exists(test_state_file):
        os.remove(test_state_file)
    rm.cb._save_state()
    
    yield rm
    
    # Cleanup
    if os.path.exists(test_state_file):
        os.remove(test_state_file)


# ── CircuitBreakerState fixture ───────────────────────────────────────────────

@pytest.fixture
def fresh_circuit_breaker(tmp_path):
    """A fresh CircuitBreakerState with capital=1_000_000 and isolated state file."""
    from python_app.core.risk_manager import CircuitBreakerState
    import os
    
    # Use a temporary state file for tests to avoid polluting the real state
    test_state_file = str(tmp_path / "test_circuit_breaker_state.json")
    
    cb = CircuitBreakerState(
        capital=1_000_000.0,
        max_consecutive_losses=3,
        daily_max_loss_pct=0.05,
    )
    # Override the state file path for this test instance
    cb._state_file = test_state_file
    
    # Clean up any existing state and start fresh
    if os.path.exists(test_state_file):
        os.remove(test_state_file)
    cb._save_state()
    
    yield cb
    
    # Cleanup after test
    if os.path.exists(test_state_file):
        os.remove(test_state_file)


# ── Coordinator fixtures ─────────────────────────────────────────────────────

@pytest.fixture
def mock_engine():
    """Mock BrainEngine that returns a fixed analysis dict."""
    engine = MagicMock()
    engine.analyze_symbol.return_value = {
        "probability": 0.75,
        "signal": "BUY",
        "brains": {
            "trend": {"signal": "UP", "value": 1.0},
            "rsi": {"value": 28.0},
            "volatility": {"value": 0.015},
            "delta": {"value": 0.52},
        },
        "error": None,
    }
    return engine


@pytest.fixture
def mock_state():
    """Mock AppState singleton for coordinator tests."""
    from python_app.core.state import AppState

    state = AppState()
    state.kanban = {"SCANNING": [], "SIGNAL": [], "ACTIVE": [], "CLOSED": []}
    state.capital = 1_000_000.0
    state.fixed_lots = 1
    return state


@pytest.fixture
def coordinator(risk_manager_defaults, mock_broker):
    """Coordinator with mocked broker and risk_manager."""
    from python_app.core.coordinator import Coordinator

    coord = Coordinator(
        broker=mock_broker,
        risk_manager=risk_manager_defaults,
        reconcile_positions=False,  # Disable reconciliation in tests
    )
    return coord


# ── Sample data fixtures ───────────────────────────────────────────────────────

@pytest.fixture
def sample_market_data():
    """NIFTY 24500 CE at-the-money option data."""
    return {
        "symbol": "NIFTY",
        "strike": 24500.0,
        "option_type": "CE",
        "entry": 24500.0,
        "exit": 24550.0,
        "sl": 24400.0,
        "qty": 50,
        "last_price": 24500.0,
        "curr_vol": 0.015,
        "avg_vol": 0.012,
    }


@pytest.fixture
def sample_ohlcv():
    """20 rows of 1-minute OHLCV data for BrainEngine tests."""
    import numpy as np

    close = 24500.0 + np.cumsum(np.random.randn(20) * 20)
    high = close + np.abs(np.random.randn(20) * 10)
    low = close - np.abs(np.random.randn(20) * 10)
    open_ = low + np.random.rand(20) * (high - low)
    volume = np.random.randint(50000, 200000, size=20)

    return {
        "close": close.tolist(),
        "high": high.tolist(),
        "low": low.tolist(),
        "open": open_.tolist(),
        "volume": volume.tolist(),
    }