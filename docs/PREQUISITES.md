# NSEFO Master Pro — Prerequisites & Pre-Installation Guide

**Last Updated:** 2026-07-13

---

## System Requirements

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.10 or higher | Download from [python.org/downloads](https://www.python.org/downloads/) |
| Rust | Latest stable | Install via [rustup.rs](https://rustup.rs/) |
| Git | Any recent | For cloning the repository |
| OS | Windows 10/11 or Linux/macOS | All scripts work cross-platform |
| Memory | 4GB minimum | 8GB recommended for running dashboards + trading |
| Network | Stable internet | Required for broker API connectivity |

---

## Required Software

### 1. Python 3.10+

**Download:** [https://www.python.org/downloads/](https://www.python.org/downloads/)

During installation on Windows:
- ✅ Check "Add Python to PATH"
- ✅ Check "Install pip"

Verify:
```bash
python --version   # Should show 3.10 or higher
pip --version      # Should show pip 21+
```

### 2. Rust Toolchain

**Install:** [https://rustup.rs/](https://rustup.rs/)

```bash
# After installation, verify:
cargo --version    # Should show cargo 1.XX+
rustc --version    # Should show rustc 1.XX+
```

### 3. Git

**Download:** [https://git-scm.com/download](https://git-scm.com/download)

---

## Python Packages (Installed Automatically by `install.py`)

All dependencies are listed in `requirements.txt` and installed by `install.py`:

| Package | Version | Purpose |
|---------|---------|---------|
| `dhanhq` | Latest | Dhan API SDK |
| `fenix` | Latest | Fenix Dhan gateway |
| `kiteconnect` | Latest | Zerodha Kite Connect |
| `pydantic` | Latest | Data validation |
| `fastapi` | Latest | Web dashboard |
| `uvicorn` | Latest | ASGI server |
| `python-multipart` | Latest | Form data |
| `pyotp` | Latest | TOTP generation |
| `httpx` | Latest | HTTP client |
| `websockets` | Latest | WebSocket support |
| `pyside6` | Latest | Desktop dashboard |
| `pandas` | Latest | Data analysis |
| `numpy` | Latest | Numerical computing |
| `spacy` | Latest | NLP processing |
| `opengreeks` | Latest | Black-Scholes delta |
| `pycryptodome` | Latest | Encryption |
| `requests-oauthlib` | Latest | OAuth support |
| `selenium` | Latest | Browser automation |
| `trio` | Latest | Async I/O |
| `trio-websocket` | Latest | WebSocket |
| `websocket-client` | Latest | WebSocket client |
| `playwright` | Latest | Browser login automation |
| `curl_cffi` | Latest | TLS fingerprinting |
| `requests` | Latest | HTTP library |

---

## Optional: Browser Automation Packages

Required for brokers that use browser-based OAuth or form-post login (Zerodha, ICICI, Geojit, Edelweiss, Anand Rathi, etc.):

```bash
pip install playwright
playwright install chromium

pip install curl_cffi
```

Without these, enter tokens directly into `config.json`.

---

## Broker API Credentials

You need an active trading account with at least one supported broker.

### Broker API Status

| # | Broker | Provider Key | Auth Method | F&O | Status |
|---|--------|-------------|-------------|-----|--------|
| 1 | Dhan (Fenix) | `fenix` | client_id + access_token | ✅ | Working |
| 2 | Dhan (SDK) | `dhan` | client_id + access_token | ✅ | Working |
| 3 | Zerodha Kite | `zerodha` | api_key + access_token | ✅ | Working |
| 4 | AngelOne SmartAPI | `angelone` | client_id + password + TOTP | ✅ | Working |
| 5 | Upstox | `upstox` | client_id + access_token | ✅ | Working |
| 6 | Fyers API v2 | `fyers` | client_id + access_token | ✅ | Working |
| 7 | Kotak Securities | `kotak` | consumer_key + access_token | ✅ | Working |
| 8 | Kotak Neo | `kotak_neo` | consumer_key + access_token | ✅ | Working |
| 9 | 5paisa | `5paisa` | client_id + password + TOTP | ✅ | Working |
| 10 | IIFL Markets | `iifl` | api_key + password | ✅ | Working |
| 11 | Motilal Oswal | `motilal` | api_key + password | ✅ | Working |
| 12 | Finvasia (Shoonya) | `finvasia` | vendor_code + yob + TOTP | ✅ | Working |
| 13 | Choice Broking | `choice` | client_id + TOTP | ✅ | Working |
| 14 | AliceBlue | `aliceblue` | app_code + api_secret | ✅ | Working |
| 15 | Moneysukh | `moneysukh` | client_id + api_key | ✅ | Working |
| 16 | HDFC Securities | `hdfc` | client_id + access_token | ✅ | Working |
| 17 | ICICI Direct | `icici` | OAuth2 + refresh_token | ✅ | Working |
| 18 | SBI Securities | `sbi` | app_name + access_token | ✅ | Working |
| 19 | Bajaj Financial | `bajaj` | api_key + client_id + access_token | ✅ | Working |
| 20 | Geojit | `geojit` | client_id + password + yob | ✅ | Working |
| 21 | Mirae Asset Sharekhan | `sharekhan` | client_id + access_token | ✅ | Working |
| 22 | Anand Rathi | `anand_rathi` | client_id + access_token | ✅ | Working |
| 23 | Edelweiss | `edelweiss` | client_id + access_token | ✅ | Working |
| 24 | Axis Direct | `axis_direct` | client_id + access_token | ✅ | Working |
| 25 | Groww | `groww` | api_key + access_token | ✅ | Working |
| 26 | Master Trust | `master_trust` | app_key | ✅ | Working |
| 27 | PaperBroker | `paper` | N/A | ✅ | Working |
| — | **VPC** ⚠️ | `vpc` | — | ❌ | DEPRECATED — empty base_url |
| — | **Nirmal Bang** ⚠️ | `nirmal_bang` | — | ❌ | DEPRECATED — HTTP 404 |
| — | **Kunjee** ⚠️ | `kunjee` | — | ❌ | DEPRECATED — API blocked |
| — | **Paytm Money** ⚠️ | `paytm_money` | — | ❌ | DEPRECATED — equity only |
| — | **mStock** ⚠️ | `mstock` | — | ❌ | DEPRECATED — unverified endpoints |

---

## How to Get Broker Credentials

### Dhan (Recommended — Primary Tested Broker)

1. Sign up at [https://www.dhan.in](https://www.dhan.in)
2. Go to **Profile → Developer Settings**
3. Create an app to get your **Client ID** and **Access Token**
4. For TOTP-enabled auto-login: note your **TOTP secret**

### Zerodha

1. Sign up at [https://kite.trade](https://kite.trade)
2. Go to **Console → Create App**
3. Get your **API Key** and **API Secret**
4. Complete OAuth flow to get **Access Token**

### AngelOne

1. Sign up at [https://www.angelone.in](https://www.angelone.in)
2. Go to **SmartAPI → Create App**
3. Get **API Key**, **Client ID**, **Password**
4. Set up **TOTP Secret** for auto-login

---

## Environment Variables (Optional)

Set these in your shell profile for test scripts:

```bash
# Dhan
export DHAN_CLIENT_ID="your_client_id"
export DHAN_ACCESS_TOKEN="your_access_token"

# Zerodha (for test_zerodha_live.py)
export ZERODHA_API_KEY="your_api_key"
export ZERODHA_ACCESS_TOKEN="your_access_token"

# Dashboard
export DASHBOARD_PORT=9099

# Trading mode
export NSEFO_MODE=paper
```

On Windows:
```cmd
set ZERODHA_API_KEY=your_api_key
set ZERODHA_ACCESS_TOKEN=your_access_token
```

---

## Pre-Installation Checklist

Before running `install.py`:

- [ ] Python 3.10+ is installed and `python --version` works
- [ ] Rust is installed and `cargo --version` works
- [ ] Git is installed
- [ ] You have broker API credentials ready
- [ ] You have a code editor (VS Code recommended)
- [ ] Network connection is stable

---

## Installation Methods

### Method 1: One-Command Install (Recommended)

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

### Method 2: Non-Interactive (Skip Prompts)

```bash
./install --non-interactive   # Linux
install --non-interactive      # Windows
python install.py --non-interactive
```

### Method 3: Manual Installation

See [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md) for detailed step-by-step manual installation.

---

## Post-Installation Checklist

After running `install.py`, verify:

- [ ] Python packages installed: `pip list | grep -E "dhan|fenix|kiteconnect|pyside6|fastapi"`
- [ ] Rust extension built: `python -c "import nsefo_core; print(nsefo_core.get_rsi_list([1,2,3,4,5], 3))"`
- [ ] `config.json` created with your broker credentials
- [ ] `python run.py` starts without errors
- [ ] Web dashboard accessible at `http://localhost:9099`
- [ ] Broker connection shows `[OK]` in terminal

---

## Troubleshooting Installation

| Problem | Solution |
|---------|---------|
| `Python 3.10+ required` | Download from [python.org/downloads](https://www.python.org/downloads/) |
| `Rust not found` | Install from [rustup.rs](https://rustup.rs/) |
| `ModuleNotFoundError: nsefo_core` | Re-run `install.py` to compile Rust extension |
| `Permission denied (Linux)` | `chmod +x install nsefo` |
| `Port 9099 in use` | Change port in `run.py:start_web_dashboard()` |
| `EOFError during install` | Run with `--non-interactive` flag |
| `Connectivity check failed` | Verify credentials in `config.json` |