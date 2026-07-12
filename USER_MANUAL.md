# NSEFO Master Pro: User Manual

## Activating the System

### Single-Command Launch

**Linux / macOS:**
```bash
./nsefo
```

**Windows:**
```cmd
nsefo
```
or double-click `nsefo.bat` in the project directory.

The startup script (`run.py`) will:
1. Verify Python version
2. Load configuration from `config.json`
3. Test Dhan API connectivity — if it fails, the application will not start
4. Start the web dashboard at `http://localhost:9099`
5. Launch the trading engine (daemon thread)
6. Attempt to launch the PySide6 desktop terminal (if PySide6 is installed)

**Direct engine start (without connectivity check):**
```bash
python start_master_pro.py
```

**NLP command-only mode (no daemon, no dashboard):**
```bash
python start_master_pro.py "Buy Nifty 24500 ce"
```

---

## Natural Language Execution (NLP)

The system accepts professional trading commands in plain English. Use the terminal input or pass as CLI arguments.

### Supported Command Patterns

| Pattern | Example |
|---------|---------|
| `BUY SYMBOL STRIKE CE` | `Buy Nifty 24500 ce` |
| `SELL SYMBOL STRIKE PE` | `Sell Banknifty 48000 pe` |
| `LONG SYMBOL STRIKE CALL` | `Go long Finnifty 21000 call` |
| `SHORT SYMBOL STRIKE PUT` | `Short Nifty 24400 put` |
| `BUY/SELL SYMBOL` (market) | `Buy Nifty` — uses current ATM strike |

**Symbol aliases**: `NIFTY`, `NIFTY` / `BANK NIFTY`, `BN`, `BANKNIFTY` / `FINNIFTY`, `FN`, `FINNIFTY`
**Option types**: `CE`, `CALL`, `CALLS` → Call / `PE`, `PUT`, `PUTS` → Put

### NLP → Order Flow

```
NLP Command
    ↓
CommandParser.parse_command(text)   [python_app/nlp/parser.py]
    ↓  {symbol, strike, option_type, action}
TradingApp.handle_manual_suggestion(command)
    ↓
BrainEngine.analyze_symbol(df)      [Rust: get_rsi, get_supertrend, get_volatility]
    ↓  {probability, signal, brains: {trend, rsi, volatility, delta}}
RiskManager.assess_trade()          [capital risk check]
    ↓  {risk_amount, risk_percent, is_safe, recommendation}
Recommendation: EXECUTE or REJECT
    ↓
auto_confirm_trade() → 10s window → Broker.place_order()
```

### Example Full Session

```
$ python start_master_pro.py "Buy Nifty 24500 ce"

============================================================
MASTER PRO EXPERT ANALYSIS
============================================================
{
  "symbol": "NIFTY",
  "last_price": 248.50,
  "probability": 0.847,
  "fixed_lots": 1,
  "quantity": 50,
  "brains": {
    "trend": "UP",
    "rsi": 42.3,
    "volatility": "NORMAL",
    "delta": 0.512
  },
  "risk": {
    "risk_amount": 12.43,
    "risk_percent": 0.0012,
    "is_safe": true,
    "recommendation": "PROCEED"
  },
  "decision": "EXECUTE"
}

--- TRADE CONFIRMATION REQUIRED ---
Details: {'action': 'BUY', 'symbol': 'NIFTY', ...}
Confirm trade execution? (Default: YES) [Timeout 10s]:
```

---

## Dashboard Monitoring

### Web Dashboard (http://localhost:9099)

The web dashboard has two tabs:

**Terminal Tab**: Four Kanban columns auto-populated via WebSocket:
- **SCANNING**: Symbols currently monitored by the neural engine
- **SIGNAL**: High-conviction setups (probability > 0.90) awaiting entry
- **ACTIVE**: Open positions with current P&L and trailing stop-loss status
- **CLOSED**: Completed trades for the session

**Configuration Tab**: Live editing of `config.json` fields:
- Trading mode (paper/live)
- Dhan Client ID
- API Access Token
- Initial capital
- Fixed lot size

Changes take effect on page reload.

### Desktop Terminal (PySide6)

The Qt desktop application (`dashboards/desktop/main.py`) provides a native UI with:
- Real-time Kanban board with color-coded signal cards (green = BUY, red = SELL)
- System configuration tab with masked token input
- 1-second auto-refresh via `QTimer`

Launch from the web terminal or when `start_master_pro.py` detects PySide6 is available.

---

## Risk Controls

### Configurable Parameters

| Parameter | Location | Effect |
|-----------|----------|--------|
| `risk.capital` | `config.json` or Config tab | Denominator for risk % calculations |
| `risk.fixed_lots` | `config.json` or Config tab | Strictly enforced quantity divisor |
| `risk.max_risk_per_trade_percent` | `config.json` only | Max loss as % of capital per trade (default 1%) |

### Risk Calculation

```
risk_percent = |entry_price − stop_loss| × quantity / capital
PROCEED if risk_percent ≤ 1.0 (default), else REDUCE QUANTITY/SIZE
```

Example: Capital = ₹1,000,000. Entry = ₹250, SL = ₹245, Qty = 50 (1 lot).
```
risk = |250 − 245| × 50 = ₹250
risk_percent = 250 / 1,000,000 × 100 = 0.025%  ✓ SAFE
```

### Mode Switching

Edit `config.json` or use the web dashboard Configuration tab:

```json
"mode": "paper"    ← Simulation, simulated fills, real or simulated prices
"mode": "live"     ← Real execution via Dhan API
```

---

## Mode: Paper vs Live

### Paper Mode
- Order fills are simulated with virtual balance
- Market data: if `data_provider` (Fenix) is available, real prices are used; otherwise `random.uniform` fallback
- Useful for validating strategy before going live

### Live Mode
- Real orders sent to Dhan exchange
- Requires valid API credentials and TOTP secret
- `[CRITICAL]` shown in terminal header when running in live mode

---

## System Logs

All system events are logged to the terminal output and stored in `global_state.system_logs` (last 100 entries, rolling). Use the web dashboard's browser console or the desktop terminal for real-time log streaming.

Log prefix format: `[HH:MM:SS] MESSAGE`

Key log events:
- `[MASTER-PRO]` — startup/initialization
- `[ENGINE]` — market cycle, signal generation
- `[FenixDhanProvider]` — broker API calls
- `[BrainEngine]` — neural analysis results
- `[Coordinator]` — trade tracking, trailing SL updates
- `[RiskManager]` — risk assessment results