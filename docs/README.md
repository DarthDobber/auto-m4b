# Auto-M4B Documentation

Welcome to the Auto-M4B documentation! This guide will help you get started with automated audiobook conversion and management.

## Quick Links

### Getting Started
- **[Getting Started Guide](getting-started.md)** - Quick start guide for new users
- **[Configuration Reference](configuration.md)** - Complete list of all environment variables and settings
- **[Docker Compose Examples](examples/)** - Example configurations for common use cases

### Troubleshooting & Guides
- **[Troubleshooting Guide](troubleshooting.md)** - Common issues and solutions
- **[Architecture Overview](architecture.md)** - System design and technical details
- **[Contributing Guide](contributing.md)** - How to contribute to the project

### API Documentation
- **[Audiobook API](api/audiobook.md)** - Audiobook class and book processing
- **[Config API](api/config.md)** - Configuration management
- **[Inbox State API](api/inbox-state.md)** - State management and tracking

## What is Auto-M4B?

Auto-M4B is a Docker-based automation tool that:
- **Watches** a folder for new audiobooks
- **Converts** multi-file MP3/M4A/OGG books to chapterized M4B format
- **Organizes** completed books into an output folder
- **Archives** original files for safekeeping
- **Backs up** your data (optional)

## Quick Start

```bash
# 1. Create your folder structure
mkdir -p ~/audiobooks/{inbox,converted,archive,backup}

# 2. Create docker-compose.yml
cat > docker-compose.yml << EOF
version: '3.7'
services:
  auto-m4b:
    image: darthdobber/auto-m4b
    container_name: auto-m4b
    restart: unless-stopped
    volumes:
      - ~/audiobooks/inbox:/inbox
      - ~/audiobooks/converted:/converted
      - ~/audiobooks/archive:/archive
      - ~/audiobooks/backup:/backup
    environment:
      - PUID=1000
      - PGID=1000
      - INBOX_FOLDER=/inbox
      - CONVERTED_FOLDER=/converted
      - ARCHIVE_FOLDER=/archive
      - BACKUP_FOLDER=/backup
EOF

# 3. Start the container
docker-compose up -d

# 4. Add audiobooks to ~/audiobooks/inbox
# They'll automatically be converted and moved to ~/audiobooks/converted
```

See the **[Getting Started Guide](getting-started.md)** for detailed instructions.

## Key Features

### ✅ Automated Conversion
- Converts MP3, M4A, M4B, OGG, and WMA files
- Creates chapterized M4B audiobooks
- Preserves metadata and cover art
- Handles multi-disc books and series

### ✅ Smart Processing
- Watches inbox folder continuously
- Handles nested folder structures
- Detects and skips already-processed books
- Graceful error handling

### ✅ Flexible Configuration
- Configure via environment variables
- Adjustable CPU cores, chapter lengths, and more
- Test mode for dry runs
- Debug mode for troubleshooting

### ✅ Docker-Ready
- Pre-built images on Docker Hub
- No manual dependencies to install
- Configurable PUID/PGID for permissions
- Works on Linux, macOS (Intel/ARM), and Windows

## System Requirements

- **Docker** and **Docker Compose** installed
- **CPU**: Multi-core recommended (configurable)
- **Storage**: Sufficient space for inbox, converted, archive, and working directories
- **Supported Audio Formats**: MP3, M4A, M4B, OGG, WMA

## Common Use Cases

### Automated Audiobook Pipeline
```
1. Download audiobooks → inbox/
2. Auto-M4B converts to M4B → converted/
3. Tag with beets-audible → organized library
4. Import to Plex/Audiobookshelf
```

### Manual Chapter Adjustment
1. Let Auto-M4B process the book
2. Edit the `.chapters.txt` file in the output
3. Move folder back to `inbox/` for re-processing

### Batch Conversion
```bash
# Copy multiple books at once
cp -r /path/to/books/* ~/audiobooks/inbox/

# Auto-M4B will process them sequentially
```

## Getting Help

- **Issues**: Check the [Troubleshooting Guide](troubleshooting.md)
- **Questions**: [GitHub Discussions](https://github.com/DarthDobber/auto-m4b/discussions)
- **Bugs**: [GitHub Issues](https://github.com/DarthDobber/auto-m4b/issues)
- **Contributing**: See [Contributing Guide](contributing.md)

## Credits

- **Original Project**: [brandonscript/auto-m4b](https://github.com/brandonscript/auto-m4b)
- **Fork Maintainer**: [DarthDobber](https://github.com/DarthDobber)
- **Powered By**: [m4b-tool](https://github.com/sandreas/m4b-tool) by sandreas

## License

This project is licensed under the MIT License. See the LICENSE file for details.
