"""Status endpoint providing system health and metrics snapshot"""

import time
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from src.api.schemas.v1 import (
    StatusResponse,
    Metrics,
    LifetimeMetrics,
    SessionMetrics,
    TimingMetrics,
    ConversionHistoryItem
)

router = APIRouter()


@router.get("/api/v1/status")
def get_status():
    """
    Get system status and conversion metrics snapshot.

    Returns overall system status (idle/processing/waiting),
    configuration snapshot, and comprehensive metrics.
    """
    from src.lib.metrics import metrics
    from src.lib.config import cfg
    from src.lib.inbox_state import InboxState

    # Reload metrics from file to get latest data
    metrics.load()

    inbox = InboxState()
    inbox.scan()  # Ensure fresh data

    # Determine system status
    if inbox.num_matched_ok > 0:
        status = "processing"
    elif inbox.has_failed_books:
        status = "waiting"
    else:
        status = "idle"

    # Get recent conversions (last 20)
    recent_conversions = [
        ConversionHistoryItem(
            book_name=record.book_name,
            status=record.status,
            duration_seconds=record.duration_seconds,
            timestamp=record.timestamp,
            file_size_bytes=record.file_size_bytes,
            error_message=record.error_message
        )
        for record in metrics.get_recent_conversions(limit=20)
    ]

    data = StatusResponse(
        timestamp=time.time(),
        uptime_seconds=metrics.session.uptime_seconds,
        status=status,
        config={
            "max_retries": cfg.MAX_RETRIES,
            "retry_base_delay": cfg.RETRY_BASE_DELAY,
            "cpu_cores": cfg.CPU_CORES,
            "sleep_time": cfg.SLEEP_TIME
        },
        metrics=Metrics(
            lifetime=LifetimeMetrics(
                total=metrics.lifetime_attempted,
                successful=metrics.lifetime_successful,
                failed=metrics.lifetime_failed,
                success_rate=round(metrics.lifetime_success_rate, 1),
                avg_duration_seconds=int(metrics.lifetime_avg_duration),
                total_bytes_processed=metrics.lifetime_bytes_processed,
                first_run_timestamp=metrics.first_run_timestamp
            ),
            session=SessionMetrics(
                started_at=metrics.session.started_at,
                total=metrics.session.conversions_attempted,
                successful=metrics.session.conversions_successful,
                failed=metrics.session.conversions_failed,
                success_rate=round(metrics.session.success_rate, 1),
                total_bytes_processed=metrics.session.total_bytes_processed,
                uptime_seconds=metrics.session.uptime_seconds
            ),
            timing=TimingMetrics(
                fastest_seconds=metrics.fastest_conversion_seconds,
                slowest_seconds=metrics.slowest_conversion_seconds,
                average_seconds=int(metrics.lifetime_avg_duration)
            )
        ),
        recent_conversions=recent_conversions
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
