"""
NSEFO Broker Integration API — Standalone Server (port 8888)
=============================================================
Serves ONLY the /api/* broker management endpoints.
No dashboard, no static files, no WebSocket.
Intended for programmatic/API consumers (curl, scripts, external services).
Authentication: X-NSEFO-SECRET header (same as dashboard).
"""
from fastapi import FastAPI
from python_app.broker_integration.api import router as broker_api

app = FastAPI(
    title="NSEFO Broker API",
    description="Broker management REST API — credentials never returned by GET",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(broker_api)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8888)