# NSEFO Master Pro

**Professional-grade automated trading system for NSE Options & Futures.**

Powered by a hybrid **Python + Rust** architecture — Python for orchestration, Rust (`nsefo_core`) for sub-millisecond indicator calculations. Multi-brain synthesis (Trend + Momentum + Volatility + Delta), NLP command interface ("Buy Nifty 24500 ce"), dual dashboards, and 30 broker integrations.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Features](#2-features)
3. [Architecture](#3-architecture)
4. [Prerequisites](#4-prerequisites)
5. [Installation (One Command)](#5-installation-one-command)
6. [Startup (One Command)](#6-startup-one-command)
7. [NLP Trading Commands](#7-nlp-trading-commands)
8. [Dashboard](#8-dashboard)
9. [Configuration](#9-configuration)
10. [Trading Modes](#10-trading-modes)
11. [Supported Brokers](#11-supported-brokers)
12. [File Structure](#12-file-structure)
13. [Troubleshooting](#13-troubleshooting)
14. [Security Notes](#14-security-notes)

---

## 1. Project Overview

| Attribute | Detail |
|-----------|--------|
| **Type** | Automated algorithmic trading system |
| **Market** | NSE Futures & Options (F&O) |
| **Languages** | Python 3.10+ (orchestration), Rust (performance core) |
| **License** | Expert trading — see disclaimer |
| **Build** | Maturin + PyO3 (Rust Python extension) |
| **Brokers** | 30 Indian brokers supported |

**Why hybrid Python + Rust?** Options analysis requires real-time computation of RSI, Supertrend, ATR, Standard Deviation, and probability synthesis on every market tick. Python handles orchestration, broker abstraction, and state; Rust (`nsefo_core`) handles all O(n) numerical calculations via the `ta` crate with `rayon` parallel processing.

---

## 2. Features

- **Rust Performance Core** — `nsefo_core` compiled via Maturin/PyO3; RSI, Supertrend, ATR, StdDev, probability — all sub-millisecond
- **Multi-Brain Synthesis** — Four expert brains synthesize conviction scores before any order:
  - **Trend Brain**: Supertrend (10-period ATR, 3× multiplier) → UP/DOWN/NEUTRAL
  - **Momentum Brain**: RSI (14-period) → overbought/oversold conviction
  - **Volatility Brain**: Standard Deviation (20-period) → volatility-adjusted multiplier
  - **Options Brain**: Black-Scholes Delta → strike selection efficiency
- **NLP Command Interface** — Issue orders in plain English:
  - `Buy Nifty 24500 ce`
  - `Go long Banknifty 48000 pe`
  - `Short Finnifty 21000 calls`
- **30 Broker Integrations** — Dhan, Fenix, Zerodha, AngelOne, Upstox, Fyers, and 24 more
- **Dual Dashboards** — Web (FastAPI + WebSocket, port 9099) + Desktop (PySide6 Qt)
- **Paper + Live Modes** — Simulate first, switch to live execution
- **Risk Manager** — Capital-based position sizing, max 1% risk per trade
- **Trailing Stop-Loss** — Dynamic SL that follows favorable price movement
- **10-Second Confirmation Gate** — Non-blocking timed confirmation with fallback
- **Cross-Platform** — Single-command install and launch on Windows and Linux

---

## 3. Architecture

```
┌──────────────────────────────────────────────────────┐
│              TradingApp  (python_app/main.py)         │
│  ┌──────────┬───────────┬──────────┬───────────────┐  │
│  │Command   │ Brain     │Coordinator│Risk          │  │
│  │Parser    │ Engine    │          │Manager       │  │
│  │(NLP)     │(synthesis)│(tracking)│(capital)     │  │
│  └────┬─────┴─────┬─────┴─────┬────┴──────┬────────┘  │
│       │           │           │           │           │
│  Broker Abstraction Layer                          │
│  ┌────────────────────────────────────────────────┐ │
│  │FenixDhanProvider │ DhanProvider │ PaperBroker │ │
│  │ + 27 other brokers (Zerodha, AngelOne, etc.)  │ │
│  └────────────────────────────────────────────────┘ │
│                      │                               │
│         ┌────────────┴────────────┐                  │
│         │     nsefo_core (Rust)   │  ← PyO3/Maturin  │
│         │  get_rsi_list           │                  │
│         │  get_supertrend         │                  │
│         │  get_volatility_list    │                  │
│         │  calculate_probability   │                  │
│         └──────────────────────────┘                  │
└──────────────────────────────────────────────────────┘
```

### Trade Lifecycle (10 Phases)

| Phase | Name | What Happens |
|-------|------|-------------|
| 1 | **Integrity** | `broker.login()` verifies API credentials |
| 2 | **Market Data** | `get_market_data()` + `get_historical_data()` fetches OHLCV |
| 3 | **Neural Analysis** | Rust computes RSI, Supertrend, ATR, StdDev |
| 4 | **Signal Convergence** | `calculate_probability()` synthesizes conviction score |
| 5 | **Greeks Verification** | `opengreeks.black_scholes.delta()` computes option Delta |
| 6 | **Risk Assessment** | `RiskManager.assess_trade()` checks capital exposure |
| 7 | **Confirmation Gate** | 10-second `timed_input_with_default()` waits for user |
| 8 | **Order Execution** | `broker.place_order()` dispatches to exchange |
| 9 | **Autonomous Tracking** | `track_trades()` runs every 1 second |
| 10 | **Dynamic Trailing SL** | `apply_trailing_sl()` moves SL with favorable price |

---

## 4. Prerequisites

### Required Software

| Requirement | Version | Install |
|-------------|---------|---------|
| Python | 3.10+ | [python.org/downloads](https://www.python.org/downloads/) |
| Rust | Latest | [rustup.rs](https://rustup.rs/) |
| Git | Any recent | For cloning the repository |

### Broker API Account

You need an API account from one of the supported brokers. For Dhan (primary tested broker):

1. Sign up at [https://www.dhan.in](https://www.dhan.in)
2. Go to **Profile → Developer Settings**
3. Create an app to get your **Client ID** and **Access Token**
4. For TOTP-enabled auto-login: note your **TOTP secret**

### Optional Software (Browser Login)

For brokers requiring browser-based OAuth or form-post login (Zerodha, ICICI, Geojit, Anand Rathi, etc.), install browser automation packages. Without these, enter tokens directly into `config.json`.

| Package | Purpose | Install |
|---------|---------|---------|
| `playwright` | Stealth browser token extraction | `pip install playwright && playwright install chromium` |
| `curl_cffi` | TLS fingerprint (Chrome JA3 impersonation) | `pip install curl_cffi` |

---

## 5. Installation (One Command)

### Linux / macOS

```bash
./install
```

### Windows

```cmd
install
```

or equivalently:

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

### Non-Interactive Install (Skip Prompts)

```bash
./install --non-interactive   # Linux
install --non-interactive      # Windows
python install.py --non-interactive  # Alternative
```

This uses existing `config.json` without prompting.

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

## 6. Startup (One Command)

### Linux

```bash
./nsefo
```

### Windows

```cmd
nsefo
```

or double-click `nsefo.bat` in the project directory.

### What the Startup Does

1. Verifies Python version
2. Loads configuration from `config.json`
3. Ensures `nsefo_core` Rust extension is importable
4. Tests broker API connectivity (fails fast if credentials are wrong)
5. Launches the web dashboard at `http://localhost:9099`
6. Starts the trading engine (market scanning cycle)

**NLP command-only mode (no daemon, no dashboard):**
```bash
python run.py "Buy Nifty 24500 ce"
```

---

## 7. NLP Trading Commands

Give trading instructions in plain English:

| Pattern | Example |
|---------|---------|
| `BUY SYMBOL STRIKE CE` | `Buy Nifty 24500 ce` |
| `SELL SYMBOL STRIKE PE` | `Sell Banknifty 48000 pe` |
| `LONG SYMBOL STRIKE CALL` | `Go long Finnifty 21000 call` |
| `SHORT SYMBOL STRIKE PUT` | `Short Nifty 24400 put` |
| `BUY/SELL SYMBOL` (market order) | `Buy Nifty` — uses current ATM strike |

### Supported Symbols

| Alias | Full Name |
|-------|-----------|
| `NIFTY`, `N` | NSE NIFTY Index |
| `BANKNIFTY`, `BN` | NSE BANKNIFTY Index |
| `FINNIFTY`, `FN` | NSE FINNIFTY Index |

### Supported Option Types

| Input | Interpreted As |
|-------|---------------|
| `CE`, `CALL`, `CALLS` | Call Option |
| `PE`, `PUT`, `PUTS` | Put Option |

### Execution Flow

```
NLP Command
    ↓  CommandParser.parse_command()      [python_app/nlp/parser.py]
{action, symbol, strike, option_type}
    ↓  TradingApp.handle_manual_suggestion()
BrainEngine.analyze_symbol(df)           [Rust: get_rsi, get_supertrend, get_volatility]
{probability, signal, brains: {trend, rsi, volatility, delta}}
    ↓
RiskManager.assess_trade()               [capital risk check]
{risk_amount, risk_percent, is_safe, recommendation}
    ↓  Recommendation: EXECUTE or REJECT
auto_confirm_trade() → 10s window → Broker.place_order()
```

### Example Output

```
MASTER PRO EXPERT ANALYSIS
{
  "symbol": "NIFTY",
  "last_price": 248.50,
  "probability": 0.847,
  "fixed_lots": 1,
  "quantity": 50,
  "brains": {
    "trend": "UP",
    "rsi": 42.3,
    "volatility": "NORMAL",
    "delta": 0.512
  },
  "risk": {
    "risk_amount": 12.43,
    "risk_percent": 0.0012,
    "is_safe": true,
    "recommendation": "PROCEED"
  },
  "decision": "EXECUTE"
}
```

---

## 8. Dashboard

### Web Dashboard — `http://localhost:9099`

Four Kanban columns, auto-updated via WebSocket every second:

| Column | Contents |
|--------|----------|
| **SCANNING** | Symbols being monitored by the neural engine |
| **SIGNAL** | High-conviction setups (probability > 0.90) |
| **ACTIVE** | Open positions with current P&L |
| **CLOSED** | Completed trades for the session |

**Configuration tab** lets you edit `config.json` fields live — trading mode, broker credentials, capital, lot size.

### Desktop Dashboard (PySide6)

Launched automatically when PySide6 is available. Native Qt application with the same Kanban + Config tabs.

---

### Browser Login (Playwright)

For brokers requiring browser-based OAuth or form-post authentication (Zerodha, ICICI,
Geojit, Edelweiss, Anand Rathi, etc.), NSEFO uses Playwright to automate token extraction:

```bash
pip install playwright && playwright install chromium
pip install curl_cffi  # TLS fingerprinting (Chrome impersonation)
```

The browser-login engine (`python_app/auth/browser_login.py`) opens a stealth browser,
navigates to the broker login URL, intercepts the OAuth redirect or API response,
extracts the access token, and closes — returning a `TokenInfo` object to the session manager.
Token refresh and auto-relogin on 401 are handled automatically.

### Manual Token Setup

If Playwright is unavailable, obtain your access token manually from your broker's API
dashboard and paste it directly into `config.json` (`access_token` field). This is the
default and works for all brokers without Playwright dependency.

---

## 9. Configuration

Configuration is stored in `config.json` in the project root.

```json
{
    "mode": "paper",
    "provider": "zerodha",
    "client_id": "YOUR_CLIENT_ID",
    "access_token": "YOUR_ACCESS_TOKEN",
    "totp_secret": "YOUR_TOTP_SECRET",
    "api_key": "YOUR_API_KEY",
    "password": "YOUR_PASSWORD",
    "yob": "1990",
    "client_secret": "YOUR_CLIENT_SECRET",
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
| `provider` | Yes | Broker key — see [Supported Brokers](#11-supported-brokers) |
| `client_id` | Yes | Your broker Client ID / User ID |
| `access_token` | Yes | API Access Token from your broker |
| `totp_secret` | No | TOTP secret for automated login (AngelOne, Finvasia, etc.) |
| `api_key` | Varies | Required for Zerodha, AngelOne, IIFL, Motilal, Groww, Moneysukh, Bajaj |
| `risk.capital` | Yes | Total capital for risk % calculations |
| `risk.fixed_lots` | Yes | Enforced quantity divisor (lot size) |
| `risk.max_risk_per_trade_percent` | No | Max loss as % of capital per trade (default 1%) |
| `risk.daily_max_loss` | No | Daily loss limit in rupees (default ₹5,000) |
| `password` | Geojit only | Geojit login password (form-urlencoded POST, not OAuth) |
| `yob` | Geojit only | Year of birth (4-digit, e.g. `1990`) — used for Geojit login |
| `client_secret` | Paytm Money | Client secret for Paytm Money API authentication |
| `data_provider` | No | Live broker key for paper mode price feed (e.g. `zerodha`) |
| `target_frequency` | No | Trading frequency: `scalping` (default), `swing`, `hft` — controls poll intervals and WebSocket vs REST |

---

## 10. Trading Modes

### Paper Mode (`"mode": "paper"`)

- Order fills are simulated with virtual balance
- Market data: real prices from your broker's data feed
- Useful for validating strategy before going live
- Set in `config.json` or via the dashboard Configuration tab

### Live Mode (`"mode": "live"`)

- Real orders sent to the exchange via your broker's API
- Requires valid API credentials with live trading enabled
- All risk controls (position sizing, trailing SL) still active
- `[CRITICAL]` displayed in terminal when running live

### Switching Modes

Edit `config.json`:
```json
"mode": "paper"    // Simulation
"mode": "live"     // Real execution
```

Or use the Configuration tab in the web dashboard.

### Target Frequency

Controls order execution cadence and polling intervals. Set via `target_frequency` in `config.json`:

| Mode | Poll Interval | Order Style | WebSocket |
|------|-------------|-------------|-----------|
| `scalping` (default) | 2 seconds | Fast REST, batch-ready | Optional |
| `swing` | 60 seconds | Intraday holds | No |
| `hft` | < 50ms | WebSocket-native, minimal latency | Required |

- **Scalping**: Ideal for NIFTY/BANKNIFTY intraday. REST polling every 2s. Paper-first by default.
- **Swing**: Overnight holds. REST polling every 60s. Lower API call volume.
- **HFT**: Requires WebSocket-enabled broker (Zerodha Kite, Dhan, AngelOne). Sub-50ms latency target.
  HFT mode also requires the Rust `nsefo_core` compiled extension for sub-millisecond indicator calculations.

---

## 11. Supported Brokers

| # | Broker | Provider Key | Auth Method | API Docs |
|---|--------|-------------|-------------|----------|
| 1 | **Dhan** (Fenix SDK) | `fenix` | client_id + access_token | [dhan.in](https://www.dhan.in/developer) |
| 2 | **Dhan** (SDK) | `dhan` | client_id + access_token | [dhanhq](https://pypi.org/project/dhanhq/) |
| 3 | **Zerodha Kite** | `zerodha` | api_key + access_token | [kite.trade](https://kite.trade) |
| 4 | **AngelOne SmartAPI** | `angelone` | client_id + password + TOTP | [smartapi](https://smartapi.angelone.in) |
| 5 | **Upstox** | `upstox` | client_id + access_token | [upstox.com](https://upstox.com/developer) |
| 6 | **Fyers API v2** | `fyers` | client_id + access_token | [fyers.in](https://api.fyers.in) |
| 7 | **Kotak Securities** | `kotak` | consumer_key + access_token | [kotaksecurities.com](https://api.kotaksecurities.com) |
| 8 | **Kotak Neo** | `kotak_neo` | consumer_key + access_token | — |
| 9 | **5paisa** | `5paisa` | client_id + password + TOTP | — |
| 10 | **IIFL Markets** | `iifl` | api_key + password | — |
| 11 | **Motilal Oswal** | `motilal` | api_key + password | — |
| 12 | **Finvasia (Shoonya)** | `finvasia` | vendor_code + yob + TOTP | — |
| 13 | **Choice Broking** | `choice` | client_id + TOTP | — |
| 14 | ~~**VPC**~~ ⚠️ DEPRECATED | `vpc` | client_id + access_token | api.vpcapis.com returns 404 |
| 15 | **AliceBlue** | `aliceblue` | app_code + api_secret | — |
| 16 | **Moneysukh (ONUS Capital)** | `moneysukh` | client_id + api_key | — |
| 17 | **HDFC Securities** | `hdfc` | client_id + access_token | — |
| 18 | **ICICI Direct** | `icici` | api_key + client_secret + access_token + refresh_token | OAuth2 with auto token refresh |
| 19 | **SBI Securities** | `sbi` | app_name + access_token | — |
| 20 | **Bajaj Financial** | `bajaj` | api_key + client_id + access_token | — |
| 21 | **Geojit** | `geojit` | client_id + password + yob | — |
| 22 | **Mirae Asset Sharekhan** | `sharekhan` | client_id + access_token | — |
| 23 | **Anand Rathi** | `anand_rathi` | client_id + access_token | — |
| 24 | **Edelweiss** | `edelweiss` | client_id + access_token | — |
| 25 | ~~**Nirmal Bang**~~ ⚠️ DEPRECATED | `nirmal_bang` | client_id + access_token + api_key | BASE_URL returns HTTP 404 — no public REST API. Verify endpoint from browser trace or use Zerodha/AngelOne/Dhan. |
| 26 | **Axis Direct** | `axis_direct` | client_id + access_token | — |
| 27 | **Groww** | `groww` | api_key + access_token | — |
| 28 | ~~**Paytm Money**~~ ⚠️ DEPRECATED | `paytm_money` | client_id + access_token | F&O segment not supported — equity only |
| 29 | ~~**Kunjee**~~ ⚠️ DEPRECATED | `kunjee` | client_id + access_token | api.kunjee.in unverified — SSRF blocked |
| 30 | **Master Trust** | `master_trust` | app_key | — |

> **Note**: WebSocket real-time data feeds are implemented for Dhan and Fenix. Other brokers use polling-based `get_market_data()` calls. WebSocket implementations for remaining brokers are documented but require broker-specific SDK integration.

---

## 12. File Structure

```
nsefo/
├── install.py                 # Cross-platform installer (Python)
├── run.py                      # Cross-platform startup (Python)
├── config.json                 # Runtime configuration
├── requirements.txt             # Python dependencies
│
├── nsefo_core/                 # Rust extension (Maturin/PyO3)
│   ├── Cargo.toml              # Rust project config
│   ├── pyproject.toml          # Maturin build config
│   └── src/
│       ├── lib.rs              # PyO3 module entry point
│       ├── analysis/
│       │   └── probability.rs  # Conviction score synthesis
│       └── strategies/
│           ├── trend.rs        # Supertrend + ATR
│           ├── volatility.rs   # Standard Deviation
│           └── mean_reversion.rs  # RSI
│
├── python_app/
│   ├── main.py                 # TradingApp orchestrator
│   ├── broker/
│   │   ├── base.py             # Abstract Broker class
│   │   ├── session_manager.py   # Broker factory (30 providers)
│   │   ├── fenix_broker.py     # Fenix Dhan gateway (primary)
│   │   ├── dhan.py             # Dhan SDK provider
│   │   ├── paper.py            # Paper/simulation broker
│   │   └── [24 other broker files]
│   ├── core/
│   │   ├── engine.py           # BrainEngine — multi-brain synthesis
│   │   ├── coordinator.py      # Trade tracking + trailing SL
│   │   ├── risk_manager.py     # Capital-based position sizing
│   │   ├── state.py            # Global AppState singleton
│   │   ├── utils.py            # Timed input, trade confirmation
│   │   └── greeks_calculator.py # Black-Scholes Greeks
│   └── nlp/
│       └── parser.py           # Regex-based NLP command parser
│
├── dashboards/
│   ├── web/
│   │   ├── app.py              # FastAPI + WebSocket
│   │   └── static/index.html   # Kanban UI (TailwindCSS)
│   └── desktop/
│       └── main.py             # PySide6 Qt terminal
│
├── install                     # Linux single-word install
├── setup                       # Linux install alias
├── nsefo                       # Linux single-word startup
├── run_app.sh                  # Linux alternative startup
│
├── install.bat                 # Windows single-word install
├── setup.bat                   # Windows install alias
├── nsefo.bat                   # Windows single-word startup
├── run_app.bat                 # Windows alternative startup
│
└── *.md                        # Documentation
    ├── README.md               # This file
    ├── INSTALLATION_GUIDE.md   # Detailed installation guide
    ├── USER_MANUAL.md          # NLP commands + dashboard usage
    ├── ARCHITECTURE_REPORT.md  # Technical architecture details
    ├── PROJECT_REPORT.md      # Development stages + feature matrix
    ├── OPERATIONAL_PHASES.md   # 10-phase trade lifecycle
    ├── PROJECT_MEMORY.md       # Engineering decisions + troubleshooting
    ├── BENCHMARK_REPORT.md     # Performance benchmarks
    ├── SURVEY_REPORT.md        # Greeks + NSE F&O market structure
    └── survey/                 # Indian broker API research
```

---

## 13. Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: No module named 'nsefo_core'` | Re-run install script to compile the Rust extension |
| `[CRITICAL] Authentication Failed` | Check `client_id` and `access_token` in `config.json` |
| `Rust not found` | Install from [rustup.rs](https://rustup.rs) and restart terminal |
| Port 9099 already in use | Change port in `run.py:start_web_dashboard()` |
| `EOFError` during install | Run with `--non-interactive` flag |
| Permission denied on Linux scripts | Run `chmod +x install nsefo` |
| Upstox / AngelOne returns empty market data | Verify the symbol/security_id format for that broker |
| Dhan API rate limit | Space out `get_market_data` calls; use paper mode for testing |
| VPC / Kunjee / Paytm Money broker fails | These brokers are ⚠️ DEPRECATED — API base URL is 404 or unverified. Use Zerodha, AngelOne, or Dhan instead |
| `security_id` returns empty | `security_id` is the exchange TOKEN (e.g. `26037` for NIFTY FUT), NOT the trading symbol. Use the broker's instruments list API to resolve symbols to tokens |
| Python `from` keyword warning | Some brokers use `from` as a dict key in `get_historical_data()` params, shadowing Python's reserved keyword. This is a code smell but not a functional bug — rename to `from_date` if you see lint warnings |

---

## 14. Security Notes

- **TOTP secret** is stored in plain text in `config.json` — protect the file accordingly
- **API access tokens** are stored in plain text — treat `config.json` as a secrets file
- SSL verification configurable per-broker via `verify_ssl` kwarg (all 30 brokers accept `verify_ssl=True/False`). Default `True` for production. `False` only for controlled test environments with self-signed certificates. Use `verify_ssl=False` only when a broker's TLS certificate chain is incomplete.
- **Never run live trading** without first validating your strategy in paper mode
- **Always test** in paper mode with small capital before scaling up

---

## Disclaimer

**Futures & Options trading involves substantial financial risk.** This system is for expert traders. Always validate your strategy in **paper mode** before going live. The authors accept no liability for losses incurred through use of this software.