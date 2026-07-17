from fastapi import FastAPI, WebSocket, Request, Query, HTTPException, Header, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from typing import List, Dict, Any, Optional, Callable
import json
import asyncio
import os
import time
from pathlib import Path
from python_app.broker.session_manager import SessionManager
from python_app.core.secrets import get_secrets
from python_app.core.state import global_state
from python_app.broker_integration.api import router as broker_api

# Resolve paths relative to THIS file's location — works regardless of cwd
_BASE_DIR = Path(__file__).parent.parent
_STATIC_DIR = _BASE_DIR / "web" / "static"

app = FastAPI()

# ── In-memory rate limiting (broker API only — per-IP sliding window) ────────
# 60 req/min per IP — reject with 429 if exceeded.
# For production: replace with Redis-backed rate limiter (e.g. slowapi + Redis).
_rate_limit_window = 60.0
_rate_limit_max = 60
_rate_limit_store: Dict[str, List[float]] = {}


def _rate_limit_ip(request: Request) -> str:
    """Extract client IP from X-Forwarded-For or direct client host."""
    fwd = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    return fwd or (request.client.host if request.client else "unknown")


@app.middleware("http")
async def _broker_rate_limit_middleware(request: Request, call_next):
    """Apply rate limiting only to /api/* broker routes."""
    if request.url.path.startswith("/api"):
        client_ip = _rate_limit_ip(request)
        now = time.monotonic()
        ts = _rate_limit_store.get(client_ip, [])
        ts = [t for t in ts if (now - t) < _rate_limit_window]
        _rate_limit_store[client_ip] = ts
        if len(ts) >= _rate_limit_max:
            retry_after = int(_rate_limit_window - (now - ts[0])) + 1
            return JSONResponse(
                status_code=429,
                content={"error": "rate_limit_exceeded", "retry_after": retry_after},
                headers={"Retry-After": str(retry_after)},
            )
        ts.append(now)
        _rate_limit_store[client_ip] = ts
    return await call_next(request)

# Lazy init — TradingApp() triggers broker login, defer until first request
_trade_engine = None
_secrets = get_secrets(config_path=str(_BASE_DIR / "config.json"))

# ── Fields that are NEVER returned by GET /config ─────────────────────────────
_SENSITIVE_CONFIG_KEYS = frozenset({
    "access_token",
    "totp_secret",
    "api_key",
    "refresh_token",
    "client_secret",
    "password",
    "yob",
})

# ── Fields that can be updated via POST /config (non-sensitive only) ──────────
_CONFIGURABLE_VIA_API = frozenset({
    "mode",
    "provider",
    "target_frequency",
    "data_provider",
    "risk",
})


def _get_engine():
    global _trade_engine
    if _trade_engine is None:
        from python_app.main import TradingApp
        _trade_engine = TradingApp()
    return _trade_engine


# ── Auth dependency ────────────────────────────────────────────────────────────

async def verify_dashboard_secret(
    secret: Optional[str] = Header(None, alias="X-NSEFO-SECRET"),
) -> str:
    """
    Require the shared dashboard secret from the X-NSEFO-SECRET header.

    If NSEFO_DASHBOARD_SECRET is not set in the environment, the dashboard
    is in "open mode" — auth is disabled and a warning is logged.

    Returns the validated secret so callers can distinguish "open" from "authenticated".
    """
    expected = _secrets.dashboard_secret()
    if expected is None:
        # Auth not configured — log and permit (open mode for dev)
        import logging
        logging.getLogger("dashboard").warning(
            "NSEFO_DASHBOARD_SECRET not set — dashboard is UNPROTECTED. "
            "Set the env var to enable authentication."
        )
        return "open"
    if secret != expected:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing X-NSEFO-SECRET header.",
        )
    return secret


def _sanitize_config(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Strip all sensitive fields before returning config to the browser."""
    result = dict(cfg)
    for key in _SENSITIVE_CONFIG_KEYS:
        result.pop(key, None)
    return result


# ── Mount static files ─────────────────────────────────────────────────────────

app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


# ── Public routes (no auth required) ───────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def get_index():
    """Dashboard UI — always accessible (no credentials in the HTML page)."""
    index_path = _STATIC_DIR / "index.html"
    with open(index_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


# ── Authenticated routes ────────────────────────────────────────────────────────

@app.get("/config")
async def get_config(_: str = Depends(verify_dashboard_secret)):
    """
    Return the current config with all sensitive fields stripped.

    Sensitive fields (access_token, totp_secret, api_key, etc.) are never
    sent to the browser — they must be set via environment variables
    (NSEFO_CLIENT_ID, NSEFO_ACCESS_TOKEN, etc.).
    """
    raw = _secrets.as_config_dict()
    return JSONResponse(content=_sanitize_config(raw))


@app.post("/config")
async def update_config(
    request: Request,
    _: str = Depends(verify_dashboard_secret),
):
    """
    Update non-sensitive configuration fields.

    Sensitive credentials (access_token, api_key, totp_secret, etc.) CANNOT
    be updated via this endpoint — they must be set via environment variables.
    Attempting to set them is silently ignored.

    Configurable fields: mode, provider, target_frequency, data_provider, risk.
    """
    raw = await request.json()

    # Reject any attempt to set sensitive fields via the API
    for key in _SENSITIVE_CONFIG_KEYS:
        raw.pop(key, None)

    # Load existing config (from env vars + json), update only allowed fields
    existing = _secrets.as_config_dict()
    for key in _CONFIGURABLE_VIA_API:
        if key in raw:
            existing[key] = raw[key]

    # Persist only non-sensitive fields to config.json
    # Sensitive fields remain in env vars and are never written to disk
    session_manager = SessionManager(config_path=str(_BASE_DIR / "config.json"))
    session_manager.save_config(existing)
    _secrets.invalidate_cache()

    return {"status": "success", "updated": list(raw.keys())}


@app.get("/config/test")
async def test_connection(_: str = Depends(verify_dashboard_secret)):
    """Test broker connection with current credentials (from env vars)."""
    try:
        sm = SessionManager(config_path=str(_BASE_DIR / "config.json"))
        broker = sm.get_broker()
        ok = broker.login() if broker else False
        if ok:
            return {"login_ok": True}
        else:
            return {"login_ok": False, "error": "Login returned False — check credentials"}
    except Exception as e:
        return {"login_ok": False, "error": str(e)}


@app.get("/mode")
async def get_mode(_: str = Depends(verify_dashboard_secret)):
    """
    Return actual trading mode (detects silent live→paper fallback).
    Use this BEFORE placing orders to verify you're in the right mode.

    Response:
      configured: what the user set in config.json (live/paper)
      actual:     the actual broker mode after auth attempt
      is_live:    True if actually live trading
      is_paper:   True if actually paper trading
      warning:    non-empty string if configured != actual (DANGER alert)
    """
    try:
        sm = SessionManager(config_path=str(_BASE_DIR / "config.json"))
        sm.get_broker()  # triggers the live→paper fallback detection
        return JSONResponse(content=sm.get_actual_mode())
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket feed — authenticate via ?secret= query param on first connect.
    Falls back to open if NSEFO_DASHBOARD_SECRET is not set.
    """
    expected = _secrets.dashboard_secret()
    await websocket.accept()

    if expected is not None:
        try:
            first_msg = await websocket.receive_json()
            if first_msg.get("secret") != expected:
                await websocket.close(code=4001, reason="Invalid secret")
                return
        except Exception:
            await websocket.close(code=4001, reason="Auth required")
            return

    while True:
        trade_engine = _get_engine()
        sm = SessionManager(config_path=str(_BASE_DIR / "config.json"))
        sm.get_broker()  # Ensure mode is resolved
        actual_mode = sm.get_actual_mode()

        # Get active trades from global_state (sole source of truth)
        with global_state._lock:
            active_trades = list(global_state.kanban["ACTIVE"])

        raw_cfg = _secrets.as_config_dict()
        sanitized_cfg = _sanitize_config(raw_cfg)

        state = {
            "summary": {
                "capital": raw_cfg.get("risk", {}).get("capital", 0),
                "active_trades_count": len(active_trades),
                "mode": actual_mode["actual"],          # actual broker mode
                "mode_configured": actual_mode["configured"],  # what user configured
                "mode_warning": actual_mode["warning"],  # non-empty = danger alert
            },
            "kanban": {
                "SCANNING": trade_engine.watch_list,
                "ACTIVE": active_trades,
                "SIGNAL": list(global_state.kanban.get("SIGNAL", [])),
            },
        }

        await websocket.send_json({
            "dashboard": state,
            "config": sanitized_cfg,  # Never send credentials over WS
        })
        await asyncio.sleep(1.0)


@app.get("/brokers/search")
async def search_brokers(
    q: str = Query(..., min_length=1, max_length=200),
    limit: int = Query(20, ge=1, le=100),
    api_status: Optional[str] = Query(None),
    _: str = Depends(verify_dashboard_secret),
) -> JSONResponse:
    """
    Search NSE Clearing registered brokers.
    Authenticated — requires X-NSEFO-SECRET header.
    """
    from python_app.brokers.search import search_brokers as _do_search
    results = _do_search(q=q, limit=limit, api_status=api_status)
    return JSONResponse({
        "q": q,
        "count": len(results),
        "results": results,
    })


# ── Broker Management REST API ───────────────────────────────────────────────
app.include_router(broker_api)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9099)