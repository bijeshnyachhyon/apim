# Admin Endpoints - OFS Template Management
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List
import structlog

from app.models.schemas import OFSTemplateCreate, ApiResponse
from app.db.session import AsyncSessionLocal
from app.services.audit import AuditService

logger = structlog.get_logger()
router = APIRouter(prefix="/ofs-templates", tags=["Admin - OFS Templates"])

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

@router.get("", response_model=dict)
async def list_ofs_templates(
    page: int = 1,
    limit: int = 25,
    ofs_type: Optional[str] = None,
    status: Optional[str] = None,
    db=Depends(get_db)
):
    """List all OFS templates."""
    from app.models.db.base import OFSTemplate

    stmt = select(OFSTemplate)
    if ofs_type:
        stmt = stmt.where(OFSTemplate.ofs_type == ofs_type)
    if status:
        stmt = stmt.where(OFSTemplate.status == status)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await db.scalar(count_stmt)

    offset = (page - 1) * limit
    stmt = stmt.order_by(OFSTemplate.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    templates = result.scalars().all()

    return {
        "success": True,
        "data": {
            "ofs_templates": [{
                "id": t.id,
                "uuid": t.uuid,
                "name": t.name,
                "ofs_type": t.ofs_type,
                "application_name": t.application_name,
                "status": t.status,
            } for t in templates],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit,
            }
        },
        "meta": {"request_id": "req_" + str(hash(str(page))[:16])},
        "error": None
    }

@router.post("", response_model=dict)
async def create_ofs_template(
    template: OFSTemplateCreate,
    admin_user_id: int = 1,
    db=Depends(get_db)
):
    """Create new OFS template."""
    from app.models.db.base import OFSTemplate

    new_template = OFSTemplate(
        uuid=str(__import__('uuid').uuid4()),
        name=template.name,
        description=template.description,
        ofs_type=template.ofs_type,
        application_name=template.application_name,
        ofs_message_template=template.ofs_message_template,
        variable_definitions=template.variable_definitions,
        t24_version=template.t24_version,
        status=template.status,
    )
    db.add(new_template)
    await db.flush()

    # Audit log
    audit = AuditService(db)
    await audit.log_action(
        admin_user_id=admin_user_id,
        action_type="CREATE",
        resource_type="ofs_template",
        resource_id=str(new_template.uuid),
        old_value=None,
        new_value={"name": new_template.name, "ofs_type": new_template.ofs_type},
        ip_address="0.0.0.0"
    )
    await db.commit()

    return {
        "success": True,
        "data": {
            "id": new_template.id,
            "uuid": new_template.uuid,
            "name": new_template.name,
            "ofs_type": new_template.ofs_type,
            "status": new_template.status,
        },
        "meta": {"request_id": "req_" + str(hash(new_template.uuid))[:16]},
        "error": None
    }

@router.put("/{template_id}", response_model=dict)
async def update_ofs_template(
    template_id: int,
    template: OFSTemplateCreate,
    admin_user_id: int = 1,
    db=Depends(get_db)
):
    """Update OFS template."""
    from app.models.db.base import OFSTemplate

    stmt = select(OFSTemplate).where(OFSTemplate.id == template_id)
    existing = await db.scalar(stmt)

    if not existing:
        raise HTTPException(status_code=404, detail="OFS template not found")

    old_value = {"name": existing.name, "ofs_type": existing.ofs_type, "status": existing.status}

    existing.name = template.name
    existing.description = template.description
    existing.ofs_type = template.ofs_type
    existing.application_name = template.application_name
    existing.ofs_message_template = template.ofs_message_template
    existing.variable_definitions = template.variable_definitions
    existing.t24_version = template.t24_version
    existing.status = template.status

    # Audit log
    audit = AuditService(db)
    await audit.log_action(
        admin_user_id=admin_user_id,
        action_type="UPDATE",
        resource_type="ofs_template",
        resource_id=str(existing.uuid),
        old_value=old_value,
        new_value={"name": existing.name, "ofs_type": existing.ofs_type, "status": existing.status},
        ip_address="0.0.0.0"
    )
    await db.commit()

    return {
        "success": True,
        "data": {"updated": True},
        "meta": {"request_id": "req_" + str(hash(str(template_id))[:16])},
        "error": None
    }

@router.delete("/{template_id}", response_model=dict)
async def delete_ofs_template(
    template_id: int,
    admin_user_id: int = 1,
    db=Depends(get_db)
):
    """Deactivate OFS template."""
    from app.models.db.base import OFSTemplate

    stmt = select(OFSTemplate).where(OFSTemplate.id == template_id)
    existing = await db.scalar(stmt)

    if not existing:
        raise HTTPException(status_code=404, detail="OFS template not found")

    old_value = {"status": existing.status}
    existing.status = "inactive"

    # Audit log
    audit = AuditService(db)
    await audit.log_action(
        admin_user_id=admin_user_id,
        action_type="DELETE",
        resource_type="ofs_template",
        resource_id=str(existing.uuid),
        old_value=old_value,
        new_value={"status": "inactive"},
        ip_address="0.0.0.0"
    )
    await db.commit()

    return {
        "success": True,
        "data": {"deactivated": True},
        "meta": {"request_id": "req_" + str(hash(str(template_id))[:16])},
        "error": None
    }

@router.post("/{template_id}/test", response_model=dict)
async def test_ofs_template(
    template_id: int,
    variables: dict,
    db=Depends(get_db)
):
    """Test OFS template by sending enquiry."""
    from app.models.db.base import OFSTemplate, DataSource
    from app.adapters.t24.connector import T24Connector
    from app.adapters.t24.ofs_builder import OFSBuilder
    from app.services.encryption import decrypt_password

    stmt = select(OFSTemplate).where(OFSTemplate.id == template_id)
    template = await db.scalar(stmt)

    if not template:
        raise HTTPException(status_code=404, detail="OFS template not found")

    # Get T24 data source
    ds_stmt = select(DataSource).where(
        DataSource.db_type == "t24_tcserver",
        DataSource.status == "active"
    )
    data_source = await db.scalar(ds_stmt)

    if not data_source:
        raise HTTPException(status_code=500, detail="T24 data source not configured")

    try:
        password = decrypt_password(data_source.password_encrypted)

        ofs_message = OFSBuilder.build_ofs_message(
            template.ofs_message_template,
            variables,
            data_source.username,
            password
        )

        connector = T24Connector(
            host=data_source.host,
            port=data_source.port,
            username=data_source.username,
            password=password,
            mode=data_source.connection_options.get("connection_mode", "http") if data_source.connection_options else "http",
        )

        ofs_response = await connector.send_ofs(ofs_message)
        await connector.close()

        return {
            "success": True,
            "data": {
                "ofs_message": ofs_message,
                "raw_response": ofs_response,
            },
            "meta": {"request_id": "req_" + str(hash(str(template_id))[:16])},
            "error": None
        }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "meta": {"request_id": "req_" + str(hash(str(template_id))[:16])},
            "error": {"code": "APIM_T24_005", "message": str(e)}
        }
