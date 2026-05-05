# Query Endpoints - Third-party facing data query endpoints
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any, List
import time
import uuid
from datetime import datetime
import hashlib
import json

from app.core.security import verify_api_key, hash_api_key
from app.services.routing import RoutingEngine
from app.services.rate_limiter import RateLimiter
from app.services.metrics import MetricsService
from app.adapters.factory import AdapterFactory
from app.adapters.base import QueryResult
from app.db.session import AsyncSessionLocal
from app.models.schemas import QueryResponse, ApiResponse

router = APIRouter()

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

@router.post("/query/{endpoint_slug}", response_model=dict)
async def execute_query_post(
    endpoint_slug: str,
    request: Request,
    db=Depends(get_db)
):
    """Execute a registered endpoint query (POST)."""
    return await _execute_query(endpoint_slug, request, db)

@router.get("/query/{endpoint_slug}", response_model=dict)
async def execute_query_get(
    endpoint_slug: str,
    request: Request,
    db=Depends(get_db)
):
    """Execute a read query via GET parameters."""
    return await _execute_query(endpoint_slug, request, db)

async def _execute_query(endpoint_slug: str, request: Request, db):
    """Common query execution logic."""
    start_time = time.time()
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    client_ip = request.client.host if request.client else "unknown"
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()

    # Get request body or query params
    request_data = {}
    if request.method == "POST":
        try:
            request_data = await request.json()
        except:
            request_data = {}
    else:
        request_data = dict(request.query_params)

    # Hash request body for logging
    body_hash = hashlib.sha256(
        json.dumps(request_data, sort_keys=True).encode()
    ).hexdigest() if request_data else None

    # Authenticate
    api_key_header = request.headers.get("X-API-Key")
    auth_header = request.headers.get("Authorization")

    api_key_id = None
    consumer_id = None
    rate_limit_per_hour = 1000
    rate_limit_per_minute = 100

    if api_key_header:
        from sqlalchemy import select
        from app.models.db.base import ApiKey, Consumer

        key_hash = hash_api_key(api_key_header)
        stmt = (
            select(ApiKey, Consumer)
            .join(Consumer, ApiKey.consumer_id == Consumer.id)
            .where(ApiKey.key_hash == key_hash, ApiKey.status == "active")
        )
        result = await db.execute(stmt)
        row = result.first()

        if not row:
            return _error_response("APIM_AUTH_001", "Invalid API key", 401, request_id)

        api_key_obj, consumer = row
        api_key_id = api_key_obj.id
        consumer_id = consumer.id

        # Check expiry
        if api_key_obj.expires_at and api_key_obj.expires_at < datetime.now():
            return _error_response("APIM_AUTH_006", "API key expired", 401, request_id)

        rate_limit_per_hour = api_key_obj.rate_limit_per_hour
        rate_limit_per_minute = api_key_obj.rate_limit_per_minute

    elif auth_header and auth_header.startswith("Bearer "):
        from app.core.security import decode_token
        token = auth_header.split(" ", 1)[1]
        payload = decode_token(token)
        if not payload or payload.get("type") != "access":
            return _error_response("APIM_AUTH_002", "Invalid JWT token", 401, request_id)
    else:
        return _error_response("APIM_AUTH_009", "Missing authentication", 401, request_id)

    # Rate limiting
    rate_limiter = RateLimiter(redis_client=None, db=db)
    allowed, rate_info = await rate_limiter.check_rate_limit(
        api_key_id or 0, rate_limit_per_hour, rate_limit_per_minute
    )

    if not allowed:
        return _error_response(
            "APIM_RATELIMIT_001",
            f"Rate limit exceeded. Try again in {rate_info['reset_minute'] - int(time.time())} seconds.",
            429,
            request_id,
            extra_headers={
                "X-RateLimit-Limit": str(rate_info["limit_per_minute"]),
                "X-RateLimit-Remaining": str(rate_info["remaining"]),
                "X-RateLimit-Reset": str(rate_info["reset_minute"]),
            }
        )

    # Resolve endpoint
    routing = RoutingEngine(db)
    resolved = await routing.resolve_endpoint(endpoint_slug)

    if not resolved:
        return _error_response("APIM_VAL_005", "Invalid endpoint slug", 404, request_id)

    # Check auth if required
    if resolved["auth_required"] and not api_key_header and not auth_header:
        return _error_response("APIM_AUTH_009", "Authentication required", 401, request_id)

    # Check scopes
    if resolved.get("allowed_scopes"):
        # Would check against consumer scopes here
        pass

    try:
        # Execute query based on target type
        if resolved.get("data_source"):
            ds = resolved["data_source"]
            from app.services.encryption import decrypt_password
            password = decrypt_password(ds["password_encrypted"])

            adapter = AdapterFactory.create_adapter(
                ds["name"], ds["db_type"], ds["host"], ds["port"],
                ds["database_name"], ds["username"], password,
                ds["pool_min"], ds["pool_max"], ds.get("connection_options")
            )

            await adapter.connect()
            query_template = resolved["query_template"]
            if not query_template:
                return _error_response("APIM_DB_003", "Query template not found", 400, request_id)

            result: QueryResult = await adapter.execute_query(query_template, request_data)
            await adapter.disconnect()

            latency_ms = (time.time() - start_time) * 1000

            # Log request
            metrics = MetricsService(db=db)
            await metrics.log_request_to_db(
                request_id, api_key_id, consumer_id, resolved["endpoint_id"],
                request.method, str(request.url), dict(request.query_params), body_hash,
                ds["db_type"], ds["id"], 200, latency_ms, None, client_ip,
                request.headers.get("User-Agent")
            )

            return {
                "success": True,
                "data": {
                    "records": result.records,
                    "count": result.count,
                    "target": ds["db_type"],
                    "execution_time_ms": result.execution_time_ms,
                },
                "meta": {
                    "request_id": request_id,
                    "timestamp": datetime.now().isoformat(),
                    "latency_ms": round(latency_ms, 2),
                },
                "error": None,
            }

        return _error_response("APIM_DB_013", "No data source configured", 400, request_id)

    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        error_msg = str(e)

        # Log error
        metrics = MetricsService(db=db)
        await metrics.log_request_to_db(
            request_id, api_key_id, consumer_id, resolved.get("endpoint_id"),
            request.method, str(request.url), dict(request.query_params), body_hash,
            resolved.get("data_source", {}).get("db_type"),
            resolved.get("data_source", {}).get("id"),
            500, latency_ms, "APIM_DB_001", error_msg, client_ip,
            request.headers.get("User-Agent")
        )
        await db.commit()

        return _error_response("APIM_DB_001", f"Database error: {error_msg}", 500, request_id)

def _error_response(code: str, message: str, status_code: int, request_id: str, extra_headers: dict = None):
    content = {
        "success": False,
        "data": None,
        "meta": {
            "request_id": request_id,
            "timestamp": datetime.now().isoformat(),
        },
        "error": {
            "code": code,
            "message": message,
        }
    }
    headers = extra_headers or {}
    headers["Content-Type"] = "application/json"
    from fastapi.responses import JSONResponse
    return JSONResponse(content=content, status_code=status_code, headers=headers)
