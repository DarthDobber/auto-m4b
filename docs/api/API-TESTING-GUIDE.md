# Auto-M4B API Testing Guide

**Version**: 1.0.0
**Phase**: 2.0.2 Implementation Complete

This guide provides instructions for testing the Auto-M4B Dashboard API endpoints.

---

## Prerequisites

The API requires:
- FastAPI and uvicorn installed (added to Pipfile)
- Auto-M4B configuration initialized
- Access to metrics.json and InboxState data

---

## Running the API

### Method 1: Standalone (Development)

```bash
# From project root
python3 -m src.api.app

# Or using uvicorn directly
uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload
```

The API will start on `http://localhost:8000`

###Method 2: Docker (Recommended for Testing)

**Will be implemented in Phase 2.0.3**

```bash
# Build image with API support
docker build -t darthdobber/auto-m4b:api-test .

# Run with API enabled
docker run -p 8000:8000 \
  -e API_ENABLED=Y \
  -v ~/audiobooks/inbox:/inbox \
  -v ~/audiobooks/converted:/converted \
  darthdobber/auto-m4b:api-test
```

---

## Testing Endpoints

### 1. Health Check

```bash
curl http://localhost:8000/api/v1/health | jq
```

**Expected Response**:
```json
{
  "status": "healthy",
  "timestamp": 1697215200.5,
  "checks": {
    "inbox_accessible": true,
    "converted_accessible": true,
    "m4b_tool_available": true,
    "disk_space_ok": true,
    "retry_queue_length": 0
  },
  "message": ""
}
```

**Status Values**:
- `healthy`: All checks pass
- `degraded`: Non-critical issues (low disk, high retry queue)
- `unhealthy`: Critical failures (directories not accessible, m4b-tool missing)

---

### 2. System Status

```bash
curl http://localhost:8000/api/v1/status | jq
```

**Expected Response**:
```json
{
  "version": "1.0.0",
  "timestamp": 1697215200.5,
  "uptime_seconds": 3650,
  "status": "idle",
  "config": {
    "max_retries": 3,
    "retry_base_delay": 60,
    "cpu_cores": 8,
    "sleep_time": 10
  },
  "metrics": {
    "lifetime": {
      "total": 47,
      "successful": 45,
      "failed": 2,
      "success_rate": 95.7,
      "avg_duration_seconds": 754,
      "total_bytes_processed": 8916992000,
      "first_run_timestamp": 1690000000.0
    },
    "session": {
      "started_at": 1697211550.5,
      "total": 3,
      "successful": 3,
      "failed": 0,
      "success_rate": 100.0,
      "total_bytes_processed": 685768000,
      "uptime_seconds": 3650
    },
    "timing": {
      "fastest_seconds": 192,
      "slowest_seconds": 1725,
      "average_seconds": 754
    }
  }
}
```

**Status Values**:
- `idle`: No books in queue
- `processing`: At least one book being converted
- `waiting`: Books in queue but none processing (retry delays)

---

### 3. Queue Overview

```bash
curl http://localhost:8000/api/v1/queue | jq
```

**Expected Response**:
```json
{
  "version": "1.0.0",
  "timestamp": 1697215200.5,
  "summary": {
    "total": 3,
    "pending": 1,
    "processing": 0,
    "failed": 1,
    "retrying": 1
  },
  "books": [
    {
      "key": "Harry Potter Book 1",
      "path": "/inbox/Harry Potter Book 1",
      "status": "ok",
      "size_bytes": 350000000,
      "last_updated": 1697215100.0,
      "hash": "abc123",
      "is_filtered": false,
      "series_info": null
    },
    {
      "key": "The Hobbit",
      "path": "/inbox/The Hobbit",
      "status": "needs_retry",
      "size_bytes": 420000000,
      "last_updated": 1697214000.0,
      "hash": "mno345",
      "is_filtered": false,
      "failed_reason": "Network timeout",
      "retry_count": 1,
      "max_retries": 3,
      "is_transient": true,
      "will_retry": true,
      "next_retry_at": 1697215260.0,
      "retry_countdown_seconds": 60,
      "series_info": null
    }
  ]
}
```

---

### 4. Single Book Detail

```bash
curl "http://localhost:8000/api/v1/queue/The%20Hobbit" | jq
```

**Expected Response**:
```json
{
  "version": "1.0.0",
  "timestamp": 1697215200.5,
  "book": {
    "key": "The Hobbit",
    "path": "/inbox/The Hobbit",
    "status": "needs_retry",
    "size_bytes": 420000000,
    "last_updated": 1697214000.0,
    "hash": "mno345",
    "hash_age_seconds": 1200,
    "is_filtered": false,
    "failed_reason": "Network timeout",
    "retry_count": 1,
    "max_retries": 3,
    "is_transient": true,
    "will_retry": true,
    "first_failed_time": 1697213000.0,
    "last_retry_time": 1697214000.0,
    "next_retry_at": 1697215260.0,
    "retry_countdown_seconds": 60,
    "retry_history": [],
    "estimated_duration_seconds": 600,
    "series_info": null
  }
}
```

**404 Response** (Book not found):
```json
{
  "detail": {
    "error": "book_not_found",
    "message": "Book 'Missing Book' not found in queue.",
    "suggestion": "Refresh queue via GET /api/v1/queue"
  }
}
```

---

### 5. Recent Metrics

```bash
curl "http://localhost:8000/api/v1/metrics/recent?limit=5" | jq
```

**Expected Response**:
```json
{
  "version": "1.0.0",
  "timestamp": 1697215200.5,
  "conversions": [
    {
      "book_name": "Harry Potter Book 1",
      "status": "success",
      "duration_seconds": 503,
      "timestamp": 1697214700.0,
      "timestamp_str": "2025-10-13 14:30:00",
      "file_size_bytes": 350000000,
      "error_message": ""
    },
    {
      "book_name": "The Hobbit",
      "status": "failed",
      "duration_seconds": 123,
      "timestamp": 1697213000.0,
      "timestamp_str": "2025-10-13 12:10:00",
      "file_size_bytes": 420000000,
      "error_message": "Network timeout"
    }
  ],
  "failures": {
    "total": 1,
    "recent": [
      {
        "book_name": "Broken Book",
        "error_message": "Invalid audio format",
        "timestamp": 1697210000.0,
        "timestamp_str": "2025-10-13 09:45:00",
        "retry_count": 0
      }
    ]
  }
}
```

**Query Parameters**:
- `limit` (int, default=10): Number of conversions to return (1-100)
- `include_failures` (bool, default=true): Include failed conversions

---

## Interactive API Documentation

FastAPI provides auto-generated interactive documentation:

### Swagger UI
```
http://localhost:8000/docs
```

### ReDoc
```
http://localhost:8000/redoc
```

### OpenAPI JSON
```
http://localhost:8000/api/v1/openapi.json
```

---

## Testing Checklist

### Manual Testing

- [ ] **Health Endpoint**
  - [ ] Returns `healthy` when all systems operational
  - [ ] Returns `degraded` with low disk space
  - [ ] Returns `unhealthy` when directories not accessible

- [ ] **Status Endpoint**
  - [ ] Returns correct metrics from ConversionMetrics
  - [ ] Shows `idle` when no books in queue
  - [ ] Shows `processing` when books are pending
  - [ ] Config snapshot includes max_retries, cpu_cores, etc.

- [ ] **Queue Endpoint**
  - [ ] Lists all books in matched_books
  - [ ] Summary counts match book list
  - [ ] Retry metadata populated for failed books
  - [ ] next_retry_at and countdown_seconds calculated correctly

- [ ] **Queue Detail Endpoint**
  - [ ] Returns 404 for non-existent books
  - [ ] hash_age_seconds reflects file stability
  - [ ] estimated_duration_seconds based on metrics
  - [ ] Series info populated for series books

- [ ] **Recent Metrics Endpoint**
  - [ ] Returns conversions in reverse chronological order
  - [ ] Respects `limit` parameter
  - [ ] Failures list populated correctly
  - [ ] timestamp_str is human-readable

---

## Performance Testing

### Response Time Targets

| Endpoint | Target | Notes |
|----------|--------|-------|
| `/api/v1/health` | < 100ms | No heavy computation |
| `/api/v1/status` | < 200ms | Reads metrics from JSON |
| `/api/v1/queue` | < 500ms | Scans inbox state |
| `/api/v1/queue/:book_key` | < 300ms | Single item lookup |
| `/api/v1/metrics/recent` | < 200ms | Reads from in-memory history |

### Load Testing (Optional)

```bash
# Install Apache Bench
sudo apt-get install apache2-utils

# Test status endpoint (100 requests, 10 concurrent)
ab -n 100 -c 10 http://localhost:8000/api/v1/status

# Test queue endpoint (50 requests, 5 concurrent)
ab -n 50 -c 5 http://localhost:8000/api/v1/queue
```

**Target**: All endpoints should handle 30 requests/minute (per planned rate limit)

---

## Troubleshooting

### Issue: ModuleNotFoundError: No module named 'fastapi'

**Solution**: Install dependencies
```bash
pip install fastapi uvicorn pydantic
# Or using pipenv
pipenv install
```

---

### Issue: API returns empty metrics

**Solution**: Ensure metrics.json exists
```bash
# Check metrics file location
python3 -c "from src.lib.config import cfg; print(cfg.METRICS_FILE)"

# If missing, run a conversion or create empty metrics
python3 -m src --status
```

---

### Issue: InboxState shows no books

**Solution**: Scan inbox directory
```bash
# Verify inbox directory exists and has books
ls -la /path/to/inbox

# API automatically scans on each request
# Check if books match MATCH_FILTER config
```

---

### Issue: Port 8000 already in use

**Solution**: Kill existing process or use different port
```bash
# Find process on port 8000
lsof -i :8000

# Kill process
kill <PID>

# Or use different port
uvicorn src.api.app:app --port 8001
```

---

## Next Steps

After manual testing completes:

1. **Phase 2.0.3**: Docker integration
   - Add API startup to entrypoint.sh
   - Configure API_ENABLED environment variable
   - Expose port 8000 in docker-compose.yml

2. **Phase 2.1.1**: Build dashboard UI
   - Create frontend consuming these endpoints
   - Implement auto-refresh with polling cadence
   - Add error handling for 404/500 responses

3. **Phase 2.1.2**: Add write operations
   - POST /api/v1/queue/:book_key/retry
   - POST /api/v1/queue/:book_key/skip
   - DELETE /api/v1/queue/:book_key

---

## Sample Test Script

```bash
#!/bin/bash
# test-api.sh - Quick API smoke test

API_URL="http://localhost:8000"

echo "Testing Auto-M4B API..."

echo "\n1. Health Check:"
curl -s "$API_URL/api/v1/health" | jq '.status'

echo "\n2. System Status:"
curl -s "$API_URL/api/v1/status" | jq '.status'

echo "\n3. Queue Summary:"
curl -s "$API_URL/api/v1/queue" | jq '.summary'

echo "\n4. Recent Conversions:"
curl -s "$API_URL/api/v1/metrics/recent?limit=3" | jq '.conversions | length'

echo "\n5. OpenAPI Spec:"
curl -s "$API_URL/api/v1/openapi.json" | jq '.info.version'

echo "\n✓ API tests complete"
```

---

## Contact & Support

- **API Documentation**: `docs/api/dashboard.md`
- **Implementation Guide**: `docs/api/PHASE-2.0.2-QUICKSTART.md`
- **Issues**: GitHub Issues with tag `[Phase 2.0 API]`
