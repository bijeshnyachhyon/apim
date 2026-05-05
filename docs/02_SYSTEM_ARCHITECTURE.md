# 02 System Architecture Document

## 2.1 Architecture Overview
The Centralized API Management System (APIM) follows a layered, modular architecture designed for scalability, security, and observability. All external requests flow through a single entry point, traverse authentication and validation layers, get routed to appropriate backend adapters, and return normalized responses.

### Layered Architecture
```
Client Applications
        │
        ▼
┌───────────────────────────────────┐
│      API Gateway Layer (FastAPI)   │  ← HTTPS REST/JSON
│  ┌─────────┐ ┌─────────────────┐ │
│  │  Auth   │ │  Rate Limiter   │ │
│  │  Layer  │ │  (Redis)        │ │
│  └─────────┘ └─────────────────┘ │
│  ┌─────────────────────────────┐  │
│  │  Request Validator          │  │  ← Pydantic Schemas
│  └─────────────────────────────┘  │
└───────────────┬───────────────────┘
                │
                ▼
┌───────────────────────────────────┐
│      Routing Engine               │  ← Endpoint Registry Lookup
│  (MySQL: api_endpoints table)    │
└──────┬─────┬─────┬─────┬─────────┘
       │     │     │     │
       ▼     ▼     ▼     ▼
┌─────────────────────────────────────────────────────────────┐
│                Backend Adapters                             │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────────────┐  │
│  │MSSQL │ │Oracle│ │ PG   │ │MySQL │ │ T24 TCServer │  │
│  │Adapt.│ │Adapt.│ │Adapt.│ │Adapt.│ │ OFS Connector│  │
│  └──────┘ └──────┘ └──────┘ └──────┘ └──────────────┘  │
└─────────────────────────────────────────────────────────────┘
                │
                ▼
┌───────────────────────────────────┐
│  Response Normalizer / Serializer │  ← Standardized JSON Envelope
└───────────────────────────────────┘
                │
                ▼
        Client Applications
```

### Deployment Topology
```
                      ┌─────────────────────┐
                      │   Load Balancer     │
                      │   (Nginx / ALB)     │
                      └──────────┬──────────┘
                                 │
                ┌────────────────┼────────────────┐
                │                │                │
         ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
         │  APIM Worker│ │  APIM Worker│ │  APIM Worker│  ← FastAPI + Uvicorn
         │  (Pod 1)    │ │  (Pod 2)    │ │  (Pod N)    │
         └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
                │                │                │
                └────────────────┼────────────────┘
                                 │
                ┌────────────────┼────────────────┐
                │                │                │
         ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
         │  MySQL      │ │   Redis     │ │  Monitoring  │
         │  (apim_db)  │ │  (Rate Lim.)│ │ Prometheus/  │
         │              │ │             │ │  Grafana      │
         └─────────────┘ └─────────────┘ └──────────────┘
                │
                └──────────────┬──────────────────┐
                               │                  │
                        ┌──────▼──────┐    ┌──────▼──────┐
                        │  Backend    │    │  T24        │
                        │  Databases  │    │  TCServer   │
                        │  (MSSQL,    │    │  (HTTP/TCP) │
                        │  Oracle,   │    └─────────────┘
                        │  PG, MySQL,│
                        │  MongoDB)  │
                        └─────────────┘
```

## 2.2 Component Architecture
```
┌─────────────────────────────────────────────────────────────────────┐
│                     THIRD-PARTY APPLICATIONS                        │
│          (Web Apps / Mobile / ERP / Core Banking Systems)           │
└───────────────────────────┬─────────────────────────────────────────┘
                            │ HTTPS REST API
┌───────────────────────────▼─────────────────────────────────────────┐
│                    API GATEWAY LAYER (FastAPI)                      │
│   ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐   │
│   │  Auth Module │  │ Rate Limiter │  │  Request Validator     │   │
│   │ (JWT/API Key)│  │   (Redis)    │  │  (Pydantic Schemas)    │   │
│   └──────────────┘  └──────────────┘  └────────────────────────┘   │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────────┐
│                     ROUTING ENGINE                                  │
│         (Determines target DB or T24 from API registry)             │
└──────┬──────────┬──────────┬──────────┬──────────┬──────────────────┘
       │          │          │          │          │
   ┌───▼──┐  ┌───▼──┐  ┌───▼──┐  ┌───▼──┐  ┌────▼───────────────┐
   │MSSQL │  │Oracle│  │ PG   │  │MySQL │  │  T24 TCServer      │
   │Adapt.│  │Adapt.│  │Adapt.│  │Adapt.│  │  OFS Connector     │
   └──────┘  └──────┘  └──────┘  └──────┘  └────────────────────┘
       │          │          │          │          │
   ┌───▼──────────▼──────────▼──────────▼──────────▼──────────────┐
   │              RESPONSE NORMALIZER / SERIALIZER                 │
   └───────────────────────────────────────────────────────────────┘
```

## 2.3 Technology Stack
| Layer | Technology | Justification |
|---|---|---|
| API Framework | FastAPI 0.111+ | Async, OpenAPI auto-docs, Pydantic v2 |
| ASGI Server | Uvicorn + Gunicorn | Production-grade async serving |
| Auth | python-jose, passlib | JWT/HMAC API key handling |
| Rate Limiting | Redis + slowapi | Distributed rate limiting |
| MS SQL | pyodbc + aioodbc | Async ODBC for MSSQL |
| Oracle | oracledb | Oracle official Python driver |
| PostgreSQL | asyncpg | Fastest async PG driver |
| MySQL (target) | aiomysql | Async MySQL queries |
| MySQL (management) | aiomysql + SQLAlchemy | ORM for management DB |
| MongoDB | motor | Async MongoDB driver |
| T24 TCServer | httpx / raw socket | OFS over HTTP or TCP |
| Management DB | MySQL 8.0 | API registry, keys, audit logs |
| Cache | Redis 7 | Rate limiting, session cache |
| Dashboard | FastAPI + Jinja2 + AlpineJS + TailwindCSS | Lightweight admin UI |
| Containerization | Docker + Docker Compose | Dev/staging deployment |
| Orchestration | Kubernetes (Helm charts) | Production deployment |
| Monitoring | Prometheus + Grafana | Metrics and dashboards |
| Logging | structlog + ELK Stack | Structured audit logging |
| Migrations | Alembic | Database schema versioning |
| Config | pydantic-settings | Type-safe environment config |

## 2.4 T24 TCServer Integration Architecture
### OFS Message Structure
```
OPERATION,APPID,OPERATION.TYPE/AUTH,ID,RECORD.DATA
```

Examples:
- **Enquiry**: `ENQ.CUSTOMER,CUSTOMER,READ/USER/PASS,,@ID=100305`
- **Transaction**: `FUNDS.TRANSFER,FUNDS.TRANSFER,INPUT/USER/PASS,,@ID=FT123456,DEBIT.ACCT=1001,CREDIT.ACCT=1002,AMOUNT=500`

### Connection Modes
1. **HTTP POST to T24 BrowserServlet**
   - Endpoint: `http://tcserver:port/BrowserWeb/servlet/BrowserServlet`
   - POST body: `OFS=ENQ...&USER=xxx&PASSWORD=yyy`
   - Response: HTML-wrapped OFS response, parse `<pre>` or XML

2. **Raw TCP Socket to OFS.SERVER**
   - Connect to `tcserver:port` (typically 9089)
   - Send OFS string + newline character
   - Read response until EOF or timeout
   - Response: Raw OFS multi-value string

### Authentication
- T24 user/password embedded in OFS header: `OPERATION.TYPE/USER/PASSWORD`
- Credentials stored encrypted in `data_sources` table
- Connection pooling with session reuse for performance

### Enquiry Execution Flow
1. Lookup OFS template from `ofs_templates` table
2. Substitute variables from request payload into template
3. Prepend authentication header to OFS message
4. Send via HTTP or TCP connector
5. Parse response: extract `@ID`, `@RECORD`, `@ERROR.CODE` fields
6. Normalize to JSON: `{ "id": "...", "record": {...}, "error": null }`

### Transaction Posting Flow
1. Validate request against `OFSTransactionRequest` schema
2. Build OFS message from template with transaction data
3. Send to TCServer via configured mode
4. Parse MULTIVAL response for success/error
5. On success: return `@ID` of created record
6. On error: return `@ERROR.CODE` and `@ERROR.TEXT` with 400 status

### Response Parsing
T24 OFS responses use multi-value delimiters:
- Field separator: `;`
- Value marker: `<` (for multi-values)
- Example: `@ID=CUS123;@RECORD=NAME<FIRST<John<LAST<Doe;...`

Parsing logic converts to JSON:
```json
{
  "@ID": "CUS123",
  "@RECORD": {
    "NAME": ["John", "Doe"],
    ...
  }
}
```

### Retry Policy
- 3 retries for network errors (connection timeout, reset)
- Exponential backoff: 1s, 2s, 4s delays
- No retry for T24 application errors (e.g., invalid OFS, auth failure)

## 2.5 Security Architecture
### Transport Security
- TLS 1.3 for all external client connections (HTTPS)
- mTLS between services in Kubernetes production deployment
- Certificate management via cert-manager / Let's Encrypt

### API Key Security
- SHA-256 hash stored in `api_keys.key_hash` (never plaintext)
- Prefix-visible format: `apim_live_xxxx` (8-char prefix stored, full key shown only at creation)
- Rate limiting per key with configurable overrides
- Keys can be revoked instantly (status → `revoked`)

### JWT Security
- RS256 algorithm with RSA key pair (private key for signing, public key for verification)
- Access token expiry: 15 minutes
- Refresh token expiry: 7 days
- Token payload: `sub` (user ID), `role`, `scopes`, `exp`, `iat`

### Credential Storage
- All DB/T24 credentials encrypted with Fernet (AES-256) before storing in MySQL
- Encryption key stored in environment variable (or Vault in production)
- No credentials in code, logs, or error messages

### Input Validation
- All request payloads validated with Pydantic v2 schemas
- SQL injection prevention: parameterized queries only, no f-string SQL
- OFS message whitelist validation: only allowed characters in variable substitutions
- Request payload size limit: 10MB (configurable)

### OWASP API Top 10 Compliance
| Threat | Mitigation |
|---|---|
| API1:2023 Broken Auth | JWT RS256, API key hashing, rate limiting |
| API2:2023 Auth Fail | RBAC enforcement on all admin endpoints |
| API3:2023 Broken Object Calc | Parameterized queries, input validation |
| API4:2023 Unrestricted Resource | Rate limiting, payload size limits |
| API5:2023 Broken Func Level Auth | Separate admin/consumer auth flows |
| API6:2023 Unrestricted Access | CORS configured, IP allowlists |
| API7:2023 Server-Side Req Forgery | No user-supplied URL fetching |
| API8:2023 Security Misconfig | Secure defaults, no debug in prod |
| API9:2023 Improper Inventory | Endpoint registry, API docs on /docs |
| API10:2023 Unsafe Consumption | Timeout on all external calls, circuit breaker |

## 2.6 Data Flow Diagrams
### Standard DB Query Flow
1. Client sends POST to `/api/v1/query/{endpoint_slug}` with API key/JWT
2. Auth middleware validates key/token, extracts `consumer_id`
3. Rate limiter checks quota in Redis; returns 429 if exceeded
4. Request validator validates payload against endpoint's `request_schema`
5. Routing engine looks up endpoint in `api_endpoints` by `slug`
6. Routing engine fetches data source config from `data_sources` by `data_source_id`
7. Appropriate DB adapter (MSSQL/Oracle/PG/MySQL/MongoDB) is instantiated
8. Query template variables are substituted from request payload
9. Parameterized query is executed on target database
10. Response normalizer converts DB result to standardized JSON envelope
11. Request log is written to `request_logs` table
12. Response is returned to client (200 OK)

### T24 OFS Enquiry Flow
1. Client sends POST to `/api/v1/t24/enquiry/{enq_name}` with API key
2. Auth middleware validates key, checks scope for T24 enquiry
3. OFS template is fetched from `ofs_templates` (type=`enquiry`)
4. Variables from request payload are substituted into OFS template
5. T24 connector (HTTP or TCP) sends OFS message to TCServer
6. Response is parsed: extract `@RECORD` fields from MULTIVAL string
7. Normalized JSON response is returned: `{ "enquiry": "...", "data": {...} }`
8. Request log is written with `target_db_type = t24_tcserver`

### T24 OFS Transaction Posting Flow
1. Client sends POST to `/api/v1/t24/transaction` with API key + transaction payload
2. Auth middleware validates key, checks scope for T24 transaction
3. OFS template is fetched (type=`transaction`) based on `application_name`
4. Transaction fields are validated against `OFSTransactionRequest` schema
5. OFS message is built: `APP,APP,INPUT/USER/PASS,,FIELD1=VAL1,...`
6. T24 connector sends message, parses response for `@ERROR.CODE`
7. On success: return `{ "success": true, "transaction_id": "@ID" }`
8. On error: return 400 with `{ "error": { "code": "APIM_T24_010", "message": "@ERROR.TEXT" } }`
9. Audit log entry written for transaction posting

### Error Handling & Retry Flow
1. Adapter catches exception (DB/T24 connection error)
2. Circuit breaker (tenacity) checks if retry is allowed
3. If retryable error (network timeout, connection reset):
   - Wait with exponential backoff (1s, 2s, 4s)
   - Retry up to 3 times
4. If non-retryable (SQL syntax error, T24 auth failure):
   - Return error immediately with appropriate status code
5. All errors logged to `request_logs` with `error_code` and `error_message`
6. If all retries exhausted, return 503 Service Unavailable

## 2.7 Integration Patterns
### Adapter Pattern (DB Connectors)
Each database adapter implements `BaseAdapter` abstract class:
```python
class BaseAdapter(ABC):
    @abstractmethod
    async def connect(self) -> None: ...

    @abstractmethod
    async def disconnect(self) -> None: ...

    @abstractmethod
    async def execute_query(self, query: str, params: dict) -> QueryResult: ...

    @abstractmethod
    async def health_check(self) -> HealthStatus: ...
```
Concrete adapters: `MSSQLAdapter`, `OracleAdapter`, `PostgreSQLAdapter`, `MySQLAdapter`, `MongoDBAdapter`

### Factory Pattern (Connection Instantiation)
```python
class AdapterFactory:
    @staticmethod
    def create_adapter(db_type: str, config: DataSourceConfig) -> BaseAdapter:
        if db_type == "mssql":
            return MSSQLAdapter(config)
        elif db_type == "oracle":
            return OracleAdapter(config)
        # ... etc.
```

### Circuit Breaker Pattern (T24 & DB Failures)
Using `tenacity` library for retry with circuit breaking:
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((ConnectionError, TimeoutError)),
    before_sleep=before_sleep_log(logger, logging.WARNING)
)
async def execute_with_retry(adapter, query, params):
    return await adapter.execute_query(query, params)
```

### Repository Pattern (Management DB Operations)
```python
class EndpointRepository:
    async def get_by_slug(self, slug: str) -> ApiEndpoint: ...
    async def list_all(self) -> List[ApiEndpoint]: ...
    async def create(self, data: EndpointCreate) -> ApiEndpoint: ...
```

### Singleton Pattern (Connection Pools)
Each adapter maintains a singleton connection pool per data source configuration, shared across requests to the same backend.
