# Security Fix: Process Restart State Persistence

## Issue Summary

**Severity:** Medium  
**Finding:** Process restart clears trading risk state and loses position monitoring

### Original Vulnerability

Prior to this fix, the trading system had two critical fail-open weaknesses:

1. **Circuit Breaker State Loss**: The `CircuitBreakerState` stored consecutive losses, session P&L, and the tripped flag only in memory. On restart, `Coordinator.__init__` unconditionally called `reset_day()`, clearing all risk limits.

2. **Position Monitoring Loss**: `AppState` kept active positions only in memory. The startup path did not query `broker.get_positions()` or reconcile open orders, leaving existing broker positions outside the local stop-loss and target monitoring loop.

### Impact

After a crash or restart:
- The process could place new trades without prior consecutive-loss or daily-loss state
- Broker positions opened before the restart were absent from local monitoring
- Manual one-shot entry commands constructed a fresh application for each invocation, making process-local circuit-breaker state ineffective

## Fix Implementation

### 1. Persistent Circuit Breaker State

**File:** `python_app/core/risk_manager.py`

**Changes:**
- Added `session_date` field to track the trading day
- Added `_state_file` field pointing to `circuit_breaker_state.json`
- Implemented `__post_init__()` to automatically load state on initialization
- Implemented `_load_state()` to restore state from disk if from the same trading day
- Implemented `_save_state()` to persist state after each trade using atomic writes
- Modified `record_trade()` to call `_save_state()` after updating counters
- Modified `is_tripped()` to persist when breaker trips
- Modified `reset_day()` to only reset when a new trading day is detected

**Behavior:**
- State is saved to `circuit_breaker_state.json` after each trade
- On startup, state is restored if the `session_date` matches today's date
- If state is from a previous day, automatic reset occurs for the new trading day
- Atomic file writes (write to `.tmp`, then rename) prevent corruption

### 2. Position Reconciliation on Startup

**File:** `python_app/core/coordinator.py`

**Changes:**
- Removed unconditional `reset_day()` call from `Coordinator.__init__`
- Added `reconcile_positions` parameter (default: `True`)
- Implemented `_reconcile_broker_positions()` method to query broker and restore monitoring

**Behavior:**
- On startup, queries `broker.get_positions()` for open positions
- Reconciles broker positions with local `global_state.kanban["ACTIVE"]`
- Adds missing positions to monitoring with conservative default stops (2% for BUY, 2% for SELL)
- Skips positions already being monitored (by order_id or symbol+side)
- Logs warnings for reconciled positions, prompting manual verification of stops
- Gracefully handles reconciliation failures without crashing

### 3. Test Infrastructure Updates

**File:** `tests/conftest.py`

**Changes:**
- Updated `fresh_circuit_breaker` fixture to use isolated state files via `tmp_path`
- Updated `risk_manager_defaults` and `risk_manager_aggressive` fixtures to use isolated state files
- Updated `coordinator` fixture to disable reconciliation during tests (`reconcile_positions=False`)
- Added cleanup logic to remove test state files after each test

**File:** `tests/test_restart_security.py` (new)

**Test Coverage:**
- Circuit breaker state persists within the same trading day
- Circuit breaker state resets automatically on a new trading day
- Tripped circuit breaker state persists across restarts
- Coordinator reconciles broker positions on startup
- Coordinator skips duplicate positions already in ACTIVE
- Coordinator handles reconciliation failures gracefully
- Coordinator respects `reconcile_positions=False` flag

## Security Properties

### Before Fix
- ❌ Circuit breaker state cleared on every restart
- ❌ Existing broker positions not monitored after restart
- ❌ Loss limits could be bypassed by restarting the process
- ❌ Positions could hit stop-loss without local monitoring

### After Fix
- ✅ Circuit breaker state persists across restarts within the same trading day
- ✅ Automatic reset only on new trading day (date-based)
- ✅ Broker positions reconciled on startup
- ✅ Existing positions added to monitoring with default stops
- ✅ Loss limits enforced across restarts
- ✅ Atomic file writes prevent state corruption
- ✅ Graceful degradation on reconciliation failure

## Operational Notes

### State File Location
- Circuit breaker state: `circuit_breaker_state.json` (project root)
- Format: JSON with fields `consecutive_losses`, `session_pnl`, `session_trades`, `session_date`, `_tripped`

### Manual Intervention Required
When positions are reconciled on startup:
1. Check the logs for "Reconciled position from broker" warnings
2. Verify the default stop-loss levels (2% conservative stops)
3. Manually adjust stops if needed via the dashboard or CLI

### Disabling Reconciliation
For testing or special scenarios, reconciliation can be disabled:
```python
coordinator = Coordinator(
    broker=broker,
    risk_manager=risk_manager,
    reconcile_positions=False,
)
```

### State File Cleanup
The circuit breaker state file is automatically managed:
- Created on first run
- Updated after each trade
- Reset automatically on new trading day
- Can be manually deleted to force a fresh start (use with caution)

## Testing

Run the security test suite:
```bash
pytest tests/test_restart_security.py -v
```

Expected output:
```
tests/test_restart_security.py::test_circuit_breaker_persists_within_same_day PASSED
tests/test_restart_security.py::test_circuit_breaker_resets_on_new_day PASSED
tests/test_restart_security.py::test_circuit_breaker_trips_and_persists PASSED
tests/test_restart_security.py::test_coordinator_reconciles_broker_positions PASSED
tests/test_restart_security.py::test_coordinator_skips_duplicate_positions PASSED
tests/test_restart_security.py::test_coordinator_handles_reconciliation_failure PASSED
tests/test_restart_security.py::test_coordinator_no_reconciliation_when_disabled PASSED
```

## Backward Compatibility

- Existing code continues to work without changes
- `reconcile_positions` parameter defaults to `True` (secure by default)
- Tests updated to use isolated state files (no pollution)
- State file format is forward-compatible (additional fields can be added)

## Future Enhancements

Potential improvements for future consideration:
1. Persist original stop-loss and target levels for reconciled positions
2. Add position reconciliation to the web dashboard
3. Implement state file rotation/archival for audit trails
4. Add metrics for reconciliation success/failure rates
5. Support manual position import from CSV/JSON
