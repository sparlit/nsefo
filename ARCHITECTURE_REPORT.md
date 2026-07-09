# 🧱 Architectural Philosophy: The Neural Coordination Model

The **NSEFO Master Pro** system is built on a distributed intellect model, specifically designed to eliminate latency in the volatile NSE F&O market.

### 1. Hybrid Engine Implementation
The core uses a high-performance bridge:
- **Rust Core (`nsefo_core`)**: Handles all O(n) calculations including Supertrend, RSI, and ATR. By utilizing multi-threading in Rust, we achieve sub-millisecond calculation latency.
- **Python Host**: Manages the high-level orchestration, NLP command parsing, and asynchronous UI state synchronization.

### 2. Multi-Brain Synthesis
Decision making is not localized to a single indicator. Instead, four specialized brains coordinate:
- **Trend Brain**: Real-time directional bias filtering.
- **Momentum Brain**: Reversal and breakout conviction.
- **Volatility Brain**: Dynamic risk and conviction adjustment.
- **Options Brain**: Real-time Delta/Theta sensitivities via `OpenGreeks`.
