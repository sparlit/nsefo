# 🧠 NSEFO Master Pro: Project Memory & Knowledge Base

This file serves as the permanent record of architectural patterns, critical learnings, and engineering decisions made during the development of the Master Pro Expert system.

## 🧱 Technical Patterns

### 1. The Python-Rust Bridge (Maturin/PyO3)
- **Decision**: Offload all O(n) technical indicator calculations to Rust.
- **Pattern**: Python sends raw list data (`Vec<f64>`) to Rust. Rust performs parallelized calculation using `rayon` and `ta` crates.
- **Benefit**: Achieved throughput of 2200+ symbols/sec, reducing brain latency to ~0.45ms.

### 2. Multi-Brain Coordination
- **Decision**: Avoid single-indicator triggers.
- **Pattern**: Weighted Synthesis. Trend (Supertrend) + Momentum (RSI) + Volatility (ATR).
- **Rule**: Minimum 0.80 conviction score required for an "EXECUTE" recommendation.

### 3. Centralized State Management
- **Decision**: Avoid disparate UI and Engine states.
- **Pattern**: Global `AppState` singleton with thread-safe updates.
- **Benefit**: Zero-latency synchronization between the trading engine and the dual (Web/Desktop) dashboards.

## 🔌 Integration Learnings

### Dhan API & Fenix
- **Lesson**: Dhan SDK initialization requires a specific `DhanContext` object in newer versions.
- **Correction**: Updated `DhanProvider` to wrap credentials in `DhanContext` before instantiating the main API client.
- **Socket Pattern**: Used `marketfeed.DhanFeed` in a daemon thread for non-blocking price discovery.

### Safety Protocols
- **Decision**: Implemented a mandatory 10-second confirmation gate.
- **Pattern**: Non-blocking `input()` using `threading.Event` for automated fallback if the trader is away from the terminal.

## 🚀 Performance Benchmarks
- **Stress Test Result**: 2000 symbols processed in 0.9s.
- **System Stability**: Successfully handled 10,000 tick updates in a 5s simulation without memory leaks.

## 🛠️ Troubleshooting Guide
- **Rust Compilation**: Ensure `cargo` is in the PATH before running `setup.sh`.
- **UI Connectivity**: If Web Terminal fails to load, ensure Port 8000 is not blocked by local firewalls.
- **API Errors**: DH-905 errors typically indicate missing required fields in `config.json`. Verify `fixed_lots` and `capital` are present.

---
*End of Memory File*
