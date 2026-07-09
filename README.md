# 🏆 NSE F&O Master Pro Expert Trading System

A professional-grade, high-performance automated trading environment for NSE Options and F&O, powered by a hybrid **Python + Rust** architecture. This system is designed for elite traders who demand ultra-fast calculations, sophisticated risk management, and a transparent, Kanban-style operational dashboard.

---

## 📊 Detailed Project Report

### 1. Architectural Philosophy
The system is built on a "Coordination of Brains" model. By offloading heavy technical analysis to **Rust**, we achieve sub-millisecond calculation latency, essential for the volatile NSE F&O market.

- **Hybrid Engine**: Python handles high-level coordination, NLP, and UI synchronization, while the Rust Core (`nsefo_core`) performs threaded calculations for indicators and probability synthesis.
- **Multi-Brain Intelligence**:
    - **Trend Brain (Rust)**: Uses optimized Supertrend and ATR algorithms to determine directional bias.
    - **Momentum Brain (Rust)**: Analyzes RSI and price velocity to detect overextensions.
    - **Volatility Brain (Rust)**: Measures market standard deviation to adjust signal conviction.
    - **Option Brain (OpenGreeks)**: Real-time calculation of Delta and other Greeks to refine option entry probability.
- **Independent Coordinator**: Operates as a "Supervisor" brain that tracks orders, manages dynamic trailing SL/TP, and enforces capital protection rules autonomously.

### 2. Operational Reality
This is a **zero-illusion** codebase. Every component is operational, using real-world broker SDKs (Dhan via Fenix) and real-time Marketfeed WebSockets. There are no mock placeholders in the execution path.

---

## 📋 Pre-requisites

Before initiating the system, the following environment must be prepared:

### Software Requirements
- **Python 3.10+**: Optimized for async/await performance.
- **Rust Toolchain (Cargo/Rustc)**: Required to compile the high-performance core.
- **Maturin**: Python package (`pip install maturin`) for Rust-Python bridging.

### Data & Access
- **Dhan API Credentials**: Valid `Client ID` and `Access Token`.
- **TOTP Secret Key**: Required for automated session renewal (Found in Dhan Security Settings).
- **Market Access**: NSE F&O segment enabled on your Dhan account.

---

## 🛠️ Step-by-Step How-To

### 1. Environment Setup
```bash
# Clone the repository
git clone <repository-url>
cd nsefo

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### 2. Compiling the Rust Core
This step is critical for the system's "Brain" to function at speed.
```bash
cd nsefo_core
maturin build --release
pip install target/wheels/*.whl
cd ..
```

### 3. Single Command Launch & Configuration
The system features a guided interactive launcher.
```bash
python3 start_master_pro.py
```
- The launcher will ask for your **Dhan ID**, **Token**, and **Capital** limits if not already configured.
- It will automatically perform a **Connectivity & Integrity Check**.
- Upon success, it will launch the Web Terminal, the Engine, and the Desktop Dashboard simultaneously.

---

## 📖 Usage & Interaction

### Natural Language Execution (NLP)
Simply instruct the system in plain English:
- *"Buy Nifty 24500 CE"* -> System calculates Greeks, probability, and risk before asking for confirmation.
- *"Go long banknifty 48000 calls"* -> Professional variation parsing.
- *"Short Finnifty"* -> Market-order logic.

### Expert Dashboards
- **Kanban View**: Track trades through **Scanning -> Signal -> Active -> Closed**.
- **Live Terminal**: High-fidelity terminal for active order monitoring.
- **System Config**: Real-time updates to Fixed Lots and risk parameters without restarting the engine.

---

## 🔍 Post-requisites

1. **Connectivity Monitoring**: Ensure your terminal shows "Marketfeed: READY". High-frequency trading requires a stable low-latency connection.
2. **One-Time TOTP Setup**: After first launch, ensure your TOTP secret is saved in the configuration for the "No-Login" experience to persist across days.
3. **Log Review**: Periodically review the `system_logs` in the dashboard for brain conviction reports (e.g., *"Neural Cluster Analysis: 92% Conviction"*).

---

## 📦 System Dependencies
- **Analysis**: `nsefo_core` (Custom Rust), `OpenGreeks` (Delta/Options), `Pandas/Numpy`.
- **Brokerage**: `Fenix` (Multi-broker abstraction), `dhanhq` (Official SDK).
- **Dashboards**: `FastAPI` (WebSocket backend), `TailwindCSS` (UI), `PySide6` (Desktop).
- **Security**: `PyOTP` (TOTP), `PyCryptodome`.

---

## 🗺️ Future Roadmap
- [ ] **Greeks Neutrality Brain**: Automated Delta-hedging logic.
- [ ] **Custom Strategy Plug-ins**: Interface for users to add their own Rust-based brains.
- [ ] **Multi-Account Coordination**: Manage and mirror trades across multiple broker accounts simultaneously.

**Disclaimer**: F&O trading involves significant risk of loss. This software is provided for expert use only. Always verify your risk parameters in "Paper Mode" before switching to "Live Mode".
