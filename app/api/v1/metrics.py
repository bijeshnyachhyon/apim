# Monitoring & Analytics Endpoints
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import structlog

from app.db.session import AsyncSessionLocal
from app.models.db.base import RequestLog, ApiEndpoint, Consumer, ApiKey

logger = structlog.get_logger()
router = APIRouter(tags=["Monitoring"])

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

@router.get("/metrics/summary", response_model=dict)
async def metrics_summary(db=Depends(get_db)):
    """KPI summary for last 24 hours."""
    from datetime import timedelta
    cutoff = datetime.now() - timedelta(hours=24)

    # Total requests
    stmt = select(func.count()).where(RequestLog.created_at >= cutoff)
    total_requests = await db.scalar(stmt) or 0

    # Success rate
    success_stmt = select(func.count()).where(
        RequestLog.created_at >= cutoff,
        RequestLog.response_status_code < 400
    )
    success_count = await db.scalar(success_stmt) or 0
    success_rate = (success_count / total_requests * 100) if total_requests > 0 else 0

    # Avg latency
    latency_stmt = select(func.avg(RequestLog.response_time_ms)).where(
        RequestLog.created_at >= cutoff
    )
    avg_latency = float(await db.scalar(latency_stmt) or 0)

    # P95, P99 latency
    p95_stmt = select(RequestLog.response_time_ms).where(
        RequestLog.created_at >= cutoff
    ).order_by(RequestLog.response_time_ms).offset(int(total_requests * 0.95)).limit(1)
    p95_result = await db.scalar(p95_stmt)
    p95_latency = float(p95_result or 0)

    p99_stmt = select(RequestLog.response_time_ms).where(
        RequestLog.created_at >= cutoff
    ).order_by(RequestLog.response_time_ms).offset(int(total_requests * 0.99)).limit(1)
    p99_result = await db.scalar(p99_stmt)
    p99_latency = float(p99_result or 0)

    # Active API keys
    keys_stmt = select(func.count()).where(ApiKey.status == "active")
    active_keys = await db.scalar(keys_stmt) or 0

    # Error count
    error_stmt = select(func.count()).where(
        RequestLog.created_at >= cutoff,
        RequestLog.response_status_code >= 400
    )
    error_count = await db.scalar(error_stmt) or 0

    return {
        "success": True,
        "data": {
            "total_requests_24h": total_requests,
            "success_rate_pct": round(success_rate, 2),
            "avg_latency_ms": round(avg_latency, 2),
            "p95_latency_ms": round(p95_latency, 2),
            "p99_latency_ms": round(p99_latency, 2),
            "active_api_keys": active_keys,
            "error_count_24h": error_count,
        },
        "meta": {"request_id": "req_metrics_summary"},
        "error": None
    }

@router.get("/metrics/requests", response_model=dict)
async def metrics_requests(
    period: str = "24h",
    interval: str = "hour",
    db=Depends(get_db)
):
    """Request time series data."""
    from datetime import timedelta

    if period == "1h":
        cutoff = datetime.now() - timedelta(hours=1)
    elif period == "7d":
        cutoff = datetime.now() - timedelta(days=7)
    elif period == "30d":
        cutoff = datetime.now() - timedelta(days=30)
    else:  # 24h
        cutoff = datetime.now() - timedelta(hours=24)

    # Simplified: return hourly aggregates
    stmt = (
        select(
            func.date_format(RequestLog.created_at, "%Y-%m-%d %H:00:00").label("hour"),
            func.count().label("total"),
            func.sum(func.if_(RequestLog.response_status_code < 300, 1, 0)).label("2xx"),
            func.sum(func.if_(RequestLog.response_status_code.between(400, 499), 1, 0)).label("4xx"),
            func.sum(func.if_(RequestLog.response_status_code >= 500, 1, 0)).label("5xx"),
        )
        .where(RequestLog.created_at >= cutoff)
        .group_by("hour")
        .order_by("hour")
    )

    result = await db.execute(stmt)
    rows = result.all()

    series = []
    for row in rows:
        series.append({
            "timestamp": str(row[0]),
            "total": row[1],
            "2xx": row[2] or 0,
            "4xx": row[3] or 0,
            "5xx": row[4] or 0,
        })

    return {
        "success": True,
        "data": {"series": series},
        "meta": {"request_id": "req_metrics_requests"},
        "error": None
    }

@router.get("/metrics/errors", response_model=dict)
async def metrics_errors(db=Depends(get_db)):
    """Error rate and detail."""
    from datetime import timedelta
    cutoff = datetime.now() - timedelta(hours=24)

    # Total and error count
    total_stmt = select(func.count()).where(RequestLog.created_at >= cutoff)
    total = await db.scalar(total_stmt) or 0

    error_count_stmt = select(func.count()).where(
        RequestLog.created_at >= cutoff,
        RequestLog.response_status_code >= 400
    )
    error_count = await db.scalar(error_count_stmt) or 0
    error_rate = (error_count / total * 100) if total > 0 else 0

    # Errors by code
    code_stmt = (
        select(
            RequestLog.error_code,
            func.count().label("cnt")
        )
        .where(
            RequestLog.created_at >= cutoff,
            RequestLog.error_code.isnot(None)
        )
        .group_by(RequestLog.error_code)
        .order_by(func.count().desc())
    )
    code_result = await db.execute(code_stmt)
    errors_by_code = [
        {"code": row[0], "count": row[1], "pct": round(row[1] / error_count * 100, 2) if error_count > 0 else 0}
        for row in code_result.all() if row[0]
    ]

    return {
        "success": True,
        "data": {
            "error_rate_pct": round(error_rate, 2),
            "errors_by_code": errors_by_code,
            "recent_errors": [],  # Would fetch recent error logs
        },
        "meta": {"request_id": "req_metrics_errors"},
        "error": None
    }

@router.get("/metrics/latency", response_model=dict)
async def metrics_latency(db=Depends(get_db)):
    """Latency percentiles per endpoint."""
    from datetime import timedelta
    cutoff = datetime.now() - timedelta(hours=24)

    # Overall percentiles
    stmt = select(RequestLog.response_time_ms).where(
        RequestLog.created_at >= cutoff
    )
    result = await db.execute(stmt)
    latencies = [row[0] for row in result.all() if row[0] is not None]
    latencies.sort()

    overall = {}
    if latencies:
        overall = {
            "p50": latencies[int(len(latencies) * 0.5)],
            "p95": latencies[int(len(latencies) * 0.95)],
            "p99": latencies[int(len(latencies) * 0.99)],
        }

    # Per endpoint
    endpoint_stmt = (
        select(
            RequestLog.endpoint_id,
            ApiEndpoint.slug,
            func.avg(RequestLog.response_time_ms).label("avg"),
        )
        .outerjoin(ApiEndpoint, RequestLog.endpoint_id == ApiEndpoint.id)
        .where(RequestLog.created_at >= cutoff)
        .group_by(RequestLog.endpoint_id, ApiEndpoint.slug)
    )
    endpoint_result = await db.execute(endpoint_stmt)

    by_endpoint = [
        {
            "endpoint": row[1] or f"id_{row[0]}",
            "avg_latency_ms": float(row[2] or 0),
        }
        for row in endpoint_result.all()
    ]

    return {
        "success": True,
        "data": {
            "overall": overall,
            "by_endpoint": by_endpoint,
        },
        "meta": {"request_id": "req_metrics_latency"},
        "error": None
    }

@router.get("/metrics/consumers", response_model=dict)
async def metrics_consumers(db=Depends(get_db)):
    """Usage metrics per consumer."""
    from datetime import timedelta
    cutoff = datetime.now() - timedelta(days=30)

    stmt = (
        select(
            Consumer.name,
            func.count(RequestLog.id).label("requests"),
            func.avg(RequestLog.response_time_ms).label("avg_latency"),
            func.sum(func.if_(RequestLog.response_status_code >= 400, 1, 0)).label("errors"),
        )
        .outerjoin(ApiKey, Consumer.id == ApiKey.consumer_id)
        .outerjoin(RequestLog, ApiKey.id == RequestLog.api_key_id)
        .where(RequestLog.created_at >= cutoff)
        .group_by(Consumer.id, Consumer.name)
    )

    result = await db.execute(stmt)
    consumers = [
        {
            "consumer": row[0],
            "requests_30d": row[1] or 0,
            "avg_latency_ms": float(row[2] or 0),
            "error_count_30d": row[3] or 0,
        }
        for row in result.all()
    ]

    return {
        "success": True,
        "data": {"consumers": consumers},
        "meta": {"request_id": "req_metrics_consumers"},
        "error": None
    }

@router.get("/audit-logs", response_model=dict)
async def audit_logs(
    page: int = 1,
    limit: int = 50,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db=Depends(get_db)
):
    """Paginated audit trail."""
    from app.services.audit import AuditService

    audit = AuditService(db)
    logs, total = await audit.get_logs(
        page=page,
        limit=limit,
        start_date=datetime.fromisoformat(start_date) if start_date else None,
        end_date=datetime.fromisoformat(end_date) if end_date else None,
    )

    return {
        "success": True,
        "data": {
            "logs": logs,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit,
            }
        },
        "meta": {"request_id": "req_audit_logs"},
        "error": None
    }
