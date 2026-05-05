# Admin API routes with rate limiting and audit
from fastapi import APIRouter
from app.api.v1.admin import endpoints, datasources, consumers, ofs_templates

router = APIRouter(prefix="/admin")
router.include_router(endpoints.router)
router.include_router(datasources.router)
router.include_router(consumers.router)
router.include_router(ofs_templates.router)
