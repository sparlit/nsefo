# Architectural Philosophy: The Neural Coordination Model

NSEFO Master Pro is built on a distributed intellect model, specifically designed to eliminate latency in the volatile NSE F&O market.

---

## 1. Hybrid Engine: Python + Rust Bridge

The core performance layer uses Maturin + PyO3 to compile a native Rust extension (`nsefo_core`) that Python imports as a regular module.

```
Python (TradingApp)  →  nsefo_core Rust extension  →  Machine code
         │                        │
    orchestration          O(n) indicator calculations
    NLP parsing             RSI, Supertrend, ATR,
    async UI state          StdDev, probability
```

- **Python** manages: orchestration, broker abstraction, NLP parsing, state synchronization, risk management, UI rendering
- **Rust** handles: all numerical indicator calculations — vectorized via `rayon` for parallel throughput, `ta` crate for Supertrend/RSI/ATR/StdDev

**Why Maturin + ABI3 forward compatibility?**
The `Cargo.toml` specifies `pyo3 = { version = "0.22", features = ["extension-module", "abi3-py310"] }`. This generates a wheel compatible with Python 3.10+ regardless of minor version. The `PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1` env var at build time ensures the wheel is truly ABI3, not tied to the build machine's Python version.

---

## 2. Multi-Brain Synthesis

Decision-making is never localized to a single indicator. Four specialized brains coordinate:

| Brain | Indicator | Role |
|-------|-----------|------|
| **Trend** | Supertrend (ATR-based, Rust) | Directional bias — up/down/neutral |
| **Momentum** | RSI (14-period, Rust) | Overbought/oversold conviction |
| **Volatility** | Standard Deviation (20-period, Rust) | Volatility-adjusted conviction multiplier |
| **Options** | OpenGreeks Black-Scholes Delta | Strike selection efficiency |

**Synthesis formula** (in `python_app/core/engine.py` → `nsefo_core/src/analysis/probability.rs`):
```
base_prob = (trend × 0.5) + (rsi_score × 0.3)
final_prob = clamp(normalize(base_prob) × vol_conviction, 0.0, 1.0)
```
Where `rsi_score = +1.0 if RSI < 30, −1.0 if RSI > 70, else 0.0`
Where `vol_conviction = 1.2 if current_vol > avg_vol else 0.8`

EXECUTE signal requires: `probability > 0.8 AND trend == UP`

---

## 3. Broker Abstraction Layer

The `Broker` abstract base class (`python_app/broker/base.py`) defines the interface. Three concrete implementations:

| Broker | Use Case | Data Source |
|--------|----------|-------------|
| `FenixDhanProvider` | Live trading (Fenix gateway) | Dhan API v2 via `fenix` library |
| `DhanProvider` | Live trading (direct) | Dhan SDK via `dhanhq` library |
| `PaperBroker` | Simulation mode | Falls back to `data_provider` for real data; generates simulated fills if unavailable |

**Symbol ID mapping** (hardcoded in `python_app/main.py`):
```python
symbol_map = {"NIFTY": "13", "BANKNIFTY": "25", "FINNIFTY": "27"}
```

**PaperBroker fallback logic**: When `data_provider` is available (i.e., Fenix), `PaperBroker.get_market_data` calls the real API and returns live prices — paper mode uses real market data but simulates order execution. When `data_provider` is unavailable, it generates simulated prices via `random.uniform(100±1)` as a last resort.

---

## 4. State Management

`python_app/core/state.py` defines an `AppState` dataclass with a global singleton `global_state`:

```python
@dataclass
class AppState:
    summary: Dict         # capital, total_pnl, active_trades_count, mode, last_update
    kanban: Dict          # SCANNING, SIGNAL, ACTIVE, CLOSED
    pnl_history: List     # per-trade P&L
    system_logs: List     # rolling log (max 100 entries)
```

The WebSocket endpoint (`dashboards/web/app.py`) reads from this singleton and pushes JSON to the browser every 1 second. The Desktop Qt app (`dashboards/desktop/main.py`) polls via `QTimer` at 1-second intervals.

---

## 5. Independent Coordinator

`python_app/core/coordinator.py` manages the trade lifecycle post-execution:

- **`track_trades`**: Called every 1 second by the market cycle. Fetches LTP for each active position.
- **`apply_trailing_sl`**: When price moves favourably by `trailing_step` (default 1.0), the stop-loss is updated to lock in profit.

---

## 6. Risk Manager

`python_app/core/risk_manager.py` enforces capital-based position sizing:

```python
risk_amount = abs(entry - sl) * quantity
risk_percent = (risk_amount / capital) * 100
is_safe = risk_percent <= (max_risk_per_trade * 100)  # default 1%
```

`is_safe=False` causes the Coordinator to reject the order with a `REDUCE QUANTITY/SIZE` recommendation.

---

## 7. NLP Command Parser

`python_app/nlp/parser.py` uses regex to parse natural language order instructions:

| Pattern | Example |
|---------|---------|
| `ACTION SYMBOL STRIKE TYPE` | `Buy Nifty 24500 ce` |
| `SYMBOL STRIKE TYPE` (default buy) | `Nifty 24500 pe` |
| `ACTION SYMBOL` (market order) | `Sell Nifty` |

Supported actions: `buy`, `sell`, `long`, `short`
Supported types: `ce`, `call`, `calls`, `pe`, `put`, `puts`

The parser returns: `{action, symbol, strike, option_type, raw}`

---

## 8. Dashboard Layer

**Web (FastAPI + WebSocket):**
- `dashboards/web/app.py` — FastAPI app with `/config`, `/config` (POST), and `/ws` WebSocket endpoints
- `dashboards/web/static/index.html` — Single-page Kanban UI with TailwindCSS, two-sub-tab Settings panel (Connection + Risk Management), JS WebSocket client, and sensitive-credential env-var-only design
- Port 9099, launched by `start_master_pro.py` via `uvicorn`

**Desktop (PySide6):**
- `dashboards/desktop/main.py` — `QMainWindow` with `QTabWidget` (Live Terminal + Config)
- Kanban columns rendered as `QFrame` widgets with scroll areas
- 1-second refresh via `QTimer`

---

## 9. Trade Lifecycle (10 Phases)

1. **Integrity** — `broker.login()` verifies API credentials
2. **Market Data** — `broker.get_market_data()` + `broker.get_historical_data()` fetches OHLCV
3. **Neural Analysis** — Rust `get_rsi_list`, `get_supertrend`, `get_volatility_list` compute indicators
4. **Signal Convergence** — `calculate_probability` synthesizes conviction score
5. **Greeks Verification** — `opengreeks.black_scholes.delta` computes option Delta
6. **Risk Assessment** — `RiskManager.assess_trade` checks capital exposure
7. **Human Confirmation** — Explicit YES/Y required (fail-safe authorization) in `python_app/core/utils.py`
8. **Order Execution** — `broker.place_order` dispatches to Dhan
9. **Autonomous Tracking** — `Coordinator.track_trades` runs every 1 second
10. **Dynamic Trailing SL** — `Coordinator.apply_trailing_sl` adjusts stop-loss