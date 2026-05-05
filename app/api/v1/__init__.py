# API v1 routes
from fastapi import APIRouter
from app.api.v1 import auth, query, t24, metrics
from app.api.v1.admin import router as admin_router

router = APIRouter(prefix="/api/v1")
router.include_router(auth.router)
router.include_router(query.router)
router.include_router(t24.router)
router.include_router(metrics.router)
router.include_router(admin_router)
