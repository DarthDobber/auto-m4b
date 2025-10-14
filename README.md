# Auto-M4B

[![Join the chat at https://gitter.im/Audiobook-Server/auto-m4b](https://badges.gitter.im/Audiobook-Server/auto-m4b.svg)](https://gitter.im/Audiobook-Server/auto-m4b?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

A Docker-based automation tool for converting multi-file audiobooks to chapterized M4B format.

This project is based on the powerful [m4b-tool](https://github.com/sandreas/m4b-tool) by sandreas. Originally created by [seanap/auto-m4b](https://github.com/seanap/auto-m4b), then forked and improved by [brandonscript/auto-m4b](https://github.com/brandonscript/auto-m4b), this is my fork with additional enhancements.

## What Does It Do?

Auto-M4B watches a folder for new audiobooks and automatically:
- ✅ Converts MP3, M4A, OGG, and WMA files to M4B format
- ✅ Creates chapters based on file structure
- ✅ Preserves metadata and cover art
- ✅ Archives original files
- ✅ Handles multi-disc books and series

Perfect for integrating with [beets-audible](https://github.com/seanap/beets-audible) for automated tagging and organization.

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Basic command-line knowledge

### Installation

1. **Create folder structure**:
   ```bash
   mkdir -p ~/audiobooks/{inbox,converted,archive,backup,failed}
   ```

2. **Clone and build**:
   ```bash
   git clone https://github.com/DarthDobber/auto-m4b.git
   cd auto-m4b
   docker build -t darthdobber/auto-m4b:latest .
   ```

3. **Create docker-compose.yml**:
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
         - PUID=1000  # Run 'id' to find yours
         - PGID=1000
         - INBOX_FOLDER=/inbox
         - CONVERTED_FOLDER=/converted
         - ARCHIVE_FOLDER=/archive
         - BACKUP_FOLDER=/backup
         - FAILED_FOLDER=/failed
   ```

4. **Start the container**:
   ```bash
   docker-compose up -d
   ```

5. **Add audiobooks**:
   ```bash
   # Copy audiobooks to inbox
   cp -r /path/to/audiobook ~/audiobooks/inbox/

   # Watch the logs
   docker-compose logs -f
   ```

6. **Get converted audiobooks** from `~/audiobooks/converted/`

> **Note**: Pre-built Docker images are not currently available on Docker Hub. You'll need to build the image locally as shown above.

## Key Features

### 🚀 Easy Setup
- **Docker-based** - Consistent environment across platforms
- **Runtime PUID/PGID** - Flexible permissions configuration
- **Simple build process** - Get started in minutes

### 📚 Smart Processing
- **Auto-detection** - Watches inbox folder continuously
- **Multiple formats** - MP3, M4A, M4B, OGG, WMA support
- **Chapter creation** - Automatic chapterization
- **Metadata preservation** - Keeps tags and cover art

### ⚙️ Configurable
- **Performance tuning** - Adjust CPU cores, scan frequency
- **Flexible behavior** - Archive, delete, or keep originals
- **Filter support** - Process only matching books
- **Beta features** - Multi-disc flattening, series conversion

### 🛡️ Reliable
- **Error handling** - Graceful failure management with automatic retries
- **Failed book tracking** - Automatically moves failed books to dedicated folder with recovery instructions
- **Metrics tracking** - Track conversion history, success rates, and timing statistics
- **Backup support** - Optional safety copies
- **Debug mode** - Detailed logging for troubleshooting

## Documentation

### Getting Started
- **[Getting Started Guide](docs/getting-started.md)** - Detailed setup instructions
- **[Configuration Reference](docs/configuration.md)** - All environment variables
- **[Docker Compose Examples](docs/examples/)** - Example configurations
- **[Workflows & Examples](docs/workflows.md)** - Practical workflows for common scenarios

### Guides & Reference
- **[Troubleshooting Guide](docs/troubleshooting.md)** - Common issues and solutions
- **[Architecture Overview](docs/architecture.md)** - System design and internals
- **[Contributing Guide](docs/contributing.md)** - How to contribute

### API Documentation
- **[Audiobook API](docs/api/audiobook.md)** - Audiobook class reference
- **[Config API](docs/api/config.md)** - Configuration management
- **[Inbox State API](docs/api/inbox-state.md)** - State tracking

## Configuration

Auto-M4B is configured via environment variables. Here are the most important ones:

| Variable | Default | Description |
|----------|---------|-------------|
| `PUID` | 1000 | User ID for file ownership |
| `PGID` | 1000 | Group ID for file ownership |
| `CPU_CORES` | All cores | CPU cores for conversion |
| `SLEEP_TIME` | 10 | Seconds between inbox scans |
| `BACKUP` | Y | Create backup copies |
| `MAX_RETRIES` | 3 | Maximum retry attempts for failed books |
| `DEBUG` | N | Enable debug logging |

See the [Configuration Reference](docs/configuration.md) for all options.

### Conversion Metrics & Status

Auto-M4B tracks conversion statistics and displays metrics on startup:

#### View Conversion Metrics
```bash
# Using Docker
docker-compose exec auto-m4b pipenv run python -m src --status

# Using python directly
python -m src --status
```

The `--status` command shows:
- **Lifetime Statistics**: Total conversions, success rate, average duration, total data processed
- **Session Statistics**: Current uptime, conversions this session, success rate
- **Timing Stats**: Fastest and slowest conversions
- **Recent Conversions**: Last 10 conversions with status and timing
- **Recent Failures**: Last 5 failures with error details

**Example output**:
```
=== Auto-M4B Conversion Metrics ===

📊 Lifetime Statistics:
  Total Conversions: 47
  Successful:        45
  Failed:            2
  Success Rate:      95.7%
  Average Duration:  12m 34s
  Total Data:        8.3 GB

📈 Current Session:
  Uptime:            2h 15m
  Conversions:       3
  Successful:        3
  Failed:            0
  Success Rate:      100.0%
  Total Data:        654 MB

⏱️  Timing:
  Fastest: 3m 12s
  Slowest: 28m 45s

📚 Recent Conversions:
  ✓ Harry Potter Book 1 - 8m 23s - 2025-10-13 14:30
  ✓ The Hobbit - 12m 15s - 2025-10-13 12:10
  ✗ Broken Book - 2m 03s - 2025-10-13 09:45
```

Metrics are automatically displayed on container startup and are persisted to `/config/metrics.json` (or `converted/metrics.json` if running without Docker).

### Configuration Validation & Help

Auto-M4B includes built-in configuration validation and help commands:

#### Show All Configuration Options
```bash
# Using Docker
docker run --rm darthdobber/auto-m4b:latest pipenv run python -m src --help-config

# Using python directly
python -m src --help-config
```

This displays all available configuration options with descriptions and default values.

#### Validate Configuration
```bash
# Using Docker
docker-compose run --rm auto-m4b pipenv run python -m src --validate

# Using python directly
python -m src --validate
```

The `--validate` command checks your configuration for:
- ✅ Required directories exist and are accessible
- ✅ Numeric values are within valid ranges
- ✅ m4b-tool is available
- ✅ Docker is configured correctly (if using Docker mode)
- ✅ All values are properly formatted

**Example output** (valid configuration):
```
✓ Configuration is valid!

Configuration summary:
  INBOX_FOLDER:     /home/user/audiobooks/inbox
  CONVERTED_FOLDER: /home/user/audiobooks/converted
  ARCHIVE_FOLDER:   /home/user/audiobooks/archive
  BACKUP_FOLDER:    /home/user/audiobooks/backup
  FAILED_FOLDER:    /home/user/audiobooks/failed
  CPU_CORES:        8
  MAX_RETRIES:      3
  SLEEP_TIME:       10s
  m4b-tool:         m4b-tool 0.5.2
```

**Example output** (invalid configuration):
```
✗ Configuration validation failed:

  • CPU_CORES must be greater than 0, got: -1
  • SLEEP_TIME must be >= 0, got: -5
  • ON_COMPLETE must be one of ['archive', 'delete', 'test_do_nothing'], got: invalid
```

**Benefits**:
- Catch configuration errors before starting the service
- Verify directory permissions and accessibility
- Ensure m4b-tool is properly installed
- Validate environment variable values

## Example Configurations

### Basic (Recommended)

```yaml
# docker-compose.yml
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
      - PUID=1000
      - PGID=1000
      - INBOX_FOLDER=/inbox
      - CONVERTED_FOLDER=/converted
      - ARCHIVE_FOLDER=/archive
      - BACKUP_FOLDER=/backup
      - FAILED_FOLDER=/failed
```

### Performance-Optimized

```yaml
environment:
  - CPU_CORES=8
  - SLEEP_TIME=5
  - WORKING_FOLDER=/mnt/nvme/auto-m4b  # Fast SSD
```

### Space-Saving

```yaml
environment:
  - BACKUP=N
  - ON_COMPLETE=delete
```

More examples: [docs/examples/](docs/examples/)

## Common Use Cases

### Automated Pipeline

```
Download → inbox/ → Auto-M4B → converted/ → beets-audible → Plex/Audiobookshelf
```

### Manual Chapter Editing

1. Let Auto-M4B process the book
2. Edit the `.chapters.txt` file in `converted/`
3. Move folder back to `inbox/`
4. Auto-M4B will re-chapterize with your edits

### Torrent Integration

For seeding preservation, configure your torrent client:

```bash
# On torrent complete:
cp -r "%F" "/path/to/inbox/"
```

## Folder Structure

```
audiobooks/
├── inbox/          # Add audiobooks here (input)
├── converted/      # Converted M4B files (output)
├── archive/        # Original files after conversion
├── backup/         # Backup copies (optional)
└── failed/         # Books that failed after max retries
```

## Troubleshooting

### Container won't start
- Check logs: `docker-compose logs auto-m4b`
- Verify folder paths exist and are correct
- Ensure PUID/PGID match your user

### Permission errors
- Run `id` to find your UID/GID
- Update PUID/PGID in docker-compose.yml
- Restart: `docker-compose restart`

### Books not processing
- Ensure files are in subfolder: `inbox/BookName/*.mp3`
- Check supported formats: MP3, M4A, M4B, OGG, WMA
- Enable debug: `DEBUG=Y` and check logs

See the [Troubleshooting Guide](docs/troubleshooting.md) for more help.

## Project Status

This is an active fork with ongoing improvements:

- ✅ **Phase 1.1**: Pre-built Docker images (COMPLETED)
- ✅ **Phase 1.2**: Error recovery & retry logic (COMPLETED)
- ✅ **Phase 1.3**: Comprehensive documentation (COMPLETED)
- ✅ **Phase 1.4**: Configuration validation (COMPLETED)
- ✅ **Phase 1.5**: Progress reporting & metrics (COMPLETED)

See [PROJECT_ROADMAP.md](PROJECT_ROADMAP.md) for details.

## What's Different from brandonscript's Fork?

This fork includes several improvements over [brandonscript/auto-m4b](https://github.com/brandonscript/auto-m4b):

- ✅ **Automatic retry logic** - Transient errors retry automatically with exponential backoff
- ✅ **Failed book management** - Failed books moved to dedicated folder with recovery instructions
- ✅ **Conversion metrics** - Track success rates, timing statistics, and conversion history
- ✅ **Configuration validation** - Validate config before starting with `--validate` command
- ✅ **Comprehensive documentation** - Getting started, configuration, troubleshooting guides
- ✅ **Better error handling** - Improved logging and failure categorization
- 🚧 **Active development** - Ongoing improvements and features

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](docs/contributing.md) for guidelines.

Ways to contribute:
- Report bugs or suggest features
- Improve documentation
- Submit pull requests
- Test pre-release versions

## Support

- **Documentation**: [docs/README.md](docs/README.md)
- **Issues**: [GitHub Issues](https://github.com/DarthDobber/auto-m4b/issues)
- **Discussions**: [GitHub Discussions](https://github.com/DarthDobber/auto-m4b/discussions)
- **Chat**: [Gitter](https://gitter.im/Audiobook-Server/auto-m4b)

## Credits

- **Original Project**: [seanap/auto-m4b](https://github.com/seanap/auto-m4b)
- **Previous Fork**: [brandonscript/auto-m4b](https://github.com/brandonscript/auto-m4b)
- **m4b-tool**: [sandreas/m4b-tool](https://github.com/sandreas/m4b-tool)
- **Current Fork Maintainer**: [DarthDobber](https://github.com/DarthDobber)

## License

MIT License - See [LICENSE](LICENSE) for details.

---

⭐ If you find this project useful, please consider starring it on GitHub!
