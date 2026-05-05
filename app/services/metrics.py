# Metrics Service - Prometheus metrics and request tracking
from typing import Optional, Dict, Any
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
import time
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert
from app.models.db.base import RequestLog

# Prometheus metrics
REQUEST_COUNT = Counter(
    'apim_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status', 'target_db']
)

REQUEST_LATENCY = Histogram(
    'apim_request_latency_seconds',
    'Request latency in seconds',
    ['endpoint', 'target_db'],
    buckets=[0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0]
)

DB_POOL_GAUGE = Gauge(
    'apim_db_pool_active_connections',
    'Active DB connections',
    ['db_name', 'db_type']
)

T24_HEALTH_GAUGE = Gauge(
    'apim_t24_health_status',
    'T24 TCServer health (1=ok, 0=error)',
    ['host', 'port']
)

ERROR_COUNTER = Counter(
    'apim_errors_total',
    'Total errors by code',
    ['error_code']
)

class MetricsService:
    """Collects and exposes metrics."""

    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db

    def record_request(
        self,
        method: str,
        endpoint: str,
        status_code: int,
        latency_seconds: float,
        target_db: str = "unknown",
        error_code: Optional[str] = None,
    ) -> None:
        """Record metrics for a request."""
        status = f"{status_code // 100}xx"
        REQUEST_COUNT.labels(
            method=method,
            endpoint=endpoint,
            status=status,
            target_db=target_db
        ).inc()

        REQUEST_LATENCY.labels(
            endpoint=endpoint,
            target_db=target_db
        ).observe(latency_seconds)

        if error_code:
            ERROR_COUNTER.labels(error_code=error_code).inc()

    def update_db_pool_metrics(self, db_name: str, db_type: str, active: int) -> None:
        DB_POOL_GAUGE.labels(db_name=db_name, db_type=db_type).set(active)

    def update_t24_health(self, host: str, port: int, is_healthy: bool) -> None:
        T24_HEALTH_GAUGE.labels(host=host, port=str(port)).set(1 if is_healthy else 0)

    async def log_request_to_db(
        self,
        request_id: str,
        api_key_id: Optional[int],
        consumer_id: Optional[int],
        endpoint_id: Optional[int],
        method: str,
        path: str,
        query_params: Optional[Dict],
        request_body_hash: Optional[str],
        target_db_type: Optional[str],
        target_data_source_id: Optional[int],
        status_code: int,
        latency_ms: float,
        error_code: Optional[str],
        error_message: Optional[str],
        client_ip: str,
        user_agent: Optional[str],
    ) -> None:
        """Log request to MySQL for audit and analytics."""
        if self.db is None:
            return

        log_entry = RequestLog(
            request_id=request_id,
            api_key_id=api_key_id,
            consumer_id=consumer_id,
            endpoint_id=endpoint_id,
            http_method=method,
            path=path,
            query_params=query_params,
            request_body_hash=request_body_hash,
            target_db_type=target_db_type,
            target_data_source_id=target_data_source_id,
            response_status_code=status_code,
            response_time_ms=int(latency_ms),
            error_code=error_code,
            error_message=error_message,
            client_ip=client_ip,
            user_agent=user_agent,
        )
        self.db.add(log_entry)
        await self.db.flush()

    def get_prometheus_metrics(self) -> Response:
        """Return Prometheus metrics in text format."""
        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST
        )
