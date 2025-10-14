"""Auto-M4B Dashboard API

FastAPI application providing read-only access to conversion queue,
metrics, and system health for monitoring and operational visibility.

Run with: python -m src.api.app
Or: uvicorn src.api.app:app --host 0.0.0.0 --port 8000
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import src modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Import routers
from src.api.routes import health, status, queue, metrics

# Initialize FastAPI app
app = FastAPI(
    title="Auto-M4B Dashboard API",
    version="1.0.0",
    description=(
        "Read-only API for monitoring Auto-M4B conversion queue and metrics. "
        "Provides endpoints for system status, queue management, and conversion history."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/api/v1/openapi.json"
)

# Add CORS middleware (will be configured in Phase 2.0.3)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Configure in Phase 2.0.3
    allow_credentials=True,
    allow_methods=["GET"],  # Read-only for Phase 2.0.2
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["health"])
app.include_router(status.router, tags=["status"])
app.include_router(queue.router, tags=["queue"])
app.include_router(metrics.router, tags=["metrics"])


@app.get("/")
def root():
    """API root endpoint"""
    return JSONResponse({
        "name": "Auto-M4B Dashboard API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/api/v1/health",
            "status": "/api/v1/status",
            "queue": "/api/v1/queue",
            "queue_detail": "/api/v1/queue/{book_key}",
            "recent_metrics": "/api/v1/metrics/recent",
            "docs": "/docs",
            "openapi": "/api/v1/openapi.json"
        }
    })


@app.on_event("startup")
async def startup_event():
    """Initialize API on startup"""
    from src.lib.config import cfg
    from src.lib.metrics import metrics

    # Initialize metrics
    try:
        with cfg.load_env(quiet=True):
            pass
        metrics.set_metrics_file(cfg.METRICS_FILE)
        print(f"✓ API started - Metrics file: {cfg.METRICS_FILE}")
    except Exception as e:
        print(f"⚠ Warning: Could not initialize metrics: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
