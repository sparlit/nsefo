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

## 🏗️ 10 Stages of Development
1. **Logic Modeling** | 2. **Hybrid Architecture** | 3. **Neural Core** | 4. **Broker Gateway** | 5. **State Sync** | 6. **NLP Engine** | 7. **Coordinator Brain** | 8. **Dual Terminals** | 9. **Performance Optimization** | 10. **Turnkey Packaging**

---

## 🔄 10 Phases of Operation
The system executes a precise 10-phase cycle for every trading session:
1. **Integrity Check** -> 2. **Market Awareness** -> 3. **Neural Scanning** -> 4. **Signal Convergence** -> 5. **Option Validation** -> 6. **Risk Check** -> 7. **Safety Confirmation** -> 8. **Order Dispatch** -> 9. **Autonomous Tracking** -> 10. **Dynamic Trailing**

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

## 🛠️ 10 Steps to Deployment (Windows & Linux)

### 1. Installation
Run the unified setup command for your platform:

**Linux:**
```bash
chmod +x setup.sh && ./setup.sh
```

**Windows (Command Prompt / PowerShell):**
```cmd
setup.bat
```

### The Lifecycle:
1. **Clone** | 2. **Venv** | 3. **Deps** | 4. **Compile Core** | 5. **Run Setup** | 6. **Config Wizard** | 7. **Connect API** | 8. **Launch Suite** | 9. **NLP Trade** | 10. **Monitor Kanban**

---

## 📖 Using the System

### Single-Word Command Launch
Once installed, simply type:

**Linux:** `./nsefo`
**Windows:** `nsefo`

### Natural Language Execution
Execute trades by speaking/typing in plain English:
- *"Buy Nifty 24500 CE"*
- *"Go long banknifty 48000 calls"*
- *"Short Finnifty"*

---

## 🔍 Post-requisites & Maintenance

1.  **Connectivity Health**: Monitor the "Marketfeed" status in logs. High-frequency synthesis requires sub-100ms latency.
2.  **TOTP Update**: If your TOTP secret changes, update it via the **System Config** tab in the dashboard.
3.  **Log Auditing**: Review `web_dashboard.log` for detailed brain conviction reports and risk audit trails.

---

**Disclaimer**: F&O trading involves substantial risk. This system is for expert use. Always start in **Paper Mode** to verify your strategy and risk settings.
