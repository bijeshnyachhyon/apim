# Rate Limiting Service using Redis (with MySQL fallback)
import time
import json
from typing import Optional, Tuple
from redis import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, delete, and_
from app.core.config import settings
from app.models.db.base import RateLimitCounter, ApiKey

class RateLimiter:
    """Distributed rate limiting using Redis with MySQL fallback."""

    def __init__(self, redis_client: Optional[Redis] = None, db: Optional[AsyncSession] = None):
        self.redis = redis_client
        self.db = db

    async def check_rate_limit(
        self, key_id: int, per_hour: int, per_minute: int
    ) -> Tuple[bool, dict]:
        """
        Check if request is within rate limits.
        Returns: (allowed, info_dict)
        info_dict: { "limit": ..., "remaining": ..., "reset": ..., "window": ... }
        """
        now = time.time()
        minute_window = int(now // 60 * 60)
        hour_window = int(now // 3600 * 3600)

        # Check both windows
        minute_count = await self._get_count(key_id, "minute", minute_window)
        hour_count = await self._get_count(key_id, "hour", hour_window)

        # Calculate remaining
        minute_remaining = max(0, per_minute - minute_count)
        hour_remaining = max(0, per_hour - hour_count)

        # Use the more restrictive limit
        allowed = (minute_count < per_minute) and (hour_count < per_hour)
        remaining = min(minute_remaining, hour_remaining)

        info = {
            "limit_per_minute": per_minute,
            "limit_per_hour": per_hour,
            "minute_count": minute_count,
            "hour_count": hour_count,
            "remaining": remaining,
            "reset_minute": minute_window + 60,
            "reset_hour": hour_window + 3600,
        }

        if allowed:
            # Increment counters
            await self._increment(key_id, "minute", minute_window)
            await self._increment(key_id, "hour", hour_window)

        return allowed, info

    async def _get_count(self, key_id: int, window_type: str, window_start: int) -> int:
        if self.redis:
            redis_key = f"ratelimit:{key_id}:{window_type}:{window_start}"
            count = await self.redis.get(redis_key)
            return int(count) if count else 0
        elif self.db:
            stmt = select(RateLimitCounter).where(
                and_(
                    RateLimitCounter.api_key_id == key_id,
                    RateLimitCounter.window_type == window_type,
                    RateLimitCounter.window_start == window_start,
                )
            )
            result = await self.db.execute(stmt)
            record = result.scalar_one_or_none()
            return record.request_count if record else 0
        return 0

    async def _increment(self, key_id: int, window_type: str, window_start: int) -> None:
        if self.redis:
            redis_key = f"ratelimit:{key_id}:{window_type}:{window_start}"
            pipe = self.redis.pipeline()
            pipe.incr(redis_key)
            pipe.expire(redis_key, 3600 if window_type == "hour" else 120)
            await pipe.execute()
        elif self.db:
            stmt = select(RateLimitCounter).where(
                and_(
                    RateLimitCounter.api_key_id == key_id,
                    RateLimitCounter.window_type == window_type,
                    RateLimitCounter.window_start == window_start,
                )
            )
            result = await self.db.execute(stmt)
            record = result.scalar_one_or_none()
            if record:
                record.request_count += 1
            else:
                self.db.add(RateLimitCounter(
                    api_key_id=key_id,
                    window_start=window_start,
                    window_type=window_type,
                    request_count=1,
                ))

    async def check_global_rate_limit(self, window_start: int) -> Tuple[bool, dict]:
        """Check global rate limit (per-minute)."""
        limit = settings.GLOBAL_RATE_LIMIT_PER_MINUTE
        # Simplified: use a single global counter
        if self.redis:
            redis_key = f"ratelimit:global:minute:{window_start}"
            count = await self.redis.get(redis_key)
            count = int(count) if count else 0
            allowed = count < limit
            if allowed:
                await self.redis.incr(redis_key)
                await self.redis.expire(redis_key, 120)
            return allowed, {"limit": limit, "remaining": max(0, limit - count - (1 if allowed else 0)), "reset": window_start + 60}
        return True, {"limit": limit, "remaining": limit, "reset": window_start + 60}
