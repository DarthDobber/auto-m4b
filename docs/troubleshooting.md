# Troubleshooting Guide

This guide covers common issues and their solutions when using Auto-M4B.

## Quick Diagnostics

### Check Container Status

```bash
# Is the container running?
docker-compose ps

# View recent logs
docker-compose logs --tail=50 auto-m4b

# Follow logs in real-time
docker-compose logs -f auto-m4b
```

### Enable Debug Mode

Add to your `docker-compose.yml`:

```yaml
environment:
  - DEBUG=Y
```

Then restart:

```bash
docker-compose down
docker-compose up -d
```

## Common Issues

### 1. Container Won't Start

#### Symptom
Container exits immediately or shows `Exited (1)` status.

#### Diagnosis
```bash
docker-compose logs auto-m4b
```

#### Common Causes & Solutions

**Missing required folders:**
```
Error: INBOX_FOLDER is not set
```

**Solution:** Set all required folder paths in environment:
```yaml
environment:
  - INBOX_FOLDER=/inbox
  - CONVERTED_FOLDER=/converted
  - ARCHIVE_FOLDER=/archive
  - BACKUP_FOLDER=/backup
```

**Invalid folder paths:**
```
Error: /inbox does not exist and could not be created
```

**Solution:** Ensure volume mounts point to existing directories:
```bash
mkdir -p ~/audiobooks/{inbox,converted,archive,backup}
```

**m4b-tool not found:**
```
Error: Could not find 'm4b-tool' in PATH
```

**Solution:** The Docker image includes m4b-tool. If you see this error, you may be running outside Docker. Use the Docker image or install m4b-tool manually.

### 2. Permission Errors

#### Symptom
```
PermissionError: [Errno 13] Permission denied
```
Or files owned by `root` instead of your user.

#### Diagnosis
```bash
# Check file ownership in your folders
ls -la ~/audiobooks/inbox/
ls -la ~/audiobooks/converted/

# Check your user ID
id
```

#### Solutions

**Fix PUID/PGID:**

1. Find your user's UID/GID:
   ```bash
   id
   # uid=1026(yourname) gid=1000(yourname)
   ```

2. Update `docker-compose.yml`:
   ```yaml
   environment:
     - PUID=1026
     - PGID=1000
   ```

3. Fix existing file ownership:
   ```bash
   sudo chown -R 1026:1000 ~/audiobooks/
   ```

4. Restart container:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

### 3. Books Not Being Processed

#### Symptom
Books added to inbox folder are ignored or not detected.

#### Diagnosis
```bash
# Check if Auto-M4B sees the files
docker-compose logs auto-m4b | grep -i "found\|scanning"

# Verify file structure
ls -la ~/audiobooks/inbox/
```

#### Common Causes & Solutions

**Wrong folder structure:**

Auto-M4B expects:
```
inbox/
└── BookName/
    ├── Chapter01.mp3
    ├── Chapter02.mp3
    └── ...
```

Not:
```
inbox/
├── Chapter01.mp3    # ❌ Standalone files should be in subfolder
└── Chapter02.mp3
```

**Solution:** Create a subfolder for each book:
```bash
mkdir ~/audiobooks/inbox/MyBook
mv ~/audiobooks/inbox/*.mp3 ~/audiobooks/inbox/MyBook/
```

**Unsupported file format:**

Check file extensions:
```bash
file ~/audiobooks/inbox/MyBook/*
```

Supported: `.mp3`, `.m4a`, `.m4b`, `.ogg`, `.wma`

**Match filter active:**

If you have `MATCH_FILTER` set, only matching books are processed.

Check your configuration:
```yaml
environment:
  # - MATCH_FILTER=Dresden.*  # Comment out or remove
```

**Files still being copied:**

Auto-M4B waits for file modifications to stop (WAIT_TIME) before processing.

Solution: Wait a few seconds after copying completes, or increase `WAIT_TIME`:
```yaml
environment:
  - WAIT_TIME=10
```

### 4. Conversion Failures

#### Symptom
Book processing starts but fails with errors.

#### Diagnosis
```bash
# Check for error messages
docker-compose logs auto-m4b | grep -i "error\|failed"

# Look for the book in the inbox failure state
ls ~/audiobooks/inbox/.failed/
```

#### Common Causes & Solutions

**Corrupted audio files:**

```
Error: Could not decode audio file
```

**Solution:**
1. Check file integrity:
   ```bash
   ffmpeg -v error -i file.mp3 -f null -
   ```
2. Re-download or replace corrupted files
3. Move fixed book back to inbox

**Insufficient disk space:**

```
Error: No space left on device
```

**Solution:**
1. Check disk usage:
   ```bash
   df -h
   ```
2. Free up space or adjust folder locations
3. Consider disabling backup:
   ```yaml
   environment:
     - BACKUP=N
   ```

**Complex folder structure:**

```
Warning: Nested subfolders detected
```

**Solution:**
Auto-M4B handles nested folders, but deeply nested or complex structures may cause issues. Flatten the structure:

```bash
# Before: Book/Disc1/Chapter01.mp3, Book/Disc2/Chapter01.mp3
# After: Book/Disc1-Chapter01.mp3, Book/Disc2-Chapter01.mp3

find Book/ -type f -name "*.mp3" -exec mv {} Book/ \;
```

Or enable the beta feature:
```yaml
environment:
  - FLATTEN_MULTI_DISC_BOOKS=Y
```

**m4b-tool errors:**

```
Error: m4b-tool merge failed
```

**Solution:**
1. Enable debug mode: `DEBUG=Y`
2. Check logs for specific m4b-tool error
3. Verify m4b-tool version:
   ```bash
   docker exec auto-m4b m4b-tool --version
   ```
4. Ensure you have v0.5-prerelease (required)

### 5. Slow Conversion Speed

#### Symptom
Conversion takes a very long time.

#### Diagnosis
```bash
# Check CPU usage
docker stats auto-m4b

# Check configured CPU cores
docker exec auto-m4b env | grep CPU_CORES
```

#### Solutions

**Increase CPU cores:**

```yaml
environment:
  - CPU_CORES=8  # Use more cores
```

Don't exceed your system's core count:
```bash
# Check available cores
nproc
```

**Use faster storage:**

Move WORKING_FOLDER to SSD:
```yaml
environment:
  - WORKING_FOLDER=/mnt/nvme/auto-m4b
```

**Large file optimization:**

For very large audiobooks (>1GB), ensure you have:
- Adequate RAM (4GB+ recommended)
- Fast storage for working directory
- Multiple CPU cores allocated

### 6. Chapter Issues

#### Symptom
Chapters have wrong names, lengths, or are missing.

#### Diagnosis
```bash
# Check chapter file
cat ~/audiobooks/converted/BookName/BookName.chapters.txt
```

#### Solutions

**Wrong chapter names:**

Enable filename-based chapters:
```yaml
environment:
  - USE_FILENAMES_AS_CHAPTERS=Y
```

Or manually edit chapters:

1. Find `.chapters.txt` in converted folder
2. Edit chapter names
3. Move entire book folder to inbox
4. Auto-M4B will re-chapterize

**Chapter length issues:**

Adjust MAX_CHAPTER_LENGTH:
```yaml
environment:
  - MAX_CHAPTER_LENGTH=10,20  # 10-20 minute chapters
```

**Missing chapters:**

Ensure all audio files are valid:
```bash
# Test each file
for f in ~/audiobooks/inbox/BookName/*.mp3; do
    echo "Testing: $f"
    ffmpeg -v error -i "$f" -f null - 2>&1
done
```

### 7. Docker-Specific Issues

#### Container keeps restarting

```bash
# Check restart loop
docker-compose ps

# See why it's crashing
docker-compose logs auto-m4b
```

**Common causes:**
- Fatal error on last run (check for `fatal.log`)
- Invalid configuration
- Missing dependencies

**Solution:**
```bash
# Remove fatal lock file
docker exec auto-m4b rm /tmp/auto-m4b/fatal.log

# Or manually:
rm /path/to/working/folder/fatal.log

# Restart
docker-compose restart
```

#### Volume mount issues

```
Error: /inbox is not writable
```

**Solution:**
Check volume mounts in `docker-compose.yml`:
```yaml
volumes:
  - ~/audiobooks/inbox:/inbox:rw  # Ensure :rw (read-write)
```

#### Network issues (if using named network)

```
Error: network auto-m4b_default not found
```

**Solution:**
```bash
# Recreate network
docker-compose down
docker-compose up -d
```

### 8. Output/Converted Folder Issues

#### Books not appearing in converted folder

**Check ON_COMPLETE setting:**
```yaml
environment:
  - ON_COMPLETE=archive  # Should move to archive after conversion
```

**Check logs for move operation:**
```bash
docker-compose logs auto-m4b | grep -i "moving to converted"
```

#### Duplicate files

**Solution:**
Set overwrite behavior:
```yaml
environment:
  - OVERWRITE_EXISTING=Y  # Overwrite existing files
```

Or:
```yaml
environment:
  - OVERWRITE_EXISTING=N  # Skip existing files (default)
```

### 9. Memory Issues

#### Symptom
```
Error: Cannot allocate memory
```

#### Solutions

**Increase Docker memory limit:**

In Docker Desktop:
- Settings → Resources → Memory → Increase to 4GB+

Or in `docker-compose.yml`:
```yaml
services:
  auto-m4b:
    mem_limit: 4g
```

**Process smaller batches:**

Use `MAX_LOOPS` to process fewer books at a time:
```bash
docker exec auto-m4b python -m src --max_loops 1
```

### 10. Logs and Debugging

#### Enable verbose logging

```yaml
environment:
  - DEBUG=Y
```

#### Save logs to file

```bash
# Continuous logging
docker-compose logs -f auto-m4b > auto-m4b.log

# Or check the global log file
cat ~/audiobooks/converted/auto-m4b.log
```

#### Check specific operations

```bash
# Find errors
docker-compose logs auto-m4b | grep -i error

# Find specific book
docker-compose logs auto-m4b | grep "BookName"

# Find conversion operations
docker-compose logs auto-m4b | grep -i "converting\|merge"
```

## Advanced Troubleshooting

### Run m4b-tool manually

Test m4b-tool directly:

```bash
docker exec -it auto-m4b bash

# Inside container
m4b-tool --version
m4b-tool merge /inbox/BookName --output-file=/tmp/test.m4b
```

### Inspect container

```bash
# Open shell in container
docker exec -it auto-m4b bash

# Check environment
env | grep -E "(INBOX|CONVERTED|PUID)"

# Check file permissions
ls -la /inbox /converted

# Check processes
ps aux
```

### Reset everything

If all else fails:

```bash
# Stop and remove container
docker-compose down

# Remove volumes (⚠️ deletes data)
docker-compose down -v

# Rebuild image
docker-compose build --no-cache

# Start fresh
docker-compose up -d
```

### Check for known issues

Search GitHub issues: [https://github.com/DarthDobber/auto-m4b/issues](https://github.com/DarthDobber/auto-m4b/issues)

## Getting Help

If you've tried the solutions above and still have issues:

1. **Enable debug mode**: `DEBUG=Y`
2. **Collect information**:
   ```bash
   # System info
   docker --version
   docker-compose --version
   uname -a

   # Container info
   docker-compose ps
   docker-compose logs --tail=100 auto-m4b

   # Configuration
   cat docker-compose.yml
   ```
3. **Create a GitHub issue**: [Report a bug](https://github.com/DarthDobber/auto-m4b/issues/new)

Include:
- Description of the problem
- Steps to reproduce
- Debug logs
- System information
- docker-compose.yml (remove sensitive data)

## Prevention Tips

### Regular maintenance

```bash
# Periodically clean working directory
docker exec auto-m4b rm -rf /tmp/auto-m4b/*

# Check disk space regularly
df -h

# Monitor logs for warnings
docker-compose logs auto-m4b | grep -i warning
```

### Best practices

1. **Test first**: Use `TEST=Y` mode before processing your entire library
2. **Keep backups**: Enable `BACKUP=Y` until you're confident
3. **Monitor disk space**: Ensure adequate space for conversion (3x book size recommended)
4. **Update regularly**: Pull latest Docker image periodically
5. **Use version tags**: Pin to specific versions in production

```yaml
services:
  auto-m4b:
    image: darthdobber/auto-m4b:v1.0.0  # Pin version
```

## See Also

- [Configuration Reference](configuration.md)
- [Architecture Overview](architecture.md)
- [Getting Started Guide](getting-started.md)
