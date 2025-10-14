"""Metrics endpoint for conversion history"""

import time
from fastapi import APIRouter, Query
from src.api.schemas.v1 import (
    RecentMetricsResponse,
    RecentConversion,
    RecentFailure
)

router = APIRouter()


@router.get("/api/v1/metrics/recent", response_model=RecentMetricsResponse)
def get_recent_metrics(
    limit: int = Query(default=10, ge=1, le=100, description="Number of recent conversions to return"),
    include_failures: bool = Query(default=True, description="Include failed conversions in results")
):
    """
    Get recent conversion history.

    Returns the most recent conversions with timing and status,
    plus a summary of recent failures.
    """
    from src.lib.metrics import metrics

    recent = metrics.get_recent_conversions(limit)
    conversions = [
        RecentConversion(
            book_name=r.book_name,
            status=r.status,
            duration_seconds=r.duration_seconds,
            timestamp=r.timestamp,
            timestamp_str=r.timestamp_str,
            file_size_bytes=r.file_size_bytes,
            error_message=r.error_message
        )
        for r in reversed(recent)  # Most recent first
    ]

    failures_list = []
    if include_failures:
        failures_list = [
            RecentFailure(
                book_name=f.book_name,
                error_message=f.error_message,
                timestamp=f.timestamp,
                timestamp_str=f.timestamp_str,
                retry_count=0  # TODO: Link to InboxItem retry_count if available
            )
            for f in reversed(metrics.get_recent_failures(5))
        ]

    return RecentMetricsResponse(
        timestamp=time.time(),
        conversions=conversions,
        failures={
            "total": len(failures_list),
            "recent": failures_list
        }
    )
