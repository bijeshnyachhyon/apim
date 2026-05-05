# Admin Endpoints - Consumer Management
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List
import structlog

from app.models.schemas import ApiResponse
from app.db.session import AsyncSessionLocal
from app.services.audit import AuditService

logger = structlog.get_logger()
router = APIRouter(prefix="/consumers", tags=["Admin - Consumers"])

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

@router.get("", response_model=dict)
async def list_consumers(
    page: int = 1,
    limit: int = 25,
    status: Optional[str] = None,
    db=Depends(get_db)
):
    """List all consumers."""
    from app.models.db.base import Consumer

    stmt = select(Consumer)
    if status:
        stmt = stmt.where(Consumer.status == status)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await db.scalar(count_stmt)

    offset = (page - 1) * limit
    stmt = stmt.order_by(Consumer.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    consumers = result.scalars().all()

    return {
        "success": True,
        "data": {
            "consumers": [{
                "id": c.id,
                "uuid": c.uuid,
                "name": c.name,
                "email": c.email,
                "status": c.status,
            } for c in consumers],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit,
            }
        },
        "meta": {"request_id": "req_" + str(hash(str(page)))[:16]},
        "error": None
    }

@router.post("", response_model=dict)
async def create_consumer(
    data: dict,  # Would use proper schema
    admin_user_id: int = 1,
    db=Depends(get_db)
):
    """Create new consumer."""
    from app.models.db.base import Consumer

    new_consumer = Consumer(
        uuid=str(__import__('uuid').uuid4()),
        name=data.get("name", ""),
        description=data.get("description"),
        email=data.get("email", ""),
        status="active"
    )
    db.add(new_consumer)
    await db.flush()

    # Audit log
    audit = AuditService(db)
    await audit.log_action(
        admin_user_id=admin_user_id,
        action_type="CREATE",
        resource_type="consumer",
        resource_id=str(new_consumer.uuid),
        old_value=None,
        new_value={"name": new_consumer.name, "email": new_consumer.email},
        ip_address="0.0.0.0"
    )
    await db.commit()

    return {
        "success": True,
        "data": {
            "id": new_consumer.id,
            "uuid": new_consumer.uuid,
            "name": new_consumer.name,
            "email": new_consumer.email,
        },
        "meta": {"request_id": "req_" + str(hash(new_consumer.uuid))[:16]},
        "error": None
    }

@router.put("/{consumer_id}", response_model=dict)
async def update_consumer(
    consumer_id: int,
    data: dict,
    admin_user_id: int = 1,
    db=Depends(get_db)
):
    """Update consumer."""
    from app.models.db.base import Consumer

    stmt = select(Consumer).where(Consumer.id == consumer_id)
    consumer = await db.scalar(stmt)

    if not consumer:
        raise HTTPException(status_code=404, detail="Consumer not found")

    old_value = {"name": consumer.name, "status": consumer.status}
    consumer.name = data.get("name", consumer.name)
    consumer.description = data.get("description", consumer.description)
    consumer.status = data.get("status", consumer.status)

    # Audit log
    audit = AuditService(db)
    await audit.log_action(
        admin_user_id=admin_user_id,
        action_type="UPDATE",
        resource_type="consumer",
        resource_id=str(consumer.uuid),
        old_value=old_value,
        new_value={"name": consumer.name, "status": consumer.status},
        ip_address="0.0.0.0"
    )
    await db.commit()

    return {
        "success": True,
        "data": {"updated": True},
        "meta": {"request_id": "req_" + str(hash(str(consumer_id)))[:16]},
        "error": None
    }

@router.delete("/{consumer_id}", response_model=dict)
async def delete_consumer(
    consumer_id: int,
    admin_user_id: int = 1,
    db=Depends(get_db)
):
    """Deactivate consumer."""
    from app.models.db.base import Consumer

    stmt = select(Consumer).where(Consumer.id == consumer_id)
    consumer = await db.scalar(stmt)

    if not consumer:
        raise HTTPException(status_code=404, detail="Consumer not found")

    old_value = {"status": consumer.status}
    consumer.status = "inactive"

    # Audit log
    audit = AuditService(db)
    await audit.log_action(
        admin_user_id=admin_user_id,
        action_type="DELETE",
        resource_type="consumer",
        resource_id=str(consumer.uuid),
        old_value=old_value,
        new_value={"status": "inactive"},
        ip_address="0.0.0.0"
    )
    await db.commit()

    return {
        "success": True,
        "data": {"deactivated": True},
        "meta": {"request_id": "req_" + str(hash(str(consumer_id)))[:16]},
        "error": None
    }
