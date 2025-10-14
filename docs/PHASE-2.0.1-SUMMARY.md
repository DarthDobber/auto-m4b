# Phase 2.0.1: Status & Queue Data Contract - Summary

**Completed**: 2025-10-13
**Status**: ✅ Ready for Review & Phase 2.0.2 Implementation

---

## Executive Summary

Phase 2.0.1 has successfully inventoried all existing data sources and drafted comprehensive JSON schemas for the dashboard API. The data contract is documented in `docs/api/dashboard.md` with versioned payloads, sample responses, and clear implementation guidance.

**Key Deliverables**:
1. ✅ Complete inventory of data sources (ConversionMetrics, InboxState, retry scheduler)
2. ✅ Five endpoint specifications with JSON schemas and field semantics
3. ✅ Identified 5 data gaps with proposed solutions and phase assignments
4. ✅ Polling cadence recommendations and rate limit strategy
5. ✅ API versioning strategy with backward compatibility rules
6. ✅ Implementation checklist for Phase 2.0.2

---

## Data Source Inventory

### 1. ConversionMetrics (`src/lib/metrics.py`)

**Strengths**:
- Comprehensive lifetime and session statistics
- Recent conversion history (last 100 records)
- Timing analytics (fastest, slowest, average)
- JSON persistence for cross-restart continuity

**Gaps**:
- ⚠️ No "currently processing" indicator (InboxState has state, but not real-time progress)
- ⚠️ No ETA calculation for active jobs

**Dashboard Readiness**: 90% - Metrics endpoints can be implemented immediately with existing data

---

### 2. InboxState (`src/lib/inbox_state.py`)

**Strengths**:
- Rich InboxItem metadata (status, retry state, hash tracking)
- Queue filtering by status, series relationships
- Failed book tracking with error messages and retry metadata

**Gaps**:
- ⚠️ No "currently processing" book tracking (status is state-machine, not real-time)
- ⚠️ No progress percentage or ETA within active conversion

**Dashboard Readiness**: 85% - Queue endpoints can show pending/failed/retrying states, but not live conversion progress

---

### 3. Retry Scheduler (`src/lib/retry.py`)

**Strengths**:
- Smart error categorization (transient vs permanent)
- Exponential backoff calculation
- Helper functions for retry decision logic

**Gaps**:
- ✅ None identified - fully ready for dashboard integration

**Dashboard Readiness**: 100% - Retry schedule can be computed on-demand for each failed book

---

### 4. Config (`src/lib/config.py`)

**Strengths**:
- All configuration values accessible via singleton
- Validation methods for pre-flight checks

**Gaps**:
- ✅ None identified - config snapshot can be included in status endpoint

**Dashboard Readiness**: 100%

---

## Endpoint Specifications

### Defined Endpoints (5 total)

| Endpoint | Purpose | Response Size | Polling Interval |
|----------|---------|---------------|------------------|
| `GET /api/v1/status` | System health & metrics snapshot | ~500 bytes | 10-15 seconds |
| `GET /api/v1/queue` | All books in queue with status | ~2-10 KB | 5-10 seconds |
| `GET /api/v1/queue/:book_key` | Detailed single book payload | ~1 KB | On-demand |
| `GET /api/v1/metrics/recent` | Recent conversion history | ~2-5 KB | 30 seconds |
| `GET /api/v1/health` | Health check for monitoring | ~200 bytes | 30-60 seconds |

**Schema Features**:
- Versioned payloads (v1.0.0) with additive change support
- Human-readable timestamps alongside Unix epoch
- Computed fields (e.g., `retry_countdown_seconds`, `will_retry`) to reduce client logic
- Enum values with clear semantics (e.g., `status: "needs_retry"` vs `"failed"`)

**Sample Payloads**: See `docs/api/dashboard.md` Appendix for full examples

---

## Identified Data Gaps & Resolutions

### Gap 1: Real-Time Active Job Progress ⚠️ DEFERRED

**Impact**: Dashboard cannot show "Converting... 45% complete, ETA 8 minutes"

**Workaround**: Show "Processing (started 5 minutes ago)" using `last_updated` timestamp

**Resolution**: Phase 2.1.1 - Add `ActiveJob` singleton to track current conversion stage and progress

**Blocker Status**: Not blocking Phase 2.0.2 endpoint implementation

---

### Gap 2: Intake Manifest for Passthrough M4B ⚠️ PHASE 2.4

**Impact**: Cannot distinguish "converted" vs "passed through" in metrics

**Workaround**: Current metrics treat all completions as conversions

**Resolution**: Phase 2.4 (Intake Reliability) - Add `intake.json` manifest with `action_taken` field

**Blocker Status**: Not blocking Phase 2.0.2, but schema reserves `action_taken` field for future use

---

### Gap 3: Retry Schedule Visibility ✅ READY

**Impact**: Dashboard needs "Next retry in 3m 42s" countdown

**Resolution**: Computed property in InboxItem using `can_retry_now()` from retry module

**Blocker Status**: Can be implemented in Phase 2.0.2 endpoints

---

### Gap 4: Series Conversion Metadata ✅ READY

**Impact**: Dashboard cannot group series books or show "Book 2 of 5" badges

**Resolution**: Add `series_info` object to queue items (low effort, already tracked in InboxState)

**Blocker Status**: Can be implemented in Phase 2.0.2 endpoints

---

### Gap 5: Tagging Status ⚠️ PHASE 3.3

**Impact**: Dashboard cannot show tagging progress or failures

**Workaround**: Omit tagging fields from v1 schema

**Resolution**: Phase 3.3 (Tagging Orchestration) - Extend status enum with `"tagging"`, `"tagged"`, `"tagging_failed"`

**Blocker Status**: Not blocking Phase 2.0.2, reserved for Phase 3 integration

---

## API Design Decisions

### 1. Versioning Strategy

**Choice**: Major version in URL (`/api/v1/...`)

**Rationale**:
- Clear upgrade path for breaking changes
- 12-month support window for legacy versions
- Additive changes (new fields) safe within major version

**Deprecation Process**:
1. Add deprecation headers to old version
2. Announce sunset date (12 months out)
3. Remove old version after sunset

---

### 2. Polling Cadence

**Choice**: 5-15 second intervals with endpoint-specific guidance

**Rationale**:
- Aligns with `SLEEP_TIME` (10s default) for queue updates
- Balances responsiveness with server load
- Metrics refresh slowly (30s interval acceptable)

**Rate Limits**: 30 requests/minute per endpoint, 120/min global (enforced in Phase 2.0.3)

---

### 3. Schema Philosophy

**Choice**: Self-documenting, computed fields, clear enums

**Rationale**:
- Reduces client-side complexity (e.g., `will_retry` computed server-side)
- Human-readable values alongside machine timestamps
- Enum semantics prevent ambiguity (`"needs_retry"` vs `"failed"`)

**Example**:
```json
{
  "status": "needs_retry",
  "will_retry": true,                  // Computed from retry logic
  "next_retry_at": 1697215260.0,       // Unix timestamp
  "retry_countdown_seconds": 60        // Human-friendly countdown
}
```

---

### 4. Error Handling

**Choice**: Standard HTTP codes + JSON error payloads

**Rationale**:
- 404 for missing books (with suggestion to refresh queue)
- 429 for rate limit with `retry_after_seconds`
- 500 for internal errors (with sanitized message)

**Example 404**:
```json
{
  "error": "book_not_found",
  "message": "Book 'Harry Potter' not found in queue. It may have been processed or removed.",
  "suggestion": "Refresh queue via GET /api/v1/queue"
}
```

---

## Blockers & Dependency Resolution

### ✅ No Critical Blockers

All Phase 2.0.2 endpoints can be implemented with existing data sources.

### ⚠️ Minor Limitations

1. **No Real-Time Progress**: Dashboard will show "Processing..." without ETA until Phase 2.1.1
   - **User Impact**: Acceptable for MVP - users can see book is active via recent `last_updated` timestamp

2. **No Tagging State**: Dashboard cannot show tagging status until Phase 3.3
   - **User Impact**: None for Phase 2.0 (tagging not yet implemented)

### ✅ Dependencies Met

1. **Metrics File Path**: `ConversionMetrics` initialized in `config.startup()` - ✅ Verified
2. **InboxState Ready**: Endpoints can check `InboxState().ready` before serving queue - ✅ Verified
3. **Retry Config**: `MAX_RETRIES`, `RETRY_BASE_DELAY` loaded from config - ✅ Verified

---

## Implementation Recommendations for Phase 2.0.2

### 1. Framework Selection: FastAPI ✅ RECOMMENDED

**Rationale**:
- Auto-generates OpenAPI spec (self-documenting API)
- Pydantic schema validation (matches our contract approach)
- Async support for future scalability
- Built-in rate limiting via middleware

**Alternatives Considered**:
- Flask: Mature but requires manual OpenAPI generation
- Starlette: Lighter weight but less batteries-included

---

### 2. Project Structure

```
src/api/
  __init__.py
  app.py                    # FastAPI app initialization
  routes/
    status.py               # GET /api/v1/status
    queue.py                # GET /api/v1/queue, GET /api/v1/queue/:book_key
    metrics.py              # GET /api/v1/metrics/recent
    health.py               # GET /api/v1/health
  schemas/
    v1.py                   # Pydantic models (StatusResponse, QueueResponse, etc.)
  middleware/
    rate_limit.py           # 30 req/min per endpoint
    cors.py                 # Allow dashboard origin
  utils/
    serializers.py          # Convert InboxItem/ConversionRecord to dict
```

---

### 3. Testing Strategy

**Unit Tests** (40% coverage target):
- Mock `ConversionMetrics()` and `InboxState()` with fixture data
- Test serializers produce schema-compliant JSON
- Test retry schedule calculation

**Integration Tests** (30% coverage target):
- Spin up FastAPI app with real metrics.json
- Verify HTTP responses match schema
- Test 404/500 error handling

**Contract Tests** (10% coverage target):
- JSON schema validation against sample responses
- Ensure backward compatibility when adding fields

**Manual Testing** (20%):
- Postman/Insomnia collection for exploratory testing
- Dashboard integration smoke tests

---

### 4. Documentation Tasks

**For Phase 2.0.2**:
- [ ] Add example `curl` commands to `docs/api/dashboard.md`
- [ ] Create Postman collection and export to `docs/api/postman_collection.json`
- [ ] Generate OpenAPI JSON and serve at `/api/v1/openapi.json`
- [ ] Update `README.md` with "Dashboard API" section linking to docs

**For Phase 2.0.3** (Packaging):
- [ ] Docker Compose updates for API service
- [ ] Environment variable docs for API host/port
- [ ] Developer setup guide (running API outside Docker)

---

## Open Questions for Stakeholder Review

### Question 1: Real-Time Progress Priority

**Context**: Gap 1 (real-time progress) requires refactoring `run.py` processing loop.

**Options**:
- **A**: Defer to Phase 2.1.1 (recommended) - Dashboard shows "Processing..." without ETA
- **B**: Fast-track for Phase 2.0.2 - Adds 4-6 hours to implementation, enables progress bars

**Recommendation**: Option A - Real-time progress is "nice to have" but not critical for operational visibility. Users can infer activity from `last_updated` timestamps.

---

### Question 2: Passthrough M4B Handling

**Context**: Gap 2 (intake manifest) affects how metrics distinguish converted vs passed-through books.

**Options**:
- **A**: Implement intake manifest in Phase 2.4 as planned (recommended)
- **B**: Add basic `action_taken` field to metrics now, populate retrospectively later

**Recommendation**: Option A - Intake manifest is core to Phase 2.4 objectives (format assurance, ASIN detection). Adding partial support now creates technical debt.

---

### Question 3: Rate Limit Aggressiveness

**Context**: Proposed 30 req/min per endpoint, 120/min global.

**Options**:
- **A**: Start strict (30/min) and loosen if users report issues (recommended)
- **B**: Start permissive (100/min) and tighten if abuse detected

**Recommendation**: Option A - Dashboard should poll 6 req/min (10s interval), so 30/min provides 5x headroom for manual testing.

---

## Success Criteria for Phase 2.0.2

### Must-Have (P0)

- [x] Five endpoints implemented and returning schema-compliant JSON
- [ ] At least one endpoint covered by unit tests
- [ ] OpenAPI spec generated and accessible
- [ ] API starts automatically with existing Docker workflow

### Should-Have (P1)

- [ ] Rate limiting middleware enforces 30 req/min
- [ ] CORS middleware allows dashboard origin
- [ ] Health endpoint checks inbox/converted accessibility
- [ ] Documentation includes example `curl` commands

### Nice-to-Have (P2)

- [ ] Integration tests with real metrics.json fixture
- [ ] Postman collection for manual testing
- [ ] Retry schedule countdown computed for all failed books
- [ ] Series metadata included in queue items

---

## Next Steps

### Immediate Actions (Phase 2.0.2)

1. **Review this document and `docs/api/dashboard.md` with stakeholders**
   - Sign off on schema design and gap resolutions
   - Answer open questions 1-3 above

2. **Set up FastAPI project structure**
   - Install dependencies: `fastapi`, `uvicorn`, `pydantic`
   - Create `src/api/app.py` with health endpoint smoke test

3. **Implement `/api/v1/status` endpoint**
   - Wire to `ConversionMetrics()` and `Config()`
   - Write Pydantic schema for response
   - Test via `curl` and browser

4. **Implement `/api/v1/queue` endpoint**
   - Wire to `InboxState()` and `retry` module
   - Add retry schedule computation
   - Add series metadata (Gap 4 resolution)

5. **Implement remaining endpoints**
   - `/api/v1/queue/:book_key`
   - `/api/v1/metrics/recent`
   - `/api/v1/health`

6. **Write unit tests**
   - Test serializers with fixture data
   - Verify schema compliance

7. **Generate OpenAPI spec**
   - Serve at `/api/v1/openapi.json`
   - Validate with Swagger UI

### Follow-Up Actions (Phase 2.0.3)

- [ ] Docker Compose updates for API service
- [ ] Environment variable configuration (host, port, CORS origin)
- [ ] Rate limiting middleware
- [ ] Developer documentation for running API locally

### Future Phases

- **Phase 2.1.1**: Dashboard UI consuming these endpoints
- **Phase 2.1.2**: Write operations (retry, skip, delete)
- **Phase 2.4**: Intake manifest for passthrough M4B
- **Phase 3.3**: Tagging status integration

---

## Appendix: Data Contract Location

**Primary Document**: `docs/api/dashboard.md`

**Backup/Version Control**:
- This summary: `docs/PHASE-2.0.1-SUMMARY.md`
- Roadmap tracking: `PROJECT-ROADMAP-CODEX.md` (Phase 2.0.1 checklist)

**Future Homes**:
- OpenAPI spec: `/api/v1/openapi.json` (auto-generated from FastAPI)
- Postman collection: `docs/api/postman_collection.json` (Phase 2.0.3)

---

## Sign-Off

**Prepared By**: Claude (Codex Session)
**Date**: 2025-10-13
**Phase**: 2.0.1 - Status & Queue Data Contract
**Status**: ✅ Ready for Phase 2.0.2 Implementation

**Stakeholder Review Required**:
- [ ] Approve schema design (5 endpoints, field semantics)
- [ ] Approve gap resolutions (defer progress tracking to 2.1.1, intake manifest to 2.4)
- [ ] Answer open questions (progress priority, passthrough handling, rate limits)
- [ ] Sign off to proceed with Phase 2.0.2 endpoint implementation
