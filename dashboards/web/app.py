from fastapi import FastAPI, WebSocket
from typing import List, Dict, Any
import json
import asyncio

app = FastAPI()

# In-memory state for the dashboard
state = {
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
    return state

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        await websocket.send_json(state)
        await asyncio.sleep(1) # Stream state every second

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
