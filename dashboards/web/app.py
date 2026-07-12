from fastapi import FastAPI, WebSocket, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from typing import List, Dict, Any, Optional
import json
import asyncio
import os
from pathlib import Path
from python_app.broker.session_manager import SessionManager

# Resolve paths relative to THIS file's location — works regardless of cwd
_BASE_DIR = Path(__file__).parent.parent
_STATIC_DIR = _BASE_DIR / "web" / "static"

app = FastAPI()
session_manager = SessionManager()
# Lazy init — TradingApp() triggers broker login, defer until first request
_trade_engine = None

def _get_engine():
    global _trade_engine
    if _trade_engine is None:
        from python_app.main import TradingApp
        _trade_engine = TradingApp()
    return _trade_engine

app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

@app.get("/", response_class=HTMLResponse)
async def get_index():
    index_path = _STATIC_DIR / "index.html"
    with open(index_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.get("/config")
def get_config():
    return session_manager.load_config()

@app.post("/config")
async def update_config(request: Request):
    new_config = await request.json()
    session_manager.save_config(new_config)
    # Reload the broker so new credentials take effect on next use
    session_manager.broker = None
    return {"status": "success"}

@app.get("/config/test")
def test_connection():
    """Test broker connection with current config."""
    try:
        broker = session_manager.get_broker()
        ok = broker.login() if broker else False
        if ok:
            return {"login_ok": True}
        else:
            return {"login_ok": False, "error": "Login returned False — check credentials"}
    except Exception as e:
        return {"login_ok": False, "error": str(e)}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        # Pushing REAL data from the Coordinator and Engine
        trade_engine = _get_engine()
        active_trades = [
            {"symbol": t['symbol'], "side": t['side'], "price": t['price']}
            for t in trade_engine.coordinator.active_trades.values()
        ]

        state = {
            "summary": {
                "capital": session_manager.config['risk']['capital'],
                "active_trades_count": len(active_trades),
                "mode": session_manager.config['mode']
            },
            "kanban": {
                "SCANNING": trade_engine.watch_list,
                "ACTIVE": active_trades,
                "SIGNAL": [] # Populated dynamically during scan
            }
        }

        await websocket.send_json({
            "dashboard": state,
            "config": session_manager.config
        })
        await asyncio.sleep(1.0)

@app.get("/brokers/search")
def search_brokers(
    q: str = Query(..., min_length=1, max_length=200, description="Search query"),
    limit: int = Query(20, ge=1, le=100, description="Max results"),
    api_status: Optional[str] = Query(None, description="Filter by api_status: verified, stub, deprecated, unknown, bank, all"),
) -> JSONResponse:
    """
    Search NSE Clearing registered brokers by name, provider key, or NSE member code.
    Returns brokers sorted by match quality (exact key > name exact > starts-with > word-match > substring).
    """
    from python_app.brokers.search import search_brokers as _do_search
    results = _do_search(q=q, limit=limit, api_status=api_status)
    return JSONResponse({
        "q": q,
        "count": len(results),
        "results": results,
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9099)
