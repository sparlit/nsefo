from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import JSONResponse
from typing import List, Dict, Any
import json
import asyncio
import os

# Import session manager to allow real-time updates
from python_app.broker.session_manager import SessionManager

app = FastAPI()
session_manager = SessionManager()

# In-memory state for UI components
dashboard_state = {
    "capital": 100000,
    "pnl": 0,
    "running_trades": [],
    "closed_trades": [],
    "kanban": {
        "scanning": ["NIFTY", "BANKNIFTY", "FINNIFTY"],
        "signals": [],
        "awaiting_confirmation": [],
        "active": [],
        "closed": []
    },
    "progress": 0
}

@app.get("/")
def read_root():
    return {"message": "NSEFO Trading Dashboard API"}

@app.get("/state")
def get_state():
    return dashboard_state

@app.get("/config")
def get_config():
    return session_manager.load_config()

@app.post("/config")
async def update_config(request: Request):
    new_config = await request.json()
    session_manager.save_config(new_config)
    return {"status": "success", "message": "Configuration updated"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        # Merging dashboard stats with live config for the frontend
        data = {
            "dashboard": dashboard_state,
            "config": session_manager.config
        }
        await websocket.send_json(data)
        await asyncio.sleep(1)

if __name__ == "__main__":
    import uvicorn
    import sys
    # Add project root to sys.path
    sys.path.append(os.getcwd())
    uvicorn.run(app, host="0.0.0.0", port=8000)
