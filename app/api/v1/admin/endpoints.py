# Admin Endpoints - API Endpoint Management
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List
import structlog

from app.models.schemas import (
    EndpointRegistration, EndpointResponse, ApiResponse
)
from app.db.session import AsyncSessionLocal
from app.services.audit import AuditService

logger = structlog.get_logger()
router = APIRouter(prefix="/endpoints", tags=["Admin - Endpoints"])

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

@router.get("", response_model=dict)
async def list_endpoints(
    page: int = 1,
    limit: int = 25,
    status: Optional[str] = None,
    db=Depends(get_db)
):
    """List all API endpoints."""
    from app.models.db.base import ApiEndpoint

    stmt = select(ApiEndpoint)
    if status:
        stmt = stmt.where(ApiEndpoint.status == status)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await db.scalar(count_stmt)

    offset = (page - 1) * limit
    stmt = stmt.order_by(ApiEndpoint.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    endpoints = result.scalars().all()

    return {
        "success": True,
        "data": {
            "endpoints": [{
                "id": e.id,
                "uuid": e.uuid,
                "slug": e.slug,
                "name": e.name,
                "http_method": e.http_method,
                "path_pattern": e.path_pattern,
                "data_source_id": e.data_source_id,
                "status": e.status,
            } for e in endpoints],
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
async def create_endpoint(
    endpoint: EndpointRegistration,
    admin_user_id: int = 1,  # Would get from JWT
    db=Depends(get_db)
):
    """Create new API endpoint."""
    from app.models.db.base import ApiEndpoint, DataSource, OsfTemplate

    # Check if slug already exists
    stmt = select(ApiEndpoint).where(ApiEndpoint.slug == endpoint.slug)
    if await db.scalar(stmt):
        raise HTTPException(status_code=400, detail="Slug already exists")

    # Verify data source if provided
    if endpoint.data_source_id:
        ds_stmt = select(DataSource).where(DataSource.id == endpoint.data_source_id)
        if not await db.scalar(ds_stmt):
            raise HTTPException(status_code=404, detail="Data source not found")

    # Verify OFS template if provided
    if endpoint.ofs_template_id:
        tpl_stmt = select(OsfTemplate).where(OsfTemplate.id == endpoint.ofs_template_id)
        if not await db.scalar(tpl_stmt):
            raise HTTPException(status_code=404, detail="OFS template not found")

    new_endpoint = ApiEndpoint(
        uuid=str(__import__('uuid').uuid4()),
        slug=endpoint.slug,
        name=endpoint.name,
        description=endpoint.description,
        http_method=endpoint.http_method,
        path_pattern=endpoint.path_pattern,
        data_source_id=endpoint.data_source_id or None,
        query_template=endpoint.query_template,
        ofs_template_id=endpoint.ofs_template_id,
        request_schema=endpoint.request_schema,
        response_schema=endpoint.response_schema,
        auth_required=endpoint.auth_required,
        allowed_scopes=endpoint.allowed_scopes,
        cache_ttl_seconds=endpoint.cache_ttl_seconds,
        status=endpoint.status,
    )
    db.add(new_endpoint)
    await db.flush()

    # Audit log
    audit = AuditService(db)
    await audit.log_action(
        admin_user_id=admin_user_id,
        action_type="CREATE",
        resource_type="api_endpoint",
        resource_id=str(new_endpoint.uuid),
        old_value=None,
        new_value={"slug": new_endpoint.slug, "name": new_endpoint.name},
        ip_address="0.0.0.0"
    )
    await db.commit()

    return {
        "success": True,
        "data": {
            "id": new_endpoint.id,
            "uuid": new_endpoint.uuid,
            "slug": new_endpoint.slug,
            "name": new_endpoint.name,
            "status": new_endpoint.status,
        },
        "meta": {"request_id": "req_" + str(hash(new_endpoint.uuid))[:16]},
        "error": None
    }

@router.put("/{endpoint_id}", response_model=dict)
async def update_endpoint(
    endpoint_id: int,
    endpoint: EndpointRegistration,
    admin_user_id: int = 1,
    db=Depends(get_db)
):
    """Update API endpoint."""
    from app.models.db.base import ApiEndpoint

    stmt = select(ApiEndpoint).where(ApiEndpoint.id == endpoint_id)
    existing = await db.scalar(stmt)

    if not existing:
        raise HTTPException(status_code=404, detail="Endpoint not found")

    old_value = {"slug": existing.slug, "name": existing.name, "status": existing.status}

    existing.slug = endpoint.slug
    existing.name = endpoint.name
    existing.description = endpoint.description
    existing.http_method = endpoint.http_method
    existing.path_pattern = endpoint.path_pattern
    existing.data_source_id = endpoint.data_source_id
    existing.query_template = endpoint.query_template
    existing.ofs_template_id = endpoint.ofs_template_id
    existing.request_schema = endpoint.request_schema
    existing.response_schema = endpoint.response_schema
    existing.auth_required = endpoint.auth_required
    existing.allowed_scopes = endpoint.allowed_scopes
    existing.cache_ttl_seconds = endpoint.cache_ttl_seconds
    existing.status = endpoint.status

    # Audit log
    audit = AuditService(db)
    await audit.log_action(
        admin_user_id=admin_user_id,
        action_type="UPDATE",
        resource_type="api_endpoint",
        resource_id=str(existing.uuid),
        old_value=old_value,
        new_value={"slug": existing.slug, "name": existing.name, "status": existing.status},
        ip_address="0.0.0.0"
    )
    await db.commit()

    return {
        "success": True,
        "data": {"updated": True},
        "meta": {"request_id": "req_" + str(hash(str(endpoint_id)))[:16]},
        "error": None
    }

@router.delete("/{endpoint_id}", response_model=dict)
async def delete_endpoint(
    endpoint_id: int,
    admin_user_id: int = 1,
    db=Depends(get_db)
):
    """Deactivate API endpoint."""
    from app.models.db.base import ApiEndpoint

    stmt = select(ApiEndpoint).where(ApiEndpoint.id == endpoint_id)
    existing = await db.scalar(stmt)

    if not existing:
        raise HTTPException(status_code=404, detail="Endpoint not found")

    old_value = {"status": existing.status}
    existing.status = "inactive"

    # Audit log
    audit = AuditService(db)
    await audit.log_action(
        admin_user_id=admin_user_id,
        action_type="DELETE",
        resource_type="api_endpoint",
        resource_id=str(existing.uuid),
        old_value=old_value,
        new_value={"status": "inactive"},
        ip_address="0.0.0.0"
    )
    await db.commit()

    return {
        "success": True,
        "data": {"deactivated": True},
        "meta": {"request_id": "req_" + str(hash(str(endpoint_id)))[:16]},
        "error": None
    }
