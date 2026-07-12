# Installation & Setup Guide

Complete step-by-step guide for installing and configuring NSEFO Master Pro on Windows and Linux.

---

## Prerequisites

### 1. Python 3.10+

Download from [python.org](https://www.python.org/downloads/) or use your system package manager.

**Verify:**
```cmd
python --version   # Windows
python3 --version  # Linux
```

### 2. Rust Toolchain

Required to compile the `nsefo_core` Rust extension.

**Install (Linux/macOS):**
```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

**Install (Windows):**
Download and run [rustup.rs](https://rustup.rs/)

**Verify:**
```bash
cargo --version
```

### 3. Dhan API Account

1. Sign up / log in at [https://www.dhan.in](https://www.dhan.in)
2. Navigate to **Profile → Developer Settings** (or `/developer`)
3. Create a new app to get your **Client ID** and **Access Token**
4. Enable **TOTP** and note your secret (used for automated login)

---

## Installation

### Linux / macOS

Run the single-word install command from the project root:

```bash
./install
```

The first run will prompt for:
- Dhan Client ID
- Dhan API Access Token
- Trading mode (`live` or `paper`)
- Operational capital
- Fixed lot count
- TOTP secret (optional)

It compiles the Rust core and verifies your Dhan API connection automatically.

**Non-interactive (skip prompts, use existing config.json):**
```bash
./install --non-interactive
```

### Windows

Open Command Prompt or PowerShell in the project directory and run:

```cmd
install
```

or equivalently:

```cmd
python install.py
```

Non-interactive mode:
```cmd
python install.py --non-interactive
```

---

## What the Installer Does

| Step | Action |
|------|--------|
| 1 | Verify Python 3.10+ and pip |
| 2 | Install `requirements.txt` (all Python packages) |
| 3 | Install `maturin` (Rust-Python build tool) |
| 4 | Compile `nsefo_core` Rust extension via `maturin build --release` |
| 5 | Install the compiled wheel into site-packages |
| 6 | Prompt for Dhan API credentials |
| 7 | Verify API connectivity (login/authenticate test) |
| 8 | Save configuration to `config.json` |

---

## Post-Installation Verification

After installation, start the application:

```cmd
nsefo          # Windows
./nsefo        # Linux
```

Look for `[OK] Connection to Dhan API Verified` in the output. If you see `[CRITICAL] Authentication Failed`, check that your `client_id` and `access_token` in `config.json` are correct.

**Verify the Rust extension is installed:**
```bash
python -c "import nsefo_core; print(nsefo_core.get_rsi_list([1,2,3,4,5], 2))"
```

---

## Manual Installation (Alternative)

If you prefer to install dependencies manually:

```bash
# Linux
python3 -m pip install -r requirements.txt
python3 -m pip install maturin
cd nsefo_core && PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1 python3 -m maturin build --release
python3 -m pip install target/wheels/*.whl --force-reinstall
```

```cmd
:: Windows
python -m pip install -r requirements.txt
python -m pip install maturin
cd nsefo_core
set PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1
python -m maturin build --release
for %i in (target\wheels\*.whl) do python -m pip install "%i" --force-reinstall
cd ..
```

Then configure manually:
```bash
python start_master_pro.py --setup
```

---

## Configuration File

Configuration is stored in `config.json` in the project root:

```json
{
    "mode": "paper",
    "client_id": "YOUR_CLIENT_ID",
    "access_token": "YOUR_ACCESS_TOKEN",
    "totp_secret": "YOUR_TOTP_SECRET",
    "provider": "fenix",
    "risk": {
        "capital": 1000000,
        "fixed_lots": 1,
        "max_risk_per_trade_percent": 1.0,
        "daily_max_loss": 5000.0
    }
}
```

| Field | Description |
|-------|-------------|
| `mode` | `paper` (simulation) or `live` (real execution) |
| `client_id` | Your Dhan Client ID |
| `access_token` | Your Dhan API Access Token |
| `totp_secret` | TOTP secret for automated login (optional) |
| `provider` | Broker provider: `fenix` (default) or `dhan` |
| `capital` | Total capital for risk % calculations |
| `fixed_lots` | Enforced lot size per order |

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: No module named 'nsefo_core'` | Re-run install or manually build the Rust core |
| `Permission denied: 'nsefo_core'` | Use a virtual environment; avoid system-wide install |
| `EOFError` during install | Run with `--non-interactive` flag or ensure stdin is available |
| `[CRITICAL] Authentication Failed` | Verify credentials in `config.json`; regenerate your access token |
| `Rust not found` | Install Rust from https://rustup.rs and restart terminal |
| Port 9099 already in use | Change port in `start_master_pro.py` or `run.py` |
| `maturin build` fails on Windows | Install Visual Studio Build Tools with C++ workload |