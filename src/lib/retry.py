"""
Retry logic and error categorization for Auto-M4B.

This module provides utilities for:
- Categorizing errors as transient or permanent
- Calculating exponential backoff delays
- Managing retry state for failed books
"""

import re
import time
from typing import Literal

ErrorType = Literal["transient", "permanent"]

# Error patterns that indicate transient (retryable) errors
TRANSIENT_ERROR_PATTERNS = [
    # Network/Connection errors
    r"connection\s+(timed?\s*out|reset|refused|aborted)",
    r"network\s+is\s+unreachable",
    r"temporary\s+failure",
    r"no\s+route\s+to\s+host",
    r"name\s+or\s+service\s+not\s+known",

    # Resource exhaustion (temporary)
    r"out\s+of\s+memory",
    r"cannot\s+allocate\s+memory",
    r"no\s+space\s+left\s+on\s+device",
    r"disk\s+full",
    r"too\s+many\s+open\s+files",

    # I/O errors (may be transient)
    r"i/o\s+error",
    r"input/output\s+error",
    r"read\s+error",
    r"write\s+error",

    # Process/System errors
    r"resource\s+temporarily\s+unavailable",
    r"broken\s+pipe",
    r"device\s+or\s+resource\s+busy",

    # Docker/Container errors
    r"docker\s+daemon\s+is\s+not\s+running",
    r"cannot\s+connect\s+to\s+docker",

    # m4b-tool specific transient errors
    r"could\s+not\s+create\s+temp",
    r"ffmpeg.*hung",
    r"conversion\s+timeout",
]

# Error patterns that indicate permanent (non-retryable) errors
PERMANENT_ERROR_PATTERNS = [
    # File format/corruption issues
    r"invalid\s+(format|file|data|header)",
    r"corrupt(ed)?\s+(file|data|stream)",
    r"unsupported\s+(format|codec|file)",
    r"not\s+a\s+valid\s+audio\s+file",
    r"no\s+audio\s+streams?\s+found",
    r"could\s+not\s+find\s+codec",

    # Permission/Access issues (usually need manual fix)
    r"permission\s+denied",
    r"access\s+denied",
    r"operation\s+not\s+permitted",

    # File not found (usually indicates structural problem)
    r"no\s+such\s+file\s+or\s+directory",
    r"file\s+not\s+found",

    # Configuration errors
    r"invalid\s+configuration",
    r"missing\s+required\s+(parameter|option|argument)",

    # Structural problems
    r"multi.*nested.*folders?",
    r"multiple\s+books\s+found",
    r"could\s+not\s+determine\s+structure",
]


def categorize_error(error_message: str) -> ErrorType:
    """
    Categorize an error as transient or permanent based on the error message.

    Args:
        error_message: The error message to categorize

    Returns:
        "transient" if the error might be fixed by retrying
        "permanent" if the error requires manual intervention
    """
    error_lower = error_message.lower()

    # Check permanent patterns first (more specific)
    for pattern in PERMANENT_ERROR_PATTERNS:
        if re.search(pattern, error_lower, re.IGNORECASE):
            return "permanent"

    # Check transient patterns
    for pattern in TRANSIENT_ERROR_PATTERNS:
        if re.search(pattern, error_lower, re.IGNORECASE):
            return "transient"

    # Default to transient (give it a chance to retry)
    # Better to retry once than to give up immediately
    return "transient"


def calculate_backoff_delay(retry_count: int, base_delay: int = 60, max_delay: int = 3600) -> int:
    """
    Calculate exponential backoff delay with jitter.

    Formula: min(base_delay * (2 ** retry_count), max_delay)

    Args:
        retry_count: Number of retries attempted (0-indexed)
        base_delay: Base delay in seconds (default: 60)
        max_delay: Maximum delay in seconds (default: 3600 = 1 hour)

    Returns:
        Delay in seconds before next retry

    Examples:
        >>> calculate_backoff_delay(0, base_delay=60)
        60  # 1 minute

        >>> calculate_backoff_delay(1, base_delay=60)
        120  # 2 minutes

        >>> calculate_backoff_delay(2, base_delay=60)
        240  # 4 minutes

        >>> calculate_backoff_delay(3, base_delay=60)
        480  # 8 minutes

        >>> calculate_backoff_delay(10, base_delay=60)
        3600  # Capped at 1 hour
    """
    # Exponential backoff: base * (2 ^ retry_count)
    delay = base_delay * (2 ** retry_count)

    # Cap at maximum delay
    delay = min(delay, max_delay)

    return int(delay)


def should_retry(
    retry_count: int,
    max_retries: int,
    is_transient: bool,
    retry_transient_errors: bool,
) -> bool:
    """
    Determine if a failed book should be retried.

    Args:
        retry_count: Number of times already retried
        max_retries: Maximum number of retries allowed
        is_transient: Whether the error is transient
        retry_transient_errors: Whether transient errors should be retried

    Returns:
        True if the book should be retried, False otherwise
    """
    # Don't retry if feature is disabled
    if not retry_transient_errors:
        return False

    # Don't retry permanent errors
    if not is_transient:
        return False

    # Don't retry if max retries exceeded
    if retry_count >= max_retries:
        return False

    return True


def can_retry_now(
    last_retry_time: float,
    retry_count: int,
    base_delay: int = 60,
) -> tuple[bool, int]:
    """
    Check if enough time has passed for the next retry attempt.

    Args:
        last_retry_time: Timestamp of last retry attempt
        retry_count: Number of retries attempted
        base_delay: Base delay for backoff calculation

    Returns:
        Tuple of (can_retry_now, seconds_until_retry)
    """
    if last_retry_time == 0:
        return True, 0

    required_delay = calculate_backoff_delay(retry_count - 1, base_delay)
    elapsed = time.time() - last_retry_time

    if elapsed >= required_delay:
        return True, 0

    seconds_until = int(required_delay - elapsed)
    return False, seconds_until


def format_retry_message(
    book_name: str,
    retry_count: int,
    max_retries: int,
    error_type: ErrorType,
    next_retry_seconds: int = 0,
) -> str:
    """
    Format a user-friendly retry status message.

    Args:
        book_name: Name of the failed book
        retry_count: Current retry count
        max_retries: Maximum retries allowed
        error_type: Type of error (transient or permanent)
        next_retry_seconds: Seconds until next retry

    Returns:
        Formatted message string
    """
    if error_type == "permanent":
        return f"{book_name}: Permanent error detected, will not retry (manual fix required)"

    if retry_count >= max_retries:
        return f"{book_name}: Max retries ({max_retries}) exceeded, giving up"

    if next_retry_seconds > 0:
        minutes = next_retry_seconds // 60
        if minutes > 60:
            hours = minutes // 60
            return f"{book_name}: Retry {retry_count + 1}/{max_retries} in ~{hours}h"
        elif minutes > 0:
            return f"{book_name}: Retry {retry_count + 1}/{max_retries} in ~{minutes}m"
        else:
            return f"{book_name}: Retry {retry_count + 1}/{max_retries} in {next_retry_seconds}s"

    return f"{book_name}: Ready for retry {retry_count + 1}/{max_retries}"
