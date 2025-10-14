"""Health check endpoint for monitoring systems"""

import shutil
import time
from fastapi import APIRouter
from src.api.schemas.v1 import HealthResponse

router = APIRouter()


def check_m4b_tool() -> bool:
    """Check if m4b-tool is available"""
    try:
        return bool(shutil.which("m4b-tool"))
    except Exception:
        return False


def check_disk_space(path, min_gb: int = 1) -> bool:
    """Check if disk has at least min_gb free space"""
    try:
        stat = shutil.disk_usage(path)
        free_gb = stat.free / (1024 ** 3)
        return free_gb >= min_gb
    except Exception:
        return False


@router.get("/api/v1/health", response_model=HealthResponse)
def health_check():
    """
    Health check endpoint for monitoring systems.

    Returns system health status with individual component checks.
    """
    from src.lib.config import cfg
    from src.lib.inbox_state import InboxState

    checks = {
        "inbox_accessible": cfg.inbox_dir.exists() and cfg.inbox_dir.is_dir(),
        "converted_accessible": cfg.converted_dir.exists() and cfg.converted_dir.is_dir(),
        "m4b_tool_available": check_m4b_tool(),
        "disk_space_ok": check_disk_space(cfg.inbox_dir),
        "retry_queue_length": len(InboxState().failed_books)
    }

    # Determine overall status
    critical_checks = [
        checks["inbox_accessible"],
        checks["converted_accessible"],
        checks["m4b_tool_available"]
    ]

    if all(critical_checks):
        if checks["disk_space_ok"] and checks["retry_queue_length"] < 10:
            status = "healthy"
            message = ""
        else:
            status = "degraded"
            messages = []
            if not checks["disk_space_ok"]:
                messages.append("Low disk space")
            if checks["retry_queue_length"] >= 10:
                messages.append(f"{checks['retry_queue_length']} books in retry queue")
            message = "; ".join(messages)
    else:
        status = "unhealthy"
        failed = []
        if not checks["inbox_accessible"]:
            failed.append("inbox not accessible")
        if not checks["converted_accessible"]:
            failed.append("converted folder not accessible")
        if not checks["m4b_tool_available"]:
            failed.append("m4b-tool not available")
        message = "Critical checks failed: " + ", ".join(failed)

    return HealthResponse(
        status=status,
        timestamp=time.time(),
        checks=checks,
        message=message
    )
