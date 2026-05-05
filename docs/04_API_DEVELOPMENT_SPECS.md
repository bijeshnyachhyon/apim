# 04 API Development Specifications

## 4.1 API Design Standards
### RESTful Conventions
- Base URL: `https://api.example.com/api/v1/`
- Resource naming: plural nouns (`/endpoints`, `/consumers`)
- HTTP methods: GET (read), POST (create/execute), PUT (update), DELETE (remove)
- Versioning: URL path versioning (`/api/v1/`, `/api/v2/`)

### Response Envelope (JSON:API-aligned)
```json
{
  "success": true,
  "data": { },
  "meta": {
    "request_id": "uuid-string",
    "timestamp": "2026-05-05T10:30:00Z",
    "latency_ms": 42,
    "version": "1.0.0"
  },
  "error": null
}
```

### Error Response Format
```json
{
  "success": false,
  "data": null,
  "meta": {
    "request_id": "uuid-string",
    "timestamp": "2026-05-05T10:30:00Z",
    "latency_ms": 15
  },
  "error": {
    "code": "APIM_AUTH_001",
    "message": "Invalid API key",
    "details": {
      "field": "X-API-Key",
      "reason": "Key not found or revoked"
    }
  }
}
```

### Standard HTTP Headers
- `X-API-Key`: API key for consumer authentication
- `Authorization`: JWT Bearer token for admin/refresh endpoints
- `X-Request-ID`: Client-supplied request ID (optional, UUID)
- `X-RateLimit-Limit`: Rate limit for the key (returned on responses)
- `X-RateLimit-Remaining`: Remaining requests in current window
- `X-RateLimit-Reset`: Unix timestamp when rate limit resets

## 4.2 Authentication Endpoints

### POST `/api/v1/auth/token`
Get JWT access and refresh tokens from username/password.

**Request Body:**
```json
{
  "username": "admin@example.com",
  "password": "secure-password"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbG...",
    "refresh_token": "eyJhbG...",
    "token_type": "bearer",
    "expires_in": 900
  },
  "meta": { "request_id": "...", "timestamp": "...", "latency_ms": 42 },
  "error": null
}
```

**Errors:**
- `401`: Invalid credentials → `APIM_AUTH_001`
- `423`: Account locked → `APIM_AUTH_005`

---

### POST `/api/v1/auth/refresh`
Refresh JWT access token using refresh token.

**Request Body:**
```json
{
  "refresh_token": "eyJhbG..."
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbG...",
    "expires_in": 900
  },
  "meta": { ... },
  "error": null
}
```

---

### POST `/api/v1/auth/api-keys`
**Admin Only** — Create a new API key for a consumer.

**Headers:** `Authorization: Bearer <admin_jwt>`

**Request Body:**
```json
{
  "consumer_id": "uuid",
  "name": "Production Key",
  "allowed_endpoints": ["uuid1", "uuid2"],
  "rate_limit_per_hour": 5000,
  "rate_limit_per_minute": 200,
  "expires_at": "2027-05-05T00:00:00Z"
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "key": "apim_live_8f3a9b2c1d4e5f6a7b8c9d0e1f2a3b4",
    "key_prefix": "apim_live_8f3a9b2c",
    "consumer_id": "uuid",
    "name": "Production Key",
    "rate_limit_per_hour": 5000,
    "rate_limit_per_minute": 200,
    "expires_at": "2027-05-05T00:00:00Z",
    "created_at": "2026-05-05T10:30:00Z"
  },
  "meta": { ... },
  "error": null
}
```
**Note:** Full key is only returned ONCE at creation. Store it securely.

---

### DELETE `/api/v1/auth/api-keys/{id}`
**Admin Only** — Revoke an API key.

**Response (200 OK):**
```json
{
  "success": true,
  "data": { "revoked": true, "revoked_at": "2026-05-05T10:35:00Z" },
  "meta": { ... },
  "error": null
}
```

---

### GET `/api/v1/auth/api-keys`
**Admin Only** — List all API keys (paginated).

**Query Params:** `page=1`, `limit=25`, `consumer_id=uuid`, `status=active`

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "keys": [ ... ],
    "pagination": {
      "page": 1,
      "limit": 25,
      "total": 150,
      "pages": 6
    }
  },
  "meta": { ... },
  "error": null
}
```

## 4.3 Data Query Endpoints (Third-Party Facing)

### POST `/api/v1/query/{endpoint_slug}`
Execute a registered endpoint query (POST method endpoints).

**Headers:** `X-API-Key: apim_live_xxxx` or `Authorization: Bearer <jwt>`

**Request Body:** (varies per endpoint, validated against endpoint's `request_schema`)
```json
{
  "account_id": "100305",
  "start_date": "2026-01-01",
  "end_date": "2026-05-05"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "records": [ ... ],
    "count": 42,
    "target": "postgresql"
  },
  "meta": { ... },
  "error": null
}
```

---

### GET `/api/v1/query/{endpoint_slug}`
Execute a read query via GET parameters.

**Query Params:** Passed as query string, validated against endpoint's `request_schema`

**Response:** Same format as POST variant.

---

### POST `/api/v1/t24/enquiry/{enq_name}`
Run T24 OFS Enquiry via registered template name.

**Headers:** `X-API-Key: apim_live_xxxx`

**Request Body:**
```json
{
  "variables": {
    "ACCOUNT_NUMBER": "100305",
    "CUSTOMER_ID": "CUS123"
  }
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "enquiry": "CUSTOMER.ENQUIRY",
    "record": {
      "@ID": "100305",
      "NAME": ["John", "Doe"],
      "EMAIL": "john.doe@example.com"
    }
  },
  "meta": { ... },
  "error": null
}
```

---

### POST `/api/v1/t24/transaction`
Post T24 OFS Transaction via registered template.

**Headers:** `X-API-Key: apim_live_xxxx`

**Request Body:**
```json
{
  "application": "FUNDS.TRANSFER",
  "variables": {
    "DEBIT.ACCT": "1001",
    "CREDIT.ACCT": "1002",
    "AMOUNT": "500.00",
    "VALUE.DATE": "2026-05-05"
  }
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "transaction_id": "FT123456",
    "application": "FUNDS.TRANSFER",
    "status": "posted"
  },
  "meta": { ... },
  "error": null
}
```

**Error Response (400 Bad Request):**
```json
{
  "success": false,
  "data": null,
  "meta": { ... },
  "error": {
    "code": "APIM_T24_010",
    "message": "T24 transaction failed",
    "details": {
      "error_code": "TXN.ERR.001",
      "error_text": "Insufficient funds"
    }
  }
}
```

---

### GET `/api/v1/t24/status`
Check T24 TCServer connection health.

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "connected": true,
    "host": "tcserver.bank.internal",
    "port": 9089,
    "latency_ms": 45,
    "last_check": "2026-05-05T10:30:00Z"
  },
  "meta": { ... },
  "error": null
}
```

## 4.4 Admin Endpoints

### CRUD `/api/v1/admin/endpoints`
Manage API endpoint registry.

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/admin/endpoints` | List all endpoints (paginated) |
| GET | `/api/v1/admin/endpoints/{id}` | Get endpoint detail |
| POST | `/api/v1/admin/endpoints` | Create new endpoint |
| PUT | `/api/v1/admin/endpoints/{id}` | Update endpoint |
| DELETE | `/api/v1/admin/endpoints/{id}` | Deactivate endpoint |

**POST Request Body:**
```json
{
  "slug": "customer-by-id",
  "name": "Get Customer by ID",
  "description": "Retrieve customer details by account ID",
  "http_method": "POST",
  "path_pattern": "/query/customer-by-id",
  "data_source_id": "uuid",
  "query_template": "SELECT * FROM customers WHERE id = :account_id",
  "ofs_template_id": null,
  "request_schema": { "type": "object", "properties": { "account_id": { "type": "string" } } },
  "response_schema": { "type": "object", ... },
  "auth_required": true,
  "allowed_scopes": ["customer:read"],
  "cache_ttl_seconds": 60,
  "status": "active"
}
```

---

### CRUD `/api/v1/admin/datasources`
Manage database connection configurations.

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/admin/datasources` | List all data sources |
| GET | `/api/v1/admin/datasources/{id}` | Get data source detail |
| POST | `/api/v1/admin/datasources` | Create data source |
| PUT | `/api/v1/admin/datasources/{id}` | Update data source |
| DELETE | `/api/v1/admin/datasources/{id}` | Delete data source |
| POST | `/api/v1/admin/datasources/{id}/test` | Test connection |

**POST Request Body (PostgreSQL example):**
```json
{
  "name": "Production PostgreSQL",
  "db_type": "postgresql",
  "host": "pg.prod.internal",
  "port": 5432,
  "database_name": "banking_db",
  "username": "apim_user",
  "password": "encrypted-at-rest",
  "connection_options": { "ssl": true },
  "pool_min": 2,
  "pool_max": 20,
  "status": "active"
}
```

---

### CRUD `/api/v1/admin/consumers`
Manage API consumers.

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/admin/consumers` | List consumers |
| POST | `/api/v1/admin/consumers` | Create consumer |
| PUT | `/api/v1/admin/consumers/{id}` | Update consumer |
| DELETE | `/api/v1/admin/consumers/{id}` | Deactivate consumer |

---

### CRUD `/api/v1/admin/ofs-templates`
Manage T24 OFS message templates.

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/admin/ofs-templates` | List templates |
| POST | `/api/v1/admin/ofs-templates` | Create template |
| PUT | `/api/v1/admin/ofs-templates/{id}` | Update template |
| DELETE | `/api/v1/admin/ofs-templates/{id}` | Deactivate template |
| POST | `/api/v1/admin/ofs-templates/{id}/test` | Test OFS template |

**POST Request Body:**
```json
{
  "name": "Customer Enquiry",
  "description": "Retrieve customer details via T24 enquiry",
  "ofs_type": "enquiry",
  "application_name": "CUSTOMER",
  "ofs_message_template": "ENQ.CUSTOMER,CUSTOMER,READ/{{T24_USER}}/{{T24_PASS}},,@ID={{ACCOUNT_NUMBER}}",
  "variable_definitions": {
    "ACCOUNT_NUMBER": { "type": "string", "required": true }
  },
  "t24_version": "0",
  "status": "active"
}
```

---

### GET `/api/v1/admin/rate-limit-rules`
Get rate limit configuration.

**Response:**
```json
{
  "success": true,
  "data": {
    "defaults": {
      "per_hour": 1000,
      "per_minute": 100
    },
    "endpoint_overrides": [ ... ],
    "key_overrides": [ ... ]
  },
  "meta": { ... },
  "error": null
}
```

---

### PUT `/api/v1/admin/rate-limit-rules`
Update rate limit rules.

**Request Body:**
```json
{
  "defaults": { "per_hour": 2000, "per_minute": 200 },
  "endpoint_overrides": [
    { "endpoint_id": "uuid", "per_hour": 5000, "per_minute": 500 }
  ]
}
```

## 4.5 Monitoring & Analytics Endpoints

### GET `/api/v1/metrics/summary`
KPI summary for the last 24 hours.

**Response:**
```json
{
  "success": true,
  "data": {
    "total_requests_24h": 150000,
    "success_rate_pct": 99.2,
    "avg_latency_ms": 85,
    "p95_latency_ms": 210,
    "p99_latency_ms": 450,
    "active_api_keys": 45,
    "active_db_connections": 12,
    "error_count_24h": 1200
  },
  "meta": { ... },
  "error": null
}
```

---

### GET `/api/v1/metrics/requests`
Request time series data.

**Query Params:** `period=1h|24h|7d|30d`, `interval=minute|hour|day`

**Response:**
```json
{
  "success": true,
  "data": {
    "series": [
      { "timestamp": "2026-05-05T10:00:00Z", "total": 1200, "2xx": 1180, "4xx": 15, "5xx": 5 },
      ...
    ]
  },
  "meta": { ... },
  "error": null
}
```

---

### GET `/api/v1/metrics/errors`
Error rate and detail.

**Response:**
```json
{
  "success": true,
  "data": {
    "error_rate_pct": 0.8,
    "errors_by_code": [
      { "code": "APIM_DB_010", "count": 500, "pct": 41.7 },
      { "code": "APIM_T24_005", "count": 300, "pct": 25.0 }
    ],
    "recent_errors": [ ... ]
  },
  "meta": { ... },
  "error": null
}
```

---

### GET `/api/v1/metrics/latency`
Latency percentiles per endpoint.

**Response:**
```json
{
  "success": true,
  "data": {
    "overall": { "p50": 45, "p95": 210, "p99": 450 },
    "by_endpoint": [
      { "endpoint": "customer-by-id", "p50": 35, "p95": 180, "p99": 400 },
      ...
    ]
  },
  "meta": { ... },
  "error": null
}
```

---

### GET `/api/v1/metrics/consumers`
Usage metrics per consumer.

**Response:**
```json
{
  "success": true,
  "data": {
    "consumers": [
      { "consumer": "Mobile App", "requests_24h": 50000, "avg_latency_ms": 65, "error_rate_pct": 0.5 },
      ...
    ]
  },
  "meta": { ... },
  "error": null
}
```

---

### GET `/api/v1/audit-logs`
Paginated audit trail.

**Query Params:** `page=1`, `limit=50`, `start_date=`, `end_date=`, `admin_user_id=`, `action_type=`, `resource_type=`

**Response:**
```json
{
  "success": true,
  "data": {
    "logs": [
      {
        "id": "uuid",
        "admin_user": "admin@example.com",
        "action_type": "CREATE",
        "resource_type": "api_endpoint",
        "resource_id": "uuid",
        "old_value": null,
        "new_value": { "slug": "customer-by-id", ... },
        "ip_address": "10.0.0.1",
        "created_at": "2026-05-05T10:30:00Z"
      },
      ...
    ],
    "pagination": { "page": 1, "limit": 50, "total": 5000, "pages": 100 }
  },
  "meta": { ... },
  "error": null
}
```

---

### GET `/health`
Health check endpoint (no auth required).

**Response (200 OK):**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-05-05T10:30:00Z",
  "checks": {
    "management_db": "ok",
    "redis": "ok",
    "t24": "ok"
  }
}
```

---

### GET `/metrics`
Prometheus metrics scrape endpoint (no auth required).

**Response:** Plain text in Prometheus exposition format:
```
# HELP apim_requests_total Total API requests
# TYPE apim_requests_total counter
apim_requests_total{status="2xx",endpoint="customer-by-id"} 50000
...
# HELP apim_request_latency_seconds Request latency
# TYPE apim_request_latency_seconds histogram
apim_request_latency_seconds_bucket{le="0.1",endpoint="customer-by-id"} 45000
...
```

## 4.6 Request/Response Schemas (Pydantic v2)

```python
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime

# ----- Auth Schemas -----

class TokenRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class ApiKeyCreate(BaseModel):
    consumer_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    allowed_endpoints: Optional[List[UUID]] = None
    rate_limit_per_hour: int = Field(1000, ge=1, le=1000000)
    rate_limit_per_minute: int = Field(100, ge=1, le=10000)
    expires_at: Optional[datetime] = None

class ApiKeyResponse(BaseModel):
    id: UUID
    key_prefix: str
    consumer_id: UUID
    name: str
    rate_limit_per_hour: int
    rate_limit_per_minute: int
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    status: str
    created_at: datetime

# ----- Data Source Schemas (Discriminated Union) -----

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
    status: str = Field("active", pattern="^(active|inactive|error)$")

class MSSQLDataSource(DataSourseBase):
    db_type: str = Field("mssql", Literal="mssql")
    connection_options: Optional[Dict[str, Any]] = Field(
        default_factory=lambda: {"driver": "ODBC Driver 17 for SQL Server"}
    )

class OracleDataSource(DataSourseBase):
    db_type: str = Field("oracle", Literal="oracle")
    connection_options: Optional[Dict[str, Any]] = Field(
        default_factory=lambda: {"mode": "thin"}
    )

class PostgreSQLDataSource(DataSourseBase):
    db_type: str = Field("postgresql", Literal="postgresql")

class MySQLDataSource(DataSourseBase):
    db_type: str = Field("mysql", Literal="mysql")

class MongoDBDataSource(BaseModel):
    db_type: str = Field("mongodb", Literal="mongodb")
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
    db_type: str = Field("t24_tcserver", Literal="t24_tcserver")
    name: str
    host: str
    port: int = 9089
    username: str
    password: str
    connection_mode: str = Field("http", Literal["http", "tcp"])
    http_endpoint: str = "/BrowserWeb/servlet/BrowserServlet"
    timeout_seconds: int = 30
    max_retries: int = 3
    t24_version: str = "0"
    status: str = "active"

# Union type for data source creation
DataSourceCreate = MSSQLDataSource | OracleDataSource | PostgreSQLDataSource | MySQLDataSource | MongoDBDataSource | T24DataSource

# ----- Query Schemas -----

class QueryRequest(BaseModel):
    """Dynamic query request - validated against endpoint's request_schema at runtime"""
    pass  # Actual fields validated dynamically per endpoint

class QueryResponse(BaseModel):
    records: List[Dict[str, Any]]
    count: int
    target: str
    execution_time_ms: float

# ----- OFS Schemas -----

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

# ----- OFS Template Schemas -----

class OFSTemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    ofs_type: str = Field(..., Literal["enquiry", "transaction"])
    application_name: str = Field(..., min_length=1)
    ofs_message_template: str = Field(..., min_length=1)
    variable_definitions: Dict[str, Dict[str, Any]]
    t24_version: str = "0"
    status: str = Field("active", pattern="^(active|inactive)$")

# ----- Audit Log Schemas -----

class AuditLogEntry(BaseModel):
    id: UUID
    admin_user: str
    action_type: str
    resource_type: str
    resource_id: Optional[UUID]
    old_value: Optional[Dict[str, Any]]
    new_value: Optional[Dict[str, Any]]
    ip_address: str
    created_at: datetime

# ----- Endpoint Registration Schema -----

class EndpointRegistration(BaseModel):
    slug: str = Field(..., pattern=r'^[a-z0-9-]+$')
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    http_method: str = Field(..., Literal["GET", "POST", "PUT", "DELETE"])
    path_pattern: str = Field(..., min_length=1)
    data_source_id: UUID
    query_template: Optional[str] = None
    ofs_template_id: Optional[UUID] = None
    request_schema: Optional[Dict[str, Any]] = None
    response_schema: Optional[Dict[str, Any]] = None
    auth_required: bool = True
    allowed_scopes: Optional[List[str]] = None
    cache_ttl_seconds: int = Field(0, ge=0, le=86400)
    status: str = Field("active", pattern="^(active|inactive)$")
```

## 4.7 OFS Message Specification

### OFS Message Format
Temenos OFS (Open Financial Statement) messages follow this structure:
```
OPERATION,APPLICATION,OPERATION.TYPE/AUTHENTICATION,ID,RECORD.DATA
```

### Enquiry OFS Format
```
ENQ.{ENQUIRY.NAME},{APPLICATION},{VERSION}/{USER}/{PASSWORD},,{SELECTION.CRITERIA}
```

**Example:**
```
ENQ.CUSTOMER,CUSTOMER,0/USER1/PASS1,,@ID=100305
```

**Response (simplified):**
```
@ID=CUS123<@RECORD=NAME<FIRST<John<LAST<Doe;EMAIL<john@example.com;...
```

### Transaction OFS Format
```
{APPLICATION},{APPLICATION},{FUNCTION}/{USER}/{PASSWORD},,{FIELD1}={VALUE1},{FIELD2}={VALUE2}
```

**Example (FUNDS.TRANSFER):**
```
FUNDS.TRANSFER,FUNDS.TRANSFER,INPUT/USER1/PASS1,,DEBIT.ACCT=1001,CREDIT.ACCT=1002,AMOUNT=500.00,VALUE.DATE=20260505
```

### Response Parsing Logic
T24 OFS responses use T24 multi-value delimiters:
- Field separator: `;` (semicolon)
- Multi-value marker: `<` (less-than)
- Sub-value marker: `:` (colon)

**Parsing `@RECORD` field:**
```python
def parse_ofs_record(record_str: str) -> Dict[str, Any]:
    """Parse T24 MULTIVAL record string into nested dict."""
    fields = {}
    for field in record_str.split(';'):
        if '<' in field:
            name, values = field.split('<', 1)
            fields[name] = values.split('<')
        else:
            fields[field.split('=')[0]] = field.split('=')[1] if '=' in field else field
    return fields
```

### Template Variable Substitution
Templates use `{{VARIABLE_NAME}}` syntax for variable substitution:
```
ENQ.CUSTOMER,CUSTOMER,0/{{T24_USER}}/{{T24_PASS}},,@ID={{ACCOUNT_NUMBER}}
```

At runtime:
1. Template is loaded from `ofs_templates.ofs_message_template`
2. `{{T24_USER}}` and `{{T24_PASS}}` are replaced from data source config
3. `{{ACCOUNT_NUMBER}}` is replaced from request payload `variables`
4. Resulting OFS string is sent to TCServer

### Example OFS Messages

**CUSTOMER.ENQUIRY:**
```
ENQ.CUSTOMER,CUSTOMER,0/USER1/PASS1,,@ID=100305
```
Response:
```
@ID=100305<@RECORD=NAME<FIRST<John<LAST<Doe;EMAIL<john@example.com;PHONE<+1234567890
```

**FUNDS.TRANSFER Transaction:**
```
FUNDS.TRANSFER,FUNDS.TRANSFER,INPUT/USER1/PASS1,,DEBIT.ACCT=1001,CREDIT.ACCT=1002,AMOUNT=500.00,VALUE.DATE=20260505
```
Response (success):
```
@ID=FT123456<@RECORD=DEBIT.ACCT<1001;CREDIT.ACCT<1002;AMOUNT<500.00;STATUS<POSTED
```
Response (error):
```
@ERROR.CODE=TXN.ERR.001<@ERROR.TEXT=Insufficient funds
```

## 4.8 Rate Limiting Specification

### Default Limits
- **Per API Key**: 1000 requests/hour, 100 requests/minute
- **Per Endpoint**: Configurable override per endpoint
- **Global**: 10,000 requests/minute (DDoS protection)

### Rate Limit Headers Returned
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1714908600
```

### 429 Too Many Requests Response
```json
{
  "success": false,
  "data": null,
  "meta": { ... },
  "error": {
    "code": "APIM_RATELIMIT_001",
    "message": "Rate limit exceeded. Try again in 45 seconds.",
    "details": {
      "limit": 1000,
      "remaining": 0,
      "reset_at": 1714908600
    }
  }
}
```

### Rate Limit Storage
- **Primary**: Redis sorted sets for sliding window rate limiting
- **Fallback**: MySQL `rate_limit_counters` table (used if Redis unavailable)
- **Window Types**: `minute` (60-second sliding window), `hour` (3600-second sliding window)

## 4.9 Error Codes Reference

### Authentication Errors (`APIM_AUTH_*`)
| Code | HTTP Status | Description |
|---|---|---|
| APIM_AUTH_001 | 401 | Invalid API key |
| APIM_AUTH_002 | 401 | Invalid JWT token |
| APIM_AUTH_003 | 401 | Expired JWT token |
| APIM_AUTH_004 | 401 | Invalid credentials |
| APIM_AUTH_005 | 423 | Account locked |
| APIM_AUTH_006 | 403 | Invalid API key status (revoked/expired) |
| APIM_AUTH_007 | 403 | Insufficient scope |
| APIM_AUTH_008 | 403 | Invalid role for admin endpoint |
| APIM_AUTH_009 | 401 | Missing authentication |
| APIM_AUTH_010 | 401 | Refresh token invalid/expired |

### Database Errors (`APIM_DB_*`)
| Code | HTTP Status | Description |
|---|---|---|
| APIM_DB_001 | 500 | Database connection failed |
| APIM_DB_002 | 500 | Connection pool exhausted |
| APIM_DB_003 | 400 | Query template not found |
| APIM_DB_004 | 400 | Invalid query parameters |
| APIM_DB_005 | 500 | Query execution timeout |
| APIM_DB_006 | 400 | SQL syntax error |
| APIM_DB_007 | 500 | Database not found |
| APIM_DB_008 | 500 | Authentication failed for database |
| APIM_DB_009 | 500 | Connection reset by peer |
| APIM_DB_010 | 500 | Too many connections |
| APIM_DB_011 | 400 | Parameterized query missing params |
| APIM_DB_012 | 413 | Query result too large |
| APIM_DB_013 | 500 | Data source not found |
| APIM_DB_014 | 503 | Data source inactive |
| APIM_DB_015 | 500 | Connection health check failed |
| APIM_DB_016 | 500 | Unsupported database type |
| APIM_DB_017 | 500 | SSL/TLS connection error |
| APIM_DB_018 | 400 | Invalid data source configuration |
| APIM_DB_019 | 500 | Database driver not available |
| APIM_DB_020 | 500 | Transaction rollback failed |

### T24/OFS Errors (`APIM_T24_*`)
| Code | HTTP Status | Description |
|---|---|---|
| APIM_T24_001 | 500 | T24 TCServer connection failed |
| APIM_T24_002 | 500 | T24 connection timeout |
| APIM_T24_003 | 400 | OFS template not found |
| APIM_T24_004 | 400 | Invalid OFS message format |
| APIM_T24_005 | 400 | T24 enquiry failed |
| APIM_T24_006 | 400 | T24 transaction failed |
| APIM_T24_007 | 400 | Invalid OFS variable |
| APIM_T24_008 | 500 | T24 authentication failed |
| APIM_T24_009 | 500 | T24 response parse error |
| APIM_T24_010 | 400 | T24 application error (see details) |
| APIM_T24_011 | 500 | OFS message build error |
| APIM_T24_012 | 500 | T24 server internal error |
| APIM_T24_013 | 500 | T24 response timeout |
| APIM_T24_014 | 400 | Invalid enquiry name |
| APIM_T24_015 | 400 | Invalid transaction application |
| APIM_T24_016 | 500 | T24 connection pool exhausted |
| APIM_T24_017 | 500 | T24 circuit breaker open |
| APIM_T24_018 | 400 | OFS variable substitution failed |
| APIM_T24_019 | 500 | T24 HTTP mode error |
| APIM_T24_020 | 500 | T24 TCP mode error |

### Validation Errors (`APIM_VAL_*`)
| Code | HTTP Status | Description |
|---|---|---|
| APIM_VAL_001 | 400 | Request body validation failed |
| APIM_VAL_002 | 400 | Missing required field |
| APIM_VAL_003 | 400 | Invalid field type |
| APIM_VAL_004 | 400 | Field value out of range |
| APIM_VAL_005 | 400 | Invalid endpoint slug |
| APIM_VAL_006 | 400 | Invalid data source type |
| APIM_VAL_007 | 413 | Request payload too large |
| APIM_VAL_008 | 400 | Invalid OFS template variables |
| APIM_VAL_009 | 400 | Invalid JSON in request body |
| APIM_VAL_010 | 400 | Invalid query parameters |
