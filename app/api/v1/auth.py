# Authentication Endpoints
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime
import structlog

from app.core.security import (
    create_access_token, create_refresh_token, decode_token,
    verify_password, hash_password, generate_api_key
)
from app.models.schemas import (
    TokenRequest, TokenResponse, RefreshTokenRequest,
    ApiKeyCreate, ApiKeyResponse, ApiKeyCreateResponse
)
from app.db.session import AsyncSessionLocal
from app.services.audit import AuditService

logger = structlog.get_logger()
router = APIRouter()

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

@router.post("/token", response_model=dict)
async def login(credentials: TokenRequest, db=Depends(get_db)):
    """Get JWT tokens from username/password."""
    from sqlalchemy import select
    from app.models.db.base import AdminUser

    stmt = select(AdminUser).where(AdminUser.username == credentials.username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if user.status != "active":
        raise HTTPException(status_code=423, detail="Account locked or inactive")

    # Update last login
    user.last_login_at = datetime.now()
    await db.commit()

    # Create tokens
    access_token = create_access_token({
        "sub": str(user.id),
        "username": user.username,
        "role": user.role,
        "scopes": ["admin"] if user.role in ["admin", "superadmin"] else []
    })
    refresh_token = create_refresh_token({"sub": str(user.id)})

    # Audit log
    audit = AuditService(db)
    await audit.log_action(
        admin_user_id=user.id,
        action_type="LOGIN",
        resource_type="admin_user",
        resource_id=str(user.uuid),
        old_value=None,
        new_value={"login_at": datetime.now().isoformat()},
        ip_address="0.0.0.0"  # Would get from request in real impl
    )
    await db.commit()

    return {
        "success": True,
        "data": {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": 15 * 60,
        },
        "meta": {"request_id": "req_" + str(hash(access_token))[:16]},
        "error": None
    }

@router.post("/refresh", response_model=dict)
async def refresh_token(request: RefreshTokenRequest, db=Depends(get_db)):
    """Refresh JWT access token."""
    payload = decode_token(request.refresh_token)

    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    from sqlalchemy import select
    from app.models.db.base import AdminUser

    user_id = int(payload.get("sub"))
    stmt = select(AdminUser).where(AdminUser.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or user.status != "active":
        raise HTTPException(status_code=401, detail="User not found or inactive")

    access_token = create_access_token({
        "sub": str(user.id),
        "username": user.username,
        "role": user.role,
        "scopes": ["admin"] if user.role in ["admin", "superadmin"] else []
    })

    return {
        "success": True,
        "data": {
            "access_token": access_token,
            "expires_in": 15 * 60,
        },
        "meta": {"request_id": "req_" + str(hash(access_token))[:16]},
        "error": None
    }

@router.post("/api-keys", response_model=dict)
async def create_api_key(
    key_data: ApiKeyCreate,
    admin=Depends(lambda: verify_admin),  # Would use proper dependency
    db=Depends(get_db)
):
    """Create new API key (admin only)."""
    from sqlalchemy import select
    from app.models.db.base import Consumer, ApiKey

    # Verify consumer exists
    stmt = select(Consumer).where(Consumer.id == key_data.consumer_id)
    result = await db.execute(stmt)
    consumer = result.scalar_one_or_none()

    if not consumer:
        raise HTTPException(status_code=404, detail="Consumer not found")

    # Generate API key
    full_key, prefix, key_hash = generate_api_key()

    new_key = ApiKey(
        uuid=str(__import__('uuid').uuid4()),
        consumer_id=key_data.consumer_id,
        key_prefix=prefix,
        key_hash=key_hash,
        name=key_data.name,
        scopes=key_data.allowed_endpoints,
        rate_limit_per_hour=key_data.rate_limit_per_hour,
        rate_limit_per_minute=key_data.rate_limit_per_minute,
        expires_at=key_data.expires_at,
    )
    db.add(new_key)
    await db.commit()

    return {
        "success": True,
        "data": {
            "id": new_key.id,
            "key": full_key,  # Only returned once!
            "key_prefix": prefix,
            "consumer_id": key_data.consumer_id,
            "name": key_data.name,
            "rate_limit_per_hour": key_data.rate_limit_per_hour,
            "rate_limit_per_minute": key_data.rate_limit_per_minute,
            "expires_at": key_data.expires_at,
            "created_at": new_key.created_at,
        },
        "meta": {"request_id": str(__import__('uuid').uuid4())},
        "error": None
    }

@router.delete("/api-keys/{key_id}")
async def revoke_api_key(key_id: int, admin=Depends(lambda: verify_admin), db=Depends(get_db)):
    """Revoke an API key."""
    from sqlalchemy import select
    from app.models.db.base import ApiKey

    stmt = select(ApiKey).where(ApiKey.id == key_id)
    result = await db.execute(stmt)
    key = result.scalar_one_or_none()

    if not key:
        raise HTTPException(status_code=404, detail="API key not found")

    key.status = "revoked"
    key.revoked_at = datetime.now()
    await db.commit()

    return {
        "success": True,
        "data": {"revoked": True, "revoked_at": key.revoked_at},
        "meta": {"request_id": str(__import__('uuid').uuid4())},
        "error": None
    }

@router.get("/api-keys", response_model=dict)
async def list_api_keys(
    page: int = 1,
    limit: int = 25,
    consumer_id: Optional[int] = None,
    status: Optional[str] = None,
    admin=Depends(lambda: verify_admin),
    db=Depends(get_db)
):
    """List all API keys."""
    from sqlalchemy import select, func
    from app.models.db.base import ApiKey

    stmt = select(ApiKey)
    if consumer_id:
        stmt = stmt.where(ApiKey.consumer_id == consumer_id)
    if status:
        stmt = stmt.where(ApiKey.status == status)

    # Count total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await db.scalar(count_stmt)

    # Paginate
    offset = (page - 1) * limit
    stmt = stmt.order_by(ApiKey.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    keys = result.scalars().all()

    return {
        "success": True,
        "data": {
            "keys": [{
                "id": k.id,
                "uuid": k.uuid,
                "key_prefix": k.key_prefix,
                "consumer_id": k.consumer_id,
                "name": k.name,
                "status": k.status,
                "expires_at": k.expires_at,
                "last_used_at": k.last_used_at,
            } for k in keys],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit,
            }
        },
        "meta": {"request_id": str(__import__('uuid').uuid4())},
        "error": None
    }
