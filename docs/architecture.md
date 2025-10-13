# Architecture Overview

This document explains Auto-M4B's system design, component structure, and data flow.

## High-Level Overview

Auto-M4B is a Python-based audiobook conversion pipeline that runs in Docker. It continuously monitors an inbox folder, processes audiobooks through various stages, and outputs chapterized M4B files.

```
┌──────────────┐
│ User adds    │
│ audiobook to │
│ inbox/       │
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────────────────┐
│           Auto-M4B Container                 │
│                                              │
│  ┌────────────────────────────────────────┐ │
│  │  1. Scanner (Inbox State)              │ │
│  │     - Detect new books                 │ │
│  │     - Track processing state           │ │
│  └──────────────┬─────────────────────────┘ │
│                 │                            │
│                 ▼                            │
│  ┌────────────────────────────────────────┐ │
│  │  2. Audiobook Parser                   │ │
│  │     - Extract metadata                 │ │
│  │     - Analyze structure                │ │
│  └──────────────┬─────────────────────────┘ │
│                 │                            │
│                 ▼                            │
│  ┌────────────────────────────────────────┐ │
│  │  3. Converter (m4b-tool)               │ │
│  │     - Merge audio files                │ │
│  │     - Create chapters                  │ │
│  │     - Apply metadata                   │ │
│  └──────────────┬─────────────────────────┘ │
│                 │                            │
│                 ▼                            │
│  ┌────────────────────────────────────────┐ │
│  │  4. Post-Processor                     │ │
│  │     - Move to output                   │ │
│  │     - Archive originals                │ │
│  │     - Cleanup                          │ │
│  └────────────────────────────────────────┘ │
│                                              │
└──────────────────────────────────────────────┘
       │
       ▼
┌──────────────┐
│ Converted    │
│ M4B ready in │
│ converted/   │
└──────────────┘
```

## Directory Structure

```
auto-m4b/
├── src/
│   ├── __main__.py           # CLI entry point
│   ├── auto_m4b.py           # Application loop
│   └── lib/
│       ├── audiobook.py      # Audiobook data model
│       ├── config.py         # Configuration management
│       ├── inbox_state.py    # State tracking & scanning
│       ├── inbox_item.py     # Individual book items
│       ├── run.py            # Main processing logic
│       ├── m4btool.py        # m4b-tool wrapper
│       ├── fs_utils.py       # File system utilities
│       ├── id3_utils.py      # Metadata extraction
│       ├── ffmpeg_utils.py   # Audio analysis
│       ├── parsers.py        # Path/filename parsing
│       ├── hasher.py         # File hashing for change detection
│       ├── logger.py         # Logging utilities
│       ├── term.py           # Terminal output formatting
│       └── typing.py         # Type definitions
├── Dockerfile                # Container definition
├── entrypoint.sh            # Container startup script
├── pyproject.toml           # Python dependencies
└── docs/                    # Documentation
```

## Core Components

### 1. Application Loop (`auto_m4b.py`)

The main application loop that:
- Initializes configuration
- Runs startup checks
- Continuously processes the inbox
- Handles errors and recovery

**Key Functions:**
- `app()`: Main entry point
- `use_error_handler()`: Error handling context manager

**Flow:**
```python
while infinite_loop or loop_counter <= max_loops:
    try:
        process_inbox()
    finally:
        loop_counter += 1
        sleep(SLEEP_TIME)
```

### 2. Configuration System (`config.py`)

Manages all settings and environment variables.

**Key Classes:**
- `Config`: Singleton configuration manager
- `AutoM4bArgs`: Command-line arguments parser

**Features:**
- Environment variable loading
- Type conversion and validation
- Cached properties for performance
- Dynamic folder path resolution

**Configuration Flow:**
```
1. Load .env file (if specified)
2. Parse command-line arguments
3. Merge with environment variables
4. Apply defaults
5. Validate and resolve paths
```

### 3. Inbox State Management (`inbox_state.py`)

Tracks which books are in the inbox and their processing status.

**Key Classes:**
- `InboxState`: Singleton state manager (extends `Hasher`)
- `InboxItem`: Individual book tracking

**Responsibilities:**
- Scan inbox for new books
- Track processing status (pending, processing, failed)
- Detect file changes via hashing
- Prevent duplicate processing

**State Tracking:**
```python
InboxItem:
  - key: str                    # Unique identifier
  - status: InboxItemStatus     # pending|processing|failed
  - path: Path                  # Book location
  - last_updated: float         # Timestamp
  - is_series_parent: bool      # Series detection
```

### 4. Audiobook Model (`audiobook.py`)

Represents an audiobook with metadata and structure information.

**Key Classes:**
- `Audiobook`: Pydantic model for audiobooks

**Properties:**
- **Metadata**: title, artist, album, year, cover art
- **File Info**: format, size, duration, bitrate
- **Structure**: standalone, folder, multi-disc, series
- **Paths**: inbox, merge, build, converted locations

**Book Structures:**
```
standalone: Single audio file (m4b, mp3, etc.)
folder:     Directory with multiple audio files
multi-disc: Multiple subdirectories (Disc 1, Disc 2, etc.)
series:     Series of books in subdirectories
```

### 5. Processing Pipeline (`run.py`)

The main processing logic that converts audiobooks.

**Key Functions:**
- `process_inbox()`: Main loop - scans and processes books
- `convert_book()`: Orchestrates conversion of a single book
- `process_already_m4b()`: Handles pre-converted M4B files
- `process_book_folder()`: Converts multi-file books
- `fail_book()`: Handles failures

**Processing Flow:**

```
┌─────────────────┐
│ Scan Inbox      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Filter Books    │ (Skip already processed, match filters)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ For Each Book:  │
└────────┬────────┘
         │
         ▼
    ┌────────────────────┐
    │ Already M4B?       │
    └─────┬──────┬───────┘
          │ Yes  │ No
          │      └───────────────┐
          │                      │
          ▼                      ▼
    ┌──────────────┐    ┌──────────────────┐
    │ Move to      │    │ Parse Metadata   │
    │ Converted    │    └────────┬─────────┘
    └──────────────┘             │
                                 ▼
                        ┌──────────────────┐
                        │ Extract Cover    │
                        └────────┬─────────┘
                                 │
                                 ▼
                        ┌──────────────────┐
                        │ Merge to M4B     │
                        │ (via m4b-tool)   │
                        └────────┬─────────┘
                                 │
                                 ▼
                        ┌──────────────────┐
                        │ Verify Output    │
                        └────────┬─────────┘
                                 │
                                 ▼
                        ┌──────────────────┐
                        │ Move to          │
                        │ Converted        │
                        └────────┬─────────┘
                                 │
                                 ▼
                        ┌──────────────────┐
                        │ Archive/Delete   │
                        │ Originals        │
                        └──────────────────┘
```

### 6. m4b-tool Wrapper (`m4btool.py`)

Interfaces with the sandreas/m4b-tool for audio conversion.

**Key Classes:**
- `M4bTool`: Command builder and executor

**Operations:**
- **merge**: Combine audio files into M4B
- **split**: Split M4B by chapters
- **chapters**: Import/export chapter data

**Example Command:**
```bash
m4b-tool merge "input_dir/" \
  --output-file="output.m4b" \
  --jobs=4 \
  --audio-bitrate=64k \
  --max-chapter-length=1800 \
  --use-filenames-as-chapters
```

### 7. File System Utilities (`fs_utils.py`)

Low-level file operations and audio file discovery.

**Key Functions:**
- `find_book_dirs_in_inbox()`: Discover books
- `find_audio_files()`: Locate audio files
- `mv_file_to_dir()`: Safe file moving with overwrite handling
- `hash_path_audio_files()`: Generate content hashes
- `clean_dir()`: Clean up working directories

### 8. Metadata Extraction (`id3_utils.py`, `parsers.py`)

Extract and parse metadata from files and paths.

**Sources:**
- **ID3 tags**: From audio files
- **Filenames**: Parse author, title, year
- **Folder structure**: Detect multi-disc, series

**Parsing Examples:**
```
"Author - Title (Year)" → Author, Title, Year
"Book 01 - Chapter Name" → Track 1, "Chapter Name"
"Disc 1/Chapter 01.mp3" → Multi-disc structure
```

## Data Flow

### Typical Book Processing

1. **Discovery**
   - User copies book to `inbox/MyBook/`
   - `InboxState` scanner detects new directory
   - Creates `InboxItem` with status `pending`

2. **Pre-Processing**
   - Hash files to detect completion
   - Wait `WAIT_TIME` for file transfers to finish
   - Create `Audiobook` object
   - Extract metadata from files and paths

3. **Conversion**
   - Copy files to working directory (`/tmp/auto-m4b/build/`)
   - Extract cover art if present
   - Call `m4b-tool merge` with appropriate flags
   - Monitor progress and logs

4. **Post-Processing**
   - Verify output M4B exists and is valid
   - Move M4B to `converted/MyBook/MyBook.m4b`
   - Archive originals to `archive/MyBook/` (if configured)
   - Create backup in `backup/` (if enabled)
   - Update `InboxItem` status to `completed`
   - Clean up working directories

5. **Error Handling**
   - On failure, mark `InboxItem` as `failed`
   - Log error details
   - Move book to failed state (currently stays in inbox)
   - Future: Retry logic (Phase 1.2)

### Folder Layout During Processing

```
inbox/
└── MyBook/                    # User's input
    ├── Chapter01.mp3
    └── Chapter02.mp3

/tmp/auto-m4b/
├── build/                     # Temporary build area
│   └── MyBook/
│       ├── Chapter01.mp3
│       ├── Chapter02.mp3
│       └── cover.jpg
├── merge/                     # (Currently unused)
└── trash/                     # Temporary cleanup

converted/
└── MyBook/                    # Final output
    ├── MyBook.m4b
    └── MyBook.chapters.txt

archive/
└── MyBook/                    # Archived originals
    ├── Chapter01.mp3
    └── Chapter02.mp3

backup/
└── MyBook/                    # Backup copy
    ├── Chapter01.mp3
    └── Chapter02.mp3
```

## State Management

### InboxItem States

```
pending     → Book detected, not yet processed
processing  → Currently being converted
completed   → Successfully converted and moved
failed      → Error during processing
```

### State Transitions

```
         ┌──────────┐
    ┌───►│ pending  │◄───┐
    │    └────┬─────┘    │
    │         │          │
    │         ▼          │
    │    ┌──────────┐   │
    │    │processing│   │
    │    └────┬─────┘   │
    │         │          │
    │    ┌────┴─────┐    │
    │    │          │    │
    │    ▼          ▼    │
    │ ┌────────┐ ┌──────┴───┐
    └─┤ failed │ │completed │
      └────────┘ └──────────┘
```

### Hashing & Change Detection

Auto-M4B uses file hashing to:
- Detect when file transfers are complete
- Prevent processing partial uploads
- Skip already-processed books

```python
# Hash all audio files in a directory
hash = hash_path_audio_files(book_path)

# Compare with previous hash
if hash != previous_hash:
    wait_for_stability()
```

## Concurrency & Performance

### Single-Threaded Design

Auto-M4B processes books **sequentially** (one at a time):
- Simpler error handling
- Prevents resource contention
- Easier to debug

Future enhancement (Phase 3.1): Parallel processing of multiple books.

### Performance Optimizations

1. **Caching**: Extensive use of `@cached_property` for expensive operations
2. **Lazy Loading**: Metadata extracted only when needed
3. **Hashing**: Fast change detection without file comparison
4. **CPU Cores**: m4b-tool uses multiple cores for audio encoding

### Resource Usage

- **CPU**: Configurable via `CPU_CORES` (default: all cores)
- **Memory**: Typically 500MB-2GB depending on book size
- **Disk**: Requires ~3x book size during processing:
  - 1x in inbox
  - 1x in working directory
  - 1x in output/archive/backup

## Error Handling

### Error Categories

1. **User Errors**: Invalid paths, missing permissions
   - Logged with clear messages
   - Processing skipped

2. **File Errors**: Corrupted audio, missing files
   - Book marked as failed
   - Error details logged
   - Manual intervention required

3. **System Errors**: Out of disk, m4b-tool crashes
   - Fatal error file created
   - Container stops (requires manual restart)

### Recovery

Currently manual recovery:
1. Fix the issue (repair file, free space, etc.)
2. Remove book from inbox
3. Re-add book to inbox
4. Processing resumes

Future (Phase 1.2): Automatic retry with exponential backoff.

## Extension Points

### Adding New Features

1. **Pre-processors**: Add logic before conversion in `run.py`
2. **Post-processors**: Add logic after conversion in `run.py`
3. **Metadata Sources**: Extend `parsers.py` or `id3_utils.py`
4. **Output Formats**: Extend `m4btool.py` wrapper

### Plugin System (Future)

Phase 3.2 will introduce:
- Hook system for pre/post processing
- Custom metadata enrichment
- Integration with external services (Audible, Goodreads)

## Dependencies

### Core Dependencies

- **Python 3.9+**: Runtime
- **m4b-tool**: Audio conversion (sandreas/m4b-tool)
- **FFmpeg**: Audio analysis and manipulation
- **Docker**: Container runtime

### Python Libraries

- **pydantic**: Data validation
- **cachetools**: Caching utilities
- **mutagen**: ID3 tag reading
- **tinta**: Terminal colors

### Docker Image Layers

```dockerfile
Base: ubuntu:22.04
├── System packages (ffmpeg, curl, etc.)
├── PHP 8.2 & composer
├── m4b-tool (v0.5-prerelease)
├── Python 3.9+
├── gosu (for PUID/PGID switching)
└── Auto-M4B Python application
```

## Testing

Currently minimal test coverage. Future improvements (Phase 4.3):
- Unit tests for core logic
- Integration tests for full pipeline
- Fixture-based testing with sample audiobooks

## Logging

### Log Locations

- **Container logs**: `docker-compose logs auto-m4b`
- **Global log**: `converted/auto-m4b.log`
- **Debug output**: Console (when `DEBUG=Y`)

### Log Levels

- **INFO**: Normal operations
- **DEBUG**: Detailed processing steps (DEBUG=Y)
- **WARNING**: Recoverable issues
- **ERROR**: Processing failures

## Security

### User Permissions

- Container runs as specified PUID/PGID
- No root execution after entrypoint
- File ownership matches host user

### Volume Mounts

- Read-only mounts possible for config
- Read-write required for processing folders

### Network

- No network ports exposed by default
- Future Web UI (Phase 2.1) will expose HTTP port

## Future Architecture Changes

### Planned Enhancements

1. **Retry Logic** (Phase 1.2): Automatic recovery from transient errors
2. **Metrics** (Phase 1.5): Prometheus-compatible metrics endpoint
3. **Web UI** (Phase 2.1): FastAPI-based dashboard
4. **Parallel Processing** (Phase 3.1): Process multiple books simultaneously
5. **Plugin System** (Phase 3.2): Extensibility for custom workflows

### Scalability Considerations

Current design works for:
- Single user/household
- Up to ~100 books/day
- Sequential processing

For higher throughput:
- Add parallel processing
- Distribute across multiple containers
- Add queue-based architecture (Celery, RabbitMQ)

## See Also

- [Configuration Reference](configuration.md)
- [API Documentation](api/)
- [Contributing Guide](contributing.md)
