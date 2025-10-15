"""Queue endpoints for viewing and managing book processing queue"""

import time
from typing import Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
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


class RequeueRequest(BaseModel):
    """Request body for re-queueing a failed book"""
    reset_retry_count: bool = True


class RequeueResponse(BaseModel):
    """Response for re-queue operation"""
    success: bool
    message: str
    book_key: str
    new_status: str
    retry_count: int


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


@router.get("/api/v1/queue")
def get_queue():
    """
    Get all books in the processing queue, including archived failed books.

    Returns summary counts and detailed list of:
    - Books currently in inbox (any status)
    - Books moved to failed folder (archived)
    """
    from src.lib.inbox_state import InboxState
    from src.lib.failed_books import scan_failed_folder
    from src.lib.config import cfg

    inbox = InboxState()
    inbox.scan()  # Ensure fresh data

    books = []

    # Add books from inbox
    for item in inbox.matched_books.values():
        book_data = build_queue_book(item)
        books.append(QueueBook(**book_data))

    # Add archived books from failed folder
    try:
        failed_books = scan_failed_folder(cfg.failed_dir)
        for failed_book in failed_books:
            book_data = failed_book.to_dict()
            # Add fields required by QueueBook schema
            book_data.update({
                "hash": "",
                "is_filtered": False,
                "series_info": None,
                "last_updated": failed_book.failed_at,
                "max_retries": cfg.MAX_RETRIES,
                "is_transient": True,  # Assume transient if archived
                "will_retry": False,  # Archived books won't auto-retry
                "next_retry_at": None,
                "retry_countdown_seconds": 0
            })
            books.append(QueueBook(**book_data))
    except Exception as e:
        print(f"Warning: Could not scan failed folder: {e}")

    # Calculate summary (exclude archived books - they appear in Failed Books section)
    active_books = [b for b in books if b.status != "archived"]
    pending_statuses = {"new", "ok", "pending"}
    retry_statuses = {"needs_retry", "retrying"}
    processing_statuses = {"processing"}

    summary = QueueSummary(
        total=len(active_books),
        pending=len([b for b in active_books if b.status in pending_statuses]),
        processing=len([b for b in active_books if b.status in processing_statuses]),
        failed=len([b for b in active_books if b.status == "failed"]),
        retrying=len([b for b in active_books if b.status in retry_statuses])
    )

    data = QueueResponse(
        timestamp=time.time(),
        summary=summary,
        books=books
    )

    # Return with cache-busting headers
    return JSONResponse(
        content=data.model_dump(),
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
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


@router.post("/api/v1/queue/{book_key:path}/requeue", response_model=RequeueResponse)
def requeue_failed_book(book_key: str, request: RequeueRequest):
    """
    Re-queue a failed book for retry.

    This endpoint allows operators to manually reset a failed book's status
    to "ok" so it will be picked up in the next processing loop.

    Optionally resets the retry counter to 0 (default behavior).

    **Use cases:**
    - Manually retry after fixing underlying issue (disk space, permissions, etc.)
    - Force retry of a permanently failed book after investigation
    - Reset retry count to give book more attempts

    **Requirements:**
    - Book must have status "failed" or "needs_retry"
    - Book must still exist in inbox folder

    **Effects:**
    - Sets book status to "ok" (ready for processing)
    - Optionally resets retry_count to 0
    - Clears failed_reason
    - Updates last_updated timestamp
    """
    from src.lib.inbox_state import InboxState

    inbox = InboxState()
    inbox.scan()  # Ensure fresh data

    item = inbox.get(book_key)

    if not item:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "book_not_found",
                "message": f"Book '{book_key}' not found in queue.",
                "suggestion": "Book may have been moved or deleted. Refresh queue via GET /api/v1/queue"
            }
        )

    # Verify book is actually failed
    if item.status not in ["failed", "needs_retry"]:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "book_not_failed",
                "message": f"Book '{book_key}' has status '{item.status}' and cannot be re-queued.",
                "current_status": item.status,
                "suggestion": "Only books with status 'failed' or 'needs_retry' can be re-queued."
            }
        )

    # Reset status to "ok" (ready for processing)
    item.status = "ok"
    item.failed_reason = ""

    # Reset retry count if requested
    if request.reset_retry_count:
        item.retry_count = 0
        item.first_failed_time = 0

    # Update last_updated to current time
    item._last_updated = time.time()

    # Save changes to inbox state
    inbox.set(item)

    return RequeueResponse(
        success=True,
        message=f"Book '{book_key}' has been re-queued for processing.",
        book_key=book_key,
        new_status="ok",
        retry_count=item.retry_count
    )
