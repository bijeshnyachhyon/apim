# FastAPI Main Application
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, Depends, status
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Optional, Dict, Any
import time
import uuid
from datetime import datetime
import structlog

from app.core.config import settings
from app.core.security import decode_token, verify_api_key, hash_api_key
from app.db.session import AsyncSessionLocal, engine
from app.services.metrics import MetricsService, REQUEST_COUNT, REQUEST_LATENCY, ERROR_COUNTER, get_prometheus_metrics
from app.services.routing import RoutingEngine
from app.services.rate_limiter import RateLimiter
from app.services.encryption import decrypt_password
from app.adapters.factory import AdapterFactory
from app.adapters.t24.connector import T24Connector
from app.adapters.t24.ofs_builder import OFSBuilder
from app.adapters.t24.ofs_parser import OFSParser

# Configure structured logging
if settings.STRUCTLOG_ENABLED:
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer()
        ]
    )
logger = structlog.get_logger()

# Lifespan handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("api_startup", env=settings.APP_ENV)
    yield
    # Shutdown
    await engine.dispose()
    logger.info("api_shutdown")

# Create FastAPI app
app = FastAPI(
    title="Centralized API Management System",
    description="Production-grade API Gateway for multi-database and T24 TCServer integration",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.APP_ENV != "production" else None,
    redoc_url="/redoc" if settings.APP_ENV != "production" else None,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_CREDENTIALS,
    allow_methods=settings.CORS_METHODS,
    allow_headers=settings.CORS_HEADERS,
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/dashboard/static"), name="static")

# Templates
templates = Jinja2Templates(directory="app/dashboard/templates")

# Initialize services
metrics_service = MetricsService()

# Redis client (optional)
try:
    import redis.asyncio as aioredis
    redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=False)
except Exception:
    redis_client = None

# ===================
# Dependency Injection
# ===================

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def get_metrics() -> MetricsService:
    async with AsyncSessionLocal() as session:
        metrics = MetricsService(db=session)
        try:
            yield metrics
        finally:
            await session.close()

async def get_routing(db=Depends(get_db)) -> RoutingEngine:
    return RoutingEngine(db)

async def get_rate_limiter(db=Depends(get_db)) -> RateLimiter:
    return RateLimiter(redis_client=redis_client, db=db)

# ===================
# Authentication Dependencies
# ===================

async def verify_auth(request: Request, db=Depends(get_db)) -> Dict[str, Any]:
    """Verify API key or JWT token."""
    # Check API key
    api_key = request.headers.get("X-API-Key")
    if api_key:
        key_hash = hash_api_key(api_key)
        from sqlalchemy import select
        from app.models.db.base import ApiKey, Consumer

        stmt = (
            select(ApiKey, Consumer)
            .join(Consumer, ApiKey.consumer_id == Consumer.id)
            .where(ApiKey.key_hash == key_hash, ApiKey.status == "active")
        )
        result = await db.execute(stmt)
        row = result.first()

        if row:
            api_key_obj, consumer = row
            # Check expiry
            if api_key_obj.expires_at and api_key_obj.expires_at < datetime.now():
                raise HTTPException(status_code=401, detail="API key expired")
            return {
                "type": "api_key",
                "api_key_id": api_key_obj.id,
                "consumer_id": consumer.id,
                "scopes": api_key_obj.scopes or [],
                "rate_limit_per_hour": api_key_obj.rate_limit_per_hour,
                "rate_limit_per_minute": api_key_obj.rate_limit_per_minute,
            }

    # Check JWT
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
        payload = decode_token(token)
        if payload and payload.get("type") == "access":
            return {
                "type": "jwt",
                "user_id": payload.get("sub"),
                "role": payload.get("role"),
                "scopes": payload.get("scopes", []),
            }

    raise HTTPException(status_code=401, detail="Invalid or missing authentication")

async def verify_admin(claims=Depends(verify_auth)) -> Dict[str, Any]:
    """Verify admin JWT token."""
    if claims.get("type") != "jwt":
        raise HTTPException(status_code=403, detail="Admin JWT required")
    if claims.get("role") not in ["admin", "superadmin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    return claims

# ===================
# Middleware for request logging
# ===================

@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start_time = time.time()

    # Get client IP
    client_ip = request.client.host if request.client else "unknown"
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()

    response = await call_next(request)

    process_time = (time.time() - start_time) * 1000
    logger.info(
        "request_completed",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        latency_ms=round(process_time, 2),
        client_ip=client_ip,
    )

    # Add request ID to response headers
    response.headers["X-Request-ID"] = request_id
    return response

# ===================
# Health & Metrics
# ===================

@app.get("/health")
async def health_check(db=Depends(get_db)):
    """Health check endpoint."""
    checks = {}
    overall = "healthy"

    # Check MySQL
    try:
        await db.execute("SELECT 1")
        checks["management_db"] = "ok"
    except Exception as e:
        checks["management_db"] = f"error: {str(e)}"
        overall = "degraded"

    # Check Redis
    if redis_client:
        try:
            await redis_client.ping()
            checks["redis"] = "ok"
        except Exception as e:
            checks["redis"] = f"error: {str(e)}"
    else:
        checks["redis"] = "not_configured"

    return {"status": overall, "version": "1.0.0", "timestamp": datetime.now().isoformat(), "checks": checks}

@app.get("/metrics")
async def metrics_endpoint():
    """Prometheus metrics endpoint."""
    return get_prometheus_metrics()

# ===================
# Include API routers
# ===================

from app.api.v1 import router as v1_router

app.include_router(v1_router)

# ===================
# Dashboard Routes
# ===================

from app.dashboard.routes import router as dashboard_router
app.include_router(dashboard_router)

# ===================
# Error Handlers
# ===================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "data": None,
            "meta": {
                "request_id": request.headers.get("X-Request-ID", str(uuid.uuid4())),
                "timestamp": datetime.now().isoformat(),
            },
            "error": {
                "code": "APIM_AUTH_001" if exc.status_code == 401 else "APIM_VAL_001",
                "message": exc.detail,
            }
        }
    )

# ===================
# Root
# ===================

@app.get("/")
async def root():
    return {"service": "Centralized API Management System", "version": "1.0.0", "docs": "/docs"}
