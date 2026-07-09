from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from typing import List, Dict, Any
import json
import asyncio
import os
from python_app.broker.session_manager import SessionManager
# Global reference to the trading application instance
# In real prod, this is injected or managed via a singleton
from python_app.main import TradingApp

app = FastAPI()
session_manager = SessionManager()
trade_engine = TradingApp()

app.mount("/static", StaticFiles(directory="dashboards/web/static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def get_index():
    with open("dashboards/web/static/index.html") as f:
        return HTMLResponse(content=f.read())

@app.get("/config")
def get_config():
    return session_manager.load_config()

@app.post("/config")
async def update_config(request: Request):
    new_config = await request.json()
    session_manager.save_config(new_config)
    return {"status": "success"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        # Pushing REAL data from the Coordinator and Engine
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
