from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import AsyncSessionLocal
from app.core.config import settings
from app.services.rate_limiter import RateLimiter
from app.services.metrics import MetricsService
from app.services.routing import RoutingEngine

# We will initialize this in main.py
redis_client = None

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def get_rate_limiter(db: AsyncSession = Depends(get_db)) -> RateLimiter:
    from app.main import redis_client as main_redis # Still might have circular issues
    return RateLimiter(redis_client=main_redis, db=db)

async def get_routing(db: AsyncSession = Depends(get_db)) -> RoutingEngine:
    return RoutingEngine(db)

async def get_metrics(db: AsyncSession = Depends(get_db)) -> MetricsService:
    return MetricsService(db=db)
