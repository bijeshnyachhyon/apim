# T24 OFS Endpoints - enquiry and transaction
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any
import time
import uuid
import hashlib
import json
from datetime import datetime

from app.services.routing import RoutingEngine
from app.services.metrics import MetricsService
from app.adapters.t24.connector import T24Connector
from app.adapters.t24.ofs_builder import OFSBuilder
from app.adapters.t24.ofs_parser import OFSParser
from app.services.encryption import decrypt_password
from app.db.session import AsyncSessionLocal
from app.models.schemas import OFSEnquiryRequest, OFSEnquiryResponse, OFSTransactionRequest, OFSTransactionResponse

router = APIRouter()

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

@router.post("/enquiry/{enq_name}", response_model=dict)
async def t24_enquiry(
    enq_name: str,
    request: Request,
    db=Depends(get_db)
):
    """Run T24 OFS Enquiry."""
    start_time = time.time()
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    client_ip = request.client.host if request.client else "unknown"

    # Authenticate
    api_key_header = request.headers.get("X-API-Key")
    if not api_key_header:
        return _error("APIM_AUTH_009", "Missing API key", 401, request_id)

    from sqlalchemy import select
    from app.core.security import hash_api_key
    from app.models.db.base import ApiKey, Consumer, DataSource, OsfTemplate

    key_hash = hash_api_key(api_key_header)
    stmt = (
        select(ApiKey, Consumer)
        .join(Consumer, ApiKey.consumer_id == Consumer.id)
        .where(ApiKey.key_hash == key_hash, ApiKey.status == "active")
    )
    result = await db.execute(stmt)
    row = result.first()

    if not row:
        return _error("APIM_AUTH_001", "Invalid API key", 401, request_id)

    api_key_obj, consumer = row
    api_key_id = api_key_obj.id
    consumer_id = consumer.id

    # Get request body
    try:
        body = await request.json()
    except:
        return _error("APIM_VAL_009", "Invalid JSON body", 400, request_id)

    variables = body.get("variables", {})
    if not variables:
        return _error("APIM_VAL_002", "Missing variables", 400, request_id)

    # Find OFS template by enquiry name
    stmt = select(OsfTemplate).where(
        OsfTemplate.application_name == enq_name,
        OsfTemplate.ofs_type == "enquiry",
        OsfTemplate.status == "active"
    )
    result = await db.execute(stmt)
    ofs_template = result.scalar_one_or_none()

    if not ofs_template:
        return _error("APIM_T24_003", "OFS template not found", 404, request_id)

    # Get T24 data source
    stmt = select(DataSource).where(
        DataSource.db_type == "t24_tcserver",
        DataSource.status == "active"
    )
    result = await db.execute(stmt)
    data_source = result.scalar_one_or_none()

    if not data_source:
        return _error("APIM_T24_001", "T24 data source not configured", 500, request_id)

    try:
        # Decrypt password
        password = decrypt_password(data_source.password_encrypted)

        # Build OFS message
        ofs_message = OFSBuilder.build_ofs_message(
            ofs_template.ofs_message_template,
            variables,
            data_source.username,
            password
        )

        # Send OFS message
        connector = T24Connector(
            host=data_source.host,
            port=data_source.port,
            username=data_source.username,
            password=password,
            mode=data_source.connection_options.get("connection_mode", "http") if data_source.connection_options else "http",
            http_endpoint=data_source.connection_options.get("http_endpoint", "/BrowserWeb/servlet/BrowserServlet") if data_source.connection_options else "/BrowserWeb/servlet/BrowserServlet",
        )

        ofs_response = await connector.send_ofs(ofs_message)
        await connector.close()

        # Parse response
        parsed = OFSParser.parse_ofs_enquiry_response(ofs_response)

        latency_ms = (time.time() - start_time) * 1000

        # Log request
        metrics = MetricsService(db=db)
        await metrics.log_request_to_db(
            request_id, api_key_id, consumer_id, None,
            "POST", str(request.url), dict(request.query_params),
            hashlib.sha256(json.dumps(body).encode()).hexdigest(),
            "t24_tcserver", data_source.id,
            200, latency_ms, None, client_ip,
            request.headers.get("User-Agent")
        )
        await db.commit()

        return {
            "success": True,
            "data": {
                "enquiry": enq_name,
                "record": parsed.get("@RECORD", {}),
                "raw_response": ofs_response if settings.APP_ENV == "development" else None,
            },
            "meta": {
                "request_id": request_id,
                "timestamp": datetime.now().isoformat(),
                "latency_ms": round(latency_ms, 2),
            },
            "error": None,
        }

    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        error_msg = str(e)

        metrics = MetricsService(db=db)
        await metrics.log_request_to_db(
            request_id, api_key_id, consumer_id, None,
            "POST", str(request.url), dict(request.query_params), None,
            "t24_tcserver", None,
            400, latency_ms, "APIM_T24_005", error_msg, client_ip,
            request.headers.get("User-Agent")
        )
        await db.commit()

        return _error("APIM_T24_005", f"T24 enquiry failed: {error_msg}", 400, request_id)

@router.post("/transaction", response_model=dict)
async def t24_transaction(
    request: Request,
    db=Depends(get_db)
):
    """Post T24 OFS Transaction."""
    start_time = time.time()
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    client_ip = request.client.host if request.client else "unknown"

    # Authenticate
    api_key_header = request.headers.get("X-API-Key")
    if not api_key_header:
        return _error("APIM_AUTH_009", "Missing API key", 401, request_id)

    from sqlalchemy import select
    from app.core.security import hash_api_key
    from app.models.db.base import ApiKey, Consumer, DataSource, OsfTemplate

    key_hash = hash_api_key(api_key_header)
    stmt = (
        select(ApiKey, Consumer)
        .join(Consumer, ApiKey.consumer_id == Consumer.id)
        .where(ApiKey.key_hash == key_hash, ApiKey.status == "active")
    )
    result = await db.execute(stmt)
    row = result.first()

    if not row:
        return _error("APIM_AUTH_001", "Invalid API key", 401, request_id)

    api_key_obj, consumer = row

    # Get request body
    try:
        body = await request.json()
    except:
        return _error("APIM_VAL_009", "Invalid JSON body", 400, request_id)

    application = body.get("application")
    variables = body.get("variables", {})

    if not application:
        return _error("APIM_T24_015", "Missing application", 400, request_id)
    if not variables:
        return _error("APIM_VAL_002", "Missing variables", 400, request_id)

    # Find OFS template
    stmt = select(OsfTemplate).where(
        OsfTemplate.application_name == application,
        OsfTemplate.ofs_type == "transaction",
        OsfTemplate.status == "active"
    )
    result = await db.execute(stmt)
    ofs_template = result.scalar_one_or_none()

    if not ofs_template:
        return _error("APIM_T24_003", "OFS template not found", 404, request_id)

    # Get T24 data source
    stmt = select(DataSource).where(
        DataSource.db_type == "t24_tcserver",
        DataSource.status == "active"
    )
    result = await db.execute(stmt)
    data_source = result.scalar_one_or_none()

    if not data_source:
        return _error("APIM_T24_001", "T24 data source not configured", 500, request_id)

    try:
        password = decrypt_password(data_source.password_encrypted)

        ofs_message = OFSBuilder.build_ofs_message(
            ofs_template.ofs_message_template,
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

        parsed = OFSParser.parse_ofs_transaction_response(ofs_response)

        latency_ms = (time.time() - start_time) * 1000

        # Log
        metrics = MetricsService(db=db)
        await metrics.log_request_to_db(
            request_id, api_key_obj.id, consumer.id, None,
            "POST", str(request.url), dict(request.query_params),
            hashlib.sha256(json.dumps(body).encode()).hexdigest(),
            "t24_tcserver", data_source.id,
            200, latency_ms, None, client_ip,
            request.headers.get("User-Agent")
        )
        await db.commit()

        return {
            "success": True,
            "data": {
                "transaction_id": parsed.get("transaction_id"),
                "application": application,
                "status": parsed.get("status", "unknown"),
                "raw_response": ofs_response if settings.APP_ENV == "development" else None,
            },
            "meta": {
                "request_id": request_id,
                "timestamp": datetime.now().isoformat(),
                "latency_ms": round(latency_ms, 2),
            },
            "error": None,
        }

    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        return _error("APIM_T24_006", f"T24 transaction failed: {str(e)}", 400, request_id)

@router.get("/status", response_model=dict)
async def t24_status(db=Depends(get_db)):
    """Check T24 TCServer connection health."""
    from sqlalchemy import select
    from app.models.db.base import DataSource

    stmt = select(DataSource).where(
        DataSource.db_type == "t24_tcserver",
        DataSource.status == "active"
    )
    result = await db.execute(stmt)
    data_source = result.scalar_one_or_none()

    if not data_source:
        return {
            "success": True,
            "data": {"connected": False, "reason": "No active T24 data source"},
            "meta": {"request_id": str(uuid.uuid4())},
            "error": None,
        }

    try:
        password = decrypt_password(data_source.password_encrypted)
        connector = T24Connector(
            host=data_source.host,
            port=data_source.port,
            username=data_source.username,
            password=password,
        )
        is_connected = await connector.test_connection()
        await connector.close()

        return {
            "success": True,
            "data": {
                "connected": is_connected,
                "host": data_source.host,
                "port": data_source.port,
            },
            "meta": {"request_id": str(uuid.uuid4())},
            "error": None,
        }
    except Exception as e:
        return {
            "success": True,
            "data": {"connected": False, "error": str(e)},
            "meta": {"request_id": str(uuid.uuid4())},
            "error": None,
        }

def _error(code: str, message: str, status_code: int, request_id: str):
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "data": None,
            "meta": {
                "request_id": request_id,
                "timestamp": datetime.now().isoformat(),
            },
            "error": {"code": code, "message": message},
        }
    )
