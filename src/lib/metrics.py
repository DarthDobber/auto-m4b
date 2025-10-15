"""
Conversion metrics tracking and persistence for Auto-M4B.

This module provides:
- ConversionMetrics class for tracking conversion statistics
- Metrics persistence to JSON file
- Success/failure rate tracking
- Conversion time statistics
- Data volume tracking
"""

import json
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Literal

from src.lib.misc import singleton


@dataclass
class ConversionRecord:
    """Individual conversion record."""

    book_name: str
    status: Literal["success", "failed"]
    duration_seconds: int
    timestamp: float
    file_size_bytes: int = 0
    error_message: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ConversionRecord":
        """Create from dictionary."""
        return cls(**data)

    @property
    def timestamp_str(self) -> str:
        """Human-readable timestamp."""
        return datetime.fromtimestamp(self.timestamp).strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class SessionStats:
    """Statistics for current session."""

    started_at: float = field(default_factory=time.time)
    conversions_attempted: int = 0
    conversions_successful: int = 0
    conversions_failed: int = 0
    total_duration_seconds: int = 0
    total_bytes_processed: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SessionStats":
        """Create from dictionary."""
        return cls(**data)

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.conversions_attempted == 0:
            return 0.0
        return (self.conversions_successful / self.conversions_attempted) * 100

    @property
    def avg_duration(self) -> float:
        """Average conversion duration in seconds."""
        if self.conversions_attempted == 0:
            return 0.0
        return self.total_duration_seconds / self.conversions_attempted

    @property
    def uptime_seconds(self) -> int:
        """Session uptime in seconds."""
        return int(time.time() - self.started_at)


@singleton
class ConversionMetrics:
    """
    Tracks and persists conversion metrics across restarts.

    Provides:
    - Lifetime statistics (all-time totals)
    - Current session statistics
    - Recent conversion history
    - Persistence to JSON file
    """

    MAX_HISTORY = 100  # Keep last 100 conversions

    def __init__(self):
        # Lifetime statistics (persisted)
        self.lifetime_attempted: int = 0
        self.lifetime_successful: int = 0
        self.lifetime_failed: int = 0
        self.lifetime_duration_seconds: int = 0
        self.lifetime_bytes_processed: int = 0

        # Timing statistics
        self.fastest_conversion_seconds: int = 0
        self.slowest_conversion_seconds: int = 0

        # Current session
        self.session = SessionStats()

        # Recent history (limited to MAX_HISTORY)
        self.history: list[ConversionRecord] = []

        # Metadata
        self.first_run_timestamp: float = time.time()
        self.last_updated_timestamp: float = time.time()

        # Load existing metrics if available
        self._metrics_file: Path | None = None
        self._loaded = False

    def set_metrics_file(self, path: Path):
        """Set the metrics file path and load existing data.

        On initial load, session stats are reset to fresh values and file is saved
        to ensure subsequent reloads don't restore old session data.
        """
        self._metrics_file = path
        if not self._loaded:
            self.load()
            self._loaded = True
            # Save immediately to overwrite old session data in file
            self.save()

    def record_conversion(
        self,
        book_name: str,
        status: Literal["success", "failed"],
        duration_seconds: int,
        file_size_bytes: int = 0,
        error_message: str = "",
    ):
        """
        Record a conversion result.

        Args:
            book_name: Name of the audiobook
            status: "success" or "failed"
            duration_seconds: How long the conversion took
            file_size_bytes: Size of the converted file (if successful)
            error_message: Error message if failed
        """
        # Create record
        record = ConversionRecord(
            book_name=book_name,
            status=status,
            duration_seconds=duration_seconds,
            timestamp=time.time(),
            file_size_bytes=file_size_bytes,
            error_message=error_message,
        )

        # Add to history (keep only MAX_HISTORY)
        self.history.append(record)
        if len(self.history) > self.MAX_HISTORY:
            self.history = self.history[-self.MAX_HISTORY:]

        # Update lifetime stats
        self.lifetime_attempted += 1
        self.lifetime_duration_seconds += duration_seconds
        self.lifetime_bytes_processed += file_size_bytes

        if status == "success":
            self.lifetime_successful += 1

            # Update timing stats (only for successful conversions)
            if duration_seconds > 0:  # Only consider non-zero durations
                if self.fastest_conversion_seconds == 0 or duration_seconds < self.fastest_conversion_seconds:
                    self.fastest_conversion_seconds = duration_seconds
                if duration_seconds > self.slowest_conversion_seconds:
                    self.slowest_conversion_seconds = duration_seconds
        else:
            self.lifetime_failed += 1

        # Update session stats
        self.session.conversions_attempted += 1
        self.session.total_duration_seconds += duration_seconds
        self.session.total_bytes_processed += file_size_bytes

        if status == "success":
            self.session.conversions_successful += 1
        else:
            self.session.conversions_failed += 1

        # Update timestamp and save
        self.last_updated_timestamp = time.time()
        self.save()

    @property
    def lifetime_success_rate(self) -> float:
        """Calculate lifetime success rate percentage."""
        if self.lifetime_attempted == 0:
            return 0.0
        return (self.lifetime_successful / self.lifetime_attempted) * 100

    @property
    def lifetime_avg_duration(self) -> float:
        """Average conversion duration across all conversions."""
        if self.lifetime_attempted == 0:
            return 0.0
        return self.lifetime_duration_seconds / self.lifetime_attempted

    def to_dict(self) -> dict:
        """Convert metrics to dictionary for persistence."""
        return {
            "lifetime_attempted": self.lifetime_attempted,
            "lifetime_successful": self.lifetime_successful,
            "lifetime_failed": self.lifetime_failed,
            "lifetime_duration_seconds": self.lifetime_duration_seconds,
            "lifetime_bytes_processed": self.lifetime_bytes_processed,
            "fastest_conversion_seconds": self.fastest_conversion_seconds,
            "slowest_conversion_seconds": self.slowest_conversion_seconds,
            "first_run_timestamp": self.first_run_timestamp,
            "last_updated_timestamp": self.last_updated_timestamp,
            "session": self.session.to_dict(),
            "history": [record.to_dict() for record in self.history],
        }

    def from_dict(self, data: dict):
        """Load metrics from dictionary.

        Note: Session stats are only loaded AFTER initial startup.
        On first load (_loaded=False), session starts fresh with current timestamp.
        On subsequent reloads (_loaded=True), session data is loaded to preserve current session progress.
        """
        self.lifetime_attempted = data.get("lifetime_attempted", 0)
        self.lifetime_successful = data.get("lifetime_successful", 0)
        self.lifetime_failed = data.get("lifetime_failed", 0)
        self.lifetime_duration_seconds = data.get("lifetime_duration_seconds", 0)
        self.lifetime_bytes_processed = data.get("lifetime_bytes_processed", 0)
        self.fastest_conversion_seconds = data.get("fastest_conversion_seconds", 0)
        self.slowest_conversion_seconds = data.get("slowest_conversion_seconds", 0)
        self.first_run_timestamp = data.get("first_run_timestamp", time.time())
        self.last_updated_timestamp = data.get("last_updated_timestamp", time.time())

        # Load session stats only if this is a reload (not initial startup)
        if self._loaded:
            session_data = data.get("session", {})
            if session_data:
                self.session = SessionStats.from_dict(session_data)
        # else: keep the fresh SessionStats() created in __init__

        # Load history
        history_data = data.get("history", [])
        self.history = [ConversionRecord.from_dict(record) for record in history_data]

    def save(self):
        """Persist metrics to JSON file."""
        if not self._metrics_file:
            return

        try:
            self._metrics_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._metrics_file, 'w') as f:
                json.dump(self.to_dict(), f, indent=2)
        except Exception as e:
            # Silently fail - metrics are not critical
            pass

    def load(self):
        """Load metrics from JSON file."""
        if not self._metrics_file or not self._metrics_file.exists():
            return

        try:
            with open(self._metrics_file, 'r') as f:
                data = json.load(f)
                self.from_dict(data)
        except Exception as e:
            # If we can't load, start fresh
            pass

    def get_recent_conversions(self, limit: int = 10) -> list[ConversionRecord]:
        """Get N most recent conversions."""
        return self.history[-limit:] if self.history else []

    def get_recent_failures(self, limit: int = 10) -> list[ConversionRecord]:
        """Get N most recent failed conversions."""
        failures = [r for r in self.history if r.status == "failed"]
        return failures[-limit:] if failures else []

    def reset_session(self):
        """Reset current session statistics."""
        self.session = SessionStats()

    def reset_all(self):
        """Reset all metrics (useful for testing)."""
        self.__init__()
        if self._metrics_file and self._metrics_file.exists():
            self._metrics_file.unlink()


# Singleton instance
metrics = ConversionMetrics()

__all__ = ["ConversionMetrics", "ConversionRecord", "SessionStats", "metrics"]
