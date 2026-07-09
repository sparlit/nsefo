from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import JSONResponse
from typing import List, Dict, Any
import json
import asyncio
import os
from python_app.broker.session_manager import SessionManager

app = FastAPI()
session_manager = SessionManager()

# Enhanced dashboard state with Kanban columns
dashboard_state = {
    "summary": {
        "capital": 1000000,
        "total_pnl": 0.0,
        "active_trades_count": 0,
        "daily_drawdown": 0.0
    },
    "kanban": {
        "SCANNING": [
            {"id": "s1", "symbol": "NIFTY", "brain_status": "Analyzing", "progress": 85},
            {"id": "s2", "symbol": "BANKNIFTY", "brain_status": "Trend Search", "progress": 40}
        ],
        "SIGNAL": [
            {"id": "sig1", "symbol": "FINNIFTY", "side": "BUY", "prob": 0.88, "type": "Supertrend Break"}
        ],
        "CONFIRMATION": [],
        "ACTIVE": [],
        "CLOSED": []
    },
    "pnl_history": [0, 100, -50, 200, 450, 400, 600] # For charts
}

@app.get("/state")
def get_state():
    return dashboard_state

@app.post("/confirm_trade/{signal_id}")
def confirm_trade(signal_id: str):
    # Logic to move from SIGNAL -> CONFIRMATION -> ACTIVE
    return {"status": "ok"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        # Stream the full expert state
        await websocket.send_json({
            "dashboard": dashboard_state,
            "config": session_manager.config
        })
        await asyncio.sleep(0.5) # Fast updates for expert view

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
