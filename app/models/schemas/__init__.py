# Pydantic Schemas for API requests/responses
from pydantic import BaseModel, Field, field_validator, ConfigDict, AnyUrl
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from enum import Enum

# ===== Auth Schemas =====

class TokenRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class ApiKeyCreate(BaseModel):
    consumer_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    allowed_endpoints: Optional[List[UUID]] = None
    rate_limit_per_hour: int = Field(1000, ge=1, le=1000000)
    rate_limit_per_minute: int = Field(100, ge=1, le=10000)
    expires_at: Optional[datetime] = None

class ApiKeyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    uuid: str
    key_prefix: str
    consumer_id: int
    name: str
    rate_limit_per_hour: int
    rate_limit_per_minute: int
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    status: str
    created_at: datetime

class ApiKeyCreateResponse(ApiKeyResponse):
    key: Optional[str] = None  # Only returned once at creation

# ===== Data Source Schemas =====

class DataSourceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    host: str = Field(..., min_length=1, max_length=255)
    port: int = Field(..., ge=1, le=65535)
    database_name: str = Field(..., min_length=1, max_length=255)
    username: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=1)
    connection_options: Optional[Dict[str, Any]] = None
    pool_min: int = Field(2, ge=1, le=100)
    pool_max: int = Field(20, ge=1, le=500)
    status: str = Field("active", pattern=r"^(active|inactive|error|connecting)$")

class MSSQLDataSource(DataSourceBase):
    db_type: str = Field("mssql", literal="mssql")

class OracleDataSource(DataSourceBase):
    db_type: str = Field("oracle", literal="oracle")

class PostgreSQLDataSource(DataSourceBase):
    db_type: str = Field("postgresql", literal="postgresql")

class MySQLDataSource(DataSourceBase):
    db_type: str = Field("mysql", literal="mysql")

class MongoDBDataSource(BaseModel):
    db_type: str = Field("mongodb", literal="mongodb")
    name: str
    host: str
    port: int = 27017
    database_name: str
    username: str
    password: str
    auth_source: str = "admin"
    replica_set: Optional[str] = None
    status: str = "active"

class T24DataSource(BaseModel):
    db_type: str = Field("t24_tcserver", literal="t24_tcserver")
    name: str
    host: str
    port: int = 9089
    username: str
    password: str
    connection_mode: str = Field("http", literal=["http", "tcp"])
    http_endpoint: str = "/BrowserWeb/servlet/BrowserServlet"
    timeout_seconds: int = 30
    max_retries: int = 3
    t24_version: str = "0"
    status: str = "active"

# Union for data source creation
DataSourceCreate = MSSQLDataSource | OracleDataSource | PostgreSQLDataSource | MySQLDataSource | MongoDBDataSource | T24DataSource

class DataSourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    uuid: str
    name: str
    db_type: str
    host: str
    port: int
    database_name: str
    username: str
    pool_min: int
    pool_max: int
    status: str

# ===== OFS Templates =====

class OFSTemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    ofs_type: str = Field(..., literal=["enquiry", "transaction"])
    application_name: str = Field(..., min_length=1)
    ofs_message_template: str = Field(..., min_length=1)
    variable_definitions: Dict[str, Dict[str, Any]]
    t24_version: str = "0"
    status: str = Field("active", pattern=r"^(active|inactive)$")

class OFSTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    uuid: str
    name: str
    description: Optional[str]
    ofs_type: str
    application_name: str
    ofs_message_template: str
    variable_definitions: Dict[str, Any]
    t24_version: str
    status: str

# ===== Endpoint Registration =====

class EndpointRegistration(BaseModel):
    slug: str = Field(..., pattern=r'^[a-z0-9-]+$')
    name: str = Field(..., min_length=1, max_length=255))
    description: Optional[str] = None
    http_method: str = Field(..., literal=["GET", "POST", "PUT", "DELETE"])
    path_pattern: str = Field(..., min_length=1)
    data_source_id: int
    query_template: Optional[str] = None
    ofs_template_id: Optional[int] = None
    request_schema: Optional[Dict[str, Any]] = None
    response_schema: Optional[Dict[str, Any]] = None
    auth_required: bool = True
    allowed_scopes: Optional[List[str]] = None
    cache_ttl_seconds: int = Field(0, ge=0, le=86400)
    status: str = Field("active", pattern=r"^(active|inactive)$")

class EndpointResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    uuid: str
    slug: str
    name: str
    description: Optional[str]
    http_method: str
    path_pattern: str
    data_source_id: Optional[int]
    ofs_template_id: Optional[int]
    auth_required: bool
    status: str

# ===== Query Schemas =====

class QueryRequest(BaseModel):
    """Dynamic query request - validated against endpoint's request_schema at runtime"""
    pass

class QueryResponse(BaseModel):
    records: List[Dict[str, Any]]
    count: int
    target: str
    execution_time_ms: float

# ===== OFS Schemas =====

class OFSEnquiryRequest(BaseModel):
    variables: Dict[str, str] = Field(..., min_length=1)

class OFSEnquiryResponse(BaseModel):
    enquiry: str
    record: Dict[str, Any]
    raw_response: Optional[str] = None

class OFSTransactionRequest(BaseModel):
    application: str = Field(..., min_length=1)
    variables: Dict[str, str] = Field(..., min_length=1)

class OFSTransactionResponse(BaseModel):
    transaction_id: str
    application: str
    status: str
    raw_response: Optional[str] = None

# ===== Audit =====

class AuditLogEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    admin_user: str
    action_type: str
    resource_type: str
    resource_id: Optional[str]
    old_value: Optional[Dict[str, Any]]
    new_value: Optional[Dict[str, Any]]
    ip_address: str
    created_at: datetime

# ===== Standard API Response =====

class ApiResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    meta: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
