# Inbox State API

The `InboxState` class manages state tracking and change detection for audiobooks in the inbox folder.

## Module

`src.lib.inbox_state`

## Class: InboxState

A singleton state manager that tracks which books are in the inbox, their processing status, and detects changes via file hashing.

### Accessing InboxState

```python
from src.lib.inbox_state import InboxState

# Get singleton instance
inbox = InboxState()

# Scan for books
inbox.scan()

# Get all pending books
pending = inbox.pending
```

## Core Methods

### scan()

Scan the inbox directory for new or changed books.

```python
inbox = InboxState()
inbox.scan()

# Scan without syncing failed books
inbox.scan(skip_failed_sync=True)
```

**Parameters:**
- `skip_failed_sync: bool = False` - Skip syncing failed books

**Side Effects:**
- Updates internal book tracking
- Detects new books
- Detects file changes via hashing
- Updates `_last_scan` timestamp

### get()

Get an InboxItem by key, path, or Audiobook object.

```python
# Get by key
item = inbox.get("book-key-12345")

# Get by path
item = inbox.get(Path("/inbox/MyBook"))

# Get by audiobook
item = inbox.get(audiobook)
```

**Parameters:**
- `key_path_hash_or_book: str | Path | Audiobook | None`

**Returns:** `InboxItem | None`

### set()

Set or update an InboxItem in state.

```python
from src.lib.inbox_item import InboxItem

item = InboxItem(Path("/inbox/MyBook"))
inbox.set(item, status="processing")

# Update with timestamp
inbox.set(item, last_updated=time.time())
```

**Parameters:**
- `key_path_or_book: str | Path | Audiobook | InboxItem`
- `status: InboxItemStatus | None` - Item status
- `last_updated: float | None` - Last update timestamp

### has()

Check if an item exists in inbox state.

```python
if inbox.has("book-key-12345"):
    print("Book is tracked")

if inbox.has(Path("/inbox/MyBook")):
    print("Book exists")
```

**Parameters:**
- `key_path_or_book: str | Path | Audiobook`

**Returns:** `bool`

### remove()

Remove an item from inbox state.

```python
inbox.remove("book-key-12345")
inbox.remove(Path("/inbox/MyBook"))
inbox.remove(audiobook)
```

**Parameters:**
- `key_path_or_book: str | Path | Audiobook`

### mark_as_processing()

Mark a book as currently being processed.

```python
inbox.mark_as_processing(audiobook)
```

**Parameters:**
- `book: Audiobook | InboxItem`

### mark_as_failed()

Mark a book as failed with optional error message.

```python
inbox.mark_as_failed(audiobook, error="Corrupted audio file")
```

**Parameters:**
- `book: Audiobook | InboxItem`
- `error: str | None` - Error message

## State Properties

### Books by Status

| Property | Type | Description |
|----------|------|-------------|
| `pending` | `list[InboxItem]` | Books waiting to be processed |
| `processing` | `list[InboxItem]` | Books currently being processed |
| `failed` | `list[InboxItem]` | Books that failed processing |
| `completed` | `list[InboxItem]` | Successfully processed books |

### Counts

| Property | Type | Description |
|----------|------|-------------|
| `pending_count` | `int` | Number of pending books |
| `processing_count` | `int` | Number of books being processed |
| `failed_count` | `int` | Number of failed books |
| `completed_count` | `int` | Number of completed books |

### State Information

| Property | Type | Description |
|----------|------|-------------|
| `ready` | `bool` | Whether state is ready for processing |
| `loop_counter` | `int` | Number of processing loops completed |
| `banner_printed` | `bool` | Whether startup banner was printed |
| `last_run_start` | `float` | Timestamp of last scan |

## Class: InboxItem

Represents a single audiobook item in the inbox.

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `path` | `Path` | Path to audiobook |
| `key` | `str` | Unique identifier (hash) |
| `status` | `InboxItemStatus` | Current status |
| `error` | `str \| None` | Error message (if failed) |
| `last_updated` | `float` | Last update timestamp |
| `is_maybe_series_parent` | `bool` | Possibly a series parent directory |

### Methods

#### to_audiobook()

Convert InboxItem to Audiobook object.

```python
item = inbox.get("book-key")
book = item.to_audiobook()
```

**Returns:** `Audiobook`

#### reload()

Reload item state from filesystem.

```python
item.reload()
```

## InboxItemStatus

Valid status values:

```python
InboxItemStatus = Literal["pending", "processing", "completed", "failed"]
```

## Usage Examples

### Basic State Tracking

```python
from src.lib.inbox_state import InboxState

# Get state manager
inbox = InboxState()

# Scan inbox
inbox.scan()

# Check what's pending
print(f"Found {inbox.pending_count} books to process")

for item in inbox.pending:
    print(f"  - {item.path.name}")
```

### Processing Books

```python
from src.lib.inbox_state import InboxState

inbox = InboxState()
inbox.scan()

for item in inbox.pending:
    # Mark as processing
    inbox.mark_as_processing(item)

    try:
        # Convert book
        book = item.to_audiobook()
        success = convert_book(book)

        if success:
            # Remove from tracking (completed)
            inbox.remove(item)
        else:
            # Mark as failed
            inbox.mark_as_failed(item, error="Conversion failed")

    except Exception as e:
        inbox.mark_as_failed(item, error=str(e))
```

### Checking Failed Books

```python
inbox = InboxState()
inbox.scan()

if inbox.failed_count > 0:
    print(f"Found {inbox.failed_count} failed books:")
    for item in inbox.failed:
        print(f"  - {item.path.name}: {item.error}")
```

### Filtering Books

```python
from src.lib.config import cfg

inbox = InboxState()
inbox.scan()

# Filter by pattern
if cfg.MATCH_FILTER:
    import re
    pattern = re.compile(cfg.MATCH_FILTER)
    matching = [item for item in inbox.pending
                if pattern.search(item.path.name)]
    print(f"Found {len(matching)} matching books")
```

### Manual State Management

```python
from pathlib import Path
from src.lib.inbox_state import InboxState
from src.lib.inbox_item import InboxItem

inbox = InboxState()

# Add a book manually
item = InboxItem(Path("/inbox/MyBook"))
inbox.set(item, status="pending")

# Update status
inbox.set(item, status="processing")

# Check if exists
if inbox.has(item):
    print("Book is tracked")

# Remove
inbox.remove(item)
```

### State Persistence

State persists in memory during application runtime but is rebuilt from filesystem on each scan.

```python
# State is rebuilt on scan
inbox.scan()

# Previous processing state is maintained
assert inbox.loop_counter > 0
```

## Hash-Based Change Detection

InboxState extends `Hasher` to detect file changes.

### How It Works

1. **Initial Scan**: Hash all audio files in each book directory
2. **Subsequent Scans**: Re-hash and compare
3. **Changes Detected**: If hash differs, files have changed
4. **Stability Wait**: Wait `WAIT_TIME` before processing

### Hash Properties

| Property | Type | Description |
|----------|------|-------------|
| `hash` | `str` | Current hash of directory |
| `hash_age` | `float` | Seconds since last hash update |
| `is_stable` | `bool` | Whether files haven't changed recently |

### Example

```python
item = inbox.get("book-key")

# Check if files are stable
if item.is_stable:
    print("Files haven't changed, safe to process")
else:
    print(f"Files changed {item.hash_age}s ago, waiting...")
```

## Integration with Processing Pipeline

### In run.py

```python
from src.lib.inbox_state import InboxState

def process_inbox():
    inbox = InboxState()

    # Scan for books
    inbox.scan()

    # Get pending books
    for item in inbox.pending:
        # Skip if not stable
        if not item.is_stable:
            continue

        # Convert to audiobook
        book = item.to_audiobook()

        # Mark as processing
        inbox.mark_as_processing(item)

        try:
            # Process
            convert_book(book)
            inbox.remove(item)  # Success
        except Exception as e:
            inbox.mark_as_failed(item, error=str(e))
```

## Decorators

### @scanner

Decorator that triggers a scan if hash is stale.

```python
from src.lib.inbox_state import scanner

@scanner
def my_method(self):
    # Scan will run if hash_age > SLEEP_TIME
    ...
```

### @requires_scan

Decorator that ensures a scan has been performed.

```python
from src.lib.inbox_state import requires_scan

@requires_scan
def my_method(self):
    # Guaranteed to have scanned inbox
    ...
```

## Performance Considerations

### Caching

- Book list is cached until next `scan()`
- Hashes are cached until files change
- Use `@cached_property` for expensive operations

### Scan Frequency

- Controlled by `SLEEP_TIME` (default 10s)
- Full filesystem scan on each `scan()`
- Consider increasing for large libraries

### Memory Usage

- Keeps all InboxItems in memory
- Minimal per-book overhead (~1KB)
- Scales to thousands of books

## Limitations

### Current Limitations

1. **No persistence**: State lost on restart
2. **No retry logic**: Failed books stay failed (Phase 1.2)
3. **Sequential processing**: One book at a time (Phase 3.1)

### Future Enhancements

- **State persistence** (JSON/SQLite)
- **Retry with backoff** (Phase 1.2)
- **Parallel processing** (Phase 3.1)
- **Metrics tracking** (Phase 1.5)

## See Also

- [Audiobook API](audiobook.md) - Audiobook data model
- [Config API](config.md) - Configuration management
- [Architecture Overview](../architecture.md) - System design
