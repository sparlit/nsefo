# 🏆 NSE F&O Master Pro Expert Trading System

A high-performance, production-ready trading environment for NSE Options and F&O, leveraging a hybrid **Python + Rust** architecture for sub-millisecond calculation latency.

---

## 📖 Project Overview
The **NSE F&O Master Pro** is designed for expert traders who require ultra-low latency analysis and autonomous order lifecycle management. The system coordinates multiple "Specialized Brains" to evaluate market conviction and execute high-probability trades with absolute precision.

---

## 📊 Detailed Project Report

### 1. Architectural Philosophy: The Coordination of Brains
The system operates on a distributed intellect model where specialized components handle different aspects of the trading cycle:
*   **Performance Core (Rust)**: Offloads heavy computation (Supertrend, RSI, ATR) to a threaded Rust environment, ensuring price ticks are analyzed in microseconds.
*   **Option Brain (OpenGreeks)**: Computes real-time Delta and option sensitivities to filter entries based on dynamic risk profiles.
*   **Independent Coordinator**: A dedicated supervisor thread that tracks every order, manages trailing stop-losses, and enforces capital protection rules without user intervention.

### 2. Operational Integrity: Zero Illusion
This system is **100% operational**. There are no mock data paths, stubs, or placeholders. It utilizes:
*   **Fenix Multi-Broker Layer**: Advanced abstraction for consistent execution across different Indian brokers.
*   **Real-Time Data Feed**: Live Marketfeed WebSockets via Dhan for instant price discovery.
*   **Production State Sync**: A centralized state manager that ensures the Web Console and Desktop Terminal are perfectly synchronized with the core engine.

---

## 📋 Pre-requisites

### Software
*   **Python 3.10+** (Optimized for performance)
*   **Rust Toolchain** (Cargo/Rustc) to compile the neural core.
*   **Maturin** (`pip install maturin`) for bridging.

### Credentials
*   **Dhan API ID & Token**: Obtained from the Dhan Developer portal.
*   **TOTP Secret Key**: Found in your Dhan security settings (enables "No-Login" persistence).

---

## 🛠️ Step-by-Step How-To

### 1. Installation
```bash
# 1. Clone & Enter
git clone <repository-url>
cd nsefo

# 2. Virtual Env & Deps
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Build Rust Core
cd nsefo_core
maturin build --release
pip install target/wheels/*.whl
cd ..
```

### 2. Configuration & Startup
The system is launched via a single command that initiates a guided setup:
```bash
# Launch the expert suite
./nsefo
```
*The first run will prompt you for your Dhan Client ID, Access Token, and Operational Capital.*

---

## 🔍 Usage & Interaction

### Natural Language Trading (NLP)
Once the terminal is active, you can instruct the system in plain English:
*   *"Buy Nifty 24500 CE"* -> System calculates Greeks, probability, and risk before asking for confirmation.
*   *"Go long banknifty 48000 calls"*
*   *"Short Finnifty"* (Market order)

### Dashboard Navigation
*   **Kanban Terminal**: Monitor trades through **Scanning -> Signal -> Active -> Closed**.
*   **System Settings**: Dynamically update Fixed Lots and Risk limits without stopping the engine.

---

## 🛡️ Post-requisites & Stability
1.  **Feed Status**: Ensure the terminal indicates "Marketfeed: READY". High-frequency synthesis requires a stable connection.
2.  **Safety First**: Review the "Neural Cluster Report" in the dashboard for signal conviction before confirming manual entries.
3.  **Logs**: Monitor `web_dashboard.log` and console output for real-time risk assessments.

---

## 📦 System Roadmap
- [ ] **Greeks Neutrality Brain**: Automated Delta-hedging for multi-leg strategies.
- [ ] **Custom Brain API**: Interface to plug in user-defined Rust technical indicators.
- [ ] **Institutional Mirroring**: Sync and mirror trades across multiple sub-accounts.

---

**Disclaimer**: F&O trading involves high risk. This software is provided for expert use. Verify all parameters in "Paper Mode" before switching to "Live Mode".
