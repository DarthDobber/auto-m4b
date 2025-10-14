# Phase 2.0.2 Implementation Quickstart

**For Developers Implementing Dashboard API Endpoints**

This guide provides a fast-track path to implementing the 5 dashboard API endpoints defined in Phase 2.0.1.

---

## Prerequisites

1. **Read the Data Contract**: Review `docs/api/dashboard.md` (comprehensive specification)
2. **Read the Summary**: Review `docs/PHASE-2.0.1-SUMMARY.md` (executive summary)
3. **Understand Data Sources**:
   - `src/lib/metrics.py` - ConversionMetrics singleton
   - `src/lib/inbox_state.py` - InboxState singleton
   - `src/lib/retry.py` - Retry scheduler utilities
   - `src/lib/config.py` - Config singleton

---

## Quick Setup

### Step 1: Install FastAPI Dependencies

```bash
# Add to Pipfile or requirements.txt
pipenv install fastapi uvicorn[standard] pydantic

# Or with pip
pip install fastapi uvicorn[standard] pydantic
```

### Step 2: Create API Project Structure

```bash
mkdir -p src/api/routes src/api/schemas src/api/middleware src/api/utils
touch src/api/__init__.py
touch src/api/app.py
touch src/api/routes/{status,queue,metrics,health}.py
touch src/api/schemas/v1.py
touch src/api/utils/serializers.py
```

### Step 3: Smoke Test with Health Endpoint

**File**: `src/api/app.py`

```python
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(
    title="Auto-M4B Dashboard API",
    version="1.0.0",
    description="Read-only API for monitoring Auto-M4B conversion queue and metrics"
)

@app.get("/api/v1/health")
def health_check():
    return JSONResponse({
        "status": "healthy",
        "timestamp": time.time(),
        "checks": {
            "api_running": True
        },
        "message": "API is operational"
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**Test**:
```bash
# Terminal 1: Start API
python -m src.api.app

# Terminal 2: Test
curl http://localhost:8000/api/v1/health
```

Expected output:
```json
{"status": "healthy", "timestamp": 1697215200.5, "checks": {"api_running": true}, "message": "API is operational"}
```

---

## Implementation Order

### Endpoint 1: `/api/v1/health` (30 minutes)

**Priority**: P0 (smoke test, minimal dependencies)

**Implementation**:
```python
# src/api/routes/health.py
from fastapi import APIRouter
from pathlib import Path
import time

router = APIRouter()

@router.get("/api/v1/health")
def health_check():
    from src.lib.config import cfg

    checks = {
        "inbox_accessible": cfg.inbox_dir.exists() and cfg.inbox_dir.is_dir(),
        "converted_accessible": cfg.converted_dir.exists() and cfg.converted_dir.is_dir(),
        "m4b_tool_available": check_m4b_tool(),  # Implement this helper
        "disk_space_ok": check_disk_space(cfg.inbox_dir),  # Implement this helper
        "retry_queue_length": len(InboxState().failed_books)
    }

    status = "healthy" if all(checks.values()) else "degraded"

    return {
        "status": status,
        "timestamp": time.time(),
        "checks": checks,
        "message": "" if status == "healthy" else "Some checks failed"
    }
```

**Wire into app.py**:
```python
from src.api.routes.health import router as health_router
app.include_router(health_router)
```

---

### Endpoint 2: `/api/v1/status` (1 hour)

**Priority**: P0 (core metrics, straightforward)

**Schema** (`src/api/schemas/v1.py`):
```python
from pydantic import BaseModel

class LifetimeMetrics(BaseModel):
    total: int
    successful: int
    failed: int
    success_rate: float
    avg_duration_seconds: int
    total_bytes_processed: int
    first_run_timestamp: float

class SessionMetrics(BaseModel):
    started_at: float
    total: int
    successful: int
    failed: int
    success_rate: float
    total_bytes_processed: int
    uptime_seconds: int

class TimingMetrics(BaseModel):
    fastest_seconds: int
    slowest_seconds: int
    average_seconds: int

class Metrics(BaseModel):
    lifetime: LifetimeMetrics
    session: SessionMetrics
    timing: TimingMetrics

class StatusResponse(BaseModel):
    version: str = "1.0.0"
    timestamp: float
    uptime_seconds: int
    status: str  # "idle" | "processing" | "waiting"
    config: dict
    metrics: Metrics
```

**Route** (`src/api/routes/status.py`):
```python
from fastapi import APIRouter
from src.api.schemas.v1 import StatusResponse, Metrics, LifetimeMetrics, SessionMetrics, TimingMetrics
from src.lib.metrics import metrics
from src.lib.config import cfg
from src.lib.inbox_state import InboxState
import time

router = APIRouter()

@router.get("/api/v1/status", response_model=StatusResponse)
def get_status():
    inbox = InboxState()

    # Determine status
    if inbox.num_matched_ok > 0:
        status = "processing"
    elif inbox.has_failed_books:
        status = "waiting"
    else:
        status = "idle"

    return StatusResponse(
        timestamp=time.time(),
        uptime_seconds=metrics.session.uptime_seconds,
        status=status,
        config={
            "max_retries": cfg.MAX_RETRIES,
            "retry_base_delay": cfg.RETRY_BASE_DELAY,
            "cpu_cores": cfg.CPU_CORES,
            "sleep_time": cfg.SLEEP_TIME
        },
        metrics=Metrics(
            lifetime=LifetimeMetrics(
                total=metrics.lifetime_attempted,
                successful=metrics.lifetime_successful,
                failed=metrics.lifetime_failed,
                success_rate=round(metrics.lifetime_success_rate, 1),
                avg_duration_seconds=int(metrics.lifetime_avg_duration),
                total_bytes_processed=metrics.lifetime_bytes_processed,
                first_run_timestamp=metrics.first_run_timestamp
            ),
            session=SessionMetrics(
                started_at=metrics.session.started_at,
                total=metrics.session.conversions_attempted,
                successful=metrics.session.conversions_successful,
                failed=metrics.session.conversions_failed,
                success_rate=round(metrics.session.success_rate, 1),
                total_bytes_processed=metrics.session.total_bytes_processed,
                uptime_seconds=metrics.session.uptime_seconds
            ),
            timing=TimingMetrics(
                fastest_seconds=metrics.fastest_conversion_seconds,
                slowest_seconds=metrics.slowest_conversion_seconds,
                average_seconds=int(metrics.lifetime_avg_duration)
            )
        )
    )
```

---

### Endpoint 3: `/api/v1/queue` (2 hours)

**Priority**: P0 (core queue visibility)

**Schema**:
```python
class QueueSummary(BaseModel):
    total: int
    pending: int
    processing: int
    failed: int
    retrying: int

class SeriesInfo(BaseModel):
    parent_key: str
    book_index: int
    total_books: int
    is_complete: bool

class QueueBook(BaseModel):
    key: str
    path: str
    status: str
    size_bytes: int
    last_updated: float
    hash: str
    is_filtered: bool
    failed_reason: str | None = None
    retry_count: int | None = None
    max_retries: int | None = None
    is_transient: bool | None = None
    will_retry: bool | None = None
    next_retry_at: float | None = None
    retry_countdown_seconds: int | None = None
    series_info: SeriesInfo | None = None

class QueueResponse(BaseModel):
    version: str = "1.0.0"
    timestamp: float
    summary: QueueSummary
    books: list[QueueBook]
```

**Route**:
```python
from src.api.schemas.v1 import QueueResponse, QueueSummary, QueueBook, SeriesInfo
from src.lib.inbox_state import InboxState
from src.lib.retry import can_retry_now, should_retry
from src.lib.config import cfg

@router.get("/api/v1/queue", response_model=QueueResponse)
def get_queue():
    inbox = InboxState()
    inbox.scan()  # Ensure fresh data

    books = []
    for item in inbox.matched_books.values():
        book_data = {
            "key": item.key,
            "path": str(item.path),
            "status": item.status,
            "size_bytes": item.size,
            "last_updated": item.last_updated,
            "hash": item.hash,
            "is_filtered": item.is_filtered,
            "series_info": None  # TODO: Populate if item.is_maybe_series_book
        }

        # Add retry metadata if failed
        if item.status in ["failed", "needs_retry"]:
            can_retry, seconds_until = can_retry_now(
                item.last_retry_time,
                item.retry_count,
                cfg.RETRY_BASE_DELAY
            )

            book_data.update({
                "failed_reason": item.failed_reason,
                "retry_count": item.retry_count,
                "max_retries": cfg.MAX_RETRIES,
                "is_transient": item.is_transient_error,
                "will_retry": should_retry(
                    item.retry_count,
                    cfg.MAX_RETRIES,
                    item.is_transient_error,
                    cfg.RETRY_TRANSIENT_ERRORS
                ),
                "next_retry_at": item.last_retry_time + seconds_until if not can_retry else None,
                "retry_countdown_seconds": seconds_until if not can_retry else 0
            })

        books.append(QueueBook(**book_data))

    # Calculate summary
    summary = QueueSummary(
        total=len(books),
        pending=len([b for b in books if b.status in ["new", "ok"]]),
        processing=0,  # TODO: Implement active job tracking
        failed=len([b for b in books if b.status == "failed"]),
        retrying=len([b for b in books if b.status == "needs_retry"])
    )

    return QueueResponse(
        timestamp=time.time(),
        summary=summary,
        books=books
    )
```

---

### Endpoint 4: `/api/v1/queue/:book_key` (1 hour)

**Priority**: P1 (detail view, extends Endpoint 3 logic)

**Schema**:
```python
class RetryHistoryItem(BaseModel):
    attempt: int
    timestamp: float
    error: str
    duration_seconds: int

class QueueBookDetail(QueueBook):
    hash_age_seconds: int
    first_failed_time: float | None = None
    last_retry_time: float | None = None
    retry_history: list[RetryHistoryItem] = []
    estimated_duration_seconds: int | None = None

class QueueBookDetailResponse(BaseModel):
    version: str = "1.0.0"
    timestamp: float
    book: QueueBookDetail
```

**Route**:
```python
from fastapi import HTTPException

@router.get("/api/v1/queue/{book_key}", response_model=QueueBookDetailResponse)
def get_queue_book(book_key: str):
    inbox = InboxState()
    item = inbox.get(book_key)

    if not item:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "book_not_found",
                "message": f"Book '{book_key}' not found in queue.",
                "suggestion": "Refresh queue via GET /api/v1/queue"
            }
        )

    # Build response (similar to Endpoint 3, plus extras)
    book_data = {
        # ... copy from Endpoint 3 ...
        "hash_age_seconds": int(item.hash_age),
        "first_failed_time": item.first_failed_time if item.status in ["failed", "needs_retry"] else None,
        "last_retry_time": item.last_retry_time if item.status in ["failed", "needs_retry"] else None,
        "retry_history": [],  # TODO: Implement retry history tracking
        "estimated_duration_seconds": None  # TODO: Estimate based on file size and avg duration
    }

    return QueueBookDetailResponse(
        timestamp=time.time(),
        book=QueueBookDetail(**book_data)
    )
```

---

### Endpoint 5: `/api/v1/metrics/recent` (1 hour)

**Priority**: P1 (historical view, straightforward)

**Schema**:
```python
class RecentConversion(BaseModel):
    book_name: str
    status: str
    duration_seconds: int
    timestamp: float
    timestamp_str: str
    file_size_bytes: int
    error_message: str

class RecentFailure(BaseModel):
    book_name: str
    error_message: str
    timestamp: float
    timestamp_str: str
    retry_count: int

class RecentMetricsResponse(BaseModel):
    version: str = "1.0.0"
    timestamp: float
    conversions: list[RecentConversion]
    failures: dict[str, list[RecentFailure] | int]
```

**Route**:
```python
from fastapi import Query

@router.get("/api/v1/metrics/recent", response_model=RecentMetricsResponse)
def get_recent_metrics(
    limit: int = Query(default=10, ge=1, le=100),
    include_failures: bool = Query(default=True)
):
    from src.lib.metrics import metrics

    recent = metrics.get_recent_conversions(limit)
    conversions = [
        RecentConversion(
            book_name=r.book_name,
            status=r.status,
            duration_seconds=r.duration_seconds,
            timestamp=r.timestamp,
            timestamp_str=r.timestamp_str,
            file_size_bytes=r.file_size_bytes,
            error_message=r.error_message
        )
        for r in reversed(recent)  # Most recent first
    ]

    failures_list = [
        RecentFailure(
            book_name=f.book_name,
            error_message=f.error_message,
            timestamp=f.timestamp,
            timestamp_str=f.timestamp_str,
            retry_count=0  # TODO: Link to InboxItem retry_count
        )
        for f in reversed(metrics.get_recent_failures(5))
    ]

    return RecentMetricsResponse(
        timestamp=time.time(),
        conversions=conversions,
        failures={
            "total": len(failures_list),
            "recent": failures_list
        }
    )
```

---

## Testing Checklist

### Manual Testing (30 minutes per endpoint)

```bash
# Health
curl http://localhost:8000/api/v1/health | jq

# Status
curl http://localhost:8000/api/v1/status | jq

# Queue
curl http://localhost:8000/api/v1/queue | jq

# Single book (replace with real book key)
curl http://localhost:8000/api/v1/queue/Harry%20Potter%20Book%201 | jq

# Recent metrics
curl "http://localhost:8000/api/v1/metrics/recent?limit=5" | jq
```

### Unit Tests (1 hour total)

**Test Fixtures**:
```python
# tests/fixtures/metrics.py
from src.lib.metrics import ConversionMetrics, ConversionRecord

def mock_metrics():
    m = ConversionMetrics()
    m.lifetime_attempted = 10
    m.lifetime_successful = 8
    m.lifetime_failed = 2
    m.history = [
        ConversionRecord(
            book_name="Test Book",
            status="success",
            duration_seconds=300,
            timestamp=1697215200.0,
            file_size_bytes=100000000
        )
    ]
    return m
```

**Test Example**:
```python
# tests/api/test_status.py
from fastapi.testclient import TestClient
from src.api.app import app

client = TestClient(app)

def test_status_endpoint():
    response = client.get("/api/v1/status")
    assert response.status_code == 200

    data = response.json()
    assert data["version"] == "1.0.0"
    assert "metrics" in data
    assert "lifetime" in data["metrics"]
    assert data["metrics"]["lifetime"]["total"] >= 0
```

---

## Docker Integration (Phase 2.0.3)

### Dockerfile Updates

```dockerfile
# Add to existing Dockerfile
RUN pipenv install fastapi uvicorn[standard] pydantic

# Expose API port
EXPOSE 8000
```

### docker-compose.local.yml

```yaml
services:
  auto-m4b:
    ports:
      - "8000:8000"
    environment:
      - API_ENABLED=Y
      - API_HOST=0.0.0.0
      - API_PORT=8000
```

### entrypoint.sh Updates

```bash
# Start API in background if enabled
if [ "$API_ENABLED" = "Y" ]; then
    pipenv run uvicorn src.api.app:app --host "$API_HOST" --port "$API_PORT" &
fi

# Start main conversion loop
pipenv run python -m src
```

---

## Troubleshooting

### Issue: API returns stale data

**Cause**: InboxState not scanning before endpoint access

**Fix**: Add `inbox.scan()` before reading `inbox.matched_books`

---

### Issue: Pydantic validation errors

**Cause**: Data types don't match schema

**Fix**: Check schema types (e.g., `int` vs `float`, `str | None` vs `str`)

---

### Issue: Circular imports

**Cause**: Importing Config/InboxState at module level

**Fix**: Import inside endpoint functions:
```python
@router.get("/api/v1/status")
def get_status():
    from src.lib.config import cfg  # Import here, not at top
    # ...
```

---

## OpenAPI Documentation

Once all endpoints are implemented:

```bash
# Start API
python -m src.api.app

# Access auto-generated docs
open http://localhost:8000/docs  # Swagger UI
open http://localhost:8000/redoc  # ReDoc

# Download OpenAPI JSON
curl http://localhost:8000/openapi.json > docs/api/openapi.json
```

---

## Time Estimate Summary

| Task | Estimated Time |
|------|----------------|
| Setup + Health endpoint | 1 hour |
| Status endpoint | 1 hour |
| Queue endpoint | 2 hours |
| Queue detail endpoint | 1 hour |
| Recent metrics endpoint | 1 hour |
| Unit tests | 1 hour |
| Manual testing | 1 hour |
| **Total** | **8 hours** |

---

## Success Criteria

- [ ] All 5 endpoints return schema-compliant JSON
- [ ] Health endpoint checks inbox/converted accessibility
- [ ] Status endpoint shows correct metrics from ConversionMetrics
- [ ] Queue endpoint includes retry schedule for failed books
- [ ] Queue detail endpoint returns 404 for missing books
- [ ] Recent metrics endpoint respects `limit` parameter
- [ ] OpenAPI spec generated and accessible at `/docs`
- [ ] At least one endpoint covered by unit test

---

## Next Phase: 2.0.3

After Phase 2.0.2 is complete:
- Add rate limiting middleware
- Add CORS middleware for dashboard origin
- Docker Compose integration
- Environment variable configuration
- Developer documentation

---

## Questions?

- **Data Contract**: See `docs/api/dashboard.md`
- **Summary**: See `docs/PHASE-2.0.1-SUMMARY.md`
- **Roadmap**: See `PROJECT-ROADMAP-CODEX.md` Phase 2.0.2
