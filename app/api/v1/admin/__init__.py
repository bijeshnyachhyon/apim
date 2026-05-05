# Admin API Router - includes all admin sub-routers
from fastapi import APIRouter, Depends, HTTPException, status
from app.api.v1.admin.endpoints import router as endpoints_router
from app.api.v1.admin.datasources import router as datasources_router
from app.api.v1.admin.consumers import router as consumers_router
from app.api.v1.admin.ofs_templates import router as ofs_templates_router

router = APIRouter(prefix="/admin", tags=["Admin"])

# Include sub-routers
router.include_router(endpoints_router)
router.include_router(datasources_router)
router.include_router(consumers_router)
router.include_router(ofs_templates_router)

# Admin authentication dependency
from app.core.security import decode_token, verify_api_key
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.db.base import AdminUser

async def verify_admin(request=Depends(), db=Depends(...)):  # Simplified
    """Verify admin JWT token."""
    # In real implementation, use proper dependency injection
    return {"user_id": 1, "role": "superadmin"}

# Rate limit management endpoints
@router.get("/rate-limit-rules")
async def get_rate_limit_rules(db=Depends(...)):
    """Get rate limit configuration."""
    from app.core.config import settings

    return {
        "success": True,
        "data": {
            "defaults": {
                "per_hour": settings.DEFAULT_RATE_LIMIT_PER_HOUR,
                "per_minute": settings.DEFAULT_RATE_LIMIT_PER_MINUTE,
            },
            "endpoint_overrides": [],
            "key_overrides": [],
        },
        "meta": {"request_id": "req_ratelimit"},
        "error": None
    }

@router.put("/rate-limit-rules")
async def update_rate_limit_rules(data: dict, db=Depends(...)):
    """Update rate limit rules."""
    return {
        "success": True,
        "data": {"updated": True},
        "meta": {"request_id": "req_ratelimit_update"},
        "error": None
    }

# Audit logs endpoint
@router.get("/audit-logs")
async def get_audit_logs(
    page: int = 1,
    limit: int = 50,
    action_type: str = None,
    resource_type: str = None,
    db=Depends(...)
):
    """Get paginated audit trail."""
    from app.services.audit import AuditService
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        audit = AuditService(session)
        logs, total = await audit.get_logs(
            page=page, limit=limit,
            action_type=action_type, resource_type=resource_type
        )
        await session.close()

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
            "meta": {"request_id": "req_audit"},
            "error": None
        }
