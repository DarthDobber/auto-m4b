# Audiobook API

The `Audiobook` class is the core data model representing an audiobook in Auto-M4B.

## Module

`src.lib.audiobook`

## Class: Audiobook

A Pydantic BaseModel representing an audiobook with metadata, file information, and processing state.

### Initialization

```python
from pathlib import Path
from src.lib.audiobook import Audiobook

# Create from path
book = Audiobook(Path("/inbox/MyBook"))

# Path can be relative (resolved against cfg.inbox_dir)
book = Audiobook(Path("MyBook"))
```

### Properties

#### Metadata Properties

| Property | Type | Description |
|----------|------|-------------|
| `title` | `str` | Book title (from ID3 or filename) |
| `artist` | `str` | Author/artist name |
| `albumartist` | `str` | Album artist (for compilations) |
| `album` | `str` | Album name |
| `sortalbum` | `str` | Album sort name |
| `date` | `str` | Release date |
| `year` | `str \| None` | Release year |
| `narrator` | `str` | Narrator name |
| `composer` | `str` | Composer |
| `comment` | `str` | Comment field |

#### ID3 Metadata (from audio files)

| Property | Type | Description |
|----------|------|-------------|
| `id3_title` | `str` | Title from ID3 tags |
| `id3_artist` | `str` | Artist from ID3 tags |
| `id3_album` | `str` | Album from ID3 tags |
| `id3_date` | `str` | Date from ID3 tags |
| `has_id3_cover` | `bool` | Whether ID3 contains cover art |

#### Filesystem Metadata (from paths/filenames)

| Property | Type | Description |
|----------|------|-------------|
| `fs_author` | `str` | Author parsed from filename |
| `fs_title` | `str` | Title parsed from filename |
| `fs_year` | `str` | Year parsed from filename |
| `fs_narrator` | `str` | Narrator parsed from filename |

#### File Information

| Property | Type | Description |
|----------|------|-------------|
| `path` | `Path` | Audiobook directory path |
| `orig_file_type` | `AudiobookFmt` | Original format (mp3, m4a, etc.) |
| `orig_file_name` | `str` | Original filename |
| `structure` | `BookStructure` | Structure type (see below) |

#### Structure Types

The `structure` property indicates the book's file organization:

- **`standalone`**: Single audio file
- **`folder`**: Directory with multiple audio files
- **`multi-disc`**: Multiple disc subdirectories
- **`series`**: Series of books in subdirectories

### Methods

#### extract_path_info()

Extract metadata from the audiobook's path and filename.

```python
book = Audiobook(Path("/inbox/Author - Title (2023)"))
book.extract_path_info()
print(book.fs_author)  # "Author"
print(book.fs_title)   # "Title"
print(book.fs_year)    # "2023"
```

**Parameters:**
- `quiet: bool = False` - Suppress output messages

**Returns:** `Audiobook` (self, for chaining)

#### extract_metadata()

Extract ID3 metadata from audio files.

```python
book = Audiobook(Path("/inbox/MyBook"))
book.extract_metadata()
print(book.id3_title)   # Title from ID3 tags
print(book.id3_artist)  # Artist from ID3 tags
```

**Parameters:**
- `quiet: bool = False` - Suppress output messages

**Returns:** `Audiobook` (self, for chaining)

#### extract_cover_art()

Extract cover art from ID3 tags and save to file.

```python
book = Audiobook(Path("/inbox/MyBook"))
cover = book.extract_cover_art()
print(cover)  # Path to extracted cover.jpg
```

**Returns:** `Path | None` - Path to cover art file, or None if not found

#### is_a()

Check if the audiobook matches a specific structure or format.

```python
# Check structure
if book.is_a("folder"):
    print("Book is a multi-file folder")

# Check format (and exclude another)
if book.is_a("standalone", not_fmt="m4b"):
    print("Book is a standalone file, but not M4B")
```

**Parameters:**
- `structure: BookStructure | None` - Structure to check
- `not_structure: BookStructure | None` - Structure to exclude
- `fmt: AudiobookFmt | None` - Format to check
- `not_fmt: AudiobookFmt | None` - Format to exclude

**Returns:** `bool`

### Cached Properties

These properties are computed once and cached for performance.

#### File & Audio Information

| Property | Type | Description |
|----------|------|-------------|
| `key` | `str` | Unique identifier (path hash) |
| `structure` | `BookStructure` | Book structure type |
| `dir_name` | `str` | Directory name |
| `audio_files` | `list[Path]` | List of audio files |
| `audio_file_count` | `int` | Number of audio files |
| `sample_audio1` | `Path` | First audio file (for metadata) |
| `sample_audio2` | `Path` | Second audio file (if exists) |

#### Cover Art

| Property | Type | Description |
|----------|------|-------------|
| `cover_art_file` | `Path \| None` | Path to cover art file |
| `has_cover_art` | `bool` | Whether cover art exists |

#### Audio Analysis

| Property | Type | Description |
|----------|------|-------------|
| `duration` | `float` | Total duration in seconds |
| `duration_friendly` | `str` | Human-readable duration |
| `bitrate` | `int` | Bitrate in bps |
| `bitrate_friendly` | `str` | Human-readable bitrate |
| `samplerate` | `int` | Sample rate in Hz |

#### Size Information

| Property | Type | Description |
|----------|------|-------------|
| `size` | `int` | Total size in bytes |
| `size_friendly` | `str` | Human-readable size |

#### Path Locations

| Property | Type | Description |
|----------|------|-------------|
| `inbox_dir` | `Path` | Path in inbox |
| `merge_dir` | `Path` | Path in merge directory |
| `build_dir` | `Path` | Path in build directory |
| `backup_dir` | `Path` | Path in backup directory |
| `archive_dir` | `Path` | Path in archive directory |
| `converted_dir` | `Path` | Path in converted directory |

## Usage Examples

### Basic Usage

```python
from pathlib import Path
from src.lib.audiobook import Audiobook

# Create audiobook object
book = Audiobook(Path("/inbox/Dresden Files - Book 01"))

# Extract all metadata
book.extract_path_info()
book.extract_metadata()

# Access properties
print(f"Title: {book.title}")
print(f"Author: {book.artist}")
print(f"Duration: {book.duration_friendly}")
print(f"Size: {book.size_friendly}")
print(f"Structure: {book.structure}")
```

### Checking Book Type

```python
# Check if already M4B
if book.is_a("standalone", fmt="m4b"):
    print("Already converted to M4B")

# Check if needs conversion
if book.is_a("folder", not_fmt="m4b"):
    print("Multi-file book needs conversion")
```

### Getting File Paths

```python
# Get list of audio files
for audio_file in book.audio_files:
    print(audio_file)

# Get working directories
print(f"Build in: {book.build_dir}")
print(f"Output to: {book.converted_dir}")
```

### Extracting Cover Art

```python
cover = book.extract_cover_art()
if cover:
    print(f"Cover art saved to: {cover}")
else:
    print("No cover art found")
```

### Analyzing Audio

```python
print(f"Total duration: {book.duration_friendly}")
print(f"Bitrate: {book.bitrate_friendly}")
print(f"Sample rate: {book.samplerate} Hz")
print(f"Number of files: {book.audio_file_count}")
```

## Type Definitions

### AudiobookFmt

Valid audio format strings:

```python
AudiobookFmt = Literal["mp3", "m4a", "m4b", "ogg", "wma", ""]
```

### BookStructure

Valid structure types:

```python
BookStructure = Literal["standalone", "folder", "multi-disc", "series"]
```

## Integration with Other Components

### With InboxState

```python
from src.lib.inbox_state import InboxState

inbox = InboxState()
item = inbox.get("book-key")
book = item.to_audiobook()
```

### With Converter

```python
from src.lib.run import convert_book

success = convert_book(book)
```

### With m4b-tool

```python
from src.lib.m4btool import M4bTool

m4b = M4bTool()
result = m4b.merge(
    input_dir=book.build_dir,
    output_file=book.converted_dir / f"{book.dir_name}.m4b",
    use_filenames_as_chapters=True
)
```

## See Also

- [Config API](config.md) - Configuration management
- [Inbox State API](inbox-state.md) - State tracking
- [Architecture Overview](../architecture.md) - System design
