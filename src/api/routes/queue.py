"""Queue endpoints for viewing book processing queue"""

import time
from typing import Optional
from fastapi import APIRouter, HTTPException
from src.api.schemas.v1 import (
    QueueResponse,
    QueueSummary,
    QueueBook,
    QueueBookDetailResponse,
    QueueBookDetail,
    RetryHistoryItem,
    SeriesInfo
)

router = APIRouter()


def build_series_info(item) -> Optional[SeriesInfo]:
    """Build series info if book is part of a series"""
    if not item.is_maybe_series_book:
        return None

    parent = item.series_parent
    if not parent or not parent.is_maybe_series_parent:
        return None

    series_books = parent.series_books
    try:
        book_index = series_books.index(item) + 1  # 1-indexed
    except ValueError:
        book_index = 0

    return SeriesInfo(
        parent_key=parent.key,
        book_index=book_index,
        total_books=len(series_books),
        is_complete=True  # Could check if all books are present
    )


def build_queue_book(item, include_retry_details: bool = True) -> dict:
    """Build queue book data dictionary from InboxItem"""
    from src.lib.retry import can_retry_now, should_retry
    from src.lib.config import cfg

    book_data = {
        "key": item.key,
        "path": str(item.path),
        "status": item.status,
        "size_bytes": item.size,
        "last_updated": item.last_updated,
        "hash": item.hash,
        "is_filtered": item.is_filtered,
        "series_info": build_series_info(item)
    }

    # Add retry metadata if failed
    if include_retry_details and item.status in ["failed", "needs_retry"]:
        can_retry, seconds_until = can_retry_now(
            item.last_retry_time,
            item.retry_count,
            cfg.RETRY_BASE_DELAY
        )

        will_retry = should_retry(
            item.retry_count,
            cfg.MAX_RETRIES,
            item.is_transient_error,
            cfg.RETRY_TRANSIENT_ERRORS
        )

        next_retry_at = None
        if will_retry and not can_retry:
            next_retry_at = item.last_retry_time + seconds_until

        book_data.update({
            "failed_reason": item.failed_reason,
            "retry_count": item.retry_count,
            "max_retries": cfg.MAX_RETRIES,
            "is_transient": item.is_transient_error,
            "will_retry": will_retry,
            "next_retry_at": next_retry_at,
            "retry_countdown_seconds": seconds_until if not can_retry else 0
        })

    return book_data


@router.get("/api/v1/queue", response_model=QueueResponse)
def get_queue():
    """
    Get all books in the processing queue.

    Returns summary counts and detailed list of all books
    with their current status and retry metadata.
    """
    from src.lib.inbox_state import InboxState

    inbox = InboxState()
    inbox.scan()  # Ensure fresh data

    books = []
    for item in inbox.matched_books.values():
        book_data = build_queue_book(item)
        books.append(QueueBook(**book_data))

    # Calculate summary
    summary = QueueSummary(
        total=len(books),
        pending=len([b for b in books if b.status in ["new", "ok"]]),
        processing=0,  # TODO: Implement active job tracking in Phase 2.1
        failed=len([b for b in books if b.status == "failed"]),
        retrying=len([b for b in books if b.status == "needs_retry"])
    )

    return QueueResponse(
        timestamp=time.time(),
        summary=summary,
        books=books
    )


@router.get("/api/v1/queue/{book_key:path}", response_model=QueueBookDetailResponse)
def get_queue_book(book_key: str):
    """
    Get detailed information for a single book.

    Returns extended metadata including retry history
    and estimated conversion time.
    """
    from src.lib.inbox_state import InboxState
    from src.lib.metrics import metrics

    inbox = InboxState()
    inbox.scan()  # Ensure fresh data

    item = inbox.get(book_key)

    if not item:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "book_not_found",
                "message": f"Book '{book_key}' not found in queue.",
                "suggestion": "Refresh queue via GET /api/v1/queue"
            }
        )

    # Build base book data
    book_data = build_queue_book(item, include_retry_details=True)

    # Add detail-specific fields
    book_data.update({
        "hash_age_seconds": int(item.hash_age),
        "first_failed_time": item.first_failed_time if item.status in ["failed", "needs_retry"] else None,
        "last_retry_time": item.last_retry_time if item.status in ["failed", "needs_retry"] else None,
        "retry_history": [],  # TODO: Implement retry history tracking
        "estimated_duration_seconds": None  # TODO: Estimate based on file size and avg duration
    })

    # Estimate duration based on file size and average if we have metrics
    if metrics.lifetime_attempted > 0 and metrics.lifetime_bytes_processed > 0:
        avg_bytes_per_second = metrics.lifetime_bytes_processed / metrics.lifetime_duration_seconds
        if avg_bytes_per_second > 0:
            book_data["estimated_duration_seconds"] = int(item.size / avg_bytes_per_second)

    return QueueBookDetailResponse(
        timestamp=time.time(),
        book=QueueBookDetail(**book_data)
    )
