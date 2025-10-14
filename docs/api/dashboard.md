# Auto-M4B Dashboard API Data Contract

**Version**: 1.0.0
**Status**: Phase 2.0.1 - Specification
**Last Updated**: 2025-10-13

---

## Overview

This document defines the data contract for Auto-M4B's dashboard API endpoints. These endpoints provide read-only access to queue status, active jobs, retry schedules, and conversion metrics for monitoring and operational visibility.

**Design Principles**:
- Read-only access for Phase 2.0 (write operations in Phase 2.1+)
- Versioned payloads to support future enhancements without breaking changes
- Polling-friendly with caching hints and rate limit guidance
- Self-documenting with clear field semantics and enum values

---

## Data Sources

### 1. **ConversionMetrics** (`src/lib/metrics.py`)

**Current Fields**:
- `lifetime_attempted`, `lifetime_successful`, `lifetime_failed` (int)
- `lifetime_duration_seconds`, `lifetime_bytes_processed` (int)
- `fastest_conversion_seconds`, `slowest_conversion_seconds` (int)
- `first_run_timestamp`, `last_updated_timestamp` (float)
- `history`: list of `ConversionRecord` (last 100 conversions)
  - `book_name`, `status`, `duration_seconds`, `timestamp`, `file_size_bytes`, `error_message`
- `session`: `SessionStats` (current uptime)
  - `started_at`, `conversions_attempted`, `conversions_successful`, `conversions_failed`
  - `total_duration_seconds`, `total_bytes_processed`

**Persistence**: JSON file at `converted/metrics.json` or `/config/metrics.json`

**Dashboard Needs**:
- ✅ Success rate, failure count, average duration
- ✅ Session vs lifetime breakdown
- ✅ Recent conversion history with error messages
- ⚠️ **Gap**: No "currently processing" indicator (see InboxState)
- ⚠️ **Gap**: No ETA for active jobs (requires real-time progress)

---

### 2. **InboxState** (`src/lib/inbox_state.py`)

**Current Fields**:
- `_items`: dict of `InboxItem` keyed by relative path
  - `key`, `hash`, `path`, `size`, `last_updated`, `hash_age`
  - `status`: `"new" | "ok" | "needs_retry" | "failed" | "gone"`
  - `failed_reason`, `retry_count`, `last_retry_time`, `first_failed_time`, `is_transient_error`
  - `is_filtered`, `is_maybe_series_parent`, `series_books`
- `loop_counter`, `ready`, `banner_printed`
- Methods: `ok_books`, `failed_books`, `matched_ok_books`, `filtered_books`, `has_failed_books`

**Persistence**: In-memory only (reconstructed on startup from disk scan)

**Dashboard Needs**:
- ✅ Queue overview (pending, processing, failed counts)
- ✅ Retry schedule (next retry time per book)
- ✅ Failed book details (error message, retry attempts, transient flag)
- ⚠️ **Gap**: No "currently processing" book tracking (status is state-machine, not real-time)
- ⚠️ **Gap**: No progress percentage or ETA within active conversion

---

### 3. **Retry Scheduler** (`src/lib/retry.py`)

**Current Functions**:
- `categorize_error(error_message) -> "transient" | "permanent"`
- `calculate_backoff_delay(retry_count, base_delay, max_delay) -> int`
- `should_retry(retry_count, max_retries, is_transient, retry_transient_errors) -> bool`
- `can_retry_now(last_retry_time, retry_count, base_delay) -> (bool, seconds_until)`
- `format_retry_message(book_name, retry_count, max_retries, error_type, next_retry_seconds) -> str`

**Dashboard Needs**:
- ✅ Next retry timestamp for each failed book
- ✅ Human-readable retry countdown
- ✅ Error type classification
- ✅ No gaps identified

---

### 4. **Config** (`src/lib/config.py`)

**Relevant Fields**:
- `MAX_RETRIES`, `RETRY_TRANSIENT_ERRORS`, `RETRY_BASE_DELAY`, `MOVE_FAILED_BOOKS`
- `CPU_CORES`, `SLEEP_TIME`, `ON_COMPLETE`
- Directories: `inbox_dir`, `converted_dir`, `failed_dir`

**Dashboard Needs**:
- ✅ Configuration snapshot for context
- ✅ No gaps identified

---

## Endpoint Specifications

### 1. `GET /api/v1/status`

**Purpose**: Snapshot of overall system health and conversion metrics.

**Response Schema**:

```json
{
  "version": "1.0.0",
  "timestamp": 1697215200.5,
  "uptime_seconds": 3650,
  "status": "idle" | "processing" | "waiting",
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

**Field Semantics**:
- `status`: Current activity state
  - `"idle"`: No books in queue, waiting for new arrivals
  - `"processing"`: At least one book actively converting
  - `"waiting"`: Books in queue but none currently processing (e.g., waiting for retry delay)
- `uptime_seconds`: Time since container started (from `session.started_at`)
- `metrics.lifetime.first_run_timestamp`: Timestamp of very first conversion ever recorded
- `metrics.session.started_at`: Timestamp when current session began

**Caching**: Response can be cached for `SLEEP_TIME` seconds (typically 10s)

**Example Use Cases**:
- Dashboard header showing success rate and uptime
- Alert if `status == "waiting"` for too long (suggests retry delays or failures)

---

### 2. `GET /api/v1/queue`

**Purpose**: Detailed view of books in the processing queue and their states.

**Response Schema**:

```json
{
  "version": "1.0.0",
  "timestamp": 1697215200.5,
  "summary": {
    "total": 8,
    "pending": 5,
    "processing": 1,
    "failed": 2,
    "retrying": 0
  },
  "books": [
    {
      "key": "Harry Potter Book 1",
      "path": "/inbox/Harry Potter Book 1",
      "status": "pending",
      "size_bytes": 350000000,
      "last_updated": 1697215100.0,
      "hash": "abc123def456",
      "is_filtered": false,
      "series_info": null
    },
    {
      "key": "Broken Book",
      "path": "/inbox/Broken Book",
      "status": "failed",
      "size_bytes": 120000000,
      "last_updated": 1697210000.0,
      "hash": "xyz789ghi012",
      "is_filtered": false,
      "failed_reason": "Invalid audio format: corrupted MP3 header",
      "retry_count": 3,
      "max_retries": 3,
      "is_transient": false,
      "will_retry": false,
      "next_retry_at": null,
      "series_info": null
    },
    {
      "key": "The Hobbit",
      "path": "/inbox/The Hobbit",
      "status": "needs_retry",
      "size_bytes": 420000000,
      "last_updated": 1697214000.0,
      "hash": "mno345pqr678",
      "is_filtered": false,
      "failed_reason": "Network timeout during conversion",
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

**Field Semantics**:
- `status`: One of `"new"`, `"ok"`, `"needs_retry"`, `"failed"`, `"gone"`
  - `"new"`: Just discovered, not yet processed
  - `"ok"`: Ready for processing (or successfully completed in prior run)
  - `"needs_retry"`: Failed but eligible for retry
  - `"failed"`: Permanently failed or max retries exceeded
  - `"gone"`: Previously tracked but no longer in inbox
- `is_transient`: Error categorization (transient errors are retryable)
- `will_retry`: Computed field (`status == "needs_retry" && retry_count < max_retries && is_transient`)
- `next_retry_at`: Unix timestamp when retry will occur (null if not retrying)
- `retry_countdown_seconds`: Seconds until retry (convenience field for UI)
- `series_info`: Object with `parent_key` and `books_in_series` if book is part of series, else `null`

**Caching**: Response can be cached for `SLEEP_TIME / 2` seconds (typically 5s) to balance responsiveness with load

**Example Use Cases**:
- Dashboard table listing all books with status badges
- Retry countdown timer for failed books
- Filtering by status or error type

---

### 3. `GET /api/v1/queue/:book_key`

**Purpose**: Detailed payload for a single book, including full error history and retry schedule.

**Response Schema**:

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
    "hash": "mno345pqr678",
    "hash_age_seconds": 1200,
    "is_filtered": false,
    "failed_reason": "Network timeout during conversion",
    "retry_count": 1,
    "max_retries": 3,
    "is_transient": true,
    "will_retry": true,
    "first_failed_time": 1697213000.0,
    "last_retry_time": 1697214000.0,
    "next_retry_at": 1697215260.0,
    "retry_countdown_seconds": 60,
    "retry_history": [
      {
        "attempt": 1,
        "timestamp": 1697213000.0,
        "error": "Network timeout during conversion",
        "duration_seconds": 120
      }
    ],
    "series_info": null,
    "estimated_duration_seconds": null
  }
}
```

**Field Semantics**:
- `hash_age_seconds`: Time since hash last changed (indicates file stability)
- `retry_history`: List of past retry attempts with errors
- `estimated_duration_seconds`: Predicted conversion time based on file size and historical averages (null if no data)

**Caching**: Response can be cached for `SLEEP_TIME` seconds unless `status == "needs_retry"` (then refresh every 5s)

**Example Use Cases**:
- Detailed view when clicking a book in the dashboard
- Manual intervention UI showing full error context

---

### 4. `GET /api/v1/metrics/recent`

**Purpose**: Recent conversion history for dashboard timeline/chart.

**Query Parameters**:
- `limit` (optional, default: 10): Number of recent conversions to return
- `include_failures` (optional, default: true): Include failed conversions in results

**Response Schema**:

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
      "error_message": "Network timeout during conversion"
    }
  ],
  "failures": {
    "total": 1,
    "recent": [
      {
        "book_name": "Broken Book",
        "error_message": "Invalid audio format: corrupted MP3 header",
        "timestamp": 1697210000.0,
        "timestamp_str": "2025-10-13 09:45:00",
        "retry_count": 3
      }
    ]
  }
}
```

**Field Semantics**:
- `conversions`: Reverse chronological list (most recent first)
- `failures.recent`: Only failed conversions from `conversions` list (convenience for filtering)

**Caching**: Response can be cached for `SLEEP_TIME` seconds

**Example Use Cases**:
- Timeline chart showing recent activity
- Recent failures alert banner

---

### 5. `GET /api/v1/health`

**Purpose**: Minimal health check for monitoring systems (Prometheus, Docker HEALTHCHECK, etc.)

**Response Schema**:

```json
{
  "status": "healthy" | "degraded" | "unhealthy",
  "timestamp": 1697215200.5,
  "checks": {
    "inbox_accessible": true,
    "converted_accessible": true,
    "m4b_tool_available": true,
    "disk_space_ok": true,
    "retry_queue_length": 2
  },
  "message": ""
}
```

**Status Levels**:
- `"healthy"`: All checks pass, system operational
- `"degraded"`: Some non-critical checks fail (e.g., retry queue > 10)
- `"unhealthy"`: Critical checks fail (e.g., inbox not accessible, m4b-tool missing)

**Caching**: No caching (always fresh for health monitoring)

**Example Use Cases**:
- Docker HEALTHCHECK command
- Prometheus scrape target
- Alert if `status != "healthy"` for > 5 minutes

---

## Data Gaps & Proposed Enhancements

### Gap 1: Real-Time Active Job Progress

**Current State**: InboxState tracks status (`"new"`, `"ok"`, etc.) but not real-time progress within a conversion.

**Dashboard Need**: Progress bar showing "Converting audio files... 45% complete, ETA 8 minutes"

**Proposed Solution**:
- Add `ActiveJob` class to track current conversion state
  - Fields: `book_key`, `stage`, `progress_pct`, `eta_seconds`, `started_at`
  - Stages: `"waiting"`, `"copying"`, `"extracting_metadata"`, `"merging"`, `"verifying"`, `"moving"`
- Update `process_book_folder()` to emit progress events to `ActiveJob` singleton
- Expose via `GET /api/v1/queue/active` endpoint

**Phase**: Recommend deferring to Phase 2.1 (requires refactoring `run.py` processing loop)

---

### Gap 2: Intake Manifest for Passthrough M4B Files

**Current State**: `process_already_m4b()` skips conversion but doesn't emit structured metadata.

**Dashboard Need**: Distinguish "converted" vs "passed through" in metrics and queue.

**Proposed Solution**:
- Add `intake.json` manifest to each book's output directory
  - Fields: `book_name`, `source_format`, `action_taken`, `asin`, `runtime_seconds`, `language`, `next_actions`
  - Example: `{"action_taken": "passthrough", "source_format": "m4b", "next_actions": ["tag"]}`
- Update `ConversionRecord` to include `action_taken` field
- Update metrics display to show passthrough count separately

**Phase**: Core of Phase 2.4 (Intake Reliability)

---

### Gap 3: Retry Schedule Visibility

**Current State**: Retry delay calculated on-demand in `check_failed_books()`, not persisted.

**Dashboard Need**: Show "Next retry in 3m 42s" for all retrying books.

**Proposed Solution**:
- Add `next_retry_at` field to `InboxItem` (computed property based on `last_retry_time` + backoff)
- Include in `/api/v1/queue` response for each book with `status == "needs_retry"`

**Phase**: Already feasible with existing retry logic, add to Phase 2.0.2 endpoint implementation

---

### Gap 4: Series Conversion Metadata

**Current State**: InboxState tracks `is_maybe_series_parent` and `series_books`, but no aggregate metadata.

**Dashboard Need**: Group series books in UI, show "Book 2 of 5 in The Lord of the Rings" badge.

**Proposed Solution**:
- Add `series_info` object to queue items
  - Fields: `parent_key`, `book_index`, `total_books`, `is_complete`
- Compute in `InboxItem.to_dict()` when `is_maybe_series_book == true`

**Phase**: Add to Phase 2.0.2 (low effort, high UX value)

---

### Gap 5: Tagging Status (Phase 3 Dependency)

**Current State**: No tagging workflow exists yet.

**Dashboard Need**: Show "Tagging in progress", "Tagging complete", "Tagging failed" states.

**Proposed Solution**:
- Extend `status` enum to include `"tagging"`, `"tagged"`, `"tagging_failed"`
- Add tagging metadata to queue items: `tagging_started_at`, `tagging_error`, `tags_applied`
- Phase 3.3 will integrate beets output into this schema

**Phase**: Defer to Phase 3.3 (Tagging Orchestration)

---

## Polling Cadence & Rate Limits

### Recommended Poll Intervals

| Endpoint | Poll Interval | Reasoning |
|----------|---------------|-----------|
| `/api/v1/status` | 10-15 seconds | Matches `SLEEP_TIME`, captures new conversions |
| `/api/v1/queue` | 5-10 seconds | Balances queue updates with server load |
| `/api/v1/queue/:book_key` | On-demand | Only fetch when user views detail page |
| `/api/v1/metrics/recent` | 30 seconds | Historical data changes slowly |
| `/api/v1/health` | 30-60 seconds | For monitoring systems, not dashboards |

### Rate Limits (Phase 2.0.3)

**Initial Limits** (enforce via middleware):
- **Per-endpoint**: 30 requests/minute per client IP
- **Global**: 120 requests/minute across all endpoints

**Rationale**: Prevents accidental polling loops or abuse while allowing responsive UIs.

**Rate Limit Headers** (RFC 6585):
```
X-RateLimit-Limit: 30
X-RateLimit-Remaining: 25
X-RateLimit-Reset: 1697215260
```

**429 Response**:
```json
{
  "error": "rate_limit_exceeded",
  "message": "You have exceeded 30 requests per minute for this endpoint.",
  "retry_after_seconds": 45
}
```

---

## Versioning Strategy

### API Version in URL

**Format**: `/api/v{major}/...`

**Versioning Rules**:
- **Major version** (`v1`, `v2`): Breaking changes (field renames, type changes, removed fields)
- **Minor version** (implicit): Additive changes (new fields, new endpoints)
- **Patch version** (implicit): Bug fixes, no schema changes

**Version Support**:
- Current version (`v1`): Guaranteed support for 12 months after `v2` release
- Legacy version: Deprecated warnings in headers, removed after 12 months

**Example Deprecation Header**:
```
X-API-Deprecation: true
X-API-Sunset: 2026-10-01
X-API-Replacement: /api/v2/status
```

### Schema Versioning

**Backward Compatibility Rules**:
1. **Additive changes are safe**: New optional fields, new enum values (with fallback handling)
2. **Breaking changes require major version bump**: Renaming fields, changing types, removing fields
3. **Deprecation workflow**:
   - Mark field as `deprecated` in docs
   - Add warning in logs when deprecated field is accessed
   - Remove in next major version

**Example Additive Change** (safe for `v1`):
```json
{
  "version": "1.0.0",
  "timestamp": 1697215200.5,
  "status": "idle",
  "active_job": {                     // NEW FIELD (optional, defaults to null)
    "book_key": "Harry Potter Book 1",
    "progress_pct": 45,
    "eta_seconds": 480
  },
  // ... existing fields unchanged
}
```

**Example Breaking Change** (requires `v2`):
```json
{
  "version": "2.0.0",
  "timestamp": 1697215200.5,
  "system_state": "idle",            // RENAMED: was "status"
  "metrics": {
    "lifetime": {
      "total_conversions": 47,       // RENAMED: was "total"
      // ...
    }
  }
}
```

---

## Implementation Checklist (Phase 2.0.2)

### Endpoint Implementation

- [ ] **Framework Selection**: Evaluate FastAPI vs Flask vs Starlette (recommend FastAPI for OpenAPI support)
- [ ] **Project Structure**:
  ```
  src/api/
    __init__.py
    app.py              # FastAPI app initialization
    routes/
      status.py         # /api/v1/status
      queue.py          # /api/v1/queue
      metrics.py        # /api/v1/metrics
      health.py         # /api/v1/health
    schemas/            # Pydantic models for responses
      v1.py
    middleware/
      rate_limit.py
      cors.py
  ```
- [ ] **Serializers**: Write Pydantic schemas matching this contract
- [ ] **Data Access**: Wire endpoints to `ConversionMetrics()`, `InboxState()`, and `retry` module
- [ ] **Error Handling**: Return 404 for missing books, 500 for internal errors
- [ ] **Health Check**: Implement checks for disk space, directory access, m4b-tool presence
- [ ] **OpenAPI Spec**: Auto-generate from FastAPI decorators

### Testing

- [ ] **Unit Tests**: Mock `ConversionMetrics` and `InboxState` to test serialization
- [ ] **Integration Tests**: Spin up API with real data, verify schema compliance
- [ ] **Contract Tests**: JSON schema validation against sample responses

### Documentation

- [ ] Update `docs/api/dashboard.md` with example `curl` commands
- [ ] Add Postman/Insomnia collection for manual testing
- [ ] Generate OpenAPI JSON and publish at `/api/v1/openapi.json`

---

## Blockers & Dependencies

### Blockers

1. **No Active Job Tracking**: Cannot show real-time progress without refactoring `run.py` processing loop.
   - **Workaround**: Show "Processing (no ETA available)" for books with recent `last_updated` timestamp.
   - **Resolution**: Defer to Phase 2.1.1 (Foundation & Read-Only Dashboard MVP).

2. **No Tagging State**: Cannot expose tagging status before Phase 3.3.
   - **Workaround**: Omit tagging fields from `v1` schema, add in `v2` when tagging is live.
   - **Resolution**: Document tagging fields as "reserved for future use" in this contract.

### Dependencies

1. **Metrics File Path**: Endpoints assume `ConversionMetrics` singleton is initialized with `set_metrics_file()` in `config.startup()`.
   - **Validation**: Verify `/config/metrics.json` or `converted/metrics.json` exists and is readable.

2. **InboxState Synchronization**: Endpoints read in-memory state; must ensure `InboxState().scan()` has run before serving `/api/v1/queue`.
   - **Validation**: Check `InboxState().ready == True` before returning queue data.

3. **Retry Scheduler**: Endpoints use `can_retry_now()` and `calculate_backoff_delay()` from `retry` module.
   - **Validation**: Ensure `MAX_RETRIES`, `RETRY_BASE_DELAY` config loaded before API starts.

---

## Example API Flows

### Flow 1: Dashboard Initial Load

1. **Frontend**: `GET /api/v1/status`
   - Displays header: "45 conversions (95.7% success), 3h uptime"
2. **Frontend**: `GET /api/v1/queue`
   - Renders table of 8 books with status badges
3. **Frontend**: `GET /api/v1/metrics/recent?limit=10`
   - Renders timeline chart of last 10 conversions

### Flow 2: Monitoring Failed Books

1. **Frontend**: Poll `GET /api/v1/queue` every 10 seconds
2. **Backend**: Returns book with `status: "needs_retry"`, `next_retry_at: 1697215260`
3. **Frontend**: Displays countdown timer "Retry in 2m 15s"
4. **Frontend**: User clicks book → `GET /api/v1/queue/the-hobbit`
   - Shows full error history and retry schedule

### Flow 3: Health Monitoring

1. **Prometheus**: Scrapes `GET /api/v1/health` every 30 seconds
2. **Backend**: Checks inbox accessibility, returns `{"status": "unhealthy", "checks": {"inbox_accessible": false}}`
3. **Prometheus**: Triggers alert "Auto-M4B inbox unreachable"

---

## Future Enhancements (Phase 2.1+)

### Write Operations (Phase 2.1.2)

- `POST /api/v1/queue/:book_key/retry` - Manually retry a failed book
- `POST /api/v1/queue/:book_key/skip` - Mark book as passthrough (don't convert)
- `DELETE /api/v1/queue/:book_key` - Remove book from queue

### Webhooks (Phase 2.2)

- `POST /api/v1/webhooks` - Register webhook for events (`conversion.success`, `conversion.failed`, `retry.scheduled`)
- Event payload: `{"event": "conversion.success", "book_key": "...", "timestamp": ..., "data": {...}}`

### Filtering & Search (Phase 2.x)

- `GET /api/v1/queue?status=failed&is_transient=true` - Filter queue by status and error type
- `GET /api/v1/metrics/search?book_name=harry` - Search conversion history

---

## Appendix: Sample Payloads

### Sample: `/api/v1/status`

```json
{
  "version": "1.0.0",
  "timestamp": 1697215200.5,
  "uptime_seconds": 3650,
  "status": "processing",
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

### Sample: `/api/v1/queue` (Multiple Books)

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
    },
    {
      "key": "Broken Book",
      "path": "/inbox/Broken Book",
      "status": "failed",
      "size_bytes": 120000000,
      "last_updated": 1697210000.0,
      "hash": "xyz789",
      "is_filtered": false,
      "failed_reason": "Invalid audio format",
      "retry_count": 3,
      "max_retries": 3,
      "is_transient": false,
      "will_retry": false,
      "next_retry_at": null,
      "series_info": null
    }
  ]
}
```

---

## Contact & Contribution

**Questions**: Open an issue in the GitHub repo with tag `[Phase 2.0 API]`
**Schema Changes**: Propose amendments via pull request to this document
**Implementation Tracking**: See `PROJECT-ROADMAP-CODEX.md` Phase 2.0.2 checklist
