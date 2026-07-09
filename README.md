# 🏆 NSE F&O Master Pro Expert Trading System

A professional-grade, ultra-high-performance automated trading environment for NSE Options and F&O, leveraging a hybrid **Python + Rust** architecture for sub-millisecond calculation latency.

---

## 📑 Project Report: System Intelligence

### 🧠 1. The Neural Coordination Model
The system operates on a "Coordination of Brains" architecture. Heavy technical analysis is offloaded to a multi-threaded **Rust Core**, while Python manages high-level logic and UI synchronization.
*   **Trend Brain**: Optimized Supertrend & ATR algorithms for directional bias.
*   **Momentum Brain**: Real-time RSI and price velocity detection.
*   **Volatility Brain**: Standard deviation analysis to adjust conviction levels.
*   **Options Brain**: Integrated **OpenGreeks** for real-time Delta/Gamma sensitivities.

### 🛡️ 2. Autonomous Execution & Risk
The **Independent Coordinator Brain** acts as a supervisor, ensuring that once a trade is authorized:
*   Orders are tracked across their entire lifecycle.
*   **Trailing SL/TP** is adjusted dynamically based on market volatility.
*   Capital is protected via strict per-trade risk limits and daily drawdown checks.

### 🔌 3. Broker Integration Layer
Utilizing the **Fenix** multi-broker abstraction, the system provides:
*   Direct **Dhan API** production-grade connectivity.
*   Real-time **Marketfeed WebSockets** for zero-latency price updates.
*   A sophisticated **Paper Trading** engine that uses live market data for 100% realistic simulations.

---

## 📋 Pre-requisites

### Technical Requirements
- **Hardware**: Minimum 4GB RAM, Stable Internet connection.
- **Python 3.10+**: Must be in the system PATH.
- **Rust Toolchain**: `rustc` and `cargo` installed (for building the calculation core).

### Account Access
- **Dhan API Access**: Client ID and Access Token from the Dhan Developer portal.
- **TOTP Secret**: Required for automated, session-persistent "No-Login" operation.

---

## 🛠️ Step-by-Step Installation

The entire environment can be prepared with a single command:

```bash
# Run the unified setup and configuration script
chmod +x setup.sh
./setup.sh
```

**What happens during setup:**
1.  Verification of Python and Rust environments.
2.  Installation of all professional-grade dependencies (FastAPI, PySide6, OpenGreeks, Fenix).
3.  Compilation of the **Rust Calculation Core**.
4.  Initialization of the **Master Pro Configuration Wizard**.
5.  Creation of the single-word `nsefo` entry point.

---

## ⚙️ Configuration Guide

Upon running `./setup.sh` (or `./nsefo` for the first time), the **System Wizard** will prompt for:
1.  **Operational Mode**: Choose between `live` (real money) or `paper` (simulation).
2.  **Dhan Credentials**: Input your Client ID and API Token.
3.  **Capital Allocation**: Define your trading capital for risk-percent calculations.
4.  **Fixed Lot Size**: Set the manual lot count for all F&O trades.

*Configuration is persisted securely in `config.json`.*

---

## 📖 Using the System

### Single-Word Command Launch
Once installed, simply type:
```bash
./nsefo
```

### Natural Language Execution
Execute trades by speaking/typing in plain English:
- *"Buy Nifty 24500 CE"*
- *"Go long banknifty 48000 calls"*
- *"Short Finnifty"*

### Dashboard Oversight
- **Kanban View**: Real-time tracking from Scanning to Signal to Active.
- **Live Terminal**: Professional monitoring of P&L and order status.
- **Expert Recommendation**: Every trade is vetted by the brains; wait for the "EXECUTE" green signal.

---

## 🔍 Post-requisites & Maintenance

1.  **Connectivity Health**: Monitor the "Marketfeed" status in logs. High-frequency synthesis requires sub-100ms latency.
2.  **TOTP Update**: If your TOTP secret changes, update it via the **System Config** tab in the dashboard.
3.  **Log Auditing**: Review `web_dashboard.log` for detailed brain conviction reports and risk audit trails.

---

## 📦 System Dependencies
- **Logic**: `nsefo_core` (Rust), `OpenGreeks` (Options Theory).
- **Network**: `Fenix` (Broker Abstraction), `FastAPI` (WebSockets).
- **UI**: `PySide6` (Desktop), `TailwindCSS` (Web).

---

**Disclaimer**: F&O trading involves substantial risk. This system is for expert use. Always start in **Paper Mode** to verify your strategy and risk settings.
