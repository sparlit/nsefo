# NSE F&O Master Pro Expert Trading System

A professional-grade, high-performance trading application for NSE Options and F&O, built with a hybrid **Python + Rust** architecture. Designed for expert traders who require ultra-fast technical analysis, multi-brain coordination, and a sophisticated Kanban-style operational dashboard.

---

## 🚀 Detailed System Information

The **NSE F&O Master Pro Expert** is not just a trading tool; it's a multi-component neural coordination engine.

### Core Architecture:
- **Rust Logic Engine (The Brains)**: High-speed technical analysis core implemented in Rust for sub-millisecond calculation latency. It handles Supertrend, RSI, ATR, and Standard Deviation.
- **Multi-Brain Synthesis**: The system uses three specialized brains:
    1. **Trend Brain**: Identifies market directionality.
    2. **Momentum Brain**: Detects overextensions and reversal points.
    3. **Volatility Brain**: Measures market noise to adjust conviction and position sizing.
- **Independent Coordinator Brain**: A separate execution and tracking thread that coordinates with other brains and the broker to maintain orders, manage dynamic trailing SL/TP, and ensure capital protection.
- **Expert NLP Parser**: Allows traders to execute orders using natural English (e.g., *"go long nifty 24200 calls"*).
- **Dual Dashboard Integration**: Provides a synchronized experience across Desktop (PySide6) and Web (FastAPI/WebSocket).

---

## ✨ Core Features
- **Compatible with Dhan API**: Full live execution using modern `DhanContext` and Marketfeed WebSockets.
- **Professional Paper Trading**: Full simulation environment utilizing real-time live market data.
- **Dynamic Kanban Dashboard**: Visualize trades through "Scanning", "Signal", "Active", and "Closed" stages.
- **Expert Risk Management**: Automatic calculation of win probability and risk-per-trade assessment.
- **Fixed Lot Control**: Manually configurable lot sizes (default 1) adjustable via the Configuration Tab.
- **No-Login Experience**: Automated session handling with TOTP support; no need to keep the broker's login page open.
- **Timed Auto-Confirmation**: 10-second safety window for all trades with intelligent system recommendations.

---

## 📋 Pre-requisites
Before installing, ensure you have:
1. **Python 3.10+**
2. **Rust Toolchain** (Cargo & Rustc) for building the performance core.
3. **Maturin**: For bridging Rust and Python (`pip install maturin`).
4. **Dhan API Credentials**: Client ID and Access Token from the Dhan API console.
5. **TOTP Secret**: Found in Dhan security settings (required for automated login).

---

## 🛠️ Installation

1. **Clone the Repository**:
   ```bash
   git clone <repo-url>
   cd nsefo
   ```

2. **Set up Virtual Environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install Python Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Build and Install the Rust Core**:
   ```bash
   cd nsefo_core
   maturin build --release
   pip install target/wheels/*.whl
   cd ..
   ```

---

## ⚙️ Configuration

1. **Launch the Configuration Dashboard**:
   Open the application and navigate to the **Settings** or **System Config** tab.

2. **Required Parameters**:
   - **Mode**: Toggle between `paper` and `live`.
   - **Dhan Client ID**: Your 10-digit Dhan ID.
   - **Access Token**: Your long-lived API token.
   - **Operational Capital**: Total capital for risk calculations.
   - **Fixed Lot Size**: Set your preferred manual lot count.

*Settings are automatically persisted to `config.json`.*

---

## 📖 Usage Guide

### Starting the Engine
```bash
export PYTHONPATH=$PYTHONPATH:.
python3 python_app/main.py
```

### Executing Manual Trades (NLP)
Use simple English commands directly from the terminal or dashboard input:
- *"buy nifty 24200 ce"*
- *"go long banknifty 48000 calls"*
- *"short finnifty 21000 pe"*

### Monitoring
- **Scanning**: The system continuously monitors the watchlist (NIFTY, BANKNIFTY, FINNIFTY) for high-conviction signals.
- **Active Trades**: Once a trade is executed, the **Coordinator Brain** takes over, tracking real-time price moves and updating trailing stop-losses.
- **Confirmation**: All trades require a 10s confirmation. If no action is taken, the system uses the expert recommendation as the default choice.

---

## 📦 Dependencies
- **Backend**: Python 3.10+, FastAPI, Uvicorn, Pydantic.
- **Performance Core**: Rust (2021 edition), PyO3, `ta` (Technical Analysis), `ndarray`, `rayon`.
- **Broker Integration**: `dhanhq` SDK, `marketfeed`.
- **UI**: PySide6 (Desktop), Tailwind CSS (Web).
- **Data**: Pandas, Numpy.

---

## 🔍 Post-requisites
1. **Connectivity Check**: Ensure your internet connection is stable for the Marketfeed WebSocket.
2. **Risk Verification**: Always check the "Risk Assessment" report before confirming high-lot trades.
3. **Log Monitoring**: Monitor `TradingApp.log` for real-time brain synthesis reports.

---

## 🗺️ Roadmap
- [ ] **Greeks Neural Brain**: Implementation of real-time Delta/Gamma/Theta calculations.
- [ ] **Historical Backtesting Engine**: Test Rust brains against years of 1-minute data.
- [ ] **Multi-Broker Abstraction**: Support for Zerodha, AngelOne, and Upstox.
- [ ] **AI-Pattern Recognition**: Vision-based candle pattern recognition in Rust.

---

**Disclaimer**: Trading in F&O involves high risk. This system is an expert-level tool; ensure your risk parameters are correctly configured before going live.
