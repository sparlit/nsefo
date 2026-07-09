from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from typing import List, Dict, Any
import json
import asyncio
import os
from python_app.broker.session_manager import SessionManager

app = FastAPI()
session_manager = SessionManager()

# Serve static files for the dashboard UI
app.mount("/static", StaticFiles(directory="dashboards/web/static"), name="static")

class LiveState:
    def __init__(self):
        self.state = {
            "summary": {"capital": 0, "total_pnl": 0.0, "active_trades_count": 0, "daily_drawdown": 0.0},
            "kanban": {"SCANNING": [], "SIGNAL": [], "CONFIRMATION": [], "ACTIVE": [], "CLOSED": []},
            "pnl_history": []
        }

live_state = LiveState()

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
        await websocket.send_json({
            "dashboard": live_state.state,
            "config": session_manager.config
        })
        await asyncio.sleep(0.5)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
