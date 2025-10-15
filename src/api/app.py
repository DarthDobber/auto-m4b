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

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Import routers
from src.api.routes import health, status, queue, metrics

# Set up templates and static files
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
static_path = Path(__file__).parent / "static"

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

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],  # Added POST for Phase 2.1.2 (re-queue operations)
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Include routers
app.include_router(health.router, tags=["health"])
app.include_router(status.router, tags=["status"])
app.include_router(queue.router, tags=["queue"])
app.include_router(metrics.router, tags=["metrics"])


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Dashboard UI"""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/legacy", response_class=HTMLResponse)
async def legacy_dashboard(request: Request):
    """Legacy dashboard UI"""
    return templates.TemplateResponse("dashboard_legacy.html", {"request": request})


@app.get("/api")
def api_root():
    """API root endpoint"""
    return JSONResponse({
        "name": "Auto-M4B Dashboard API",
        "version": "1.0.0",
        "endpoints": {
            "dashboard": "/",
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
