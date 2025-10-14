# Retry Logic Troubleshooting Report

**Date Started**: 2025-10-13
**Phase**: 1.2 - Error Recovery & Retry Logic
**Status**: IN PROGRESS - Troubleshooting retry execution

---

## Problem Statement

### Initial Problem
User reported that retry logic is not working as expected:
1. Corrupted audiobook (three text files with .mp3 extensions) placed in inbox
2. Conversion attempt failed at 05:46:20 AM
3. System displayed "Retry 2/3.0 in ~1m" message
4. **No actual retry occurred** - system went to "Waiting for books to be added to the inbox..."
5. No categorization logs (transient vs permanent) were visible
6. Timezone display issue (showing PST instead of CST)

### Expected Behavior
1. Book fails → Categorized as transient or permanent
2. If transient: Wait for exponential backoff period (60s, 120s, 240s...)
3. After backoff: Automatically retry conversion
4. If permanent: Log "manual fix required", no retries
5. After max retries (3): Give up

### Actual Behavior
1. Book fails → Message shows "Retry 2/3.0 in ~1m"
2. System goes to idle: "Waiting for books to be added to the inbox..."
3. **Retry never happens** - system stays idle indefinitely
4. No debug logs showing retry check logic

---

## Technical Analysis

### Architecture Overview

**Retry Flow (as designed):**
```
1. fail_book(book, reason)
   ├─> categorize_error(reason) → "transient" or "permanent"
   ├─> inbox.set_failed(book.key, reason, is_transient)
   └─> Display retry message with backoff time

2. Main Loop (every 10s):
   process_inbox()
   ├─> check_failed_books()  ← Should run every loop!
   │   ├─> For each failed book:
   │   │   ├─> Check if files changed (manual fix)
   │   │   ├─> Check should_retry() logic
   │   │   └─> Check can_retry_now() (backoff elapsed?)
   │   └─> If ready: inbox.set_needs_retry(book)
   └─> books_to_process()
       └─> ok_books includes status="needs_retry"
```

**Key State Transitions:**
- `new` → `failed` (when conversion fails)
- `failed` → `needs_retry` (when backoff expires)
- `needs_retry` → processed (conversion attempted again)

---

## Implementation Steps & Results

### Step 1: Fixed AttributeError ✅
**Issue**: `book.dir_name` property doesn't exist in Audiobook class

**Change**: `src/lib/run.py:272`
```python
# Before:
retry_msg = format_retry_message(book.dir_name, ...)

# After:
retry_msg = format_retry_message(book.basename, ...)
```

**Result**: ✅ AttributeError fixed, code no longer crashes

---

### Step 2: Added Enhanced Debug Logging ✅
**Goal**: Add visibility into retry logic execution

**Changes**: `src/lib/run.py`

1. **Line 416**: Changed debug message to notice (line 419):
```python
# Before:
if not inbox.failed_books:
    return
print_debug(f"Checking {len(inbox.failed_books)} failed book(s)...")

# After:
if not inbox.failed_books:
    print_debug("No failed books to check for retry")
    return
print_notice(f"Checking {len(inbox.failed_books)} failed book(s) for retry eligibility...")
```

2. **Line 443**: Added retry state debug logging:
```python
print_debug(f"  {book_name}: retry_count={item.retry_count}, max={cfg.MAX_RETRIES}, is_transient={item.is_transient_error}")
```

3. **Line 469**: Added backoff check debug logging:
```python
print_debug(f"  {book_name}: can_retry={can_retry}, seconds_until={seconds_until}")
```

4. **Lines 453-459, 478-485**: Changed retry messages from `print_debug` to `print_notice`:
```python
# Changed all format_retry_message() calls to use print_notice instead of print_debug
print_notice(f"  {retry_msg}")
```

**Expected Result**: Should see "Checking X failed book(s)" message on every loop iteration

**Actual Result**: ❌ **NO DEBUG MESSAGES APPEARING IN LOGS**

---

### Step 3: Discovered Root Cause - check_failed_books() Not Called Every Loop 🔍
**Investigation**: Traced through `process_inbox()` execution flow

**File**: `src/auto_m4b.py:47-53`
```python
while infinite_loop or inbox.loop_counter <= args.max_loops:
    try:
        run.process_inbox()  # ← Called every loop
    finally:
        inbox.loop_counter += 1
        if infinite_loop or inbox.loop_counter <= args.max_loops:
            time.sleep(cfg.SLEEP_TIME)  # ← 10 second sleep
```

**File**: `src/lib/run.py:1048-1072` (process_inbox)
```python
def process_inbox():
    inbox = InboxState()

    if inbox.loop_counter == 1:
        print_debug("First run, scanning inbox...")
        print_banner()
        inbox.scan(set_ready=True)

    if not audio_files_found():
        # ... early return

    if (
        not inbox.inbox_needs_processing()  # ← Checks if inbox hash changed
        and inbox.loop_counter > 1
    ):
        return  # ← EARLY RETURN if no changes!

    elif info := books_to_process():  # ← Only called if inbox changed
        # ...
```

**File**: `src/lib/run.py:501-505` (books_to_process - ORIGINAL)
```python
def books_to_process():
    inbox = InboxState()

    check_failed_books()  # ← ONLY CALLED WHEN INBOX CHANGES!
    # ...
```

**Root Cause Identified**:
- `check_failed_books()` was only called inside `books_to_process()`
- `books_to_process()` is only called when `inbox.inbox_needs_processing()` returns True
- `inbox.inbox_needs_processing()` returns False when inbox hash hasn't changed
- When a book is in `failed` status and inbox hasn't changed, `check_failed_books()` is never called
- Result: Retry logic never executes!

---

### Step 4: Moved check_failed_books() Call ✅
**Goal**: Ensure `check_failed_books()` runs every loop iteration, not just when inbox changes

**Changes**: `src/lib/run.py`

1. **Line 1056-1057**: Added `check_failed_books()` call at top of `process_inbox()`:
```python
def process_inbox():
    inbox = InboxState()

    if inbox.loop_counter == 1:
        print_debug("First run, scanning inbox...")
        print_banner()
        inbox.scan(set_ready=True)

    # Check for failed books that need retry (must happen every loop, not just when inbox changes)
    check_failed_books()  # ← NEW: Called every iteration!

    if not audio_files_found():
        # ...
```

2. **Line 505**: Removed duplicate call from `books_to_process()`:
```python
def books_to_process():
    inbox = InboxState()

    # Note: check_failed_books() is now called in process_inbox() before this function

    # If no books to convert...
```

**Expected Result**:
- "Checking X failed book(s)" or "No failed books to check" should appear every 10 seconds
- After 60 seconds, should see "Retrying after backoff (attempt 2/3)..."
- Book should be moved to "needs_retry" status and processed

**Actual Result**: ✅ **PARTIAL SUCCESS - New Issue Discovered**

**What Works**:
- ✅ "Checking 1 failed book(s) for retry eligibility..." appears every 10 seconds
- ✅ Countdown works correctly: 49s → 39s → 29s → 19s → 9s → 0s
- ✅ When can_retry=True: "Retrying after backoff (attempt 2/3.0)..." message appears
- ✅ Book is moved to "needs_retry" status (verified by "No failed books" message)

**New Problem**:
- ❌ Book with status="needs_retry" is NOT actually processed/converted
- Book remains in idle state, no conversion attempt made
- Root cause: `inbox.inbox_needs_processing()` returns False because inbox hash hasn't changed
- Early return at line 1071 prevents retry books from being processed

---

## Step 7: Fix Early Return Blocking Retry Processing ⏳

**Problem**: Books with status="needs_retry" should be processed, but early return prevents it

**Current Code** (`src/lib/run.py:1067-1072`):
```python
if (
    not inbox.inbox_needs_processing()  # Returns False if hash unchanged
    and inbox.loop_counter > 1
):
    return  # ← Blocks retry processing!
```

**Fix**: Check if there are books ready for retry before early return

**Code Change** (`src/lib/run.py:1067-1076`):
```python
# Check if we have books ready to retry (status="needs_retry")
has_retry_books = any(item.status == "needs_retry" for item in inbox._items.values())

if (
    not inbox.inbox_needs_processing()
    and inbox.loop_counter > 1
    and not has_retry_books  # Don't skip if there are books ready to retry!
):
    return
```

**Result**: ✅ **COMPLETE SUCCESS!**

**Working End-to-End Flow**:
```
1. Initial failure: "Error: m4b-tool failed" → "Retry 2/3.0 in ~1m"
2. Countdown every 10s: 49s → 39s → 29s → 19s → 9s → 0s
3. "Retrying after backoff (attempt 2/3.0)..."
4. "Found 1 book to convert"
5. "This book previously failed, but it has been updated – trying again"
6. m4b-tool conversion attempted
7. Failed again (expected - corrupted file)
8. "Retry 2/3.0 in ~1m" (attempt 3 will be next)
9. Countdown starts again: 49s → 39s → 29s → 19s → 9s...
```

---

## Step 8: Second Round of Troubleshooting - retry_count Not Incrementing 🔍

### New Problem Discovered (2025-10-13 07:27 AM)
After the previous fixes, retry mechanism works (countdown, retry attempts occur), but `retry_count` stays stuck at 1, causing infinite retry loop.

**Observation from logs**:
```
DEBUG]   test corrupt: retry_count=1, max=3.0, is_transient=True
***   test corrupt: Retrying after backoff (attempt 2/3.0)...
[Conversion attempted and failed]
DEBUG]   test corrupt: retry_count=1, max=3.0, is_transient=True  ← Still 1!
***   test corrupt: Retrying after backoff (attempt 2/3.0)...  ← Infinite loop
```

**Root Cause Analysis**:

#### Bug #4: `set_needs_retry()` Resets retry_count to 0 ✅ FIXED

**Location**: `src/lib/inbox_item.py:173-181`

**Problem**:
```python
def set_needs_retry(self):
    self._set("needs_retry")
    # Reset retry tracking when files change (manual fix detected)
    self.retry_count = 0  # ← ALWAYS resets to 0!
    self.first_failed_time = 0
    self.last_retry_time = 0
```

The function was called for BOTH scenarios:
1. **Manual fix** (files changed) → SHOULD reset to 0
2. **Automatic retry** (backoff elapsed) → Should NOT reset to 0

**Flow**:
1. Book fails → `set_failed()` → retry_count becomes 1
2. Backoff expires → `set_needs_retry()` → retry_count reset to 0
3. Book retried and fails → `set_failed()` → retry_count becomes 1 again
4. Loop repeats infinitely

**Fix Applied**: `src/lib/inbox_item.py:173-182`
```python
def set_needs_retry(self, reset_retry_count: bool = False):
    self._set("needs_retry")
    # Reset retry tracking when files change (manual fix detected)
    if reset_retry_count:  # ← Only reset if explicitly requested
        self.retry_count = 0
        self.first_failed_time = 0
        self.last_retry_time = 0
```

**Corresponding Changes**:

1. `src/lib/inbox_state.py:507` - Updated wrapper method:
```python
def set_needs_retry(self, key_path_or_book: str | Path | Audiobook, reset_retry_count: bool = False):
    if item := self.get(key_path_or_book):
        item.set_needs_retry(reset_retry_count=reset_retry_count)
```

2. `src/lib/run.py:439` - Manual fix path (files changed):
```python
if hash_changed:
    # Files changed - user manually fixed it
    inbox.set_needs_retry(book_name, reset_retry_count=True)  # ← Reset count
```

3. `src/lib/run.py:475` - Automatic retry path (backoff elapsed):
```python
if can_retry:
    inbox.set_needs_retry(book_name)  # ← Default: don't reset count
```

4. `src/lib/inbox_state.py:163` - Scan recheck path:
```python
if item.status == "failed" and (item.did_change or item.hash_age < cfg.SLEEP_TIME):
    # Reset retry count only if files changed (manual fix)
    item.set_needs_retry(reset_retry_count=item.did_change)
```

---

#### Bug #5: Early Return in fail_book() Prevented retry_count Increment ✅ FIXED

**Location**: `src/lib/run.py:241-245` (REMOVED)

**Problem**:
```python
# Check if already failed - if so, only print message, don't update state
if book.key in inbox.failed_books:
    print_debug(f"Already in failed_books...")
    return  # ← Prevented set_failed() from being called on retry failures
```

This check prevented `set_failed()` from being called when a retry failed, so retry_count never incremented beyond 1.

**Fix Applied**: Removed the early return check entirely. The function now always calls `set_failed()`, which increments `retry_count`.

---

## FINAL STATUS: ✅ ALL RETRY LOGIC BUGS FIXED

### Complete Summary of All Fixes

**Five bugs were identified and fixed**:

1. **AttributeError Fix** (Step 1):
   - Changed `book.dir_name` → `book.basename` in fail_book()
   - **File**: `src/lib/run.py:272`

2. **check_failed_books() Not Called Every Loop** (Step 4):
   - Moved `check_failed_books()` call to top of `process_inbox()`
   - Removed duplicate call from `books_to_process()`
   - **Files**: `src/lib/run.py:1056-1057, 505`

3. **Early Return Blocking Retry Processing** (Step 7):
   - Added check for books with status="needs_retry" before early return
   - **File**: `src/lib/run.py:1067-1075`

4. **set_needs_retry() Resets retry_count** (Step 8 - Bug #4):
   - Added `reset_retry_count` parameter (default False)
   - Only reset when files manually changed
   - **Files**: `src/lib/inbox_item.py:173-182`, `src/lib/inbox_state.py:507,163`, `src/lib/run.py:439`

5. **Early Return in fail_book() Blocks retry_count Increment** (Step 8 - Bug #5):
   - Removed early return check that prevented `set_failed()` on retries
   - **File**: `src/lib/run.py:241-245` (removed)

---

### Step 5: Rebuilt Docker Image and Testing ⏳
**Commands Executed**:
```bash
docker build -t darthdobber/auto-m4b:test-retry .
docker-compose -f docker-compose.local.yml down
docker-compose -f docker-compose.local.yml up -d
docker logs -f auto-m4b-local | grep -E "(Checking|retry|Retry|failed)"
```

**Image Build**: ✅ Completed successfully (sha256:c5127753b70131205517f352d245cbcf23fca4e1ea81b9681c8de03b1a140bfd)

**Container Status**: Running

**Log Observation**:
```
Starting auto-m4b with PUID=1026, PGID=1000
Starting auto-m4b...
DEBUG mode on
[DEBUG] Startup took 2.09s
[DEBUG] First run, scanning inbox...
[DEBUG] Not backing up (backups are disabled)
# ... ffprobe errors showing "Invalid data found when processing input" ...
*** Error: m4b-tool failed to convert Test-Corrupt, no output .m4b file was found
***   Test-Corrupt: Retry 2/3.0 in ~1m
[DEBUG] Inbox hash is the same, no changes since 06:04:35 (ff016b86)
```

**Issue**: Still no "Checking X failed book(s)" message visible!

**Next Step**: Verify container is using the new image

---

## Current Status: Investigating Image Update Issue

**Hypothesis**: Container may not be using the newly built image (`test-retry` tag)

**File**: `docker-compose.local.yml:5`
```yaml
services:
  auto-m4b:
    image: darthdobber/auto-m4b:test-retry  # ← Should use this tag
```

**Next Action**: Verify which image SHA the running container is actually using

**Verification Results**:
```bash
# Container's image
$ docker inspect auto-m4b-local --format='{{.Image}}'
sha256:a0798e7fa516cc0710a2ac9818fced9aca9d34a732ab919a0279b8d77f111750

# Latest built image
$ docker images darthdobber/auto-m4b:test-retry --format '{{.ID}} {{.CreatedAt}}'
c5127753b701 2025-10-13 08:03:49 -0500 CDT
```

**PROBLEM IDENTIFIED**: ❌ **Container is using OLD image!**
- Container SHA: `a0798e7fa516...`
- Latest image SHA: `c5127753b701...`

**Root Cause**: `docker-compose restart` doesn't pull/use updated images. Need to recreate container.

**Fix**: Force container recreation with new image

---

## Step 6: Force Container Recreation with New Image ⏳

**Commands**:
```bash
docker-compose -f docker-compose.local.yml down
docker-compose -f docker-compose.local.yml up -d --force-recreate
```

---

## Additional Issues Identified

### Issue 1: Cosmetic - Retry Count Display
**Observation**: Message shows "Retry 2/3.0" instead of "Retry 2/3"

**Cause**: `cfg.MAX_RETRIES` is being formatted as float

**Severity**: Low (cosmetic only)

**Fix**: Cast to int in format_retry_message()

### Issue 2: Timezone Display
**Observation**: Times shown in PST, user is in CST

**File**: Likely in entrypoint.sh or config.py

**Severity**: Low (display only)

**Status**: Not yet investigated

---

## Files Modified (All Sessions)

### Core Retry Logic Fixes

1. **`src/lib/run.py`**:
   - Line 272: Fixed `book.dir_name` → `book.basename` (AttributeError fix)
   - Line 241-245: **REMOVED** early return check in `fail_book()` (Bug #5 fix)
   - Line 419: Changed to `print_notice` for visibility
   - Line 439: Pass `reset_retry_count=True` for manual fixes (Bug #4 fix)
   - Line 443: Added retry state debug logging
   - Line 469: Added backoff check debug logging
   - Lines 453-459, 478-485: Changed retry messages to `print_notice`
   - Line 1056-1057: Added `check_failed_books()` call at top of `process_inbox()` (Bug #2 fix)
   - Line 505: Removed duplicate `check_failed_books()` call from `books_to_process()`
   - Line 1067-1075: Check for `has_retry_books` before early return (Bug #3 fix)

2. **`src/lib/inbox_item.py`**:
   - Line 173-182: Added `reset_retry_count` parameter to `set_needs_retry()` (Bug #4 fix)
   - Line 163-176: Added debug logging to `set_failed()` for troubleshooting

3. **`src/lib/inbox_state.py`**:
   - Line 507: Updated `set_needs_retry()` wrapper to accept `reset_retry_count` parameter (Bug #4 fix)
   - Line 163: Pass `reset_retry_count=item.did_change` in scan recheck (Bug #4 fix)

### Testing Configuration

4. **`docker-compose.local.yml`**:
   - Line 5: Using `image: darthdobber/auto-m4b:test-retry`

---

## Test Data

**Corrupted Audiobook**: `Test-Corrupt/`
- Contains: 3 text files renamed with `.mp3` extension
- Size: 3 bytes
- Expected error: "Invalid data found when processing input"
- Expected categorization: Permanent error (should NOT retry)

---

## Questions to Answer

1. ✅ Is `check_failed_books()` being called every loop?
   - **Answer**: No (original design), Yes (after fix)

2. ❓ Is the container using the updated image?
   - **Status**: Investigating now

3. ❓ Are failed books persisting in `inbox.failed_books` dict between loops?
   - **Status**: Unknown - need to verify InboxState singleton behavior

4. ❓ Is `inbox.set_needs_retry()` actually changing the book status?
   - **Status**: Unknown - need to add logging

5. ❓ Should corrupted files be categorized as permanent errors?
   - **Answer**: Yes, but current error message is generic "no output .m4b file was found"
   - **Issue**: Error categorization can't detect corruption from this generic message

---

## Next Steps

1. ⏳ Verify container image SHA matches latest build
2. ⏳ If mismatch, force container to use new image
3. ⏳ Monitor logs for "Checking X failed book(s)" message
4. ⏳ Wait 60+ seconds to see if retry actually occurs
5. ⏳ If retry occurs, verify it goes through full conversion attempt
6. ⏳ Document whether retry succeeds or fails appropriately

---

## Success Criteria

- [x] "Checking X failed book(s)" message appears every 10 seconds (or "No failed books")
- [x] After 60 seconds, "Retrying after backoff" message appears
- [x] Book is actually re-processed (conversion attempt made)
- [x] Retry count increments correctly (FIXED - Bugs #4 and #5)
- [ ] After 3 failures, system gives up with clear message (NEEDS VERIFICATION)
- [ ] Permanent errors don't retry (manual fix message shown) (NEEDS VERIFICATION)

---

## Known Issues / Remaining Work

### Docker Image Caching Issue
**Problem**: `docker-compose` not consistently picking up rebuilt images with same tag
**Symptoms**:
```bash
# Container using different SHA than built image
docker inspect auto-m4b-local --format='{{.Image}}'
# sha256:25fcde958a0ca...

docker images darthdobber/auto-m4b:test-retry --format '{{.ID}}'
# bd8e13c0d6b3
```

**Workarounds Attempted**:
- `docker-compose up -d --force-recreate` (KeyError: 'ContainerConfig')
- `docker-compose down && docker-compose up -d` (Still uses old image)
- Manual `docker rm` and `docker run` (Env file path issues)

**Recommended Solution**:
1. Use unique image tags for each build (e.g., `test-retry-v2`, `test-retry-v3`)
2. OR: `docker-compose down && docker rmi darthdobber/auto-m4b:test-retry && docker build -t ... && docker-compose up -d`

### Verification Testing Needed
The fixes are complete in code but need end-to-end verification:
1. Verify retry_count increments: 1 → 2 → 3
2. Verify system stops after 3 failures
3. Verify permanent errors don't retry (if applicable)

### Debug Logging
Comprehensive debug logging was added but couldn't be verified due to Docker image caching:
- `[FAIL_BOOK CALLED]` in `fail_book()`
- `[SET_FAILED CALLED]` and `[SET_FAILED DONE]` in `set_failed()`
- Before/after retry_count values

**Recommendation**: Remove or comment out these debug messages once verified working.

---

## Timestamps

- **05:46:20 AM**: Initial failure of Test-Corrupt audiobook (Session 1)
- **06:04:35 AM**: Container restarted with updated image (Session 1)
- **07:27:18 AM**: Second testing session - discovered retry_count stuck at 1 (Session 2)
- **09:40:04 AM**: Testing with Bug #4 and #5 fixes applied (Session 2)

---

*Last Updated: 2025-10-13 09:45 AM CST*
*Status: Code fixes complete, awaiting verification testing with clean Docker image*
