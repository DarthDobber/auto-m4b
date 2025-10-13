# Auto-M4B Workflows & Examples

This guide provides practical examples of common workflows for using Auto-M4B in different scenarios.

---

## Table of Contents

- [Basic Single Book Conversion](#basic-single-book-conversion)
- [Batch Processing Multiple Books](#batch-processing-multiple-books)
- [Automated Download Integration](#automated-download-integration)
- [Manual Chapter Editing Workflow](#manual-chapter-editing-workflow)
- [Handling Failed Books](#handling-failed-books)
- [Torrent Seeding Preservation](#torrent-seeding-preservation)
- [NAS/Network Storage Setup](#nasnetwork-storage-setup)
- [Testing New Books Before Bulk Processing](#testing-new-books-before-bulk-processing)

---

## Basic Single Book Conversion

**Goal**: Convert one audiobook from MP3/M4A to M4B format.

### Steps

1. **Prepare your audiobook folder**:
   ```
   MyAudiobook/
   ├── 01 - Chapter One.mp3
   ├── 02 - Chapter Two.mp3
   ├── 03 - Chapter Three.mp3
   └── cover.jpg
   ```

2. **Copy to inbox**:
   ```bash
   cp -r /path/to/MyAudiobook ~/audiobooks/inbox/
   ```

3. **Watch the logs**:
   ```bash
   docker-compose logs -f auto-m4b
   ```

4. **Get your converted M4B**:
   ```bash
   # After conversion completes
   ls ~/audiobooks/converted/MyAudiobook/
   # You'll find: MyAudiobook.m4b
   ```

5. **Originals are archived**:
   ```bash
   ls ~/audiobooks/archive/MyAudiobook/
   # Original files preserved here
   ```

### Expected Output

```
Starting auto-m4b...
Scanning inbox for new books...
Found: MyAudiobook
Converting to M4B...
  Progress: Converting audio files...
  Progress: Creating chapters...
  Progress: Embedding metadata...
Conversion complete!
Moving to converted/
Archiving originals...
Done! MyAudiobook.m4b ready.
```

---

## Batch Processing Multiple Books

**Goal**: Convert 10+ audiobooks overnight.

### Steps

1. **Prepare multiple books**:
   ```bash
   # Copy all books at once
   cp -r /path/to/audiobooks/* ~/audiobooks/inbox/
   ```

2. **Monitor progress**:
   ```bash
   # Watch logs in real-time
   docker-compose logs -f auto-m4b

   # Or check how many are left
   ls ~/audiobooks/inbox/ | wc -l
   ```

3. **Check results in the morning**:
   ```bash
   # Converted books
   ls ~/audiobooks/converted/

   # Any failures
   ls ~/audiobooks/failed/
   ```

### Performance Tuning

For faster batch processing, adjust CPU cores:

```yaml
environment:
  - CPU_CORES=8  # Use more cores for faster conversion
  - SLEEP_TIME=5  # Check inbox more frequently
```

### Tip: Overnight Processing

```bash
# Start batch before bed
cp -r /media/downloads/audiobooks/* ~/audiobooks/inbox/

# Check progress in morning
docker-compose logs --tail=50 auto-m4b
```

---

## Automated Download Integration

**Goal**: Automatically convert books as they're downloaded.

### With Download Clients

#### Example: Torrent Client (qBittorrent, Transmission)

Configure "On Download Complete" script:

**Script**: `/path/to/auto-m4b-copy.sh`
```bash
#!/bin/bash
# Copy completed audiobook to Auto-M4B inbox

SOURCE="$1"  # Torrent path
INBOX="/path/to/audiobooks/inbox"

# Copy (not move) to preserve seeding
cp -r "$SOURCE" "$INBOX/"

echo "Copied $SOURCE to Auto-M4B inbox"
```

**qBittorrent Settings**:
- Tools → Options → Downloads
- "Run external program on torrent completion"
- Command: `/path/to/auto-m4b-copy.sh "%F"`

#### Example: Usenet Client (SABnzbd, NZBGet)

**SABnzbd**:
- Config → Categories → audiobooks
- Script: `auto-m4b-copy.sh`

**NZBGet**:
- Settings → Categories → audiobooks
- PostScript: `auto-m4b-copy.sh`

### With Cloud Storage Sync

**Syncthing / Dropbox / Google Drive**:

```yaml
volumes:
  - ~/Dropbox/AudiobooksToConvert:/inbox
  - ~/audiobooks/converted:/converted
```

Drop files in Dropbox folder → Auto-M4B converts → Converted files appear in output.

---

## Manual Chapter Editing Workflow

**Goal**: Fix incorrect chapter names or adjust chapter timing.

### Steps

1. **Let Auto-M4B do initial conversion**:
   ```bash
   cp -r MyBook ~/audiobooks/inbox/
   # Wait for conversion to complete
   ```

2. **Find the chapters file**:
   ```bash
   cd ~/audiobooks/converted/MyBook/
   ls -la
   # Look for: MyBook.chapters.txt
   ```

3. **Edit chapter names**:
   ```bash
   nano MyBook.chapters.txt
   ```

   **Before**:
   ```
   CHAPTER01=00:00:00.000
   CHAPTER01NAME=01 - Track One
   CHAPTER02=00:15:30.000
   CHAPTER02NAME=02 - Track Two
   ```

   **After**:
   ```
   CHAPTER01=00:00:00.000
   CHAPTER01NAME=Prologue: The Beginning
   CHAPTER02=00:15:30.000
   CHAPTER02NAME=Chapter One: The Journey Starts
   ```

4. **Re-process with edited chapters**:
   ```bash
   # Move entire folder back to inbox
   mv ~/audiobooks/converted/MyBook ~/audiobooks/inbox/

   # Auto-M4B detects the .chapters.txt file and uses it
   ```

5. **Get re-chapterized M4B**:
   ```bash
   # New version appears in converted/
   ls ~/audiobooks/converted/MyBook/MyBook.m4b
   ```

### Tips

- Auto-M4B prioritizes existing `.chapters.txt` files
- You can manually create a `.chapters.txt` file before first conversion
- Chapter times are in format: `HH:MM:SS.mmm`

---

## Handling Failed Books

**Goal**: Troubleshoot and retry failed conversions.

### When a Book Fails

Auto-M4B will retry transient errors automatically (default: 3 attempts with exponential backoff).

**Check the logs**:
```bash
docker-compose logs auto-m4b | grep -A 10 "ERROR"
```

**If max retries exceeded**, the book moves to `failed/` folder:

```bash
ls ~/audiobooks/failed/
# Output: MyBook_2025-10-13_14-23-45/
```

### Reading Failure Information

```bash
cat ~/audiobooks/failed/MyBook_*/FAILED_INFO.txt
```

**Example**:
```
FAILED BOOK INFORMATION
============================================================

Book Name: MyBook
Failed At: 14:23:45
Error Type: Transient
Retry Count: 3
Max Retries: 3

Failure Reason:
------------------------------------------------------------
m4b-tool failed to convert MyBook, no output .m4b file was found
------------------------------------------------------------

RECOVERY INSTRUCTIONS:
1. Fix the issue with the audiobook files in this directory
2. Move the fixed folder back to: /temp/inbox
3. auto-m4b will detect it as a previously failed book and retry
```

### Common Failure Scenarios

#### Scenario 1: Corrupted Audio File

**Symptoms**: "Invalid data found when processing input"

**Fix**:
```bash
# Find corrupted file
cd ~/audiobooks/failed/MyBook_*/
for f in *.mp3; do
  ffmpeg -v error -i "$f" -f null - 2>&1 && echo "$f: OK" || echo "$f: CORRUPTED"
done

# Re-download or replace corrupted file
# Then retry
mv ~/audiobooks/failed/MyBook_*/ ~/audiobooks/inbox/MyBook
```

#### Scenario 2: Missing Cover Art

**Symptoms**: "Could not find cover art"

**Fix**:
```bash
# Add a cover.jpg to the folder
cd ~/audiobooks/failed/MyBook_*/
curl -o cover.jpg "https://example.com/book-cover.jpg"

# Retry
mv ~/audiobooks/failed/MyBook_*/ ~/audiobooks/inbox/MyBook
```

#### Scenario 3: Disk Space

**Symptoms**: "No space left on device"

**Fix**:
```bash
# Free up space
df -h ~/audiobooks/

# Clean up archives if needed
rm -rf ~/audiobooks/archive/*

# Or disable backup
docker-compose down
# Edit docker-compose.yml: BACKUP=N
docker-compose up -d

# Retry
mv ~/audiobooks/failed/MyBook_*/ ~/audiobooks/inbox/MyBook
```

### Retry Configuration

Adjust retry behavior:

```yaml
environment:
  - MAX_RETRIES=5              # Try 5 times instead of 3
  - RETRY_TRANSIENT_ERRORS=Y   # Auto-retry transient errors
  - RETRY_BASE_DELAY=120       # Wait 2 minutes between retries (doubles each time)
  - MOVE_FAILED_BOOKS=Y        # Move to failed folder after max retries
```

---

## Torrent Seeding Preservation

**Goal**: Convert audiobooks while continuing to seed the original torrent.

### Problem

Moving files from torrent client to Auto-M4B breaks seeding.

### Solution: Copy Instead of Move

#### Option 1: Post-Processing Script

**qBittorrent "Run on completion" script**:

```bash
#!/bin/bash
# auto-m4b-copy-for-seeding.sh

TORRENT_PATH="$1"
INBOX="/path/to/audiobooks/inbox"

# Copy (don't move) to preserve seeding
cp -r "$TORRENT_PATH" "$INBOX/"

echo "Copied to Auto-M4B: $(basename "$TORRENT_PATH")"
```

**Usage**:
- Tools → Options → Downloads → "Run external program"
- Command: `/path/to/auto-m4b-copy-for-seeding.sh "%F"`

#### Option 2: Separate Folder Structure

```yaml
volumes:
  # Torrent downloads stay here
  - ~/torrents/complete:/watch:ro  # Read-only!

  # Auto-M4B copies to inbox
  - ~/audiobooks/inbox:/inbox
  - ~/audiobooks/converted:/converted
```

**Sync script** (run via cron):
```bash
#!/bin/bash
# sync-torrents-to-inbox.sh

TORRENT_DIR="~/torrents/complete/audiobooks"
INBOX_DIR="~/audiobooks/inbox"

# Copy new books (rsync preserves originals)
rsync -av --ignore-existing "$TORRENT_DIR/" "$INBOX_DIR/"
```

**Cron** (every 10 minutes):
```bash
crontab -e
# Add:
*/10 * * * * /path/to/sync-torrents-to-inbox.sh
```

---

## NAS/Network Storage Setup

**Goal**: Run Auto-M4B on NAS (Synology, QNAP, TrueNAS) or use network storage.

### Synology NAS

1. **Install Docker** (Package Center → Docker)

2. **Create folder structure**:
   ```
   /volume1/audiobooks/
   ├── inbox/
   ├── converted/
   ├── archive/
   ├── backup/
   └── failed/
   ```

3. **Create docker-compose.yml** via File Station

4. **Find PUID/PGID**:
   ```bash
   # SSH into Synology
   ssh admin@synology-ip
   id username
   ```

5. **Deploy**:
   - Docker app → Container → Create
   - Import docker-compose.yml
   - Start container

### Network Shares (SMB/NFS)

**Mount network share first**:

```bash
# Mount SMB share
sudo mount -t cifs //nas-ip/audiobooks /mnt/nas-audiobooks -o username=user,password=pass

# Or NFS
sudo mount -t nfs nas-ip:/audiobooks /mnt/nas-audiobooks
```

**docker-compose.yml**:
```yaml
volumes:
  - /mnt/nas-audiobooks/inbox:/inbox
  - /mnt/nas-audiobooks/converted:/converted
  - /mnt/nas-audiobooks/archive:/archive
  - /mnt/nas-audiobooks/backup:/backup
  - /mnt/nas-audiobooks/failed:/failed
```

### Performance Considerations

- **Use local working folder** for better performance:
  ```yaml
  environment:
    - WORKING_FOLDER=/tmp/auto-m4b  # Local SSD
  volumes:
    - /fast-local-disk/auto-m4b-temp:/tmp/auto-m4b
  ```

---

## Testing New Books Before Bulk Processing

**Goal**: Test Auto-M4B with one book before processing 100+ books.

### Test Workflow

1. **Pick a representative book**:
   - Medium length (5-10 hours)
   - Typical format (MP3 or M4A)
   - Has cover art

2. **Enable debug mode**:
   ```yaml
   environment:
     - DEBUG=Y
   ```

3. **Process test book**:
   ```bash
   cp -r /path/to/TestBook ~/audiobooks/inbox/
   docker-compose logs -f auto-m4b
   ```

4. **Verify output**:
   ```bash
   # Check M4B file
   ls -lh ~/audiobooks/converted/TestBook/TestBook.m4b

   # Play in VLC or audiobook app
   # Verify chapters work correctly
   # Check metadata (title, author, cover)
   ```

5. **If successful, process full library**:
   ```bash
   docker-compose down
   # Edit docker-compose.yml: DEBUG=N
   docker-compose up -d

   # Process all books
   cp -r /library/audiobooks/* ~/audiobooks/inbox/
   ```

### Test Checklist

- [ ] M4B file created successfully
- [ ] Chapters are correct and named properly
- [ ] Cover art embedded
- [ ] Metadata preserved (title, author, year)
- [ ] File size is reasonable (similar to originals)
- [ ] Playback works in your audiobook app

---

## Advanced Workflows

### Workflow: Integration with Beets-Audible for Tagging

**Goal**: Auto-convert → Auto-tag → Auto-organize

```bash
# 1. Auto-M4B converts to M4B
/audiobooks/inbox → /audiobooks/converted

# 2. Beets-Audible tags and organizes
beet import /audiobooks/converted

# 3. Organized audiobooks
/media/audiobooks/Author/Title/Title.m4b
```

**Setup**:
```yaml
# docker-compose.yml
services:
  auto-m4b:
    volumes:
      - ./inbox:/inbox
      - ./converted:/converted
      - ../beets-import:/converted  # Same folder as beets import

  beets:
    volumes:
      - ../beets-import:/import
      - /media/audiobooks:/music
```

### Workflow: Plex/Audiobookshelf Integration

**Goal**: Converted books automatically appear in media server.

```yaml
# docker-compose.yml
volumes:
  # Auto-M4B outputs directly to Plex/Audiobookshelf library
  - /plex/audiobooks:/converted

environment:
  - ON_COMPLETE=archive  # Keep originals in archive
```

**Plex setup**:
- Add library: `/plex/audiobooks`
- Type: Music (for audiobooks)
- Scan automatically: Enabled

---

## Troubleshooting Common Workflow Issues

### Issue: Books Don't Start Processing

**Check**:
```bash
# Is Auto-M4B running?
docker-compose ps

# Are files in correct location?
ls ~/audiobooks/inbox/

# Check logs for errors
docker-compose logs auto-m4b
```

### Issue: Conversion Takes Forever

**Solutions**:
- Increase CPU cores: `CPU_CORES=8`
- Use faster storage for WORKING_FOLDER
- Process books one at a time instead of batch

### Issue: Permissions Errors

**Fix**:
```bash
# Find your user ID
id

# Update docker-compose.yml
environment:
  - PUID=1000  # Use your UID
  - PGID=1000  # Use your GID

# Restart
docker-compose restart
```

---

## Next Steps

- [Configuration Reference](configuration.md) - Tune settings for your workflow
- [Troubleshooting Guide](troubleshooting.md) - Fix common issues
- [Architecture Overview](architecture.md) - Understand how it works

---

**Questions?** [Open an issue](https://github.com/DarthDobber/auto-m4b/issues) or [start a discussion](https://github.com/DarthDobber/auto-m4b/discussions).
