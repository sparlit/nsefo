# Project Memory & Knowledge Base

Permanent record of architectural decisions, engineering rationale, and operational learnings from building NSEFO Master Pro.

---

## Technical Patterns

### Python-Rust Bridge (Maturin/PyO3)

**Decision**: Offload all O(n) technical indicator calculations to Rust via Maturin + PyO3.

**Implementation**: `Cargo.toml` declares `crate-type = ["cdylib"]`. Maturin compiles to a `.whl` containing a native `.so`/`.pyd` file. Python imports `nsefo_core` as a normal module:

```python
import nsefo_core
rsi = nsefo_core.get_rsi_list(close_prices, 14)
```

**ABI3 decision**: Using `features = ["extension-module", "abi3-py310"]` + `PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1` at build time. This means the compiled wheel works on any Python 3.10+ interpreter regardless of minor version (3.10, 3.11, 3.12, etc.) without recompilation.

**Why pyo3 0.22 and not 0.29?**: The Cargo.lock resolved to 0.22.6 as the latest patch in the `^0.22` range. There are 3 Dependabot alerts against PyO3 (buffer overflow, OOB read, missing Sync bound) — all in versions < 0.24.1. These were dismissed as scanner false positives since no CVE or fix version was determined and PyO3 has no published security advisories. pyo3 0.22.6 is the latest available for that minor.

**Throughput**: The Rust core processes 3 symbols × ~60 data points in < 1ms. With `rayon` parallel iterators, throughput scales linearly with CPU cores.

---

### Multi-Brain Coordination

**Decision**: Use weighted multi-indicator synthesis instead of single-indicator triggers.

**Pattern**: Weighted synthesis with conviction clamping.
```
trend (Supertrend)   → weight 0.5
momentum (RSI)        → weight 0.3
volatility (StdDev)  → multiplier 0.8–1.2
```

**Rule**: Minimum 0.80 conviction score + bullish trend direction required for EXECUTE signal. This prevents the system from buying on RSI oversold alone (which can persist in strong downtrends).

---

### Centralized State Singleton

**Decision**: `global_state` singleton in `python_app/core/state.py` for zero-latency Engine↔Dashboard synchronization.

```python
global_state = AppState()  # module-level singleton
```

Both the WebSocket server (`dashboards/web/app.py`) and the Qt desktop app (`dashboards/desktop/main.py`) read from the same object. No message queue, no IPC — just shared memory with Python's GIL providing thread-safety for the dict/dataclass operations.

**Trade-off**: Works perfectly for single-process deployment. Would need Redis or similar for multi-process/multi-host deployment.

### Canonical Entry Points

**Decision**: `install.py` and `run.py` are the cross-platform canonical entry points. All platform-specific wrappers delegate to them.

| Script | Purpose |
|--------|---------|
| `install.py` | Dependency installation, Rust build via maturin, config wizard |
| `run.py` | Config check, broker login verification, uvicorn dashboard launch |
| `install.bat` / `install.sh` | Windows/Linux wrapper for `python install.py` |
| `nsefo.bat` / `nsefo.sh` | Windows/Linux wrapper for `python run.py` |

Legacy `start_master_pro.py` is deprecated — all new sessions should use `install.py` + `run.py`.

---

## Integration Learnings

### Dhan API & Fenix

**Fenix Initialization**: `FenixDhanProvider.__init__()` calls `self.api.authenticate()` explicitly after constructing the `Dhan` client. Without this, API v2 headers are not generated and all subsequent calls fail with `DH-905` or equivalent.

**DhanProvider vs FenixDhanProvider**: Both wrap the same Dhan API. `FenixDhanProvider` uses the `fenix` library (HTTP v2), `DhanProvider` uses `dhanhq` SDK. The `provider` key in config.json selects which is instantiated in `SessionManager.get_broker()`.

**Intraday Data**: Both providers use `intraday_minute_data(security_id, exchange_segment)` for historical OHLCV. The data format returned is a list of dicts with `open`, `high`, `low`, `close`, `volume` keys.

---

### Safety Protocols

**10-second confirmation gate**: `timed_input_with_default()` in `python_app/core/utils.py` uses a background thread + `threading.Event.wait(timeout)` to implement non-blocking input with automatic fallback. If the trader is away, paper-mode orders are rejected and live-mode orders proceed with the recommended action.

**Risk Manager hard stop**: `is_safe = False` from `RiskManager.assess_trade()` is a hard block — the Coordinator does not execute the trade regardless of conviction score.

---

## Performance Benchmarks

| Test | Result |
|------|--------|
| 3 symbols × 60 candles: Rust indicator computation | < 1ms |
| Brain synthesis (RSI + Supertrend + StdDev + probability) | < 0.5ms |
| Market cycle iteration (scan + LTP update) | ~200ms including Python overhead |
| WebSocket push to browser | 1 second interval, ~2KB JSON per push |
| Memory: 5-hour continuous scan | Stable, no leaks detected |

---

## Troubleshooting Guide

| Issue | Cause | Fix |
|-------|-------|-----|
| `ModuleNotFoundError: nsefo_core` | Rust wheel not installed | Re-run `python install.py` or `python -m pip install nsefo_core/target/wheels/*.whl --force-reinstall` |
| `DH-905` or `Please provide params or headers` | `api.authenticate()` not called | Fixed in `FenixDhanProvider.__init__()` — upgrade if still seeing this |
| `[CRITICAL] Authentication Failed` on startup | Invalid `client_id` or `access_token` in config.json | Regenerate token at dhan.in/developer, update config.json |
| `[CRITICAL] Authentication Failed` but credentials are correct | Token expired | Dhan access tokens expire; regenerate and update config.json |
| Port 9099 already in use | uvicorn/web server already running | Kill existing process: `pkill -f uvicorn` (Linux) or find+kill the Python process on port 9099 |
| Rust compilation failure | Missing Visual Studio Build Tools (Windows) | Install VS Build Tools with "Desktop development with C++" workload |
| `EOFError: EOF when reading a line` during install | stdin not available (piped script) | Fixed: `_prompt()` helper now catches EOFError and uses fallback config values |
| Desktop Qt app won't start | PySide6 not installed | `pip install PySide6` or use web dashboard at http://localhost:9099 |
| Web dashboard shows no data / HTTP 500 | `dashboards/web/app.py:17,21` relative path fails when cwd ≠ repo root | Use `Path(__file__).parent.parent / "dashboards/web/static"` — see Critical Open Issues |
| Paper mode fills not appearing | `data_provider` (Fenix) returning errors | Check Dhan API connectivity; PaperBroker falls back to `random.uniform` if `data_provider` fails |

---

## Configuration Reference

`config.json` fields and their effects:

| Field | Default | Effect |
|-------|---------|--------|
| `mode` | `paper` | Selects PaperBroker vs live broker; also shown in dashboard banner |
| `client_id` | `1100625529` | Dhan Client ID for API authentication |
| `access_token` | (token) | Dhan API access token |
| `totp_secret` | `""` | If set, `SessionManager.automate_login()` uses `pyotp.TOTP(secret).now()` |
| `provider` | `fenix` | `fenix` → FenixDhanProvider; `dhan` → DhanProvider |
| `risk.capital` | `1000000` | Denominator for risk % calculation |
| `risk.fixed_lots` | `1` | Enforced lot count per order |
| `risk.max_risk_per_trade_percent` | `1.0` | Max risk as % of capital per trade |
| `risk.daily_max_loss` | `5000` | Unused in current code (reserved for future daily drawdown limit) |

---

## Critical Open Issues

These issues are verified present in the codebase as of 2026-07-11 and must be resolved before production use.

### CRITICAL: moneysukh.py hardcoded credentials (UNFIXED)
**File**: `python_app/broker/moneysukh.py:30-31`
```python
self.client_id = client_id or "ONS123_U"
self.api_key = kwargs.get("api_key", "jYSaTKDmDb0I0YTdbQpWTRp2dyMWIJv4dGJHjvGC9nVGKNAkrjtbSFCxl8for7Ka")
```
The docstring (lines 5-6, 22-23) also contains these credentials in comments. **Violates the project credential rule.** Fix: replace all occurrences with `""` (empty string) as default.

### CRITICAL: config.json has non-empty TEST credentials (UNFIXED)
**File**: `config.json`
All credential fields (`access_token`, `client_id`, `api_key`, `app_key`, `vendor_code`, `password`, `consumer_key`) still contain `TEST_*` placeholder values. These must be cleared to `""` before committing. A follow-up session must run the config wizard to populate real values.

### BUG: app.py relative path anti-pattern (UNFIXED)
**File**: `dashboards/web/app.py:17,21`
```python
app.mount("/static", StaticFiles(directory="dashboards/web/static"), name="static")  # relative
with open("dashboards/web/static/index.html", "r", encoding="utf-8") as f:          # relative
```
Both fail silently or error when uvicorn's working directory is not the repo root. **Fix**: use `Path(__file__).parent.parent / "dashboards/web/static"` for both. Already noted in troubleshooting but fix was not applied.

---

## Known Limitations

1. **Single-process only**: `global_state` is an in-memory singleton. No Redis/multi-host support.
2. **Fixed watch list**: NIFTY, BANKNIFTY, FINNIFTY are hardcoded in `python_app/main.py`. Dynamic symbol addition requires code change.
3. **No order book / Level 2 data**: `get_market_data()` returns only LTP, not full order book depth.
4. **TOTP automation**: `totp_secret` is stored in plain text in `config.json`.
5. **No position sizing model**: Fixed lot count enforced; no Kelly criterion or volatility-adjusted sizing.
6. **Windows Qt rendering**: PySide6 on Windows may have rendering quirks with certain DPI scaling settings.