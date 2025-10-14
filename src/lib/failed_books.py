"""Failed Books Management

Utilities for tracking and managing books that have been moved to the failed folder
after exhausting all retry attempts.
"""

import json
import time
from pathlib import Path
from typing import Optional


class FailedBook:
    """Represents a book in the failed folder"""

    def __init__(self, failed_dir: Path):
        self.path = failed_dir
        self.name = self._extract_book_name(failed_dir.name)
        self.timestamp_str = self._extract_timestamp(failed_dir.name)
        self.failed_at = self.path.stat().st_mtime
        self.size = self._calculate_size()
        self.error_message = self._read_error_info()
        self.retry_count = self._read_retry_count()

    @staticmethod
    def _extract_book_name(dirname: str) -> str:
        """Extract book name from timestamped directory name

        Example: 'test corrupt_2025-10-13_23-06-32' -> 'test corrupt'
        """
        # Split on last underscore followed by date pattern
        parts = dirname.rsplit('_', 2)
        if len(parts) >= 3:
            return parts[0]
        return dirname

    @staticmethod
    def _extract_timestamp(dirname: str) -> str:
        """Extract timestamp from directory name

        Example: 'test corrupt_2025-10-13_23-06-32' -> '2025-10-13 23:06:32'
        """
        parts = dirname.rsplit('_', 2)
        if len(parts) >= 3:
            date_part = parts[1]
            time_part = parts[2].replace('-', ':')
            return f"{date_part} {time_part}"
        return ""

    def _calculate_size(self) -> int:
        """Calculate total size of all files in failed folder"""
        total = 0
        try:
            for file in self.path.rglob('*'):
                if file.is_file():
                    total += file.stat().st_size
        except Exception:
            pass
        return total

    def _read_error_info(self) -> str:
        """Read error message from FAILED_INFO.txt"""
        info_file = self.path / "FAILED_INFO.txt"
        if info_file.exists():
            try:
                content = info_file.read_text()
                # Extract first error line (usually most informative)
                lines = [line.strip() for line in content.split('\n') if line.strip()]
                if lines:
                    # Find first line that looks like an error
                    for line in lines:
                        if any(keyword in line.lower() for keyword in ['error', 'failed', 'invalid', 'corrupt']):
                            return line
                    return lines[0]  # Fallback to first line
            except Exception:
                pass

        # Try to read from log file
        log_files = list(self.path.glob("*.log"))
        if log_files:
            try:
                content = log_files[0].read_text()
                lines = [line.strip() for line in content.split('\n') if line.strip()]
                for line in reversed(lines[-20:]):  # Check last 20 lines
                    if any(keyword in line.lower() for keyword in ['error', 'failed']):
                        return line
            except Exception:
                pass

        return "Unknown error"

    def _read_retry_count(self) -> int:
        """Try to determine retry count from FAILED_INFO.txt"""
        info_file = self.path / "FAILED_INFO.txt"
        if info_file.exists():
            try:
                content = info_file.read_text()
                # Look for retry count patterns
                import re
                match = re.search(r'retry[_ ]count[:\s]+(\d+)', content, re.IGNORECASE)
                if match:
                    return int(match.group(1))
                match = re.search(r'attempt[:\s]+(\d+)/(\d+)', content, re.IGNORECASE)
                if match:
                    return int(match.group(1))
            except Exception:
                pass
        return 3  # Assume max retries if we can't determine

    def to_dict(self) -> dict:
        """Convert to dictionary for API response"""
        return {
            "key": self.name,
            "path": str(self.path),
            "status": "archived",  # Special status for moved books
            "size_bytes": self.size,
            "failed_at": self.failed_at,
            "timestamp_str": self.timestamp_str,
            "failed_reason": self.error_message,
            "retry_count": self.retry_count,
            "is_archived": True,
            "can_requeue": True  # Can be moved back to inbox
        }


def scan_failed_folder(failed_dir: Path) -> list[FailedBook]:
    """Scan the failed folder and return list of FailedBook objects"""
    failed_books = []

    if not failed_dir.exists():
        return failed_books

    try:
        for item in failed_dir.iterdir():
            if item.is_dir():
                try:
                    failed_book = FailedBook(item)
                    failed_books.append(failed_book)
                except Exception as e:
                    # Skip books that can't be parsed
                    print(f"Warning: Could not parse failed book {item}: {e}")
                    continue
    except Exception as e:
        print(f"Warning: Could not scan failed folder {failed_dir}: {e}")

    # Sort by most recent first
    failed_books.sort(key=lambda x: x.failed_at, reverse=True)

    return failed_books


def get_failed_book(failed_dir: Path, book_key: str) -> Optional[FailedBook]:
    """Get a specific failed book by key (name)"""
    failed_books = scan_failed_folder(failed_dir)

    # Find most recent match for this book name
    for book in failed_books:
        if book.name == book_key:
            return book

    return None
