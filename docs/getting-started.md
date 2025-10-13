# Getting Started with Auto-M4B

This guide will help you set up Auto-M4B and convert your first audiobook in less than 10 minutes.

## Prerequisites

Before you begin, make sure you have:

1. **Docker** installed ([Install Docker](https://docs.docker.com/get-docker/))
2. **Docker Compose** installed ([Install Docker Compose](https://docs.docker.com/compose/install/))
3. Basic familiarity with the command line
4. An audiobook to test with (MP3 or M4A files)

### Find Your PUID and PGID

Auto-M4B needs to know your user ID and group ID to set correct file permissions:

```bash
# On Linux/macOS, run:
id

# You'll see output like:
# uid=1000(yourname) gid=1000(yourname) groups=...
# Your PUID is 1000 and PGID is 1000
```

## Installation Methods

### Method 1: Building from Source (Recommended)

> **Note**: Pre-built Docker images are not currently available on Docker Hub. You'll need to build the image locally.

#### Step 1: Clone the Repository

```bash
git clone https://github.com/DarthDobber/auto-m4b.git
cd auto-m4b
```

#### Step 2: Create Folder Structure

```bash
# Create folders for audiobook processing
mkdir -p ~/audiobooks/{inbox,converted,archive,backup,failed}
```

#### Step 3: Build the Docker Image

```bash
docker build -t darthdobber/auto-m4b:latest .
```

This will take 5-10 minutes on the first build as it compiles ffmpeg and other dependencies.

#### Step 4: Create docker-compose.yml

Create a file called `docker-compose.yml`:

```yaml
version: '3.7'
services:
  auto-m4b:
    image: darthdobber/auto-m4b:latest
    container_name: auto-m4b
    restart: unless-stopped
    volumes:
      - ~/audiobooks/inbox:/inbox
      - ~/audiobooks/converted:/converted
      - ~/audiobooks/archive:/archive
      - ~/audiobooks/backup:/backup
      - ~/audiobooks/failed:/failed
    environment:
      # Replace with your PUID/PGID from the 'id' command
      - PUID=1000
      - PGID=1000

      # Folder paths (these match the volume mounts above)
      - INBOX_FOLDER=/inbox
      - CONVERTED_FOLDER=/converted
      - ARCHIVE_FOLDER=/archive
      - BACKUP_FOLDER=/backup
      - FAILED_FOLDER=/failed

      # Optional: performance tuning
      - CPU_CORES=2
      - SLEEP_TIME=10

      # Optional: retry configuration (Phase 1.2)
      - MAX_RETRIES=3
      - RETRY_TRANSIENT_ERRORS=Y
      - RETRY_BASE_DELAY=60
```

#### Step 5: Start the Container

```bash
# Start Auto-M4B
docker-compose up -d

# Check if it's running
docker-compose ps

# View logs
docker-compose logs -f
```

#### Step 4: Add Your First Audiobook

```bash
# Copy an audiobook folder to the inbox
cp -r /path/to/your/audiobook ~/audiobooks/inbox/

# Or download directly to inbox
# The folder should contain MP3/M4A files
```

Auto-M4B will automatically detect the new book and start processing it. Watch the logs to see progress:

```bash
docker-compose logs -f auto-m4b
```

#### Step 5: Get Your Converted Audiobook

After processing completes (timing depends on book size and CPU):

- **Converted M4B**: `~/audiobooks/converted/`
- **Original Files**: `~/audiobooks/archive/` (if ON_COMPLETE=archive)
- **Backup Copy**: `~/audiobooks/backup/` (if BACKUP=Y)

### Handling Failed Books

If a book fails conversion after the maximum number of retries (default: 3), Auto-M4B will automatically:

1. Move the book to the `failed/` folder with a timestamp
2. Create a `FAILED_INFO.txt` file with:
   - Failure reason and error details
   - Number of retry attempts made
   - Recovery instructions

**To retry a failed book**:
```bash
# Fix the issues (if possible), then move it back to inbox
mv ~/audiobooks/failed/BookName_TIMESTAMP ~/audiobooks/inbox/BookName
```

Auto-M4B will detect that files changed and reset the retry counter, giving you fresh retry attempts.

## Folder Structure Explained

Auto-M4B uses five main folders:

```
~/audiobooks/
├── inbox/          # Place new audiobooks here (input)
├── converted/      # Converted M4B files appear here (output)
├── archive/        # Original files moved here after conversion
├── backup/         # Backup of original files (optional)
└── failed/         # Books that failed after max retries
```

### Folder Purposes

- **inbox/**: Add audiobooks here for processing. Auto-M4B watches this folder continuously.
- **converted/**: Your finished M4B audiobooks will be placed here, ready for tagging or importing to Plex/Audiobookshelf.
- **archive/**: Original files are moved here after successful conversion (configurable with `ON_COMPLETE`).
- **backup/**: A backup copy of originals before processing (can be disabled with `BACKUP=N`).
- **failed/**: Books that failed conversion after max retries are moved here with detailed failure information.

## Testing Your Setup

Let's verify everything works correctly.

### Test with a Sample Book

1. **Create a test audiobook folder**:

```bash
mkdir -p ~/audiobooks/inbox/test-book
```

2. **Add some MP3 files** (or use your own audiobook)

3. **Watch the logs**:

```bash
docker-compose logs -f
```

You should see output like:
```
Starting auto-m4b...
Scanning inbox for new books...
Found: test-book
Converting to M4B...
Conversion complete!
Moving to converted/
```

4. **Check the output**:

```bash
ls -la ~/audiobooks/converted/test-book/
# You should see: test-book.m4b
```

## Common Issues During Setup

### Permission Errors

If you see permission errors:

1. Make sure your `PUID` and `PGID` match your user:
   ```bash
   id  # Check your UID/GID
   ```

2. Update your `docker-compose.yml` with correct values

3. Restart the container:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

### Container Won't Start

Check the logs for errors:
```bash
docker-compose logs auto-m4b
```

Common causes:
- Invalid folder paths in environment variables
- Folders don't exist (create them first)
- Port conflicts (if using Web UI in the future)

### Books Not Processing

1. **Check folder permissions**:
   ```bash
   ls -la ~/audiobooks/inbox/
   ```

2. **Verify files are recognized audio formats**:
   - Supported: `.mp3`, `.m4a`, `.m4b`, `.ogg`, `.wma`

3. **Check logs for errors**:
   ```bash
   docker-compose logs -f
   ```

## Configuration Options

Here are the most useful settings for getting started:

| Variable | Default | Description |
|----------|---------|-------------|
| `PUID` | 1000 | User ID for file ownership |
| `PGID` | 1000 | Group ID for file ownership |
| `CPU_CORES` | All cores | Number of CPU cores to use |
| `SLEEP_TIME` | 10 | Seconds between inbox scans |
| `BACKUP` | Y | Create backup of original files |
| `DEBUG` | N | Enable detailed logging |
| `MAX_RETRIES` | 3 | Maximum retry attempts for failed books |
| `RETRY_TRANSIENT_ERRORS` | Y | Automatically retry transient errors |
| `RETRY_BASE_DELAY` | 60 | Base delay (seconds) for exponential backoff |
| `MOVE_FAILED_BOOKS` | Y | Move failed books to failed folder |

For a complete list, see the [Configuration Reference](configuration.md).

## Next Steps

Now that you have Auto-M4B running:

1. **Process your audiobook collection**: Copy books to the inbox folder
2. **Tune performance**: Adjust `CPU_CORES` based on your system
3. **Set up automation**: Configure your download client to save directly to inbox
4. **Integrate with taggers**: Use [beets-audible](https://github.com/seanap/beets-audible) to tag and organize converted books
5. **Import to media server**: Add the `converted/` folder to Plex, Audiobookshelf, etc.

## Advanced Topics

### Using with NAS/Network Storage

Mount your NAS shares and point volumes to them:

```yaml
volumes:
  - /mnt/nas/audiobooks/inbox:/inbox
  - /mnt/nas/audiobooks/converted:/converted
```

### Preserving Seeding (for Torrent Users)

Instead of moving files, use this in your torrent client's "On Complete" script:

```bash
cp -r "%F" "/path/to/audiobooks/inbox"
```

This copies files to inbox while leaving originals for seeding.

### Manual Chapter Editing

1. Let Auto-M4B process the book normally
2. Find the `.chapters.txt` file in `converted/bookname/`
3. Edit chapter names/times as needed
4. Move the entire folder back to `inbox/`
5. Auto-M4B will re-chapterize using your edited file

## Getting Help

- **Documentation**: [docs/README.md](README.md)
- **Troubleshooting**: [docs/troubleshooting.md](troubleshooting.md)
- **Configuration**: [docs/configuration.md](configuration.md)
- **GitHub Issues**: [Report a bug](https://github.com/DarthDobber/auto-m4b/issues)

Congratulations! You're now ready to start converting audiobooks with Auto-M4B. 🎉
