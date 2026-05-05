# Audit Service - immutable audit trail
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert
from app.models.db.base import AuditTrail
from datetime import datetime
from uuid import uuid4

class AuditService:
    """Handles audit trail logging (immutable)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log_action(
        self,
        admin_user_id: int,
        action_type: str,
        resource_type: str,
        resource_id: Optional[str],
        old_value: Optional[Dict[str, Any]],
        new_value: Optional[Dict[str, Any]],
        ip_address: str,
    ) -> None:
        """Log an admin action to the audit trail."""
        audit_entry = AuditTrail(
            uuid=str(uuid4()),
            admin_user_id=admin_user_id,
            action_type=action_type,
            resource_type=resource_type,
            resource_id=resource_id,
            old_value=old_value,
            new_value=new_value,
            ip_address=ip_address,
        )
        self.db.add(audit_entry)
        await self.db.flush()

    async def get_logs(
        self,
        page: int = 1,
        limit: int = 50,
        admin_user_id: Optional[int] = None,
        action_type: Optional[str] = None,
        resource_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> tuple[list, int]:
        """Get paginated audit logs with filters."""
        from sqlalchemy import select, func, and_
        from app.models.db.base import AdminUser

        stmt = (
            select(AuditTrail, AdminUser.username.label("admin_user"))
            .join(AdminUser, AuditTrail.admin_user_id == AdminUser.id)
        )

        conditions = []
        if admin_user_id:
            conditions.append(AuditTrail.admin_user_id == admin_user_id)
        if action_type:
            conditions.append(AuditTrail.action_type == action_type)
        if resource_type:
            conditions.append(AuditTrail.resource_type == resource_type)
        if start_date:
            conditions.append(AuditTrail.created_at >= start_date)
        if end_date:
            conditions.append(AuditTrail.created_at <= end_date)

        if conditions:
            stmt = stmt.where(and_(*conditions))

        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.db.scalar(count_stmt)

        # Apply pagination
        offset = (page - 1) * limit
        stmt = stmt.order_by(AuditTrail.created_at.desc()).offset(offset).limit(limit)

        result = await self.db.execute(stmt)
        rows = result.all()

        logs = []
        for audit, admin_user in rows:
            logs.append({
                "id": audit.id,
                "uuid": audit.uuid,
                "admin_user": admin_user,
                "action_type": audit.action_type,
                "resource_type": audit.resource_type,
                "resource_id": audit.resource_id,
                "old_value": audit.old_value,
                "new_value": audit.new_value,
                "ip_address": audit.ip_address,
                "created_at": audit.created_at,
            })

        return logs, total
