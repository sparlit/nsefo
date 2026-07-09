# 📖 NSEFO Master Pro: User Manual

## ⚡ Activating the System
Once installed, launch the entire suite (Engine + Dashboards) with a single command:

- **Linux**: `./nsefo`
- **Windows**: `nsefo`

---

## 🗣️ Natural Language Execution (NLP)
The Master Pro engine understands professional trading terminology. Use the input box in the terminal or provide as a CLI argument:

### Examples:
- **Call Buying**: *"Buy Nifty 24500 calls"*
- **Put Buying**: *"Go long Banknifty 48000 pe"*
- **Shorting**: *"Short Finnifty 21000 puts"*
- **Market Orders**: *"Sell Nifty"*

### The Analysis Flow:
1. **Parsing**: The NLP brain extracts the symbol, strike, and side.
2. **Greeks**: `OpenGreeks` calculates the Delta of the selected strike.
3. **Rust Brain**: The core checks Trend/Momentum alignment.
4. **Recommendation**: The system provides an **EXECUTE** or **REJECT** signal.
5. **Confirmation**: A 10-second window appears for final oversight.

---

## 📊 Dashboard Monitoring
### 1. Kanban Terminal
- **Scanning**: Symbols currently being monitored by the Rust core.
- **Signals**: High-conviction setups currently in the "Confirmation" window.
- **Active**: Live positions being managed by the Independent Coordinator.
- **Closed**: Completed trades for the current session.

### 2. Real-Time Tracking
The **Independent Coordinator Brain** autonomously manages:
- **Trailing Stop-Loss**: Adjusts SL in favor of the trade based on volatility.
- **P&L Updates**: Real-time per-trade and cumulative profit tracking.

---

## 🛡️ Risk Controls
Modify these in the **Configuration** tab without restarting the engine:
- **Operational Capital**: Affects the risk % display.
- **Fixed Lot Size**: Strictly enforces the number of lots per order.
