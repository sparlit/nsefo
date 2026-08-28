# Operational Roadmap: 10 Critical Phases

Every trade executed by NSEFO Master Pro passes through a strict 10-phase lifecycle. This ensures no order reaches the exchange without passing through risk controls and human oversight.

---

## Phase 1 — System Integrity

**Trigger**: Application startup (`start_master_pro.py → run_application()`)

The `TradingApp` constructor initializes all components and immediately calls `broker.login()`:

```python
if not app.broker or not app.broker.login():
    print("[CRITICAL] Authentication Failed.")
    sys.exit(1)
```

This is a synchronous, blocking call. If Dhan API credentials are invalid, the entire application refuses to start. No partial state — the system fails fast and loud.

---

## Phase 2 — Market Awareness

**Trigger**: WebSocket synchronization (Dhan MarketFeed) or polling cycle

The `run_market_cycle()` method in `python_app/main.py` runs as a daemon thread. Every 1 second it:

1. Fetches LTP for all symbols in `watch_list` (NIFTY, BANKNIFTY, FINNIFTY) via `broker.get_market_data()`
2. Fetches 60 minutes of intraday minute-data via `broker.get_historical_data()` for neural analysis
3. Updates `global_state` with current prices

The symbol→security_id mapping:
```python
symbol_map = {"NIFTY": "13", "BANKNIFTY": "25", "FINNIFTY": "27"}
```

---

## Phase 3 — Neural Scanning

**Trigger**: Each iteration of `run_market_cycle()`

For every symbol in the watch list, the `BrainEngine.analyze_symbol()` method:

1. Converts OHLCV DataFrame to `Vec<f64>` lists
2. Calls Rust extension functions:
   - `nsefo_core.get_rsi_list(close, 14)` → Relative Strength Index
   - `nsefo_core.get_supertrend(high, low, close, 10, 3.0)` → Supertrend + trend direction
   - `nsefo_core.get_volatility_list(close, 20)` → Rolling standard deviation
3. Computes Delta via `opengreeks.black_scholes.delta(flag, S, K, t, r, sigma)`

**Rust performance**: All calculations are vectorized and run in parallel via `rayon` + `ta` crate. The 60-minute dataset for 3 symbols completes in < 1ms.

---

## Phase 4 — Signal Convergence

**Trigger**: After neural analysis completes for all symbols

`calculate_probability([trend_score, rsi_score])` in Rust synthesizes a conviction score:

```
trend_score:  1.0 (bullish), -1.0 (bearish), from Supertrend
rsi_score:   +1.0 (RSI < 30 oversold), -1.0 (RSI > 70 overbought), 0.0 (neutral)
vol_conviction: 1.2 if current_vol > 10-avg, else 0.8

base_score = (trend × 0.5) + (rsi × 0.3)
final_prob = clamp((base_score + 0.8) / 1.6 × vol_conviction, 0.0, 1.0)
```

A signal is emitted to the Kanban board (`global_state.add_signal()`) if `probability > 0.90`.

---

## Phase 5 — Greeks Verification

**Trigger**: Before any order recommendation is generated

The `BrainEngine.analyze_symbol()` computes **Delta** via Black-Scholes:

```python
sigma = (curr_vol / close[-1]) * (252**0.5)   # annualized volatility
d = calculate_delta('c', S=spot, K=spot, t=30/365, r=0.1, sigma=sigma)
```

This validates whether the at-money strike selected by the NLP parser is efficiently priced. The Delta is included in the signal output.

---

## Phase 6 — Risk Management

**Trigger**: When `handle_manual_suggestion()` is called (NLP command or scan signal)

Before any order is dispatched, `RiskManager.assess_trade()` evaluates:

```python
risk_amount = abs(entry - sl) * quantity
risk_percent = (risk_amount / capital) * 100
is_safe = risk_percent <= 1.0  # max_risk_per_trade (default 1%)
```

If `is_safe = False`, the Coordinator rejects the order with recommendation `REDUCE QUANTITY/SIZE`.

---

## Phase 7 — Expert Confirmation

**Trigger**: After analysis, risk check, and before order dispatch

The `auto_confirm_trade()` function in `python_app/core/utils.py` enforces a 10-second human-in-the-loop window with fail-safe authorization:

```python
choice = timed_input_explicit("Confirm trade execution? [YES/Y to confirm]:", timeout=10)
if choice is None:
    return False  # Reject on timeout or stdin unavailable
return choice.upper() in ["YES", "Y"]
```

**SECURITY**: Trade execution requires explicit user confirmation. The function returns `True` ONLY if the user types "YES" or "Y" within the timeout period. Any of the following conditions result in automatic rejection:
- Timeout without input
- stdin unavailable, closed, or redirected
- Empty input or any response other than "YES"/"Y"

This ensures unattended processes or processes with closed stdin cannot accidentally authorize live trades.

---

## Phase 8 — Order Execution

**Trigger**: Explicit user confirmation received

`Coordinator.execute_confirmed_trade()` calls `broker.place_order(proposal)`:

```python
order_id = self.broker.place_order(proposal)
self.active_trades[order_id] = proposal
```

The `proposal` dict includes: `security_id`, `exchange_segment`, `symbol`, `side`, `quantity`, `price`, `sl`, `tag: 'NSEFO_EXPERT'`

For `FenixDhanProvider`, this calls `self.api.market_order()` (market order, no price specification).
For `PaperBroker`, this generates a simulated fill with a UUID order ID.

---

## Phase 9 — Autonomous Tracking

**Trigger**: Every 1 second via `run_market_cycle()` → `Coordinator.track_trades()`

For each active trade in `self.active_trades`:
1. Fetch current LTP for the symbol
2. Pass to `apply_trailing_sl()` for stop-loss adjustment
3. Update `global_state.update_active_trades()` for dashboard refresh

---

## Phase 10 — Dynamic Trailing Stop-Loss

**Trigger**: Each call to `Coordinator.apply_trailing_sl()`

Logic for a BUY position:
```python
if side == 'BUY' and current_price > entry_price + step:
    new_sl = current_price - (entry_price - old_sl)  # lock in profit distance
    if new_sl > old_sl:
        trade['sl'] = new_sl  # trailing SL moves up, never down
```

Logic for a SELL position:
```python
if side == 'SELL' and current_price < entry_price - step:
    new_sl = current_price + (old_sl - entry_price)
    if new_sl < old_sl:
        trade['sl'] = new_sl  # trailing SL moves down, never up
```

The `step` default is `1.0` (₹1 for equity options), making the system responsive to intraday volatility while avoiding noise from minor fluctuations.