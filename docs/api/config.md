# Config API

The `Config` class manages all application configuration through environment variables and command-line arguments.

## Module

`src.lib.config`

## Class: Config

A singleton configuration manager that handles environment variables, CLI arguments, and default values.

### Accessing Configuration

```python
from src.lib.config import cfg

# Access configuration values
inbox = cfg.inbox_dir
cpu_cores = cfg.CPU_CORES
debug = cfg.DEBUG
```

The `cfg` singleton is automatically instantiated and available throughout the application.

## Configuration Properties

### Folder Paths

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `inbox_dir` | `Path` | Required | Input folder for new audiobooks |
| `converted_dir` | `Path` | Required | Output folder for converted M4B files |
| `archive_dir` | `Path` | Required | Folder for archived original files |
| `backup_dir` | `Path` | Required | Folder for backup copies |
| `working_dir` | `Path` | `/tmp/auto-m4b` | Temporary working directory |
| `build_dir` | `Path` | `{working_dir}/build` | Build directory (computed) |
| `merge_dir` | `Path` | `{working_dir}/merge` | Merge directory (computed) |
| `trash_dir` | `Path` | `{working_dir}/trash` | Trash directory (computed) |

### Performance Settings

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `CPU_CORES` | `int` | All cores | Number of CPU cores for encoding |
| `SLEEP_TIME` | `float` | `10.0` | Seconds between inbox scans |
| `WAIT_TIME` | `float` | `5.0` | Seconds to wait after file changes |

### Processing Behavior

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `ON_COMPLETE` | `OnComplete` | `"archive"` | What to do with originals after conversion |
| `OVERWRITE_MODE` | `OverwriteMode` | `"skip"` | Whether to overwrite existing files |
| `BACKUP` | `bool` | `True` | Create backup before processing |
| `MATCH_FILTER` | `str \| None` | `None` | Regex filter for book selection |

### Audio Settings

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `MAX_CHAPTER_LENGTH` | `str` | `"900,1800"` | Min/max chapter length in seconds |
| `USE_FILENAMES_AS_CHAPTERS` | `bool` | `False` | Use filenames as chapter names |
| `AUDIO_EXTS` | `list[str]` | `[".mp3", ...]` | Recognized audio extensions |

### Beta Features

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `FLATTEN_MULTI_DISC_BOOKS` | `bool` | `False` | Combine multi-disc books |
| `CONVERT_SERIES` | `bool` | `False` | Process series as units |

### Development/Debug

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `DEBUG` | `bool` | `False` | Enable debug logging |
| `TEST` | `bool` | `False` | Enable test mode |
| `NO_CATS` | `bool` | `False` | Disable ASCII cat art |

### Docker/Tool Settings

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `USE_DOCKER` | `bool` | Auto-detect | Force Docker m4b-tool usage |
| `docker_path` | `Path` | Auto-detect | Path to Docker executable |
| `m4b_tool` | `str` | Computed | m4b-tool command string |
| `m4b_tool_version` | `str` | Computed | m4b-tool version string |

### System Files

| Property | Type | Description |
|----------|------|-------------|
| `GLOBAL_LOG_FILE` | `Path` | Global log file path |
| `PID_FILE` | `Path` | Process ID lock file |
| `FATAL_FILE` | `Path` | Fatal error lock file |

## Methods

### startup()

Initialize configuration and perform startup checks.

```python
from src.lib.config import cfg, AutoM4bArgs

args = AutoM4bArgs(debug=True, test=False)
cfg.startup(args)
```

**Parameters:**
- `args: AutoM4bArgs | None` - Command-line arguments

**Side Effects:**
- Loads environment variables
- Creates necessary directories
- Validates configuration
- Checks m4b-tool availability
- Prints startup information

### load_env()

Load environment variables from a `.env` file.

```python
with cfg.load_env(args) as message:
    print(message)  # "Loading ENV from /path/to/.env"
```

**Parameters:**
- `args: AutoM4bArgs | None` - Command-line arguments
- `quiet: bool = False` - Suppress messages

**Returns:** Context manager yielding load message

### get_env_var()

Get an environment variable value.

```python
# Get with default
value = cfg.get_env_var("MY_VAR", default="default_value")

# Get without default (returns None if not set)
value = cfg.get_env_var("MY_VAR")
```

**Parameters:**
- `key: str` - Environment variable name
- `default: Any = None` - Default value if not set

**Returns:** Variable value or default

### set_env_var()

Set an environment variable value.

```python
cfg.set_env_var("DEBUG", True)
cfg.set_env_var("CPU_CORES", 4)
```

**Parameters:**
- `key: str` - Environment variable name
- `value: Any` - Value to set

### check_dirs()

Verify all required directories exist and are writable.

```python
cfg.check_dirs()  # Raises exception if any dir is invalid
```

### check_m4b_tool()

Check if m4b-tool is available and configure Docker if needed.

```python
cfg.check_m4b_tool()  # Raises exception if m4b-tool unavailable
```

### clean()

Clean up working directories (build, merge, trash).

```python
cfg.clean()  # Removes all files in working directories
```

### reload()

Reload configuration from environment.

```python
cfg.reload()  # Re-reads all environment variables
```

## Command-Line Arguments

### Class: AutoM4bArgs

Parses and stores command-line arguments.

```python
from src.lib.config import AutoM4bArgs

# Parse from sys.argv
args = AutoM4bArgs()

# Or provide values
args = AutoM4bArgs(
    debug=True,
    test=False,
    max_loops=5,
    match_filter="Dresden.*"
)
```

### Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--env` | `Path` | None | Path to .env file |
| `--debug` | `bool` | False | Enable debug mode |
| `--test` | `bool` | False | Enable test mode |
| `--max_loops` | `int` | -1 | Max processing loops (-1 = infinite) |
| `--match` | `str` | None | Filter pattern for books |

### Examples

```bash
# Enable debug mode
python -m src --debug

# Run once and exit
python -m src --max_loops 1

# Use custom env file
python -m src --env /config/.env.production

# Filter books by pattern
python -m src --match "Dresden.*"

# Combine arguments
python -m src --debug --test --max_loops 5
```

## Type Definitions

### OnComplete

Valid values for `ON_COMPLETE`:

```python
OnComplete = Literal["archive", "delete", "test_do_nothing"]
```

- **archive**: Move originals to archive folder
- **delete**: Delete originals (⚠️ permanent)
- **test_do_nothing**: Leave in place (for testing)

### OverwriteMode

Valid values for `OVERWRITE_MODE`:

```python
OverwriteMode = Literal["skip", "overwrite", "overwrite-silent"]
```

- **skip**: Don't overwrite existing files
- **overwrite**: Overwrite and log
- **overwrite-silent**: Overwrite without logging

## Property Decorators

### @env_property

Decorator for creating configuration properties backed by environment variables.

```python
from src.lib.config import env_property

class Config:
    @env_property(typ=int, default=10)
    def _MY_SETTING(self): ...

    MY_SETTING = _MY_SETTING
```

**Parameters:**
- `typ: type` - Property type (str, int, bool, float, Path)
- `default: Any` - Default value
- `var_name: str | None` - Environment variable name (default: property name)
- `on_get: Callable` - Transform on read
- `on_set: Callable` - Transform on write
- `del_on_none: bool` - Delete key if set to None

## Usage Examples

### Basic Configuration Access

```python
from src.lib.config import cfg

# Get folder paths
print(f"Inbox: {cfg.inbox_dir}")
print(f"Converted: {cfg.converted_dir}")

# Get settings
print(f"CPU Cores: {cfg.CPU_CORES}")
print(f"Debug: {cfg.DEBUG}")
```

### Startup with Custom Args

```python
from src.lib.config import cfg, AutoM4bArgs

# Parse command-line args
args = AutoM4bArgs()

# Initialize
cfg.startup(args)

# Now cfg is ready to use
```

### Checking Configuration

```python
from src.lib.config import cfg

# Verify directories
try:
    cfg.check_dirs()
    print("All directories OK")
except Exception as e:
    print(f"Directory error: {e}")

# Check m4b-tool
try:
    cfg.check_m4b_tool()
    print(f"m4b-tool version: {cfg.m4b_tool_version}")
except Exception as e:
    print(f"m4b-tool error: {e}")
```

### Dynamic Configuration

```python
from src.lib.config import cfg

# Change settings at runtime
cfg.DEBUG = True
cfg.CPU_CORES = 4

# Reload from environment
cfg.reload()
```

### Using with Context Manager

```python
from src.lib.config import cfg, use_pid_file

# Ensure only one instance runs
with use_pid_file() as already_running:
    if already_running:
        print("Already running!")
    else:
        print("Starting fresh")
        # ... do work
```

## Helper Functions

### ensure_dir_exists_and_is_writable()

Ensure a directory exists and is writable.

```python
from src.lib.config import ensure_dir_exists_and_is_writable
from pathlib import Path

path = Path("/path/to/dir")
ensure_dir_exists_and_is_writable(path, throw=True)
```

**Parameters:**
- `path: Path` - Directory path
- `throw: bool = True` - Raise exception on error

### use_pid_file()

Context manager for PID file locking.

```python
from src.lib.config import use_pid_file

with use_pid_file() as already_exists:
    if already_exists:
        print("Another instance is running")
    # PID file automatically cleaned up on exit
```

## See Also

- [Audiobook API](audiobook.md) - Audiobook data model
- [Inbox State API](inbox-state.md) - State management
- [Configuration Reference](../configuration.md) - User documentation
