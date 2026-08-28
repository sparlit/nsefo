# Migration Guide: Restart State Persistence

## Overview

This guide helps operators migrate to the new restart-safe trading system that persists circuit breaker state and reconciles broker positions on startup.

## What Changed

### Before (Vulnerable)
- Circuit breaker state cleared on every restart
- Existing broker positions not monitored after restart
- Loss limits could be bypassed by restarting

### After (Secure)
- Circuit breaker state persists across restarts (same trading day)
- Broker positions automatically reconciled on startup
- Loss limits enforced across restarts

## Migration Steps

### 1. Update Dependencies (if needed)

No new dependencies required. The fix uses only Python standard library features.

### 2. First Startup After Update

On the first startup after applying this fix:

1. **Circuit Breaker State**
   - A new file `circuit_breaker_state.json` will be created in the project root
   - Initial state will be fresh (no losses, no trips)
   - This is expected and safe

2. **Position Reconciliation**
   - If you have open positions at your broker, they will be detected
   - You'll see log messages like:
     ```
     WARNING: Reconciled position from broker: BUY 50 NIFTY24500CE @ 150.00 
     (order_id: BROKER_ORDER_123). Default stops applied - verify manually!
     ```
   - **Action Required:** Verify and adjust stop-loss levels for reconciled positions

### 3. Verify Circuit Breaker State

Check the circuit breaker state file:
```bash
cat circuit_breaker_state.json
```

Expected format:
```json
{
  "consecutive_losses": 0,
  "last_trade_result": null,
  "session_pnl": 0.0,
  "session_trades": 0,
  "session_start_time": 1234567890.123,
  "session_date": "2024-01-15",
  "_tripped": false,
  "saved_at": "2024-01-15T09:15:30.123456"
}
```

### 4. Test Restart Behavior

To verify the fix is working:

1. **Start the trading system**
   ```bash
   python run.py
   ```

2. **Place a test trade** (or wait for an automated trade)

3. **Check the state file** - it should show the trade:
   ```bash
   cat circuit_breaker_state.json
   # Should show session_trades: 1, updated session_pnl
   ```

4. **Restart the system**
   ```bash
   # Stop with Ctrl+C, then restart
   python run.py
   ```

5. **Verify state persisted**
   - Check logs for "Restored circuit breaker state" message
   - State should show the same trade count and P&L
   - Any open broker positions should be reconciled

### 5. Daily Reset Verification

The circuit breaker automatically resets on a new trading day:

1. **End of day**: Stop the system normally
2. **Next day**: Start the system
3. **Check logs**: Should see "Resetting for new trading day"
4. **Verify state**: `session_date` should be today, counters reset to 0

## Operational Procedures

### Normal Startup

```bash
python run.py
```

Expected log output:
```
INFO: Restored circuit breaker state from 2024-01-15: 2 consecutive losses, session P&L: -8000.00, trades: 5, tripped: False
INFO: Reconciling broker positions with local state...
INFO: Position reconciliation complete: 0 position(s) added to monitoring
```

### Startup with Open Positions

If you have open positions at the broker:

```
INFO: Restored circuit breaker state from 2024-01-15: 1 consecutive losses, session P&L: -3000.00, trades: 3, tripped: False
INFO: Reconciling broker positions with local state...
WARNING: Reconciled position from broker: BUY 50 NIFTY24500CE @ 150.00 (order_id: BROKER_ORDER_123). Default stops applied - verify manually!
INFO: Position reconciliation complete: 1 position(s) added to monitoring
```

**Action Required:**
1. Open the dashboard or CLI
2. Verify the reconciled position details
3. Adjust stop-loss and target if needed (default is 2% conservative stop)

### Force Fresh Start

If you need to clear circuit breaker state (use with caution):

```bash
# Stop the system
# Delete the state file
rm circuit_breaker_state.json
# Restart
python run.py
```

This will start with a fresh circuit breaker state (no losses, no trips).

**Warning:** Only do this if you understand the implications. The circuit breaker is a safety mechanism.

### Monitoring State

Check current circuit breaker state at any time:
```bash
cat circuit_breaker_state.json | python -m json.tool
```

Or via the dashboard (if implemented):
- Navigate to Risk Management tab
- View Circuit Breaker Status section

## Troubleshooting

### Issue: State file not created

**Symptom:** No `circuit_breaker_state.json` file after startup

**Cause:** File system permissions or disk space

**Solution:**
1. Check disk space: `df -h`
2. Check write permissions: `ls -la .`
3. Check logs for "Failed to save circuit breaker state" errors

### Issue: State not persisting

**Symptom:** State resets on every restart even within the same day

**Cause:** State file being deleted or overwritten

**Solution:**
1. Check if any cleanup scripts are deleting `*.json` files
2. Verify the file exists: `ls -la circuit_breaker_state.json`
3. Check file modification time: `stat circuit_breaker_state.json`

### Issue: Reconciliation fails

**Symptom:** "Failed to reconcile broker positions" in logs

**Cause:** Broker API error or network issue

**Solution:**
1. Check broker API connectivity
2. Verify broker credentials are valid
3. Check broker API rate limits
4. System will continue without reconciliation (positions won't be monitored)
5. Manually verify open positions at broker

### Issue: Duplicate positions after restart

**Symptom:** Same position appears twice in ACTIVE

**Cause:** Position reconciliation logic issue (should not happen)

**Solution:**
1. Stop the system immediately
2. Check `global_state.kanban["ACTIVE"]` in logs
3. Report the issue with logs
4. Manually close duplicate positions at broker if needed

## Rollback Procedure

If you need to rollback to the previous version:

1. **Stop the system**
   ```bash
   # Ctrl+C or kill the process
   ```

2. **Backup the state file** (for investigation)
   ```bash
   cp circuit_breaker_state.json circuit_breaker_state.json.backup
   ```

3. **Checkout previous version**
   ```bash
   git checkout <previous-commit>
   ```

4. **Restart**
   ```bash
   python run.py
   ```

**Note:** After rollback, circuit breaker state will be lost on restart (original vulnerability returns).

## Best Practices

1. **Monitor Logs**: Always check logs after restart for reconciliation warnings
2. **Verify Stops**: Manually verify stop-loss levels for reconciled positions
3. **Backup State**: Periodically backup `circuit_breaker_state.json` for audit trails
4. **Test Restarts**: Test restart behavior in paper trading mode first
5. **Document Overrides**: If you manually clear state, document why and when

## Support

If you encounter issues:
1. Check logs in `logs/` directory
2. Verify state file format with `python -m json.tool circuit_breaker_state.json`
3. Run test suite: `pytest tests/test_restart_security.py -v`
4. Report issues with full logs and state file contents
