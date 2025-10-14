"""Pydantic schemas for API v1 responses

All schemas follow the data contract defined in docs/api/dashboard.md
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# Status endpoint schemas
class LifetimeMetrics(BaseModel):
    total: int = Field(..., description="Total conversions attempted")
    successful: int = Field(..., description="Successful conversions")
    failed: int = Field(..., description="Failed conversions")
    success_rate: float = Field(..., description="Success rate percentage")
    avg_duration_seconds: int = Field(..., description="Average conversion duration")
    total_bytes_processed: int = Field(..., description="Total bytes processed")
    first_run_timestamp: float = Field(..., description="Timestamp of first conversion")


class SessionMetrics(BaseModel):
    started_at: float = Field(..., description="Session start timestamp")
    total: int = Field(..., description="Conversions this session")
    successful: int = Field(..., description="Successful conversions this session")
    failed: int = Field(..., description="Failed conversions this session")
    success_rate: float = Field(..., description="Session success rate")
    total_bytes_processed: int = Field(..., description="Bytes processed this session")
    uptime_seconds: int = Field(..., description="Session uptime in seconds")


class TimingMetrics(BaseModel):
    fastest_seconds: int = Field(..., description="Fastest conversion time")
    slowest_seconds: int = Field(..., description="Slowest conversion time")
    average_seconds: int = Field(..., description="Average conversion time")


class Metrics(BaseModel):
    lifetime: LifetimeMetrics
    session: SessionMetrics
    timing: TimingMetrics


class StatusResponse(BaseModel):
    version: str = Field(default="1.0.0", description="API version")
    timestamp: float = Field(..., description="Response timestamp")
    uptime_seconds: int = Field(..., description="System uptime")
    status: str = Field(..., description="System status: idle, processing, or waiting")
    config: Dict[str, Any] = Field(..., description="Configuration snapshot")
    metrics: Metrics


# Queue endpoint schemas
class SeriesInfo(BaseModel):
    parent_key: str = Field(..., description="Parent series folder key")
    book_index: int = Field(..., description="Position in series (1-indexed)")
    total_books: int = Field(..., description="Total books in series")
    is_complete: bool = Field(..., description="Whether all series books are present")


class QueueBook(BaseModel):
    key: str = Field(..., description="Book identifier (relative path)")
    path: str = Field(..., description="Full path to book")
    status: str = Field(..., description="Book status: new, ok, needs_retry, failed, gone, archived")
    size_bytes: int = Field(..., description="Total size in bytes")
    last_updated: float = Field(..., description="Last modified timestamp")
    hash: str = Field(..., description="Content hash for change detection")
    is_filtered: bool = Field(..., description="Whether book matches filter")
    failed_reason: Optional[str] = Field(None, description="Error message if failed")
    retry_count: Optional[int] = Field(None, description="Number of retry attempts")
    max_retries: Optional[int] = Field(None, description="Maximum retries allowed")
    is_transient: Optional[bool] = Field(None, description="Whether error is transient")
    will_retry: Optional[bool] = Field(None, description="Whether book will be retried")
    next_retry_at: Optional[float] = Field(None, description="Next retry timestamp")
    retry_countdown_seconds: Optional[int] = Field(None, description="Seconds until retry")
    series_info: Optional[SeriesInfo] = Field(None, description="Series metadata if applicable")
    is_archived: Optional[bool] = Field(False, description="Whether book is in failed folder")
    timestamp_str: Optional[str] = Field(None, description="Human-readable timestamp for archived books")
    can_requeue: Optional[bool] = Field(False, description="Whether book can be re-queued")


class QueueSummary(BaseModel):
    total: int = Field(..., description="Total books in queue")
    pending: int = Field(..., description="Books pending processing")
    processing: int = Field(..., description="Books currently processing")
    failed: int = Field(..., description="Permanently failed books")
    retrying: int = Field(..., description="Books waiting to retry")


class QueueResponse(BaseModel):
    version: str = Field(default="1.0.0", description="API version")
    timestamp: float = Field(..., description="Response timestamp")
    summary: QueueSummary
    books: List[QueueBook]


# Queue detail endpoint schemas
class RetryHistoryItem(BaseModel):
    attempt: int = Field(..., description="Attempt number")
    timestamp: float = Field(..., description="Attempt timestamp")
    error: str = Field(..., description="Error message")
    duration_seconds: int = Field(..., description="Duration of attempt")


class QueueBookDetail(QueueBook):
    hash_age_seconds: int = Field(..., description="Seconds since hash last changed")
    first_failed_time: Optional[float] = Field(None, description="First failure timestamp")
    last_retry_time: Optional[float] = Field(None, description="Last retry timestamp")
    retry_history: List[RetryHistoryItem] = Field(default_factory=list, description="Retry history")
    estimated_duration_seconds: Optional[int] = Field(None, description="Estimated conversion time")


class QueueBookDetailResponse(BaseModel):
    version: str = Field(default="1.0.0", description="API version")
    timestamp: float = Field(..., description="Response timestamp")
    book: QueueBookDetail


# Recent metrics endpoint schemas
class RecentConversion(BaseModel):
    book_name: str = Field(..., description="Book name")
    status: str = Field(..., description="Conversion status: success or failed")
    duration_seconds: int = Field(..., description="Conversion duration")
    timestamp: float = Field(..., description="Conversion timestamp")
    timestamp_str: str = Field(..., description="Human-readable timestamp")
    file_size_bytes: int = Field(..., description="Output file size")
    error_message: str = Field(default="", description="Error message if failed")


class RecentFailure(BaseModel):
    book_name: str = Field(..., description="Book name")
    error_message: str = Field(..., description="Error message")
    timestamp: float = Field(..., description="Failure timestamp")
    timestamp_str: str = Field(..., description="Human-readable timestamp")
    retry_count: int = Field(..., description="Number of retries")


class RecentMetricsResponse(BaseModel):
    version: str = Field(default="1.0.0", description="API version")
    timestamp: float = Field(..., description="Response timestamp")
    conversions: List[RecentConversion]
    failures: Dict[str, Any] = Field(..., description="Failure summary with total and recent list")


# Health endpoint schemas
class HealthResponse(BaseModel):
    status: str = Field(..., description="Health status: healthy, degraded, or unhealthy")
    timestamp: float = Field(..., description="Response timestamp")
    checks: Dict[str, Any] = Field(..., description="Individual health checks")
    message: str = Field(default="", description="Additional status message")
