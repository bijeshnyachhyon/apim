# Routing Engine - determines target from endpoint registry
from typing import Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.models.db.base import ApiEndpoint, DataSource, OsfTemplate

class RoutingEngine:
    """Determines target database or T24 based on registered endpoint."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def resolve_endpoint(self, slug: str) -> Optional[Dict[str, Any]]:
        """
        Resolve an endpoint by slug.
        Returns dict with endpoint info, data source, and OFS template if applicable.
        """
        stmt = (
            select(ApiEndpoint, DataSource, OsfTemplate)
            .outerjoin(DataSource, ApiEndpoint.data_source_id == DataSource.id)
            .outerjoin(OsfTemplate, ApiEndpoint.ofs_template_id == OsfTemplate.id)
            .where(ApiEndpoint.slug == slug, ApiEndpoint.status == "active")
        )
        result = await self.db.execute(stmt)
        row = result.first()

        if not row:
            return None

        endpoint, data_source, ofs_template = row

        result = {
            "endpoint_id": endpoint.id,
            "endpoint_uuid": str(endpoint.uuid),
            "slug": endpoint.slug,
            "name": endpoint.name,
            "http_method": endpoint.http_method,
            "query_template": endpoint.query_template,
            "request_schema": endpoint.request_schema,
            "auth_required": endpoint.auth_required,
            "allowed_scopes": endpoint.allowed_scopes,
            "cache_ttl_seconds": endpoint.cache_ttl_seconds,
        }

        if data_source:
            result["data_source"] = {
                "id": data_source.id,
                "name": data_source.name,
                "db_type": data_source.db_type,
                "host": data_source.host,
                "port": data_source.port,
                "database_name": data_source.database_name,
                "username": data_source.username,
                "password_encrypted": data_source.password_encrypted,
                "connection_options": data_source.connection_options,
                "pool_min": data_source.pool_min,
                "pool_max": data_source.pool_max,
            }

        if ofs_template:
            result["ofs_template"] = {
                "id": ofs_template.id,
                "name": ofs_template.name,
                "ofs_type": ofs_template.ofs_type,
                "application_name": ofs_template.application_name,
                "ofs_message_template": ofs_template.ofs_message_template,
                "variable_definitions": ofs_template.variable_definitions,
                "t24_version": ofs_template.t24_version,
            }

        return result

    async def resolve_by_id(self, endpoint_id: int) -> Optional[Dict[str, Any]]:
        """Resolve endpoint by ID."""
        stmt = (
            select(ApiEndpoint, DataSource, OsfTemplate)
            .outerjoin(DataSource, ApiEndpoint.data_source_id == DataSource.id)
            .outerjoin(OsfTemplate, ApiEndpoint.ofs_template_id == OsfTemplate.id)
            .where(ApiEndpoint.id == endpoint_id, ApiEndpoint.status == "active")
        )
        result = await self.db.execute(stmt)
        row = result.first()

        if not row:
            return None

        endpoint, data_source, ofs_template = row
        return {
            "endpoint_id": endpoint.id,
            "slug": endpoint.slug,
            "name": endpoint.name,
            "data_source": {
                "db_type": data_source.db_type if data_source else None,
                "host": data_source.host if data_source else None,
                "port": data_source.port if data_source else None,
                "database_name": data_source.database_name if data_source else None,
                "username": data_source.username if data_source else None,
                "password_encrypted": data_source.password_encrypted if data_source else None,
            } if data_source else None,
            "ofs_template": {
                "ofs_type": ofs_template.ofs_type,
                "application_name": ofs_template.application_name,
                "ofs_message_template": ofs_template.ofs_message_template,
            } if ofs_template else None,
        }
