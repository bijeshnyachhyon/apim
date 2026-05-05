# Admin Endpoints - Data Source Management
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List
import structlog
from app.core.security import verify_password
from app.models.schemas import DataSourceCreate, DataSourceResponse, ApiResponse
from app.services.encryption import encrypt_password
from app.db.session import AsyncSessionLocal
from app.services.audit import AuditService

logger = structlog.get_logger()
router = APIRouter(prefix="/datasources", tags=["Admin - Data Sources"])

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

@router.get("", response_model=dict)
async def list_datasources(
    page: int = 1,
    limit: int = 25,
    db_type: Optional[str] = None,
    status: Optional[str] = None,
    db=Depends(get_db)
):
    """List all data sources."""
    from app.models.db.base import DataSource

    stmt = select(DataSource)
    if db_type:
        stmt = stmt.where(DataSource.db_type == db_type)
    if status:
        stmt = stmt.where(DataSource.status == status)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await db.scalar(count_stmt)

    offset = (page - 1) * limit
    stmt = stmt.order_by(DataSource.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    sources = result.scalars().all()

    return {
        "success": True,
        "data": {
            "data_sources": [{
                "id": ds.id,
                "uuid": ds.uuid,
                "name": ds.name,
                "db_type": ds.db_type,
                "host": ds.host,
                "port": ds.port,
                "database_name": ds.database_name,
                "pool_min": ds.pool_min,
                "pool_max": ds.pool_max,
                "status": ds.status,
            } for ds in sources],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
            }
        },
        "meta": {"request_id": "req_" + str(hash(str(page)))[:16]},
        "error": None
    }

@router.post("", response_model=dict)
async def create_datasource(
    data: DataSourceCreate,
    admin_user_id: int = 1,  # Would get from JWT
    db=Depends(get_db)
):
    """Create new data source."""
    from app.models.db.base import DataSource

    # Encrypt password
    encrypted_password = encrypt_password(data.password)

    new_ds = DataSource(
        uuid=str(__import__('uuid').uuid4()),
        name=data.name,
        db_type=data.db_type,
        host=data.host,
        port=data.port,
        database_name=data.database_name,
        username=data.username,
        password_encrypted=encrypted_password,
        connection_options=data.connection_options,
        pool_min=data.pool_min,
        pool_max=data.pool_max,
        status=data.status,
    )
    db.add(new_ds)
    await db.flush()

    # Audit log
    audit = AuditService(db)
    await audit.log_action(
        admin_user_id=admin_user_id,
        action_type="CREATE",
        resource_type="data_source",
        resource_id=str(new_ds.uuid),
        old_value=None,
        new_value={"name": new_ds.name, "db_type": new_ds.db_type},
        ip_address="0.0.0.0"
    )
    await db.commit()

    return {
        "success": True,
        "data": {
            "id": new_ds.id,
            "uuid": new_ds.uuid,
            "name": new_ds.name,
            "db_type": new_ds.db_type,
            "status": new_ds.status,
        },
        "meta": {"request_id": "req_" + str(hash(new_ds.uuid))[:16]},
        "error": None
    }

@router.put("/{ds_id}", response_model=dict)
async def update_datasource(
    ds_id: int,
    data: DataSourceCreate,
    admin_user_id: int = 1,
    db=Depends(get_db)
):
    """Update data source."""
    from app.models.db.base import DataSource

    stmt = select(DataSource).where(DataSource.id == ds_id)
    ds = await db.scalar(stmt)

    if not ds:
        raise HTTPException(status_code=404, detail="Data source not found")

    old_value = {"name": ds.name, "host": ds.host, "status": ds.status}

    ds.name = data.name
    ds.host = data.host
    ds.port = data.port
    ds.database_name = data.database_name
    ds.username = data.username
    if data.password:
        ds.password_encrypted = encrypt_password(data.password)
    ds.connection_options = data.connection_options
    ds.pool_min = data.pool_min
    ds.pool_max = data.pool_max
    ds.status = data.status

    # Audit log
    audit = AuditService(db)
    await audit.log_action(
        admin_user_id=admin_user_id,
        action_type="UPDATE",
        resource_type="data_source",
        resource_id=str(ds.uuid),
        old_value=old_value,
        new_value={"name": ds.name, "host": ds.host, "status": ds.status},
        ip_address="0.0.0.0"
    )
    await db.commit()

    return {
        "success": True,
        "data": {"updated": True},
        "meta": {"request_id": "req_" + str(hash(str(ds_id)))[:16]},
        "error": None
    }

@router.delete("/{ds_id}", response_model=dict)
async def delete_datasource(
    ds_id: int,
    admin_user_id: int = 1,
    db=Depends(get_db)
):
    """Deactivate data source."""
    from app.models.db.base import DataSource

    stmt = select(DataSource).where(DataSource.id == ds_id)
    ds = await db.scalar(stmt)

    if not ds:
        raise HTTPException(status_code=404, detail="Data source not found")

    old_value = {"status": ds.status}
    ds.status = "inactive"

    # Audit log
    audit = AuditService(db)
    await audit.log_action(
        admin_user_id=admin_user_id,
        action_type="DELETE",
        resource_type="data_source",
        resource_id=str(ds.uuid),
        old_value=old_value,
        new_value={"status": "inactive"},
        ip_address="0.0.0.0"
    )
    await db.commit()

    return {
        "success": True,
        "data": {"deactivated": True},
        "meta": {"request_id": "req_" + str(hash(str(ds_id)))[:16]},
        "error": None
    }

@router.post("/{ds_id}/test", response_model=dict)
async def test_datasource(ds_id: int, db=Depends(get_db)):
    """Test data source connection."""
    from app.models.db.base import DataSource
    from app.services.encryption import decrypt_password
    from app.adapters.factory import AdapterFactory

    stmt = select(DataSource).where(DataSource.id == ds_id)
    ds = await db.scalar(stmt)

    if not ds:
        raise HTTPException(status_code=404, detail="Data source not found")

    try:
        password = decrypt_password(ds.password_encrypted)
        adapter = AdapterFactory.create_adapter(
            ds.name, ds.db_type, ds.host, ds.port,
            ds.database_name, ds.username, password,
            ds.pool_min, ds.pool_max, ds.connection_options
        )
        health = await adapter.health_check()
        await adapter.disconnect()

        return {
            "success": True,
            "data": {
                "connected": health.status == "ok",
                "latency_ms": health.latency_ms,
                "error": health.error_message,
            },
            "meta": {"request_id": "req_" + str(hash(str(ds_id)))[:16]},
            "error": None
        }
    except Exception as e:
        return {
            "success": True,
            "data": {"connected": False, "error": str(e)},
            "meta": {"request_id": "req_" + str(hash(str(ds_id)))[:16]},
            "error": None
        }
