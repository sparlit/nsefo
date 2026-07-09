# 🏆 NSE F&O Master Pro Expert Trading System

A professional-grade, ultra-high-performance automated trading environment for NSE Options and F&O, leveraging a hybrid **Python + Rust** architecture for sub-millisecond calculation latency.

---

## 📑 System Documentation
The **NSE F&O Master Pro** is a zero-illusion, 100% operational trading system.
- [Detailed Architectural Report](ARCHITECTURE_REPORT.md)
- [Operational Roadmap & Phases](OPERATIONAL_PHASES.md)
- [System Memory & Patterns](PROJECT_MEMORY.md)

---

## 📋 Pre-requisites

### Software Requirements
- **Python 3.10+**: Optimized for async/await performance.
- **Rust Toolchain (Cargo/Rustc)**: Required to compile the high-performance core.
- **Maturin**: Python bridge for Rust (`pip install maturin`).

### Data & Access
- **Dhan API Credentials**: Valid `Client ID` and `Access Token`.
- **TOTP Secret Key**: Found in Dhan Security Settings (enables "No-Login" persistence).

---

## 🛠️ Step-by-Step Installation

The environment is prepared using a single turnkey command for your platform:

**Linux:**
```bash
./install
```

**Windows (CMD/PowerShell):**
```cmd
install.bat
```

**What this command does:**
1.  Installs all professional dependencies.
2.  Compiles the **Rust Brain Core** for your OS.
3.  Launches the **Interactive Configuration Wizard**.
4.  Validates **Broker Connectivity**.

---

## ⚙️ Configuration

The system stores parameters in `config.json`. On first run, the Wizard will ask for:
1.  **Trading Mode**: `live` or `paper`.
2.  **Dhan Credentials**: ID and Token.
3.  **Capital & Risk**: Initial capital and fixed lot count.

---

## 📖 Usage Manual

### Activation (Single Command)
Type the following from the root directory:

**Linux:** `./nsefo`
**Windows:** `nsefo.bat`

### Natural Language Trading (NLP)
Once live, you can instruct the system in plain English:
- *"Buy Nifty 24500 CE"* -> Triggers multi-brain analysis.
- *"Go long banknifty 48000 calls"*
- *"Short Finnifty"* (Market order logic)

### Expert Dashboards
- **Terminal**: Monitor trades on the live Kanban board.
- **Settings**: Update Fixed Lots and Risk limits in real-time.

---

## 🔍 Post-requisites & Maintenance
1.  **Feed Integrity**: Ensure terminal shows "Marketfeed: READY".
2.  **Confirmation Window**: All trades have a 10s safety window; monitor for expert recommendations.
3.  **Safety First**: Verify all risk parameters in `paper` mode before going `live`.

**Disclaimer**: F&O trading involves substantial risk. This software is for expert use only.
