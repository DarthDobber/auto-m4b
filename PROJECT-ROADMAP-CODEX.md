# Auto-M4B Improvement Roadmap (Codex Edition)

**Repository**: darthdobber-auto-m4b
**Forked From**: brandonscript/auto-m4b
**Prepared By**: Codex (GPT-5)
**Started**: 2025-10-12
**Current Status**: Phase 1 - Critical Improvements (foundation complete, preparing Phase 2 initiatives)

---

## Project Goals

Transform the auto-m4b fork into a production-ready, user-friendly audiobook conversion and intake service with:
- Easy installation via pre-built Docker images
- Robust error handling and recovery
- Comprehensive documentation
- Better user visibility and control
- Extended functionality via plugins and integrations
- Seamless hand-off to automated tagging with beets-audible

### Codex Vision Addendum
- Establish Auto-M4B as the canonical intake pipeline for all audiobook sources, ensuring everything emerges as a fully tagged M4B ready for library ingestion.
- Minimize manual intervention by automating conversion-or-pass routing, metadata enrichment from Audible, and downstream notifications.
- Provide observable, testable stages so future forks (beets-audible, library importers) can evolve independently without breaking the intake flow.

---

## Implementation Phases

### ✅ Phase 0: Planning & Analysis (COMPLETED)
- [x] Analyzed differences between original and fork
- [x] Created comparison documentation
- [x] Created migration guide
- [x] Identified 16 potential improvements
- [x] Prioritized improvements by impact/effort

**Artifacts Created**:
- `COMPARISON.md` - Detailed comparison with original
- `MIGRATION_GUIDE.md` - How to migrate from original
- `DOCKER_PUBLISHING_GUIDE.md` - How to publish Docker images
- `IMPROVEMENT_RECOMMENDATIONS.md` - Ranked list of improvements

**Codex Notes**:
- Revisit `COMPARISON.md` while designing the beets integration to ensure new features keep parity where it matters and document user-visible divergences.

---

### ✅ Phase 1: Critical Improvements (COMPLETED)

#### 1.1 Pre-Built Docker Image Support ⭐⭐⭐⭐⭐
**Status**: ✅ COMPLETED
**Priority**: CRITICAL
**Actual Effort**: 4 hours

**Tasks**:
- [x] Create entrypoint.sh script for runtime PUID/PGID
- [x] Modify Dockerfile to remove build-time user creation
- [x] Install gosu in Dockerfile
- [x] Test with various PUID/PGID values
- [x] Update docker-compose examples
- [x] Document new behavior

**Files Modified**:
- `Dockerfile` - Removed ARG PUID/PGID requirements, added gosu, configured entrypoint
- `entrypoint.sh` - NEW FILE (runtime user creation)
- `docker-compose.template.yml` - Removed build args, added comments
- `docker-compose.auto-m4b.yml` - Removed build args, added comments
- `docker-compose.local.yml` - Removed build args

**Success Criteria**:
- [x] Image builds without requiring PUID/PGID args
- [x] Container respects PUID/PGID from environment at runtime
- [x] File permissions work correctly for different users
- [x] No rebuild needed when changing PUID/PGID

**Testing**:
- [x] Tested with PUID=1000, PGID=1000 (default)
- [x] Tested with PUID=1026, PGID=1000 (local workstation)
- [x] Tested with PUID=5000, PGID=5000 (arbitrary values)

#### 1.2 Error Recovery & Retry Logic ⭐⭐⭐⭐⭐
**Status**: ✅ COMPLETED
**Priority**: CRITICAL
**Actual Effort**: 6 hours

**Tasks**:
- [x] Add retry tracking fields to InboxItem
- [x] Implement exponential backoff algorithm
- [x] Categorize errors (transient vs permanent)
- [x] Add MAX_RETRIES, RETRY_TRANSIENT_ERRORS, RETRY_BASE_DELAY config options
- [x] Update fail_book() to track retry state and categorize errors
- [x] Modify check_failed_books() for retry logic with backoff
- [x] Test with corrupted audiobook files
- [x] Fix retry counter reset bug in set_needs_retry()
- [x] Fix early return bug in fail_book()
- [x] Add failed book folder feature with MOVE_FAILED_BOOKS option
- [x] Create move_to_failed() function with FAILED_INFO.txt generation
- [x] Fix integer display bug (MAX_RETRIES showing as float)

**Files Modified**:
- `src/lib/inbox_item.py` - Added retry tracking fields (retry_count, last_retry_time, first_failed_time, is_transient_error), fixed set_needs_retry() with reset_retry_count parameter
- `src/lib/retry.py` - NEW FILE (error categorization, exponential backoff, retry utilities)
- `src/lib/config.py` - Added MAX_RETRIES (default: 3), RETRY_TRANSIENT_ERRORS (default: True), RETRY_BASE_DELAY (default: 60s), MOVE_FAILED_BOOKS (default: True), failed_dir property; fixed env_property decorator to prioritize int over float
- `src/lib/run.py` - Updated fail_book() and check_failed_books() with retry logic; added move_to_failed() function; removed problematic early return
- `src/lib/inbox_state.py` - Updated set_failed() to track retry metadata; updated set_needs_retry() with reset_retry_count parameter

**Success Criteria**:
- [x] Transient errors retry automatically with exponential backoff (60s, 120s, 240s, ...)
- [x] Permanent errors don't retry (logged as "manual fix required")
- [x] Max retries respected (default: 3 attempts)
- [x] Failed books can be manually retried (when files change, retry count resets)
- [x] Retry state tracked in InboxItem (persists in memory during runtime)
- [x] Failed books automatically moved to dedicated folder with recovery instructions
- [x] FAILED_INFO.txt contains error details, retry count, and recovery steps

**Testing**:
- [x] Created corrupted test audiobook
- [x] Built Docker image with retry logic (v1 through v6)
- [x] Verified error categorization works correctly
- [x] Verified retry counter increments properly
- [x] Verified failed books move to failed folder after max retries
- [x] Verified FAILED_INFO.txt contains correct information

**Bugs Fixed**:
1. **Retry counter stuck at 1**: set_needs_retry() was resetting retry_count to 0 on every call
2. **Retry counter not incrementing**: Early return in fail_book() prevented state updates
3. **MAX_RETRIES displayed as float**: env_property decorator checked is_floatish before typ == int
4. **AttributeError**: Used item.reason instead of item.failed_reason in move_to_failed()
5. **ImportError**: Used non-existent human_datetime instead of friendly_short_date

**Key Features**:
- **Smart Error Categorization**: Automatically detects transient vs permanent errors using pattern matching
- **Exponential Backoff**: Retry delays increase exponentially (1min → 2min → 4min → 8min → capped at 1hour)
- **User-Friendly Messages**: Clear retry status messages showing next retry time
- **Manual Override**: If user fixes files manually (hash changes), retry counter resets
- **Failed Book Management**: Books that fail after max retries are moved to timestamped folder with detailed recovery instructions

#### 1.3 Comprehensive Documentation ⭐⭐⭐⭐
**Status**: ✅ COMPLETED
**Priority**: HIGH
**Actual Effort**: 8 hours

**Tasks**:
- [x] Create docs/ directory structure
- [x] Write getting-started.md
- [x] Write configuration.md (all env vars)
- [x] Write troubleshooting.md (common issues)
- [x] Write architecture.md (system design)
- [x] Write contributing.md (contribution guidelines)
- [x] Create API documentation for main modules
- [x] Add docker-compose examples
- [x] Update main README.md with links
- [x] Update documentation for retry logic and failed folder feature
- [x] Remove MAX_CHAPTER_LENGTH from all documentation (unused feature)
- [x] Add workflows and practical examples document

**Files Created**:
- `docs/README.md` - Documentation index ✅
- `docs/getting-started.md` - Complete setup guide with retry config ✅
- `docs/configuration.md` - All env vars documented ✅
- `docs/troubleshooting.md` - Common issues and solutions ✅
- `docs/architecture.md` - System design overview ✅
- `docs/contributing.md` - Contribution guidelines ✅
- `docs/workflows.md` - Practical workflow examples (NEW) ✅
- `docs/api/audiobook.md` - Audiobook class reference ✅
- `docs/api/config.md` - Config API (cleaned up) ✅
- `docs/api/inbox-state.md` - State management API ✅
- `docs/examples/docker-compose.advanced.yml` - Advanced example ✅
- `docs/examples/.env.example` - Environment template ✅

**Files Updated**:
- `README.md` - Updated with failed folder, building from source, retry features, workflows link ✅
- `docs/README.md` - Added workflows.md to navigation ✅
- `docs/getting-started.md` - Added retry configuration, failed folder handling ✅
- `docs/configuration.md` - Removed MAX_CHAPTER_LENGTH, cleaned up ✅
- `docs/api/config.md` - Removed MAX_CHAPTER_LENGTH ✅
- `docs/troubleshooting.md` - Removed MAX_CHAPTER_LENGTH references ✅
- `docs/examples/.env.example` - Removed MAX_CHAPTER_LENGTH ✅
- `docs/examples/docker-compose.advanced.yml` - Removed MAX_CHAPTER_LENGTH ✅

**Success Criteria**:
- [x] New user can get started in <10 minutes
- [x] All configuration options documented
- [x] Common issues have solutions
- [x] Architecture is clear to contributors
- [x] API documentation is complete
- [x] Documentation reflects current features accurately

#### 1.4 Configuration Validation & Help ⭐⭐⭐⭐
**Status**: ✅ COMPLETED
**Priority**: HIGH
**Actual Effort**: 4 hours

**Tasks**:
- [x] Add --validate CLI argument
- [x] Add --help-config CLI argument
- [x] Implement validate_config() method
- [x] Add pre-flight checks for directories
- [x] Check m4b-tool availability
- [x] Validate value ranges (CPU_CORES > 0, etc.)
- [x] Create helpful error messages
- [x] Add validation to startup sequence

**Files Modified**:
- `src/lib/config.py` - Added validate_config() and print_config_help() methods; added --validate and --help-config CLI arguments
- `src/auto_m4b.py` - Added validation handling before startup; deferred imports to support help flags
- `src/__main__.py` - Updated to support new CLI flags
- `README.md` - Added comprehensive validation documentation with examples

**Success Criteria**:
- [x] `--validate` checks all configuration (directories, numeric values, m4b-tool, ON_COMPLETE values)
- [x] Clear error messages for invalid config (lists all validation failures)
- [x] `--help-config` shows all options (displays all config vars with types, descriptions, and defaults)
- [x] Validation can run independently with --validate flag
- [x] Invalid config shows detailed error messages

**Key Features**:
- **Comprehensive Validation**: Checks directories, numeric ranges, m4b-tool availability, and enum values
- **Helpful Error Messages**: Lists all validation errors with specific details
- **Configuration Help**: Static method displays all configuration options without requiring valid config
- **Pre-flight Checks**: Validates configuration before starting main processing loop

**Implementation Notes**:
- validate_config() returns tuple[bool, list[str]] with validation status and error messages
- print_config_help() is a static method that works without config initialization
- Config.__init__ now gracefully handles missing config for help/validate commands
- Validation checks include: directory existence, write permissions, CPU_CORES > 0, retry values >= 0, ON_COMPLETE enum validation

#### 1.5 Progress Reporting & Metrics ⭐⭐⭐⭐
**Status**: ✅ COMPLETED
**Priority**: HIGH
**Actual Effort**: 6 hours

**Tasks**:
- [x] Create ConversionMetrics class with persistence
- [x] Track success/failure rates
- [x] Track conversion times (average, fastest, slowest)
- [x] Track total data converted
- [x] Add --status CLI command
- [x] Persist metrics to JSON file
- [x] Display metrics on startup
- [x] Track recent conversions (last 100)
- [x] Track session vs lifetime statistics
- [x] Add format utilities (duration, bytes)

**Files Created**:
- `src/lib/metrics.py` - NEW FILE (ConversionMetrics singleton with JSON persistence)
- `src/lib/progress.py` - NEW FILE (format utilities: format_duration, format_bytes, ProgressTracker class for future use)

**Files Modified**:
- `src/lib/run.py` - Integrated metrics recording in convert_book() for both success and failure cases
- `src/auto_m4b.py` - Added --status command handler with comprehensive metrics display
- `src/lib/config.py` - Added METRICS_FILE cached property, metrics initialization in startup()

**Success Criteria**:
- [x] Metrics persist across restarts (stored in converted/metrics.json)
- [x] `--status` shows lifetime and session statistics
- [x] Success rate tracked accurately
- [x] Tracks conversion timing (fastest, slowest, average)
- [x] Displays recent 10 conversions and recent 5 failures
- [x] Metrics displayed on container startup
- [x] Format utilities for human-readable durations and file sizes

**Key Features**:
- **Comprehensive Tracking**: Records every conversion with status, duration, file size, and error messages
- **Session vs Lifetime**: Separates current session stats from lifetime totals
- **Recent History**: Maintains last 100 conversions for detailed tracking
- **Automatic Persistence**: JSON file auto-saves after each conversion
- **Startup Display**: Shows metrics summary when container starts (if data exists)
- **Format Utilities**: Human-readable durations ("2h 15m 30s") and sizes ("1.5 GB")

**Implementation Notes**:
- ConversionMetrics uses singleton pattern for global access
- Metrics file stored in converted folder (converted/metrics.json)
- Session tracking via start time and uptime calculation
- ConversionRecord dataclass stores individual conversion details
- Format functions handle edge cases (0 seconds, large values, etc.)

**Codex Notes**:
- Metrics file will become the data source for tagging analytics (e.g., time-to-tag, metadata coverage). Plan schema extensions now to avoid breaking changes later.

---

### 🚀 Phase 2: Operational Visibility & Intake Hardening (PLANNED)

#### 2.0 API Foundations for Dashboard ⭐⭐⭐
**Status**: NOT STARTED
**Priority**: HIGH
**Estimated Effort**: 8-12 hours

##### 2.0.1 Status & Queue Data Contract ⭐
**Status**: ✅ COMPLETED
**Priority**: HIGH
**Actual Effort**: 3 hours

**Tasks**:
- [x] Inventory existing data sources (ConversionMetrics, InboxState, retry scheduler) and identify fields needed by the UI
- [x] Draft JSON schemas for queue overview, active job payload, retry schedule, and metrics snapshot
- [x] Document endpoint requirements (rate limits, pagination, poll cadence) in docs/api/dashboard.md

**Success Criteria**:
- [x] Schema document published with examples for each payload
- [x] Data owners agree the fields cover dashboard and future automation needs
- [x] Contract versioning approach defined to avoid breaking changes later

**Artifacts Created**:
- `docs/api/dashboard.md` - Complete API data contract with 5 endpoint specifications
- `docs/PHASE-2.0.1-SUMMARY.md` - Executive summary with findings and recommendations

**Key Findings**:
- Identified 5 data gaps (2 deferred, 2 ready for 2.0.2, 1 for Phase 3.3)
- Recommended FastAPI framework for implementation
- No critical blockers for Phase 2.0.2 endpoint implementation
- Dashboard can achieve 85-90% functionality with existing data sources

##### 2.0.2 Implement Read-Only Status Endpoints ⭐⭐
**Status**: NOT STARTED
**Priority**: HIGH
**Estimated Effort**: 3-4 hours

**Tasks**:
- [ ] Add lightweight FastAPI (or chosen framework) app to expose `/api/status` and `/api/queue` according to the schema
- [ ] Serialize ConversionMetrics, InboxState, and retry planner state into the documented payloads
- [ ] Include basic error handling and health response for the API service

**Success Criteria**:
- [ ] `curl` requests return JSON matching the contract with live data
- [ ] Missing data gracefully returns empty/default structures without crashing the service
- [ ] Unit or integration tests cover at least one happy-path response per endpoint

##### 2.0.3 Endpoint Access & Packaging ⭐
**Status**: NOT STARTED
**Priority**: MEDIUM
**Estimated Effort**: 2-3 hours

**Tasks**:
- [ ] Wire the API app into container startup (docker-compose.local.yml, Dockerfile, entrypoint updates)
- [ ] Provide configuration for binding host/port and optional auth stubs for later phases
- [ ] Document how to run the API locally and in Docker for dashboard development

**Success Criteria**:
- [ ] API service starts automatically with the existing Docker workflow
- [ ] Local developers can run `pipenv run python -m src.api` (or equivalent) outside Docker
- [ ] Documentation in docs/api/dashboard.md includes setup instructions and endpoint list

#### 2.1 Web UI / Dashboard ⭐⭐⭐⭐
**Status**: NOT STARTED
**Priority**: MEDIUM-HIGH
**Estimated Effort**: 16-24 hours

##### 2.1.1 Foundation & Read-Only Dashboard MVP ⭐
**Status**: NOT STARTED
**Priority**: MEDIUM-HIGH
**Estimated Effort**: 6-8 hours
**Prerequisites**:
- 2.0.1/2.0.2 schema and endpoints implemented
- Metrics data verified against ConversionMetrics CLI output

**Tasks**:
- [ ] Choose and scaffold the core web framework (e.g., FastAPI backend with HTMX/Alpine front-end)
- [ ] Consume the `/api/status` and `/api/queue` endpoints to render live queue + metrics
- [ ] Build dashboard layout with auto-refresh and empty-state handling
- [ ] Document UI architecture, polling cadence, and authentication expectations for contributors

**Success Criteria**:
- [ ] Dashboard loads in a browser and reflects live conversion queue and current job state
- [ ] Metrics shown on the dashboard match the CLI `--status` output (totals, failures, uptime)
- [ ] UI documentation references the API contract and explains how to extend widgets

##### 2.1.2 Failed Job Management MVP ⭐⭐
**Status**: NOT STARTED
**Priority**: MEDIUM-HIGH
**Estimated Effort**: 4-6 hours
**Prerequisites**:
- Intake manifest schema defined for failed books (see Phase 2.4)
- API contract for retrieving failed item metadata and retry state

**Tasks**:
- [ ] Create a view that lists failed and archived books with key metadata (ASIN, series, runtime)
- [ ] Add API support for re-queueing a failed book and updating retry counters
- [ ] Expose contextual guidance (e.g., FAILED_INFO.txt contents) within the UI

**Success Criteria**:
- [ ] UI lists all failed conversions with actionable metadata
- [ ] Operators can re-queue a failed job from the UI without CLI access
- [ ] Retry attempts triggered from the UI update metrics and state correctly

##### 2.1.3 Advanced Manual Controls MVP ⭐⭐
**Status**: NOT STARTED
**Priority**: MEDIUM
**Estimated Effort**: 4-6 hours
**Prerequisites**:
- Action endpoints for skip/reprocess/tagging defined and secured
- Clear business rules for passthrough M4B handling documented

**Tasks**:
- [ ] Implement a UI control to mark a book as "skip conversion" (pass-through to tagging)
- [ ] Add manual "reprocess from scratch" and "send to beets" actions with confirmation dialogs
- [ ] Provide audit logging for all manual interventions initiated via the UI

**Success Criteria**:
- [ ] Users can manage passthrough M4Bs and trigger manual workflows directly from the dashboard
- [ ] Manual actions feed into metrics/logs for traceability
- [ ] Tagging hand-off controls respect future Phase 3 orchestration rules

##### 2.1.4 Security & Integration MVP ⭐
**Status**: NOT STARTED
**Priority**: MEDIUM
**Estimated Effort**: 2-4 hours
**Prerequisites**:
- Decision on authentication method (basic auth, token, reverse proxy integration)
- Endpoint inventory complete from prior sub-phases

**Tasks**:
- [ ] Protect dashboard and API endpoints with the chosen auth mechanism
- [ ] Add UI indicators for upcoming beets tagging jobs (dependent on Phase 3 completion)
- [ ] Consolidate API documentation in docs/ or OpenAPI spec for downstream integrations

**Success Criteria**:
- [ ] Dashboard and APIs require authentication before access
- [ ] UI surfaces end-to-end pipeline visibility from intake through tagging (once Phase 3 is live)
- [ ] API reference published with routes, parameters, and sample responses

#### 2.2 Notification System ⭐⭐⭐
**Status**: NOT STARTED
**Priority**: MEDIUM
**Estimated Effort**: 4-6 hours

**Tasks**:
- [ ] Install Apprise library
- [ ] Add notification configuration to environment/docs
- [ ] Implement Discord webhook notifications (success, failure, tagging complete)
- [ ] Implement email/Pushover notifications for escalations
- [ ] Add notification hooks for "ready for tagging" and "tagging failed" events
- [ ] Allow per-destination filtering (success-only vs failure-only)

**Success Criteria**:
- [ ] Notification preferences configurable via env vars
- [ ] Alerts fire for conversion failures, retries, and tagging completion
- [ ] Users can disable/enable notification categories without code changes

#### 2.3 Health Checks & Monitoring ⭐⭐⭐
**Status**: NOT STARTED
**Priority**: MEDIUM
**Estimated Effort**: 3-4 hours

**Tasks**:
- [ ] Add /health endpoint and Docker HEALTHCHECK
- [ ] Check directory accessibility, disk space, and m4b-tool availability
- [ ] Emit Prometheus-friendly metrics (conversion counts, tagging backlog)
- [ ] Surface beets integration health (credentials present, plugin reachable)
- [ ] Document recommended monitoring dashboards/alerts

**Success Criteria**:
- [ ] Container health reflects actual intake readiness
- [ ] Operators alerted before storage or credential issues break the pipeline
- [ ] Observability covers both conversion and tagging stages

#### 2.4 Intake Reliability & Format Assurance ⭐⭐⭐⭐
**Status**: NOT STARTED
**Priority**: HIGH
**Estimated Effort**: 8-10 hours

**Tasks**:
- [ ] Document and harden `process_already_m4b()` path with tests and metrics
- [ ] Add configuration to explicitly choose convert-always vs convert-if-needed behavior
- [ ] Implement checksum + duration validation for incoming M4B files
- [ ] Generate ingestion manifest (`converted/<book>/intake.json`) capturing source format, detected ASIN, runtime, language, and next actions
- [ ] Emit structured event when book is ready for tagging (file path, manifest location)
- [ ] Ensure retry logic respects manifest state and resumes correctly after manual fixes

**Success Criteria**:
- [ ] Every book exits Phase 2 with an intake manifest describing next steps
- [ ] Already-M4B flows skip conversion but still produce manifests and notifications
- [ ] Conversion metrics annotate whether the book was converted or passed through
- [ ] Intake manifest schema versioned and documented for downstream consumers


### 🔄 Phase 3: Audible Metadata & beets-audible Integration (PLANNED)

#### 3.1 Requirements & Gap Analysis ⭐⭐⭐⭐
**Status**: NOT STARTED
**Priority**: HIGH
**Estimated Effort**: 6-8 hours

**Tasks**:
- [ ] Audit beets-audible capabilities and configuration requirements
- [ ] Compare mp3tag `.inc` fields with beets data model (cover, ASIN, series, narrators, release date, runtime, language)
- [ ] Document Audible API usage patterns and rate limits
- [ ] Define metadata contract between intake manifest and tagging stage
- [ ] Decide whether to fork beets-audible or build pluggable extension hooks
- [ ] Capture credential management strategy (Audible auth, cookies, API keys)

**Success Criteria**:
- [ ] Signed-off technical design covering data flow, mapping, and security
- [ ] Known gaps between existing beets plugin features and target tagging format
- [ ] Risk register for Audible API changes, authentication, and rate-limiting

#### 3.2 beets-audible Fork & Enhancements ⭐⭐⭐⭐
**Status**: NOT STARTED
**Priority**: HIGH
**Estimated Effort**: 12-18 hours

**Tasks**:
- [ ] Fork beets-audible under project namespace
- [ ] Add CLI/REST entry point that accepts intake manifest payloads
- [ ] Extend metadata extraction to include missing fields (subtitle, content group, WWWAUDIOFILE, ITUNESMEDIATYPE, ITUNESGAPLESS)
- [ ] Implement caching to avoid duplicate Audible lookups during retries
- [ ] Add dry-run and verbose logging for troubleshooting
- [ ] Publish documentation for forked plugin usage and configuration

**Success Criteria**:
- [ ] Fork builds/tests locally with sample manifests
- [ ] Plugin populates all fields defined in mp3tag template (or documents gaps)
- [ ] Cached lookups reduce repeated Audible requests on retries
- [ ] New README explains integration points with Auto-M4B

#### 3.3 Auto-M4B → beets Orchestration ⭐⭐⭐⭐⭐
**Status**: NOT STARTED
**Priority**: CRITICAL
**Estimated Effort**: 10-14 hours

**Tasks**:
- [ ] Implement post-conversion worker that reads manifests and invokes beets tagger
- [ ] Support synchronous (blocking) and asynchronous (queued) tagging modes
- [ ] Stream tagging progress into metrics, logs, notifications, and UI
- [ ] Persist tagging results (success/error, applied fields) back into manifest
- [ ] Allow tagging retries with exponential backoff separate from conversion retries
- [ ] Expose CLI command (e.g., `python -m src --tag /path/to/book`) and docker-compose examples

**Success Criteria**:
- [ ] Tagging runs automatically after each successful conversion or pass-through
- [ ] Tagged files remain in converted directory with updated metadata/cover art
- [ ] Manifest indicates final state (`converted`, `tagged`, `failed_tagging`)
- [ ] UI/notifications show tag status alongside conversion status

#### 3.4 Metadata Validation & Feedback ⭐⭐⭐
**Status**: NOT STARTED
**Priority**: MEDIUM
**Estimated Effort**: 6-8 hours

**Tasks**:
- [ ] Build validation that compares beets output to manifest expectations
- [ ] Flag missing critical fields (title, author, narrator, duration, ASIN) for manual review
- [ ] Allow manual overrides (e.g., supply ASIN) and re-run tagging
- [ ] Update metrics to track tagging accuracy and manual intervention rate
- [ ] Document manual recovery workflows

**Success Criteria**:
- [ ] Automated checks catch regressions before files reach library
- [ ] Manual override workflow documented and exposed via CLI/UI
- [ ] Metrics differentiate conversion success from tagging success

---

### 📦 Phase 4: Library Orchestration & Ecosystem (FUTURE)

#### 4.1 Workflow Automation ⭐⭐⭐
**Status**: NOT STARTED
**Priority**: MEDIUM
**Estimated Effort**: 6-8 hours

**Tasks**:
- [ ] Provide hooks to copy tagged M4B into downstream libraries (Plex, Audiobookshelf, Jellyfin)
- [ ] Publish post-tagging script templates (rsync, rclone, S3 uploads)
- [ ] Support optional library-specific metadata tweaks (e.g., Plex naming)
- [ ] Allow pipeline to pause after tagging for manual QA before release
- [ ] Document end-to-end pipeline examples (download → convert → tag → library)

**Success Criteria**:
- [ ] Users can enable/disable downstream moves via configuration
- [ ] Library-specific docs exist for at least one target platform
- [ ] Tagged files remain auditable with manifest snapshots

#### 4.2 Downstream Connectors ⭐⭐⭐
**Status**: NOT STARTED
**Priority**: MEDIUM
**Estimated Effort**: 8-10 hours

**Tasks**:
- [ ] Evaluate and document API integration with Audiobookshelf/Plex (library refresh)
- [ ] Trigger library rescans via webhooks/API after tagging completes
- [ ] Capture cover/narrator/series mapping quirks per platform
- [ ] Expose generic webhook interface so users can plug in custom automations
- [ ] Provide smoke tests that simulate webhook success/failure

**Success Criteria**:
- [ ] At least one downstream connector implemented and tested
- [ ] Webhook failures logged with retries and notifications
- [ ] Documentation outlines how to add new connectors

#### 4.3 Format & Series Normalization ⭐⭐
**Status**: NOT STARTED
**Priority**: MEDIUM-LOW
**Estimated Effort**: 6 hours

**Tasks**:
- [ ] Add optional series/collection normalization rules (padding, numbering)
- [ ] Support multi-language metadata fallback (Audible locale selection)
- [ ] Expose configuration for alternate tag schemes (iTunes vs MP4 atoms)
- [ ] Ensure manifest captures localization choices for reproducibility

**Success Criteria**:
- [ ] Tagged output matches desired naming conventions across series
- [ ] Localization choices persist through retries and downstream moves

---

### 🧪 Phase 5: Quality, Testing & Release Engineering (FUTURE)

#### 5.1 Automated Testing ⭐⭐⭐
**Status**: NOT STARTED
**Priority**: MEDIUM
**Estimated Effort**: 10-12 hours

**Tasks**:
- [ ] Add unit tests for intake manifest generation and tagging orchestration
- [ ] Build integration test harness with sample audiobooks and mocked Audible responses
- [ ] Introduce regression tests ensuring mp3tag-equivalent fields remain populated
- [ ] Run tests in CI (GitHub Actions) with matrix for tagging enabled/disabled
- [ ] Provide fixtures for already-M4B pass-through cases

**Success Criteria**:
- [ ] CI gate catches schema or mapping regressions before release
- [ ] Sample data set published for contributors
- [ ] Tests cover conversion and tagging happy-path plus failure scenarios

#### 5.2 Release Automation ⭐⭐
**Status**: NOT STARTED
**Priority**: MEDIUM-LOW
**Estimated Effort**: 6 hours

**Tasks**:
- [ ] Automate Docker multi-arch builds (linux/amd64, linux/arm64)
- [ ] Publish tagged releases when major phases complete
- [ ] Generate changelog from conventional commits
- [ ] Provide upgrade notes focusing on pipeline compatibility
- [ ] Wire releases to notify community channels

**Success Criteria**:
- [ ] Releases published with minimal manual work
- [ ] Users have clear migration steps between versions
- [ ] Multi-arch images validated via smoke tests

#### 5.3 Documentation Polish ⭐⭐
**Status**: NOT STARTED
**Priority**: LOW-MEDIUM
**Estimated Effort**: 6 hours

**Tasks**:
- [ ] Expand docs with full pipeline diagrams (intake → tagging → library)
- [ ] Add troubleshooting for Audible API and beets credential issues
- [ ] Provide cookbook recipes (convert-only mode, tag-only mode, manual override)
- [ ] Record short walkthrough video or gif for onboarding
- [ ] Keep docs versioned with release tags

**Success Criteria**:
- [ ] Documentation answers 90% of support questions
- [ ] Tagging section mirrors mp3tag template capabilities
- [ ] Quickstart covers both conversion-only and fully automated pipelines

---

### ⚙️ Phase 6: Performance & Extension (FUTURE)

#### 6.1 Parallel Processing ⭐⭐⭐
**Status**: NOT STARTED
**Priority**: MEDIUM
**Estimated Effort**: 8-12 hours

**Tasks**:
- [ ] Refactor pipeline to allow multi-book concurrency without breaking manifest/tagging order
- [ ] Introduce worker queue abstraction (asyncio, multiprocessing, or Celery)
- [ ] Ensure per-book locking around beets tagging to avoid race conditions
- [ ] Update metrics to track concurrent throughput and queue depth
- [ ] Stress-test with synthetic workloads (10+ simultaneous books)

**Success Criteria**:
- [ ] Intake handles multiple conversions while maintaining deterministic tagging
- [ ] Resource usage remains bounded via configuration
- [ ] Race conditions prevented (no manifest corruption)

#### 6.2 Plugin System ⭐⭐⭐
**Status**: NOT STARTED
**Priority**: MEDIUM
**Estimated Effort**: 12-16 hours

**Tasks**:
- [ ] Design hook architecture for pre/post processing, metadata enrichment, and notifications
- [ ] Allow plugins to register additional manifest fields or tagging steps
- [ ] Provide example plugin (Goodreads enrichment) and documentation
- [ ] Ensure plugin errors are isolated from core pipeline (fail-safe)
- [ ] Package SDK/typing hints for plugin authors

**Success Criteria**:
- [ ] Plugin API documented with stable versioning
- [ ] Example plugin demonstrates metadata augmentation without core changes
- [ ] Core pipeline guards against misbehaving plugins

---

## Integration Strategy: beets-audible & Audible API

1. **Manifest-first design**: Every processed book produces `intake.json` capturing source metadata, detected ASIN, runtime, language, cover path, and conversion outcome.
2. **Contract validation**: Build JSON schema tests so both Auto-M4B and the beets fork validate the same required fields.
3. **beets bridge**: Create a thin wrapper (`scripts/run_beets_tagging.py`) that translates manifest entries into beets import arguments and captures results.
4. **Audible data mapping**: Mirror the mp3tag `.inc` fields by extending beets output to include cover URL, Audible product URL, ASIN, album, subtitle, authors, narrators, series title/part, content group, movement tags, release date, language, duration, rating, publisher summary, iTunes media type, and gapless flags.
5. **Credential management**: Store Audible API tokens in docker secrets or mounted files; expose env vars (e.g., `AUDIBLE_TOKEN_FILE`, `AUDIBLE_REGION`) and document renewal steps.
6. **Retry & caching**: Cache Audible responses keyed by ASIN + locale to limit API calls during retries; expire cache via configurable TTL and flush on demand.
7. **Feedback loop**: Write tagging results (including diff of applied tags) back into manifest and metrics so UI/CLI can display success/failure reasons.

---

## Dependencies & Open Questions

- Audible authentication method decision (cookie-based vs API key) and automation of refresh.
- beets core version compatibility; confirm required minimum and test on Python 3.10+.
- Determine where manifest schema lives (shared package vs duplicated).
- Evaluate licensing constraints for redistributing Audible-derived metadata.
- Decide on queue backend (filesystem queue vs lightweight DB) for tagging orchestration.
- Investigate whether metrics should migrate from JSON to SQLite for richer reporting.

---

## Risks & Mitigations

- **Audible API changes** – Mitigate with cached responses, feature flags, and watchdog alerts when responses fail schema validation.
- **Credential leakage** – Store secrets outside repo, document docker secrets usage, scrub logs of tokens.
- **Tagging regressions** – Establish manifest-based integration tests before promoting releases.
- **Long-running tagging jobs** – Add timeout + background queue to keep intake loop responsive.
- **User customization drift** – Provide plugin architecture and configuration templates so local tweaks survive upgrades.

---

## Session Log

### Session 1: 2025-10-12 (Planning & Analysis)
**Duration**: ~2 hours
**Completed**:
- Analyzed original vs fork differences
- Created comprehensive comparison document
- Created migration guide for existing users
- Created Docker publishing guide
- Identified and ranked 16 improvements
- Created project tracking system

**Next Steps**:
- Begin Phase 1.1: Pre-Built Docker Image Support

### Session 2: 2025-10-12 (Initial Build & Troubleshooting)
**Duration**: ~3 hours
**Completed**:
- Set up local development environment
- Resolved 4 Docker build issues (nasm, m4b-tool URL, PHP 8.2, GPG)
- Successfully built and tested working baseline
- Committed fixes to GitHub (c3ec169)

**Next Steps**:
- Implement Phase 1.1: Pre-Built Docker Image Support

### Session 3: 2025-10-12 (Phase 1.1 Implementation)
**Duration**: ~4 hours
**Completed**:
- Created entrypoint.sh with runtime PUID/PGID support
- Modified Dockerfile to use gosu and entrypoint
- Removed build-time user creation requirements
- Updated all docker-compose examples
- Tested with multiple PUID/PGID combinations
- Tested with real audiobook (Dresden Files - successful conversion)
- Phase 1.1 COMPLETED ✅
- Committed and pushed changes (d4511ec)

**Next Steps**:
- Begin Phase 1.2: Error Recovery & Retry Logic

### Session 4: 2025-10-13 (Phase 1.2 Implementation)
**Duration**: ~3 hours
**Completed**:
- Implemented retry logic with exponential backoff
- Added MAX_RETRIES, RETRY_TRANSIENT_ERRORS, RETRY_BASE_DELAY config
- Created src/lib/retry.py for error categorization
- Updated fail_book() and check_failed_books() with retry support
- Tested with corrupted audiobook
- Phase 1.2 Initial Implementation COMPLETED ✅

**Next Steps**:
- Test and debug retry logic in production

### Session 5: 2025-10-13 (Phase 1.2 Debugging & Enhancement)
**Duration**: ~3 hours
**Completed**:
- Fixed Bug #1: Retry counter stuck at 1 (set_needs_retry reset issue)
- Fixed Bug #2: Early return preventing retry_count increment
- Fixed Bug #3: MAX_RETRIES displaying as float instead of int
- Added failed book folder feature with MOVE_FAILED_BOOKS config
- Implemented move_to_failed() function with FAILED_INFO.txt
- Fixed Bug #4: AttributeError (item.reason → item.failed_reason)
- Fixed Bug #5: ImportError (human_datetime → friendly_short_date)
- Built and tested Docker images v1 through v6
- Successfully tested complete retry flow with corrupted audiobook
- Updated documentation (getting-started.md, README.md)
- Removed MAX_CHAPTER_LENGTH from entire codebase (unused feature)
- Updated all documentation to reflect current features
- Created comprehensive workflows.md with 8+ practical examples
- Phase 1.2 FULLY COMPLETED ✅
- Phase 1.3 FULLY COMPLETED ✅

**Next Steps**:
- Commit changes (retry logic, failed folder, MAX_CHAPTER_LENGTH removal, docs, workflows)
- Begin Phase 1.4: Configuration Validation & Help

### Session 6: 2025-10-13 (Phase 1.4 Configuration Validation)
**Duration**: ~4 hours
**Completed**:
- Implemented validate_config() method with comprehensive checks
- Added --validate and --help-config CLI arguments
- Created print_config_help() static method
- Added pre-flight validation checks (directories, m4b-tool, numeric ranges, enum values)
- Fixed boolean flag handling in AutoM4bArgs (prioritize argparse when True)
- Updated Config.__init__ to handle missing config gracefully
- Tested validation with various invalid configurations
- Updated documentation (README.md, getting-started.md)
- Phase 1.4 FULLY COMPLETED ✅

**Next Steps**:
- Commit Phase 1.4 changes
- Begin Phase 1.5: Progress Reporting & Metrics

### Session 7: 2025-10-13 (Phase 1.5 Metrics Implementation)
**Duration**: ~6 hours
**Completed**:
- Created src/lib/metrics.py with ConversionMetrics singleton class
- Created src/lib/progress.py with format utilities (duration, bytes)
- Added METRICS_FILE cached property to config
- Integrated metrics recording in convert_book() (success and failure)
- Added --status CLI command with comprehensive metrics display
- Implemented metrics persistence to JSON
- Added startup metrics display
- Tracked lifetime vs session statistics
- Implemented recent conversions and failures tracking
- Built and tested Docker image (darthdobber/auto-m4b:test-metrics)
- Updated docker-compose.local.yml for testing
- Updated documentation (README.md, getting-started.md, PROJECT_ROADMAP.md)
- Phase 1.5 FULLY COMPLETED ✅ (pending manual testing)

**Next Steps**:
- User performs manual testing with test audiobooks
- Commit Phase 1.5 changes after successful testing
- Begin Phase 2 planning

### Session 8: 2025-10-13 (Phase 2.0.1 Data Contract)
**Duration**: ~3 hours
**Completed**:
- Reviewed all project documentation (README, architecture, workflows, roadmap)
- Inventoried existing data sources: ConversionMetrics, InboxState, retry scheduler, Config
- Identified 5 data gaps with resolution strategies
- Drafted comprehensive API data contract for 5 dashboard endpoints
- Documented polling cadence, rate limits, and versioning strategy
- Created implementation checklist for Phase 2.0.2
- Published `docs/api/dashboard.md` (complete data contract specification)
- Published `docs/PHASE-2.0.1-SUMMARY.md` (executive summary and recommendations)
- Phase 2.0.1 FULLY COMPLETED ✅

**Key Findings**:
- Dashboard can achieve 85-90% functionality with existing data sources
- Real-time progress tracking deferred to Phase 2.1.1 (requires refactoring)
- Intake manifest for passthrough M4B deferred to Phase 2.4
- Retry schedule and series metadata ready for immediate implementation in 2.0.2
- FastAPI recommended for endpoint implementation (auto-generates OpenAPI spec)
- No critical blockers for Phase 2.0.2

**Next Steps**:
- Stakeholder review of data contract and summary
- Begin Phase 2.0.2: Implement Read-Only Status Endpoints

### Session 9 (Planned): Phase 2 Blueprint & Manifest Draft
**Focus**: Finalize intake manifest schema, UI wireframes, and monitoring requirements.
**Deliverables**:
- Draft manifest JSON schema + example outputs for converted and passthrough books
- UI mockups showing queue, tagging state, and manual actions
- Monitoring checklist (metrics, health endpoints, alert thresholds)

### Session 9 (Planned): beets-audible Integration Design
**Focus**: Complete Phase 3.1 analysis, produce integration design doc, choose credential strategy.
**Deliverables**:
- Data mapping table (manifest → beets fields → mp3tag expectations)
- Decision on fork vs extension for beets-audible with TODO list
- Security plan for storing Audible tokens and caching lookups

### Session 10 (Planned): Tagging Prototype & Pilot
**Focus**: Implement minimal manifest-to-beets pipeline on sample books.
**Deliverables**:
- `scripts/run_beets_tagging.py` prototype
- Updated manifest with tagging results section
- Metrics snapshot showing tagging latency and error handling

---

## Quick Reference

### Current Working Directory
```bash
/home/robby/Scripts/Projects/auto-m4b-compare/darthdobber-auto-m4b
```

### Key Commands
```bash
# Build image
docker build -t darthdobber/auto-m4b:latest .

# Run tests
pipenv run tests

# Validate config
python -m src --validate

# Check status
python -m src --status

# Planned (Phase 3): manual tagging trigger
# python -m src --tag /path/to/book
```

### Important Files
- `Dockerfile` - Container definition
- `src/lib/config.py` - Configuration management
- `src/lib/run.py` - Main processing logic
- `src/lib/inbox_state.py` - State management
- `src/auto_m4b.py` - Application entry point
- `converted/<book>/intake.json` - Planned manifest output for tagging (Phase 2.4)

---

## Notes & Decisions

### Design Decisions
- **Runtime PUID/PGID**: Use entrypoint script pattern (like LinuxServer.io)
- **Retry Logic**: Exponential backoff with max 3 retries default
- **Documentation**: Keep in-repo for easy access
- **Web UI**: Will be optional, not required for CLI use
- **Tagging Integration**: Orchestrate via manifest-driven worker that invokes beets fork; tagging is idempotent and separable from conversion loop

### Technical Debt
- Some functions in run.py are very long (90+ lines)
- Global state in InboxState could cause issues with parallel processing
- Test coverage is unknown, needs assessment
- Intake manifest schema and tagging pipeline not yet implemented; risk of ad-hoc coupling if delayed

### Future Considerations
- Multi-architecture builds (ARM64 support)
- Kubernetes deployment examples
- Cloud storage integration
- Advanced metadata from Audible/Goodreads API
- Optional webhooks for Calibre, Jellyseerr, or other download automation tools
- Evaluate moving manifests/metrics into lightweight database when concurrency increases

---

## Success Metrics

### Phase 1 Success Criteria
- [x] Docker image pulls in <1 minute vs 30 minute build
- [x] 90%+ of transient errors auto-recover
- [x] New users complete first conversion in <15 minutes
- [x] Config validation catches 100% of invalid configs
- [x] Users can track conversion history and metrics

### Tagging Pipeline Success (Targets)
- [ ] 95%+ of books exit tagging stage with complete metadata on first attempt
- [ ] Audible lookups average <2 seconds due to caching and parallelization
- [ ] Manual override needed for <10% of books per month
- [ ] Intake manifest schema kept backward compatible across releases
- [ ] Downstream library update latency <5 minutes after tagging complete

### Overall Project Success
- [ ] GitHub stars increase 3x
- [ ] Docker Hub pulls > 1000/month
- [ ] Issues/questions decrease 50%
- [ ] Active contributors increase
- [ ] Featured in awesome-selfhosted lists
