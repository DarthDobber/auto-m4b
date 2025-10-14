"""
Progress bar utilities for Auto-M4B conversions.

Provides progress tracking and display for audiobook conversions.
"""

import re
import sys
from typing import Callable


class ProgressTracker:
    """
    Tracks and displays conversion progress.

    Parses m4b-tool output to extract progress information and displays
    a progress bar in the terminal.
    """

    def __init__(self, book_name: str, show_progress: bool = True):
        """
        Initialize progress tracker.

        Args:
            book_name: Name of the book being converted
            show_progress: Whether to show progress bar (False for non-TTY)
        """
        self.book_name = book_name
        self.show_progress = show_progress and sys.stdout.isatty()
        self.current_progress = 0
        self.last_line = ""
        self.stages = {
            "merge": False,
            "split": False,
            "convert": False,
        }

    def parse_progress(self, line: str) -> int | None:
        """
        Parse progress from m4b-tool output line.

        m4b-tool outputs lines like:
        - "Progress: 45.2%"
        - "merging files..."
        - "splitting audio..."

        Args:
            line: Output line from m4b-tool

        Returns:
            Progress percentage (0-100) or None if no progress info
        """
        # Look for percentage
        if match := re.search(r'(\d+(?:\.\d+)?)\s*%', line):
            return int(float(match.group(1)))

        # Stage detection
        if "merg" in line.lower():
            self.stages["merge"] = True
            return 10
        elif "split" in line.lower():
            self.stages["split"] = True
            return 40
        elif "convert" in line.lower():
            self.stages["convert"] = True
            return 70

        return None

    def update(self, line: str):
        """
        Update progress from m4b-tool output line.

        Args:
            line: Output line from m4b-tool
        """
        if not self.show_progress:
            return

        progress = self.parse_progress(line)
        if progress is not None:
            self.current_progress = progress
            self.display()

    def display(self):
        """Display current progress bar."""
        if not self.show_progress:
            return

        # Progress bar configuration
        bar_length = 40
        filled_length = int(bar_length * self.current_progress / 100)
        bar = '█' * filled_length + '░' * (bar_length - filled_length)

        # Determine stage
        stage = "Converting"
        if self.stages["merge"] and not self.stages["split"]:
            stage = "Merging"
        elif self.stages["split"] and not self.stages["convert"]:
            stage = "Splitting"

        # Format progress line
        progress_line = f"\r{stage}: [{bar}] {self.current_progress}%"

        # Print (overwrite previous line)
        sys.stdout.write(progress_line)
        sys.stdout.flush()
        self.last_line = progress_line

    def complete(self):
        """Mark progress as complete."""
        if not self.show_progress:
            return

        self.current_progress = 100
        self.display()
        sys.stdout.write("\n")  # New line after completion
        sys.stdout.flush()

    def clear(self):
        """Clear the progress bar from terminal."""
        if not self.show_progress or not self.last_line:
            return

        # Clear the line
        sys.stdout.write('\r' + ' ' * len(self.last_line) + '\r')
        sys.stdout.flush()


class SimpleSpinner:
    """
    Simple spinner for operations without measurable progress.

    Shows a spinning animation to indicate activity.
    """

    FRAMES = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']

    def __init__(self, message: str = "Processing", show: bool = True):
        """
        Initialize spinner.

        Args:
            message: Message to display with spinner
            show: Whether to show spinner (False for non-TTY)
        """
        self.message = message
        self.show = show and sys.stdout.isatty()
        self.frame_index = 0

    def spin(self):
        """Advance spinner to next frame."""
        if not self.show:
            return

        frame = self.FRAMES[self.frame_index % len(self.FRAMES)]
        sys.stdout.write(f'\r{frame} {self.message}...')
        sys.stdout.flush()
        self.frame_index += 1

    def stop(self, final_message: str = ""):
        """
        Stop spinner and optionally display final message.

        Args:
            final_message: Message to display after stopping (e.g., "Done!")
        """
        if not self.show:
            return

        if final_message:
            sys.stdout.write(f'\r✓ {final_message}\n')
        else:
            sys.stdout.write('\r' + ' ' * (len(self.message) + 10) + '\r')
        sys.stdout.flush()


def format_duration(seconds: int | float) -> str:
    """
    Format duration in human-readable format.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string like "2h 15m 30s" or "45m 12s" or "23s"
    """
    seconds = int(seconds)

    if seconds < 60:
        return f"{seconds}s"

    minutes = seconds // 60
    secs = seconds % 60

    if minutes < 60:
        return f"{minutes}m {secs}s" if secs > 0 else f"{minutes}m"

    hours = minutes // 60
    mins = minutes % 60

    parts = [f"{hours}h"]
    if mins > 0:
        parts.append(f"{mins}m")
    if secs > 0 and hours == 0:  # Only show seconds if less than 1 hour
        parts.append(f"{secs}s")

    return " ".join(parts)


def format_bytes(bytes_count: int) -> str:
    """
    Format byte count in human-readable format.

    Args:
        bytes_count: Number of bytes

    Returns:
        Formatted string like "1.5 GB" or "234 MB"
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_count < 1024.0:
            if unit == 'B':
                return f"{bytes_count} {unit}"
            return f"{bytes_count:.1f} {unit}"
        bytes_count /= 1024.0
    return f"{bytes_count:.1f} PB"


def with_progress(func: Callable, book_name: str, show_progress: bool = True):
    """
    Decorator to add progress tracking to a conversion function.

    Args:
        func: Function that performs conversion
        book_name: Name of book being converted
        show_progress: Whether to show progress

    Returns:
        Wrapped function with progress tracking
    """
    def wrapper(*args, **kwargs):
        tracker = ProgressTracker(book_name, show_progress)
        try:
            result = func(*args, tracker=tracker, **kwargs)
            tracker.complete()
            return result
        except Exception as e:
            tracker.clear()
            raise e

    return wrapper


__all__ = [
    "ProgressTracker",
    "SimpleSpinner",
    "format_duration",
    "format_bytes",
    "with_progress",
]
