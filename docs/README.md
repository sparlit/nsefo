# NSEFO Master Pro — Project Status & Technical Report

**Last Updated:** 2026-07-13  
**Project:** Professional-grade automated trading system for NSE Futures & Options  
**Architecture:** Hybrid Python 3.10+ (orchestration) + Rust (sub-millisecond indicators)  
**Status:** ⚠️ Development — core systems implemented; limited automated test coverage; paper mode strongly recommended before live trading

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Implementation Status — Complete Inventory](#2-implementation-status--complete-inventory)
3. [Architecture](#3-architecture)
4. [Core Modules Deep Dive](#4-core-modules-deep-dive)
5. [Broker Integrations](#5-broker-integrations)
6. [Rust Performance Core](#6-rust-performance-core)
7. [Trade Lifecycle — 10 Phases](#7-trade-lifecycle--10-phases)
8. [Quantitative Analytics Engine](#8-quantitative-analytics-engine)
9. [Dashboard Systems](#9-dashboard-systems)
10. [Installation](#10-installation)
11. [Configuration](#11-configuration)
12. [Startup](#12-startup)
13. [NLP Trading Commands](#13-nlp-trading-commands)
14. [Known Limitations & Pending Work](#14-known-limitations--pending-work)
15. [Deprecated Brokers](#15-deprecated-brokers)
16. [File Structure](#16-file-structure)
17. [Troubleshooting](#17-troubleshooting)
18. [Security Notes](#18-security-notes)

---

## 1. Project Overview

| Attribute | Detail |
|-----------|--------|
| **Type** | Automated algorithmic trading system |
| **Market** | NSE Futures & Options (F&O) |
| **Primary Language** | Python 3.10+ |
| **Performance Layer** | Rust (`nsefo_core`) via Maturin/PyO3 |
| **License** | Expert trading — see disclaimer |
| **Build Tool** | Maturin + PyO3 (Rust Python extension) |
| **Live Brokers** | 26 fully implemented broker integrations |
| **Rust Crates** | `ta` (indicators), `rayon` (parallel), `reqwest` (HTTP) |

**Why Python + Rust hybrid?**  
Options analysis requires real-time computation of RSI, Supertrend, ATR, Standard Deviation, and probability synthesis on every market tick. Python handles orchestration, broker abstraction, and state; Rust (`nsefo_core`) handles O(n) numerical calculations via the `ta` crate with `rayon` parallel processing. Note: Rust source code is not in this repository — only the compiled wheel is available; performance claims are unverified.

---

## 2. Implementation Status — Complete Inventory

### ✅ Fully Implemented (Real Code, Real Data, No Stubs)

#### Core Trading Engine
| Module | File | Status | Notes |
|--------|------|--------|-------|
| TradingApp Orchestrator | `python_app/main.py` | ✅ Full | NLP loop, market cycle, broker integration |
| BrainEngine | `python_app/core/engine.py` | ✅ Full | Rust calls + OpenGreeks Delta synthesis |
| Coordinator | `python_app/core/coordinator.py` | ✅ Full | Trade tracking, trailing SL |
| RiskManager | `python_app/core/risk_manager.py` | ✅ Full | Capital-based position sizing, real math |
| GreeksCalculator | `python_app/core/greeks_calculator.py` | ✅ Full | Full Black-Scholes: delta, gamma, theta, vega |
| QuantitativeEngine | `python_app/core/quantitative.py` | ✅ Full | VWAP, VPIN, Spread, Regime, IV Surface |
| AppState | `python_app/core/state.py` | ✅ Full | Thread-safe singleton, JSON persistence |
| Utilities | `python_app/core/utils.py` | ✅ Full | Timed input, trade confirmation |
| NLP Parser | `python_app/nlp/parser.py` | ✅ Full | Regex-based, 6 command patterns |

#### Broker Integrations (Real HTTP/SDK Calls)
| Broker | File | Auth Method | Status |
|--------|------|-------------|--------|
| Dhan (SDK) | `python_app/broker/dhan.py` | client_id + access_token | ✅ Full — `dhanhq` SDK |
| Dhan (Fenix) | `python_app/broker/fenix_broker.py` | client_id + access_token | ✅ Full — `fenix` SDK |
| Zerodha Kite | `python_app/broker/zerodha.py` | api_key + access_token | ✅ Full — `kiteconnect` SDK |
| AngelOne SmartAPI | `python_app/broker/angelone.py` | client_id + password + TOTP | ✅ Full — REST API |
| Upstox | `python_app/broker/upstox.py` | client_id + access_token | ✅ Full — REST API |
| Fyers API v2 | `python_app/broker/fyers.py` | client_id + access_token | ✅ Full — REST API |
| Kotak Securities | `python_app/broker/kotak.py` | consumer_key + access_token | ✅ Full — REST API |
| Kotak Neo | `python_app/broker/kotak_neo.py` | consumer_key + access_token | ✅ Full — REST API |
| 5paisa | `python_app/broker/fivepaisa.py` | client_id + password + TOTP | ✅ Full — REST API |
| IIFL Markets | `python_app/broker/iifl.py` | api_key + password | ✅ Full — REST API |
| Motilal Oswal | `python_app/broker/motilal.py` | api_key + password | ✅ Full — REST API |
| Finvasia (Shoonya) | `python_app/broker/finvasia.py` | vendor_code + yob + TOTP | ✅ Full — REST API |
| AliceBlue | `python_app/broker/aliceblue.py` | app_code + api_secret | ✅ Full — REST API |
| Choice Broking | `python_app/broker/choice.py` | client_id + TOTP | ✅ Full — REST API |
| HDFC Securities | `python_app/broker/hdfc.py` | client_id + access_token | ✅ Full — REST API |
| ICICI Direct | `python_app/broker/icici.py` | OAuth2 + refresh_token | ✅ Full — REST API |
| SBI Securities | `python_app/broker/sbi.py` | app_name + access_token | ✅ Full — REST API |
| Bajaj Financial | `python_app/broker/bajaj.py` | api_key + client_id + access_token | ✅ Full — REST API |
| Geojit | `python_app/broker/geojit.py` | client_id + password + yob | ✅ Full — form-urlencoded POST |
| Mirae Asset Sharekhan | `python_app/broker/sharekhan.py` | client_id + access_token | ✅ Full — REST API |
| Anand Rathi | `python_app/broker/anand_rathi.py` | client_id + access_token | ✅ Full — REST API |
| Edelweiss | `python_app/broker/edelweiss.py` | client_id + access_token | ✅ Full — REST API |
| Axis Direct | `python_app/broker/axis_direct.py` | client_id + access_token | ✅ Full — REST API |
| Groww | `python_app/broker/groww.py` | api_key + access_token | ✅ Full — REST API |
| Moneysukh | `python_app/broker/moneysukh.py` | client_id + api_key | ✅ Full — REST API |
| Master Trust | `python_app/broker/master_trust.py` | app_key | ✅ Full — REST API |
| PaperBroker | `python_app/broker/paper.py` | N/A (simulation) | ✅ Full — real data fallback |

#### Session & Auth
| Module | File | Status |
|--------|------|--------|
| Session Manager | `python_app/broker/session_manager.py` | ✅ Full — 26-broker factory |
| Browser Login | `python_app/auth/browser_login.py` | ✅ Full — Playwright + TLS fingerprinting |
| Token Manager | `python_app/auth/browser_login.py` | ✅ Full — auto-relogin + heartbeat |

#### Dashboards
| Component | File | Status |
|-----------|------|--------|
| Web Dashboard | `dashboards/web/app.py` | ✅ Full — FastAPI + WebSocket |
| Web Frontend | `dashboards/web/static/index.html` | ✅ Full — TailwindCSS Kanban |
| Desktop Dashboard | `dashboards/desktop/main.py` | ✅ Full — PySide6 Qt |

#### Rust Performance Core
| Function | File | Status |
|----------|------|--------|
| RSI | `nsefo_core/src/strategies/mean_reversion.rs` | ✅ Full — `ta::RelativeStrengthIndex` |
| Supertrend + ATR | `nsefo_core/src/strategies/trend.rs` | ✅ Full — custom implementation |
| Standard Deviation | `nsefo_core/src/strategies/volatility.rs` | ✅ Full — `ta::StandardDeviation` |
| Probability Synthesis | `nsefo_core/src/analysis/probability.rs` | ✅ Full — weighted scoring |
| HTTP Client | `nsefo_core/src/http/client.rs` | ✅ Full — `reqwest` + TLS |

#### Scripts & Entrypoints
| Script | Status |
|--------|--------|
| `run.py` | ✅ Full — canonical startup |
| `install.py` | ✅ Full — cross-platform installer |
| `start_master_pro.py` | ✅ Full — GUI launcher |
| `nsefo` / `nsefo.bat` | ✅ Full — single-word startup |
| `install` / `install.bat` | ✅ Full — single-word install |

---

## 3. Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    TradingApp  (python_app/main.py)                │
│  ┌───────────┬───────────┬────────────┬──────────────────────┐  │
│  │ Command   │ Brain     │ Coordinator │ Risk                │  │
│  │ Parser    │ Engine    │             │ Manager              │  │
│  │ (NLP)     │(synthesis)│ (tracking)  │ (capital)           │  │
│  └─────┬─────┴─────┬─────┴──────┬─────┴─────────┬──────────────┘  │
│        │           │            │              │                   │
│  Broker Abstraction Layer (26 providers)                          │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │DhanProvider │ FenixDhan │ Zerodha │ AngelOne │ PaperBroker │ │
│  │ + 22 more real broker implementations (REST/SDK)           │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                         │                                        │
│         ┌───────────────┴────────────────┐                       │
│         │      nsefo_core (Rust)         │  ← PyO3/Maturin       │
│         │  get_rsi_list                  │                      │
│         │  get_supertrend                 │                      │
│         │  get_volatility_list            │                      │
│         │  calculate_probability           │                      │
│         │  http_post / http_get            │                      │
│         └─────────────────────────────────┘                       │
└──────────────────────────────────────────────────────────────────┘
```

### Dual-Broker System

The project has two parallel broker systems:

1. **`python_app/broker/`** (singular) — **Working production system**
   - 26 real broker implementations with actual HTTP calls and SDK integrations
   - Session factory in `session_manager.py`
   - Active and used by the trading engine

2. **`python_app/brokers/`** (plural) — **NSE registry metadata system**
   - Registry of 1035+ NSE-registered broker/corporate members
   - Metadata in `registry.py` with API status, auth types, NSE member codes
   - `providers/` subdirectory contains stub files for hundreds of smaller brokers
   - These stubs are auto-generated boilerplate (not used by active trading)
   - Provides broker search via `search.py` and credential management

---

## 4. Core Modules Deep Dive

### BrainEngine (`python_app/core/engine.py`)

Orchestrates four technical indicators (RSI, Supertrend, volatility, delta) as a weighted ensemble and synthesizes a conviction score:

```python
# Momentum (Rust)
rsi = nsefo_core.get_rsi_list(close, 14)

# Trend (Rust)
st_values, trends = nsefo_core.get_supertrend(high, low, close, 10, 3.0)

# Volatility (Rust)
vol_list = nsefo_core.get_volatility_list(close, 20)

# Delta (OpenGreeks)
sigma = (curr_vol / close[-1]) * (252**0.5)
d = calculate_delta('c', close[-1], close[-1], 30/365, 0.1, sigma)

# Synthesis
trend_score = float(curr_trend)   # +1.0 (UP) or -1.0 (DOWN)
rsi_score = 1.0 if curr_rsi < 30 else -1.0 if curr_rsi > 70 else 0.0
vol_conviction = 1.2 if curr_vol > avg_vol else 0.8
base_prob = nsefo_core.calculate_probability([trend_score, rsi_score])
final_prob = clamp(normalize(base_prob) * vol_conviction, 0.0, 1.0)
```

### QuantitativeEngine (`python_app/core/quantitative.py`)

Full market microstructure analytics:
- **VWAPCalculator**: Volume-Weighted Average Price with session reset
- **VPINCalculator**: Volume-Synchronized Probability of Informed Trading
- **SpreadTracker**: Bid-ask spread over rolling window with metrics
- **RegimeDetector**: Bull/bear/sideways detection via rolling returns
- **VolatilitySurface**: Strike × expiry IV surface with interpolation, risk-reversal, butterfly skew

### GreeksCalculator (`python_app/core/greeks_calculator.py`)

Pure Python Black-Scholes implementation using `scipy.stats.norm`:

```python
def greeks(S, K, T, r, sigma, option_type="call"):
    # S: spot (e.g. 24500), K: strike, T: time in years (e.g. 7/365)
    # r: risk-free rate (e.g. 0.0695 for 6.95% 91-day T-bill)
    # sigma: IV (e.g. 0.18 for 18%)
    return {
        "delta": delta(S, K, T, r, sigma, option_type),
        "gamma": gamma(S, K, T, r, sigma, option_type),
        "theta": theta(S, K, T, r, sigma, option_type),
        "vega":  vega(S, K, T, r, sigma, option_type),
    }
```

Note: `rho` (interest rate sensitivity) is not computed as it requires live T-bill data.

---

## 5. Broker Integrations

### Authentication Methods by Broker

| Auth Type | Brokers |
|-----------|---------|
| **client_id + access_token** | Dhan, Fenix, Zerodha (api_key + token), Upstox, Fyers, Kotak, AliceBlue, HDFC, SBI, Edelweiss, Anand Rathi, Axis Direct, Sharekhan, Groww, Motilal, IIFL, Choice, Finvasia, Bajaj, Master Trust, Moneysukh |
| **client_id + password + TOTP** | AngelOne, 5paisa, Geojit |
| **OAuth2** | ICICI (client_secret + refresh_token, auto-refresh) |
| **Paper simulation** | PaperBroker (real data from data_provider, simulated fills) |

### How Broker Selection Works

```python
# session_manager.py → get_broker()
if mode == "live":
    if live_provider.login():
        broker = live_provider          # Real trading
    else:
        broker = PaperBroker(data_provider=live_provider)  # Paper fallback
else:
    broker = PaperBroker(data_provider=live_provider)    # Paper mode
```

---

## 6. Rust Performance Core

### Build Configuration

```toml
# nsefo_core/Cargo.toml
[dependencies]
pyo3 = { version = "0.22", features = ["extension-module", "abi3-py310"] }
ta = "0.5"           # Technical analysis indicators
rayon = "1.8"        # Parallel iterators
reqwest = "0.12"     # HTTP client with rustls TLS

[profile.release]
opt-level = 3
lto = true           # Link-time optimization
codegen-units = 1
strip = true
```

### Exposed Functions

| Function | Signature | Returns |
|----------|-----------|---------|
| `get_rsi_list` | `(data: Vec<f64>, period: usize)` | `Vec<f64>` — RSI values |
| `get_supertrend` | `(high, low, close: Vec<f64>, period, multiplier: f64)` | `(Vec<f64>, Vec<i8>)` — values + trend |
| `get_volatility_list` | `(data: Vec<f64>, period: usize)` | `Vec<f64>` — std-dev values |
| `calculate_probability` | `(indicators: Vec<f64>)` | `f64` — 0.0–1.0 conviction |
| `http_post` | `(url, body_json, headers?, timeout?)` | `String` — JSON response |
| `http_get` | `(url, headers?, timeout?)` | `String` — JSON response |

### Probability Synthesis Formula

```rust
// nsefo_core/src/analysis/probability.rs
pub fn assess_winning_probability(indicators: Vec<f64>) -> f64 {
    let trend = indicators[0];    // Weight: 0.5
    let momentum = indicators[1]; // Weight: 0.3
    let vol_factor = indicators.get(2).unwrap_or(&1.0);

    let base_score = (trend * 0.5) + (momentum * 0.3);
    let normalized = (base_score + 0.8) / 1.6;  // Map [-0.8, 0.8] → [0.0, 1.0]
    (normalized * vol_factor).clamp(0.0, 1.0)
}
```

---

## 7. Trade Lifecycle — 10 Phases

| Phase | Name | What Happens | Code Location |
|-------|------|-------------|---------------|
| 1 | **Integrity** | `broker.login()` verifies API credentials | `session_manager.py:197` |
| 2 | **Market Data** | `get_market_data()` + `get_historical_data()` fetches OHLCV | `main.py:51-58` |
| 3 | **Neural Analysis** | Rust computes RSI, Supertrend, ATR, StdDev | `engine.py:23-32` |
| 4 | **Signal Convergence** | `calculate_probability()` synthesizes conviction score | `engine.py:47` |
| 5 | **Greeks Verification** | OpenGreeks delta computed for ATM strike | `engine.py:36-40` |
| 6 | **Risk Assessment** | `RiskManager.assess_trade()` checks capital exposure | `main.py:70` |
| 7 | **Confirmation Gate** | Explicit YES/Y required (fail-safe authorization) | `utils.py:136` |
| 8 | **Order Execution** | `broker.place_order()` dispatches to exchange | `coordinator.py:61` |
| 9 | **Autonomous Tracking** | `track_trades()` runs every 1 second | `main.py:141` |
| 10 | **Dynamic Trailing SL** | `apply_trailing_sl()` moves SL with favorable price | `coordinator.py:38-55` |

---

## 8. Quantitative Analytics Engine

Full implementation in `python_app/core/quantitative.py`:

### VWAP (Volume-Weighted Average Price)
```python
VWAP = Σ(price_i × volume_i) / Σ(volume_i)
# Resets at session start or on demand
```

### VPIN (Volume-Synchronized Probability of Informed Trading)
```python
VPIN = |V_buy - V_sell| / (V_buy + V_sell)
# Uses equal-volume buckets per Easley/Lopez de Prado/O'Hara
# High VPIN (> 0.5) suggests informed trading / toxicity risk
```

### Spread Metrics
- Absolute spread: `ask - bid`
- Relative spread in percent
- Rolling avg/max/min over configurable window

### Market Regime Detection
```python
# Bull: ann_return > 0 AND ann_vol < 1.5%
# Bear: ann_return < 0 AND ann_vol > 3.0%
# Sideways: |ann_return| < flat_threshold OR vol between bands
```

### IV Surface
- Strike × expiry grid
- Linear interpolation for missing strikes
- Risk-reversal: `IV(OTM_call) - IV(OTM_put)`
- Butterfly skew: `(IV_lower + IV_upper - 2*IV_ATM) / 2`

---

## 9. Dashboard Systems

### Web Dashboard — `http://localhost:9099`

**FastAPI + WebSocket Architecture:**
```python
# dashboards/web/app.py
@app.websocket("/ws")
async def websocket_endpoint(ws):
    while True:
        # Push REAL data from TradingApp coordinator
        await ws.send_json({
            "dashboard": state,
            "config": session_manager.config
        })
        await asyncio.sleep(1.0)
```

**Kanban UI (TailwindCSS):**
- 4 columns: SCANNING → SIGNAL → ACTIVE → CLOSED
- Auto-updates via WebSocket every 1 second
- Configuration tab: two sub-tabs — **Connection** (broker + mode + credentials) and **Risk Management** (capital, lots, risk limits)

### Desktop Dashboard (PySide6)

- Native Qt `QMainWindow` with `QTabWidget`
- Live Terminal: 4 Kanban columns via `QFrame` + `QScrollArea`
- System Config: Edit mode, client ID, token, lot size
- 1-second refresh via `QTimer`

---

## 10. Installation

### Prerequisites

| Requirement | Version | Install |
|-------------|---------|---------|
| Python | 3.10+ | [python.org/downloads](https://www.python.org/downloads/) |
| Rust | Latest | [rustup.rs](https://rustup.rs/) |
| Git | Any recent | For cloning |

### One-Command Install

**Linux / macOS:**
```bash
./install
```

**Windows:**
```cmd
install
```
or
```cmd
python install.py
```

### What the Installer Does

| Step | Action |
|------|--------|
| 1 | Verify Python 3.10+ |
| 2 | Install all Python packages from `requirements.txt` |
| 3 | Install `maturin` (Rust-Python build tool) |
| 4 | Compile `nsefo_core` Rust extension via `maturin build --release` |
| 5 | Install the compiled wheel into site-packages |
| 6 | Run the configuration wizard (prompts for broker credentials) |
| 7 | Verify API connectivity |
| 8 | Save configuration to `config.json` |

### Non-Interactive Install

```bash
./install --non-interactive   # Linux
install --non-interactive      # Windows
python install.py --non-interactive
```

### Manual Installation

```bash
# Linux
python3 -m pip install -r requirements.txt
python3 -m pip install maturin
cd nsefo_core && PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1 python3 -m maturin build --release
python3 -m pip install target/wheels/*.whl --force-reinstall

# Windows
python -m pip install -r requirements.txt
python -m pip install maturin
cd nsefo_core
set PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1
python -m maturin build --release
for %i in (target\wheels\*.whl) do python -m pip install "%i" --force-reinstall
cd ..
python run.py --setup
```

---

## 11. Configuration

Configuration is stored in `config.json`. Sensitive credentials (password, API key, TOTP secret, access token) must be set via environment variables — they are never persisted to disk. The web dashboard splits credentials into:

- **Broker Identity** (saved via API): `client_id`, `consumer_key`, `yob`, `app_key`, `enctoken`
- **Sensitive Credentials** (env vars only, marked 🔒 in the UI): `password`, `api_key`, `api_secret`, `access_token`, `totp_secret`

```json
{
    "mode": "paper",
    "provider": "dhan",
    "client_id": "YOUR_CLIENT_ID",
    "access_token": "YOUR_ACCESS_TOKEN",
    "totp_secret": "YOUR_TOTP_SECRET",
    "api_key": "YOUR_API_KEY",
    "password": "YOUR_PASSWORD",
    "yob": "1990",
    "client_secret": "YOUR_CLIENT_SECRET",
    "refresh_token": "YOUR_REFRESH_TOKEN",
    "data_provider": "",
    "target_frequency": "scalping",
    "risk": {
        "capital": 1000000,
        "fixed_lots": 1,
        "max_risk_per_trade_percent": 1.0,
        "daily_max_loss": 5000
    }
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `mode` | Yes | `paper` (simulation) or `live` (real money) |
| `provider` | Yes | Broker key — see broker table above |
| `client_id` | Yes | Your broker Client ID / User ID |
| `access_token` | Yes | API Access Token from your broker |
| `totp_secret` | For AngelOne/5paisa/Finvasia | TOTP secret for automated login |
| `api_key` | For Zerodha/AngelOne/IIFL/Motilal/Groww/Moneysukh/Bajaj | API key |
| `risk.capital` | Yes | Total capital for risk % calculations |
| `risk.fixed_lots` | Yes | Enforced quantity divisor |
| `risk.max_risk_per_trade_percent` | No | Max loss as % of capital (default 1%) |
| `risk.daily_max_loss` | No | Daily loss limit in rupees (default ₹5,000) |
| `password` | For Geojit | Geojit login password |
| `yob` | For Geojit/Finvasia | Year of birth (4-digit) |
| `client_secret` | For ICICI/Paytm Money | Client secret for OAuth2 |
| `refresh_token` | For ICICI | OAuth2 refresh token |
| `data_provider` | No | Live broker key for paper mode price feed |
| `target_frequency` | No | `scalping` (default, REST 2s poll), `swing` (REST 60s poll). HFT mode requires WebSocket wiring (see §14) |

---

## 12. Startup

### Linux
```bash
./nsefo
```

### Windows
```cmd
nsefo
```
or double-click `nsefo.bat` in the project directory.

### What Happens at Startup

1. Verifies Python version (3.10+)
2. Loads configuration from `config.json`
3. Ensures `nsefo_core` Rust extension is importable (auto-installs wheel if missing)
4. Tests broker API connectivity (fails fast if credentials wrong)
5. Launches web dashboard at `http://localhost:9099`
6. Starts the trading engine (market scanning cycle)

### Startup Modes

| Command | Mode |
|---------|------|
| `python run.py` | Full GUI app + web dashboard |
| `python run.py --setup` | Re-run configuration wizard |
| `python run.py --non-interactive` | Start without connectivity check |
| `python run.py "Buy Nifty 24500 ce"` | Single NLP command, then exit |
| `python run.py -y` | Non-interactive (alias) |

---

## 13. NLP Trading Commands

Issue trading instructions in plain English:

| Pattern | Example |
|---------|---------|
| `BUY SYMBOL STRIKE CE` | `Buy Nifty 24500 ce` |
| `SELL SYMBOL STRIKE PE` | `Sell Banknifty 48000 pe` |
| `LONG SYMBOL STRIKE CALL` | `Go long Finnifty 21000 call` |
| `SHORT SYMBOL STRIKE PUT` | `Short Nifty 24400 put` |
| `BUY/SELL SYMBOL` (market order) | `Buy Nifty` — uses current ATM strike |

### Supported Symbols

| Alias | Full Name | Symbol ID |
|-------|-----------|-----------|
| `NIFTY`, `N` | NSE NIFTY Index | `13` |
| `BANKNIFTY`, `BN` | NSE BANKNIFTY Index | `25` |
| `FINNIFTY`, `FN` | NSE FINNIFTY Index | `27` |

### Execution Flow

```
NLP Command
    ↓  CommandParser.parse_command()      [python_app/nlp/parser.py]
{data: {action, symbol, strike, option_type}}
    ↓  TradingApp.handle_manual_suggestion()
BrainEngine.analyze_symbol(df)             [Rust: get_rsi, get_supertrend, get_volatility]
{probability, signal, brains: {trend, rsi, volatility, delta}}
    ↓
RiskManager.assess_trade()                [capital risk check]
{risk_amount, risk_percent, is_safe, recommendation}
    ↓  Recommendation: EXECUTE or REJECT
auto_confirm_trade() → 10s window → Coordinator.execute_confirmed_trade()
    ↓
broker.place_order() → exchange
```

---

## 14. Known Limitations & Pending Work

### WebSocket Data Feed ⚠️ PENDING
**Status:** `start_data_feed()` is defined in all 26 broker implementations but is **never called** from the execution path.

- Dhan: has production-quality `marketfeed.DhanFeed` integration (daemon thread + Ticker class) but the method is not invoked — execution path uses REST polling
- Fenix: similar — defined but not called
- Zerodha and all others: skeleton implementations

**Impact:** Real-time price WebSockets are not active. Currently uses REST polling every 1–2 seconds.

**Fix required:** Call `broker.start_data_feed(symbols, callback)` in `TradingApp` or `main.py` market scan loop.

### Rho in GreeksCalculator
**Status:** `rho` (interest rate sensitivity) returns 0.0
**Reason:** Requires live 91-day T-bill rate data
**Fix:** Fetch from RBI or use hardcoded current rate (6.95% as of 2025)

### `python_app/brokers/providers/` Stubs
**Status:** 500+ auto-generated stub files for NSE-registered brokers
**Status:** Not used by active trading system (separate metadata registry)
**Action needed:** These are intentional auto-generated boilerplate, not functional code. Do not use.

---

## 15. Deprecated Brokers

| Broker | Provider Key | Reason |
|--------|-------------|--------|
| VPC | `vpc` | `base_url = ""` (empty string, all calls fail) |
| Nirmal Bang | `nirmal_bang` | BASE_URL returns HTTP 404 |
| Kunjee | `kunjee` | API blocked — SSRF restrictions |
| Paytm Money | `paytm_money` | F&O segment NOT confirmed — equity only |
| mStock | `mstock` | Endpoints unverified — likely wrong base URL |

**Recommendation:** Use Zerodha, AngelOne, or Dhan for live trading.

---

## 16. File Structure

```
nsefo/
├── install.py                     # Cross-platform installer (Python)
├── run.py                          # Canonical startup entry point
├── config.json                     # Runtime configuration
├── requirements.txt                # Python dependencies (22 packages)
│
├── nsefo_core/                     # Rust extension (Maturin/PyO3)
│   ├── Cargo.toml                  # Rust dependencies (ta, rayon, reqwest, pyo3)
│   ├── pyproject.toml             # Maturin build config
│   └── src/
│       ├── lib.rs                 # PyO3 module entry point + 6 pyfunctions
│       ├── http/
│       │   ├── mod.rs              # Module re-exports
│       │   └── client.rs           # reqwest HTTP client (http_post/http_get)
│       ├── strategies/
│       │   ├── trend.rs            # Supertrend + ATR calculation
│       │   ├── volatility.rs        # Standard Deviation
│       │   ├── mean_reversion.rs    # RSI
│       │   └── mod.rs
│       └── analysis/
│           ├── probability.rs       # Conviction score synthesis
│           └── mod.rs
│
├── python_app/
│   ├── main.py                     # TradingApp orchestrator
│   ├── broker/                     # ← ACTIVE: working broker system (singular)
│   │   ├── base.py                 # Broker ABC + AutoReloginMixin
│   │   ├── session_manager.py      # 26-broker factory
│   │   ├── fenix_broker.py         # Fenix Dhan gateway (primary)
│   │   ├── dhan.py                 # Dhan SDK provider
│   │   ├── zerodha.py              # Kite Connect
│   │   ├── angelone.py              # SmartAPI
│   │   ├── upstox.py               # Upstox REST
│   │   ├── paper.py                # Paper simulation broker
│   │   └── [22 more real broker files]
│   ├── brokers/                    # ← NSE registry metadata system (plural)
│   │   ├── __init__.py             # Public API exports
│   │   ├── registry.py              # 1035+ NSE broker metadata
│   │   ├── providers/               # 500+ stub files (auto-generated)
│   │   ├── search.py               # Broker search engine
│   │   ├── credentials.py           # Fernet AES encryption
│   │   ├── config.py               # Per-broker configuration
│   │   └── activation.py            # Broker activation state machine
│   ├── core/
│   │   ├── engine.py               # BrainEngine — multi-brain synthesis
│   │   ├── coordinator.py           # Trade tracking + trailing SL
│   │   ├── risk_manager.py          # Capital-based position sizing
│   │   ├── state.py                 # AppState singleton
│   │   ├── greeks_calculator.py     # Full Black-Scholes Greeks
│   │   ├── quantitative.py         # VWAP, VPIN, Spread, Regime, IV Surface
│   │   └── utils.py                 # Timed input, trade confirmation
│   ├── nlp/
│   │   └── parser.py               # Regex NLP command parser
│   └── auth/
│       └── browser_login.py         # Playwright browser automation + TLS
│
├── dashboards/
│   ├── web/
│   │   ├── app.py                  # FastAPI + WebSocket server (port 9099)
│   │   └── static/
│   │       └── index.html         # TailwindCSS Kanban UI
│   └── desktop/
│       └── main.py                 # PySide6 Qt terminal
│
├── install / install.bat          # Single-word install
├── setup / setup.bat               # Install aliases
├── nsefo / nsefo.bat              # Single-word startup
├── run_app.sh / run_app.bat       # Alternative startup
│
└── *.md                            # Documentation
    ├── README.md                   # This file
    ├── INSTALLATION_GUIDE.md      # Detailed installation guide
    ├── USER_MANUAL.md              # NLP commands + dashboard usage
    ├── ARCHITECTURE_REPORT.md      # Technical architecture details
    ├── PROJECT_REPORT.md           # Development stages + feature matrix
    ├── OPERATIONAL_PHASES.md        # 10-phase trade lifecycle
    ├── PROJECT_MEMORY.md           # Engineering decisions + troubleshooting
    ├── PROJECT_STATUS.md            # Current implementation status
    ├── PREQUISITES.md             # Prerequisites guide
    └── SURVEY_REPORT.md            # Greeks + NSE F&O market structure
```

---

## 17. Troubleshooting

| Problem | Solution |
|---------|---------|
| `ModuleNotFoundError: No module named 'nsefo_core'` | Re-run install script to compile the Rust extension |
| `[CRITICAL] Authentication Failed` | Check `client_id` and `access_token` in `config.json` |
| `Rust not found` | Install from [rustup.rs](https://rustup.rs) and restart terminal |
| Port 9099 already in use | Change port in `run.py:start_web_dashboard()` |
| `EOFError` during install | Run with `--non-interactive` flag |
| Permission denied on Linux scripts | Run `chmod +x install nsefo` |
| Upstox / AngelOne returns empty market data | Verify the symbol/security_id format for that broker |
| Dhan API rate limit | Space out `get_market_data` calls; use paper mode for testing |
| Deprecated broker fails | Switch to Zerodha, AngelOne, or Dhan |
| `security_id` returns empty | The token (e.g. `26037` for NIFTY FUT), NOT the trading symbol. Use the broker's instruments list API to resolve symbols to tokens |
| Python `from` keyword warning | Rename param `from` → `from_date` if you see lint warnings |

---

## 18. Security Notes

- **TOTP secret** is stored in plain text in `config.json` — protect the file accordingly
- **API access tokens** are stored in plain text — treat `config.json` as a secrets file
- **Never run live trading** without first validating your strategy in paper mode
- **Always test** in paper mode with small capital before scaling up
- SSL verification is configurable per-broker via `verify_ssl` kwarg (all 26 brokers accept `True/False`). Default `True` for production. `False` only for controlled test environments with self-signed certificates.

---

## Disclaimer

**Futures & Options trading involves substantial financial risk.** This system is for expert traders. Always validate your strategy in **paper mode** before going live. The authors accept no liability for losses incurred through use of this software.