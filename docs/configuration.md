# Configuration Reference

This document lists all configuration options available in Auto-M4B.

## Configuration Methods

Auto-M4B can be configured in three ways (in order of precedence):

1. **Command-line arguments** (highest priority)
2. **Environment variables** (via Docker or `.env` file)
3. **Default values** (built-in fallbacks)

### Using Environment Variables (Docker)

In your `docker-compose.yml`:

```yaml
services:
  auto-m4b:
    environment:
      - INBOX_FOLDER=/inbox
      - CPU_CORES=4
      - DEBUG=Y
```

### Using Command-Line Arguments

```bash
docker exec auto-m4b python -m src --debug --test --max_loops 1
```

### Using a .env File

Create a `.env` file in your project directory:

```bash
INBOX_FOLDER=/inbox
CPU_CORES=4
DEBUG=Y
```

Then reference it in `docker-compose.yml`:

```yaml
services:
  auto-m4b:
    env_file:
      - .env
```

## Required Configuration

These settings **must** be configured:

### INBOX_FOLDER
- **Type**: Path
- **Required**: Yes
- **Description**: Input folder where new audiobooks are placed for processing
- **Example**: `/inbox` or `/media/audiobooks/inbox`

### CONVERTED_FOLDER
- **Type**: Path
- **Required**: Yes
- **Description**: Output folder where converted M4B files are saved
- **Example**: `/converted` or `/media/audiobooks/converted`

### ARCHIVE_FOLDER
- **Type**: Path
- **Required**: Yes
- **Description**: Folder where original files are archived after conversion
- **Example**: `/archive` or `/media/audiobooks/archive`

### BACKUP_FOLDER
- **Type**: Path
- **Required**: Yes
- **Description**: Folder where backup copies are stored (if BACKUP=Y)
- **Example**: `/backup` or `/media/audiobooks/backup`

## Docker Configuration

### PUID
- **Type**: Integer
- **Default**: `1000`
- **Description**: User ID for file ownership (run `id` command to find yours)
- **Example**: `1000`

### PGID
- **Type**: Integer
- **Default**: `1000`
- **Description**: Group ID for file ownership (run `id` command to find yours)
- **Example**: `1000`

## Performance Settings

### CPU_CORES
- **Type**: Integer
- **Default**: All available CPU cores
- **Description**: Number of CPU cores to use for conversion
- **Range**: 1 to number of cores on your system
- **Example**: `2`, `4`, `8`
- **Notes**: Higher values = faster conversion but more CPU usage

### SLEEP_TIME
- **Type**: Float (seconds)
- **Default**: `10`
- **Description**: How long to wait between inbox scans
- **Example**: `10` (10 seconds), `60` (1 minute), `0.5` (500ms)
- **Notes**: Lower values = more responsive but higher CPU overhead

### WAIT_TIME
- **Type**: Float (seconds)
- **Default**: `5`
- **Description**: Time to wait after detecting folder changes before processing
- **Example**: `5` (5 seconds)
- **Notes**: Prevents processing incomplete file transfers

## Audio Processing Settings

### MAX_CHAPTER_LENGTH
- **Type**: String (comma-separated minutes)
- **Default**: `15,30`
- **Description**: Min and max chapter length in minutes
- **Format**: `min,max`
- **Example**: `10,20` (10-20 min chapters), `5,15` (5-15 min chapters)
- **Notes**: m4b-tool will split/merge chapters to fit within this range

### USE_FILENAMES_AS_CHAPTERS
- **Type**: Boolean
- **Default**: `N`
- **Description**: Use audio filenames as chapter names
- **Values**: `Y` / `N` / `true` / `false` / `1` / `0`
- **Example**: `Y`
- **Notes**: When enabled, `01 - Chapter One.mp3` becomes chapter "Chapter One"

### AUDIO_EXTS
- **Type**: String (comma-separated)
- **Default**: `.mp3,.m4a,.m4b,.wma`
- **Description**: Audio file extensions to process
- **Example**: `.mp3,.m4a,.ogg`
- **Notes**: Extensions must include the leading dot

## Behavior Settings

### ON_COMPLETE
- **Type**: String
- **Default**: `archive` (production), `test_do_nothing` (test mode)
- **Description**: What to do with original files after successful conversion
- **Values**:
  - `archive`: Move originals to ARCHIVE_FOLDER
  - `delete`: Delete originals (⚠️ use with caution)
  - `test_do_nothing`: Leave files in place (for testing)
- **Example**: `archive`

### OVERWRITE_EXISTING
- **Type**: Boolean
- **Default**: `N`
- **Description**: Whether to overwrite existing M4B files in the converted folder
- **Values**: `Y` / `N` / `true` / `false`
- **Example**: `Y`
- **Notes**: When `N`, existing files are skipped

### BACKUP
- **Type**: Boolean
- **Default**: `Y`
- **Description**: Create backup copies before processing
- **Values**: `Y` / `N` / `true` / `false`
- **Example**: `N`
- **Notes**: Disable to save disk space if you have another backup solution

### MATCH_FILTER
- **Type**: String (regex pattern)
- **Default**: None
- **Description**: Only process books matching this pattern
- **Example**: `Dresden.*Files`, `Book [0-9]+`
- **Notes**: Useful for selective processing; backslashes must be escaped: `\\`

## Beta Features

These features are experimental and may have issues.

### FLATTEN_MULTI_DISC_BOOKS
- **Type**: Boolean
- **Default**: `N`
- **Description**: Combine multi-disc books into a single M4B
- **Values**: `Y` / `N`
- **Example**: `Y`
- **Notes**: ⚠️ Beta feature - test before production use

### CONVERT_SERIES
- **Type**: Boolean
- **Default**: `N`
- **Description**: Process book series as a single unit
- **Values**: `Y` / `N`
- **Example**: `Y`
- **Notes**: ⚠️ Beta feature - test before production use

## Development/Debugging Settings

### DEBUG
- **Type**: Boolean
- **Default**: `N`
- **Description**: Enable verbose debug logging
- **Values**: `Y` / `N` / `true` / `false`
- **Example**: `Y`
- **Notes**: Logs detailed information about processing steps

### TEST
- **Type**: Boolean
- **Default**: `N`
- **Description**: Enable test mode (uses `.env.test` file, changes defaults)
- **Values**: `Y` / `N` / `true` / `false`
- **Example**: `Y`
- **Notes**: Useful for development and testing

### NO_CATS
- **Type**: Boolean
- **Default**: `N`
- **Description**: Disable ASCII cat art in output 😿
- **Values**: `Y` / `N`
- **Example**: `Y`

## Advanced Settings

### WORKING_FOLDER
- **Type**: Path
- **Default**: `/tmp/auto-m4b`
- **Description**: Temporary working directory for conversion
- **Example**: `/tmp/auto-m4b`
- **Notes**: Should be on fast storage (SSD recommended)

### USE_DOCKER
- **Type**: Boolean
- **Default**: Auto-detected
- **Description**: Force use of Docker-based m4b-tool vs native binary
- **Values**: `Y` / `N`
- **Example**: `Y`
- **Notes**: Usually auto-detected correctly

### DOCKER_PATH
- **Type**: Path
- **Default**: Auto-detected from PATH
- **Description**: Path to Docker executable
- **Example**: `/usr/bin/docker`
- **Notes**: Only needed if Docker is not in PATH

## Command-Line Arguments

These override environment variables:

### --debug
- **Description**: Enable debug mode
- **Usage**: `--debug` or `--debug=off`
- **Example**: `python -m src --debug`

### --test
- **Description**: Enable test mode
- **Usage**: `--test` or `--test=off`
- **Example**: `python -m src --test`

### --max_loops (-l)
- **Description**: Maximum number of processing loops
- **Default**: `-1` (infinite)
- **Usage**: `--max_loops 5` or `-l 5`
- **Example**: `python -m src --max_loops 1` (process once and exit)

### --match
- **Description**: Only process books matching this pattern
- **Usage**: `--match "pattern"`
- **Example**: `python -m src --match "Dresden.*"`

### --env
- **Description**: Path to custom .env file
- **Usage**: `--env /path/to/.env`
- **Example**: `python -m src --env /config/.env.production`

## Configuration Examples

### Minimal Configuration (Docker)

```yaml
environment:
  - PUID=1000
  - PGID=1000
  - INBOX_FOLDER=/inbox
  - CONVERTED_FOLDER=/converted
  - ARCHIVE_FOLDER=/archive
  - BACKUP_FOLDER=/backup
```

### Performance-Optimized

```yaml
environment:
  - PUID=1000
  - PGID=1000
  - INBOX_FOLDER=/inbox
  - CONVERTED_FOLDER=/converted
  - ARCHIVE_FOLDER=/archive
  - BACKUP_FOLDER=/backup
  - CPU_CORES=8
  - SLEEP_TIME=5
  - WORKING_FOLDER=/mnt/nvme/auto-m4b-temp
```

### Space-Saving Configuration

```yaml
environment:
  - PUID=1000
  - PGID=1000
  - INBOX_FOLDER=/inbox
  - CONVERTED_FOLDER=/converted
  - ARCHIVE_FOLDER=/archive
  - BACKUP_FOLDER=/backup
  - BACKUP=N
  - ON_COMPLETE=delete
```

### Development/Testing

```yaml
environment:
  - PUID=1000
  - PGID=1000
  - INBOX_FOLDER=/inbox
  - CONVERTED_FOLDER=/converted
  - ARCHIVE_FOLDER=/archive
  - BACKUP_FOLDER=/backup
  - DEBUG=Y
  - TEST=Y
  - ON_COMPLETE=test_do_nothing
  - SLEEP_TIME=5
```

### Short Chapters for Podcasts

```yaml
environment:
  - PUID=1000
  - PGID=1000
  - INBOX_FOLDER=/inbox
  - CONVERTED_FOLDER=/converted
  - ARCHIVE_FOLDER=/archive
  - BACKUP_FOLDER=/backup
  - MAX_CHAPTER_LENGTH=5,10
  - USE_FILENAMES_AS_CHAPTERS=Y
```

## Environment Variable Validation

To validate your configuration before running:

```bash
# This feature is planned for Phase 1.4
docker exec auto-m4b python -m src --validate
```

To see all available configuration options:

```bash
# This feature is planned for Phase 1.4
docker exec auto-m4b python -m src --help-config
```

## Troubleshooting Configuration Issues

### Check Current Configuration

View the active configuration in the logs when Auto-M4B starts:

```bash
docker-compose logs auto-m4b | grep -A 20 "Starting auto-m4b"
```

### Common Issues

**Problem**: Files have wrong permissions
- **Solution**: Check `PUID` and `PGID` match your user (`id` command)

**Problem**: Books not processing
- **Solution**: Verify folder paths are correct and accessible

**Problem**: Conversion very slow
- **Solution**: Increase `CPU_CORES` (don't exceed your system's core count)

**Problem**: Container crashes on startup
- **Solution**: Enable `DEBUG=Y` and check logs for specific errors

## See Also

- [Getting Started Guide](getting-started.md)
- [Troubleshooting Guide](troubleshooting.md)
- [Architecture Overview](architecture.md)
