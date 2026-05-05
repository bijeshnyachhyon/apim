# Dashboard Routes - HTML pages
from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pathlib import Path

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

# Templates
template_dir = Path(__file__).parent.parent / "dashboard" / "templates"
templates = Jinja2Templates(directory=str(template_dir))

@router.get("/", response_class=HTMLResponse)
@router.get("/overview", response_class=HTMLResponse)
async def dashboard_overview(request: Request):
    return templates.TemplateResponse("dashboard/overview.html", {
        "request": request,
        "active_page": "overview"
    })

@router.get("/endpoints", response_class=HTMLResponse)
async def dashboard_endpoints(request: Request):
    return templates.TemplateResponse("dashboard/endpoints.html", {
        "request": request,
        "active_page": "endpoints"
    })

@router.get("/datasources", response_class=HTMLResponse)
async def dashboard_datasources(request: Request):
    return templates.TemplateResponse("dashboard/datasources.html", {
        "request": request,
        "active_page": "datasources"
    })

@router.get("/ofs-templates", response_class=HTMLResponse)
async def dashboard_ofs_templates(request: Request):
    return templates.TemplateResponse("dashboard/ofs_templates.html", {
        "request": request,
        "active_page": "ofs-templates"
    })

@router.get("/api-keys", response_class=HTMLResponse)
async def dashboard_api_keys(request: Request):
    return templates.TemplateResponse("dashboard/api_keys.html", {
        "request": request,
        "active_page": "api-keys"
    })

@router.get("/consumers", response_class=HTMLResponse)
async def dashboard_consumers(request: Request):
    return templates.TemplateResponse("dashboard/consumers.html", {
        "request": request,
        "active_page": "consumers"
    })

@router.get("/t24", response_class=HTMLResponse)
async def dashboard_t24(request: Request):
    return templates.TemplateResponse("dashboard/t24.html", {
        "request": request,
        "active_page": "t24"
    })

@router.get("/analytics", response_class=HTMLResponse)
async def dashboard_analytics(request: Request):
    return templates.TemplateResponse("dashboard/analytics.html", {
        "request": request,
        "active_page": "analytics"
    })

@router.get("/audit", response_class=HTMLResponse)
async def dashboard_audit(request: Request):
    return templates.TemplateResponse("dashboard/audit.html", {
        "request": request,
        "active_page": "audit"
    })

@router.get("/settings", response_class=HTMLResponse)
async def dashboard_settings(request: Request):
    return templates.TemplateResponse("dashboard/settings.html", {
        "request": request,
        "active_page": "settings"
    })
