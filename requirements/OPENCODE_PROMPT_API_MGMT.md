# OpenCode Professional Prompt — Centralized API Management System
## Full-Stack: Python + MySQL | Multi-DB + Temenos T24 Integration

---

## MASTER PROMPT FOR OPENCODE

---

You are an expert full-stack software architect and developer. Your task is to build a **production-grade, Centralized API Management System** from scratch using **Python (FastAPI)** and **MySQL** as the core management database. The system must support multi-database server integration and Temenos T24 TCServer OFS messaging.

Before writing any code, generate the following **six Markdown documentation files** with complete, professional detail. After documentation is approved, scaffold and implement the full system.

---

## SYSTEM OVERVIEW

Build a **Centralized API Gateway & Management Platform** that:

- Acts as a **single entry point** for third-party application API requests
- Routes queries to target database backends: **MS SQL Server, Oracle, PostgreSQL, MySQL, MongoDB**
- Connects to **Temenos T24 TCServer** and executes **OFS messages** for enquiries and transactions
- Provides a **web-based dashboard** for API registration, monitoring, key management, and analytics
- Enforces **authentication, authorization, rate limiting, and audit logging** on all requests
- Is deployable via **Docker Compose** for development and **Kubernetes** for production

---

## DOCUMENTATION FILES TO GENERATE

---

### FILE 1: `docs/01_PRODUCT_REQUIREMENTS.md`

Write a complete Product Requirements Document (PRD) covering:

**1.1 Executive Summary**
- Product vision, mission, and value proposition
- Target users: enterprise IT teams, third-party integration developers, banking system integrators

**1.2 Stakeholder & User Personas**
- API Consumer (third-party developer)
- API Administrator (internal IT)
- Database Administrator (DBA)
- Temenos T24 Integration Specialist
- Security/Compliance Officer

**1.3 Functional Requirements (FR)**
List numbered FRs for each module:
- FR-AUTH: API Key generation, JWT authentication, OAuth2 support, role-based access control
- FR-GATEWAY: Request routing, protocol transformation, payload validation, response normalization
- FR-DB-MSSQL: Dynamic query execution on MS SQL Server using pyodbc
- FR-DB-ORACLE: Oracle DB integration using cx_Oracle with connection pooling
- FR-DB-POSTGRES: PostgreSQL integration using asyncpg
- FR-DB-MYSQL: MySQL integration using aiomysql
- FR-DB-MONGO: MongoDB integration using motor (async)
- FR-T24: OFS message builder, TCServer HTTP/socket connector, enquiry execution, transaction posting, response parser
- FR-ADMIN: API endpoint registration, consumer onboarding, key lifecycle management
- FR-MONITOR: Real-time request logging, error tracking, latency metrics, alert thresholds
- FR-RATELIMIT: Per-key and per-endpoint rate limiting using Redis
- FR-AUDIT: Immutable audit trail for all requests and admin actions

**1.4 Non-Functional Requirements (NFR)**
- Performance: P99 latency < 200ms for DB queries, < 500ms for T24 OFS
- Availability: 99.9% uptime SLA
- Security: TLS 1.3, AES-256 encryption at rest, OWASP API Security Top 10 compliance
- Scalability: Horizontal scaling, support 10,000 concurrent API consumers
- Observability: Structured JSON logging, Prometheus metrics, OpenTelemetry tracing

**1.5 Out of Scope**
- GraphQL support (Phase 2)
- Real-time WebSocket streaming (Phase 2)

**1.6 Acceptance Criteria**
Detailed testable acceptance criteria for each FR group

---

### FILE 2: `docs/02_SYSTEM_ARCHITECTURE.md`

Write a comprehensive System Architecture Document covering:

**2.1 Architecture Overview**
- Layered architecture: Client → API Gateway → Auth Layer → Routing Engine → DB Adapters / T24 Connector → Response Normalizer
- Deployment topology diagram (text-based ASCII and description)

**2.2 Component Architecture**

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

**2.3 Technology Stack**
| Layer | Technology | Justification |
|---|---|---|
| API Framework | FastAPI 0.111+ | Async, OpenAPI auto-docs, Pydantic v2 |
| ASGI Server | Uvicorn + Gunicorn | Production-grade async serving |
| Auth | python-jose, passlib | JWT/HMAC API key handling |
| Rate Limiting | Redis + slowapi | Distributed rate limiting |
| MS SQL | pyodbc + aioodbc | Async ODBC for MSSQL |
| Oracle | cx_Oracle / oracledb | Oracle official Python driver |
| PostgreSQL | asyncpg | Fastest async PG driver |
| MySQL (target) | aiomysql | Async MySQL queries |
| MongoDB | motor | Async MongoDB driver |
| T24 TCServer | httpx / socket | OFS over HTTP or raw TCP |
| Management DB | MySQL 8.0 | API registry, keys, audit logs |
| Cache | Redis 7 | Rate limiting, session cache |
| Dashboard | FastAPI + Jinja2 + AlpineJS + TailwindCSS | Lightweight admin UI |
| Containerization | Docker + Docker Compose | Dev/staging deployment |
| Orchestration | Kubernetes (Helm charts) | Production deployment |
| Monitoring | Prometheus + Grafana | Metrics and dashboards |
| Logging | structlog + ELK Stack | Structured audit logging |

**2.4 T24 TCServer Integration Architecture**
- OFS Message Structure: `OPERATION,APPID,OPERATION.TYPE/AUTH,ID,RECORD.DATA`
- Connection modes: HTTP POST to T24 Servlet, or raw TCP socket to OFS.SERVER
- Authentication: T24 user/password embedded in OFS header
- Enquiry execution: `ENQ.` prefix OFS messages, parse XML/delimited response
- Transaction posting: full OFS record format, parse success/error MULTIVAL
- Async connection pooling for TCServer sessions
- Retry policy: 3 retries with exponential backoff for network errors
- Response normalization: Parse T24 `@ID`, `@RECORD`, `@ERROR.CODE` fields to JSON

**2.5 Security Architecture**
- mTLS between services in production
- API Key: SHA-256 hashed storage, prefix-visible format `apim_live_xxxx`
- JWT: RS256 algorithm, 15-minute access tokens, 7-day refresh tokens
- All DB credentials stored in Vault / environment secrets, never in code
- Request payload size limit: 10MB default
- SQL injection prevention: parameterized queries only, ORM-level escaping
- Input sanitization for OFS messages: whitelist character validation

**2.6 Data Flow Diagrams**
- Standard DB Query Flow (step-by-step)
- T24 OFS Enquiry Flow (step-by-step)
- T24 OFS Transaction Posting Flow (step-by-step)
- Error handling and retry flow

**2.7 Integration Patterns**
- Adapter Pattern for each DB connector
- Factory Pattern for DB connection instantiation
- Circuit Breaker Pattern for T24 and DB connection failures
- Repository Pattern for management DB operations

---

### FILE 3: `docs/03_DASHBOARD_DESIGN.md`

Write a complete Dashboard Design Specification covering:

**3.1 Design Principles**
- Professional enterprise aesthetic: clean, data-dense, accessibility-first
- Color palette: Primary `#1E3A5F` (navy), Accent `#0EA5E9` (sky blue), Success `#10B981`, Warning `#F59E0B`, Danger `#EF4444`
- Typography: Inter for UI, JetBrains Mono for code/API keys
- Responsive: supports 1280px+ desktop and 768px tablet

**3.2 Dashboard Pages & Layout**

```
SIDEBAR NAVIGATION
├── 🏠 Overview (Main Dashboard)
├── 🔌 API Registry
│   ├── Endpoints
│   ├── Data Sources
│   └── OFS Message Templates
├── 🔑 API Keys & Consumers
│   ├── Keys Management
│   └── Consumer Groups
├── 📊 Analytics
│   ├── Traffic Overview
│   ├── Latency Analysis
│   └── Error Reports
├── 🗄️ Database Connections
│   ├── Connection Pool Status
│   └── Add / Edit Connections
├── 🏦 T24 / TCServer
│   ├── Connection Status
│   ├── OFS Templates
│   └── T24 Audit Log
├── 🔒 Security
│   ├── Rate Limit Rules
│   └── IP Allowlist / Blocklist
├── 📋 Audit Logs
└── ⚙️ Settings
```

**3.3 Page-by-Page Wireframe Descriptions**

For each page, describe:
- Layout grid (columns, panels)
- All UI components with data fields
- Interactive elements (filters, search, modals)
- Charts and their data sources
- Actions (buttons, forms)

Specifically detail:

**Overview Dashboard:**
- KPI cards: Total Requests (24h), Success Rate %, Avg Latency ms, Active API Keys, Active DB Connections
- Line chart: Request volume over time (1h/24h/7d selector)
- Bar chart: Requests by database target
- Table: Top 10 API consumers by request count
- Alert panel: Failed connections, rate limit violations

**API Registry:**
- Endpoint list table: Method, Path, Target DB/T24, Auth Required, Status
- Add Endpoint modal: fields for method, path, target data source, query template, response schema, auth level
- OFS Template editor: text area with OFS syntax highlighting, test runner panel

**API Keys & Consumers:**
- Key table: Key prefix, Consumer name, Permissions, Rate limit, Created, Last used, Status
- Create Key modal: Consumer name, allowed endpoints, rate limit override, expiry
- Key detail: usage stats, recent requests, revoke action

**Database Connections:**
- Connection cards per DB type with status badge (Connected/Error/Connecting)
- Connection form modal per DB type with appropriate fields
- Pool metrics: active connections, idle, max pool size

**T24 / TCServer:**
- Server connection status card: host, port, last ping, latency
- OFS Template list: Template name, OFS operation, type (ENQ/TXN), test button
- OFS test console: input fields, raw OFS message preview, execute button, raw + parsed response

**3.4 Component Library**
- StatusBadge: Connected / Disconnected / Degraded / Unknown
- DatabaseIcon: Per-DB SVG icons (MSSQL, Oracle, PG, MySQL, MongoDB, T24)
- MetricCard component spec
- OFSTemplateEditor component spec
- RequestTable with pagination, search, filter

**3.5 Color-Coded Indicators**
- DB Type color coding: MSSQL=blue, Oracle=red, PostgreSQL=teal, MySQL=orange, MongoDB=green, T24=gold
- Request status: 2xx=green, 4xx=amber, 5xx=red
- Latency tiers: <100ms=green, 100-500ms=amber, >500ms=red

---

### FILE 4: `docs/04_API_DEVELOPMENT_SPECS.md`

Write complete API Development Specifications covering:

**4.1 API Design Standards**
- RESTful conventions, versioning via URL prefix `/api/v1/`
- JSON:API-aligned response envelope:
```json
{
  "success": true,
  "data": { },
  "meta": { "request_id": "uuid", "timestamp": "ISO8601", "latency_ms": 42 },
  "error": null
}
```
- Error response format with `error.code`, `error.message`, `error.details`

**4.2 Authentication Endpoints**
```
POST   /api/v1/auth/token          — Get JWT from username/password
POST   /api/v1/auth/refresh        — Refresh JWT
POST   /api/v1/auth/api-keys       — Create API key (admin)
DELETE /api/v1/auth/api-keys/{id}  — Revoke API key
GET    /api/v1/auth/api-keys       — List all API keys
```

**4.3 Data Query Endpoints (Third-Party Facing)**
```
POST   /api/v1/query/{endpoint_slug}    — Execute registered endpoint query
GET    /api/v1/query/{endpoint_slug}    — Execute read query via GET params
POST   /api/v1/t24/enquiry/{enq_name}  — Run T24 OFS Enquiry
POST   /api/v1/t24/transaction         — Post T24 OFS Transaction
GET    /api/v1/t24/status              — T24 connection health
```

**4.4 Admin Endpoints**
```
CRUD   /api/v1/admin/endpoints          — Manage API endpoint registry
CRUD   /api/v1/admin/datasources        — Manage DB connection configs
CRUD   /api/v1/admin/consumers          — Manage API consumers
CRUD   /api/v1/admin/ofs-templates      — Manage T24 OFS templates
GET    /api/v1/admin/rate-limit-rules   — Rate limit configuration
PUT    /api/v1/admin/rate-limit-rules   — Update rate limit rules
```

**4.5 Monitoring & Analytics Endpoints**
```
GET    /api/v1/metrics/summary          — KPI summary (24h)
GET    /api/v1/metrics/requests         — Request time series
GET    /api/v1/metrics/errors           — Error rate and detail
GET    /api/v1/metrics/latency          — Latency percentiles per endpoint
GET    /api/v1/metrics/consumers        — Usage per consumer
GET    /api/v1/audit-logs               — Paginated audit log
GET    /health                          — Health check
GET    /metrics                         — Prometheus metrics scrape
```

**4.6 Request/Response Schemas**
Provide complete Pydantic v2 model definitions for:
- `EndpointRegistration`
- `DataSourceConfig` (with discriminated union per DB type)
- `QueryRequest` and `QueryResponse`
- `OFSEnquiryRequest` and `OFSEnquiryResponse`
- `OFSTransactionRequest` and `OFSTransactionResponse`
- `ApiKeyCreate` and `ApiKeyResponse`
- `AuditLogEntry`

**4.7 OFS Message Specification**
- Detailed OFS format for enquiry: `ENQ.{ENQUIRY.NAME},{VERSION}/{USER}/{PASSWORD},,{SELECTION.CRITERIA}`
- Detailed OFS format for transaction: `{APPLICATION},{VERSION},{FUNCTION}/{USER}/{PASSWORD},,{FIELD1}={VALUE1},{FIELD2}={VALUE2}...`
- Response parsing logic: handle `@ID`, `@RECORD`, `@ERROR.CODE`, `@ERROR.TEXT` fields
- Template variable substitution: `{{ACCOUNT_NUMBER}}` replaced from request payload
- Example: FUNDS.TRANSFER OFS message, CUSTOMER.ENQUIRY OFS message

**4.8 Rate Limiting Specification**
- Default limits: 1000 req/hour per API key, 100 req/minute per endpoint
- Headers returned: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
- 429 response format

**4.9 Error Codes Reference**
Complete table of internal error codes:
- `APIM_AUTH_001` through `APIM_AUTH_010` (auth errors)
- `APIM_DB_001` through `APIM_DB_020` (database errors)
- `APIM_T24_001` through `APIM_T24_020` (T24/OFS errors)
- `APIM_VAL_001` through `APIM_VAL_010` (validation errors)

---

### FILE 5: `docs/05_DATABASE_SCHEMA.md`

Write the complete MySQL database schema for the API Management System covering:

**5.1 Schema Overview**
Database name: `apim_db`
All tables use InnoDB engine, utf8mb4 charset, with created_at/updated_at timestamps.

**5.2 Complete DDL — All Tables**

Provide complete `CREATE TABLE` statements with all columns, data types, constraints, indexes, and foreign keys for:

**`consumers`** — API consumer organizations
- id, uuid, name, description, email, status, created_at, updated_at

**`api_keys`** — API keys issued to consumers
- id, uuid, consumer_id (FK), key_prefix (visible 8-char), key_hash (SHA-256), name, scopes (JSON), rate_limit_per_hour, rate_limit_per_minute, expires_at, last_used_at, status, created_at, revoked_at

**`admin_users`** — Dashboard admin accounts
- id, uuid, username, email, password_hash, role (ENUM: superadmin, admin, viewer), last_login_at, status, created_at

**`data_sources`** — DB connection configurations
- id, uuid, name, db_type (ENUM: mssql, oracle, postgresql, mysql, mongodb, t24_tcserver), host, port, database_name, username, password_encrypted, connection_options (JSON), pool_min, pool_max, status, created_at, updated_at

**`api_endpoints`** — Registered API endpoints
- id, uuid, slug, name, description, http_method, path_pattern, data_source_id (FK), query_template (TEXT), ofs_template_id (FK nullable), request_schema (JSON), response_schema (JSON), auth_required (BOOL), allowed_scopes (JSON), cache_ttl_seconds, status, created_at, updated_at

**`ofs_templates`** — T24 OFS message templates
- id, uuid, name, description, ofs_type (ENUM: enquiry, transaction), application_name, ofs_message_template (TEXT), variable_definitions (JSON), t24_version, status, created_at, updated_at

**`request_logs`** — All API request audit records (partitioned by month)
- id, request_id (UUID), api_key_id (FK nullable), consumer_id (FK nullable), endpoint_id (FK), http_method, path, query_params (JSON), request_body_hash, target_db_type, target_data_source_id, response_status_code, response_time_ms, error_code, error_message, client_ip, user_agent, created_at

**`rate_limit_counters`** — Redis-backed, but MySQL fallback tracking
- id, api_key_id, window_start, window_type (minute/hour), request_count, created_at

**`audit_trail`** — Admin action audit log
- id, uuid, admin_user_id (FK), action_type, resource_type, resource_id, old_value (JSON), new_value (JSON), ip_address, created_at

**`db_connection_health`** — Connection health check log
- id, data_source_id (FK), check_timestamp, status, latency_ms, error_message

**`consumer_endpoint_permissions`** — Explicit permission grants
- id, consumer_id (FK), endpoint_id (FK), granted_at, granted_by (FK admin_users)

**5.3 Indexes**
List all non-PK indexes with justification for query patterns they support.

**5.4 Partitioning Strategy**
- `request_logs` partitioned by RANGE on YEAR/MONTH of created_at
- Retention policy: keep 13 months, archive to cold storage

**5.5 Views**
- `v_active_api_keys` — Join consumers + api_keys where status = active
- `v_endpoint_stats_24h` — Request counts, avg latency, error rate per endpoint
- `v_consumer_usage_summary` — Aggregated usage per consumer

**5.6 Stored Procedures**
- `sp_rotate_api_key(old_key_id, grace_period_hours)` — Key rotation with overlap period
- `sp_purge_old_logs(retention_months)` — Automated log archival

**5.7 Sample Seed Data**
INSERT statements for:
- 1 superadmin user
- 3 sample consumers
- One each of MSSQL, Oracle, PostgreSQL, MySQL, MongoDB, T24 data sources
- 5 sample endpoints
- 2 sample OFS templates (CUSTOMER.ENQUIRY and FUNDS.TRANSFER)

---

### FILE 6: `docs/06_DEPLOYMENT.md`

Write a complete Deployment Guide covering:

**6.1 Prerequisites**
- OS: Ubuntu 22.04 LTS (server), Docker Desktop (dev)
- Software: Docker 24+, Docker Compose v2, Python 3.11+, MySQL 8.0+, Redis 7+
- For T24: OFS Server hostname, port, T24 user credentials, OFS message version

**6.2 Repository Structure**
```
apim/
├── docs/                    # All MD documentation files
├── app/
│   ├── main.py              # FastAPI app entry point
│   ├── core/
│   │   ├── config.py        # Settings via pydantic-settings
│   │   ├── security.py      # JWT, API key hashing
│   │   └── dependencies.py  # FastAPI dependency injection
│   ├── api/
│   │   ├── v1/
│   │   │   ├── auth.py
│   │   │   ├── query.py
│   │   │   ├── t24.py
│   │   │   ├── admin/
│   │   │   └── metrics.py
│   ├── adapters/
│   │   ├── base.py          # Abstract DB adapter
│   │   ├── mssql.py
│   │   ├── oracle.py
│   │   ├── postgresql.py
│   │   ├── mysql.py
│   │   ├── mongodb.py
│   │   └── t24/
│   │       ├── connector.py  # TCServer HTTP/TCP connector
│   │       ├── ofs_builder.py
│   │       └── ofs_parser.py
│   ├── models/
│   │   ├── db/              # SQLAlchemy ORM models
│   │   └── schemas/         # Pydantic request/response schemas
│   ├── services/
│   │   ├── routing.py       # Routing engine
│   │   ├── rate_limiter.py
│   │   ├── audit.py
│   │   └── metrics.py
│   ├── dashboard/
│   │   ├── templates/       # Jinja2 HTML templates
│   │   └── static/          # CSS, JS assets
│   └── tests/
│       ├── unit/
│       ├── integration/
│       └── conftest.py
├── migrations/
│   └── alembic/
├── infrastructure/
│   ├── docker/
│   │   ├── Dockerfile
│   │   └── Dockerfile.dev
│   ├── docker-compose.yml
│   ├── docker-compose.dev.yml
│   └── kubernetes/
│       ├── namespace.yaml
│       ├── deployment.yaml
│       ├── service.yaml
│       ├── ingress.yaml
│       ├── configmap.yaml
│       ├── secret.yaml
│       └── hpa.yaml
├── .env.example
├── requirements.txt
├── pyproject.toml
└── README.md
```

**6.3 Environment Variables**
Complete `.env.example` with all variables:
```env
# Application
APP_ENV=development
APP_HOST=0.0.0.0
APP_PORT=8000
SECRET_KEY=<generate-256-bit>
JWT_ALGORITHM=RS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Management MySQL Database
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=apim_db
MYSQL_USER=apim_user
MYSQL_PASSWORD=<strong-password>
MYSQL_POOL_SIZE=20
MYSQL_MAX_OVERFLOW=10

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=<redis-password>
REDIS_DB=0

# Encryption (for stored DB credentials)
ENCRYPTION_KEY=<32-byte-fernet-key>

# T24 TCServer
T24_HOST=tcserver.bank.internal
T24_PORT=9089
T24_USERNAME=XXXXXX
T24_PASSWORD=XXXXXX
T24_OFS_VERSION=0
T24_CONNECTION_MODE=http  # http or tcp
T24_HTTP_ENDPOINT=/BrowserWeb/servlet/BrowserServlet
T24_TIMEOUT_SECONDS=30
T24_MAX_RETRIES=3

# Monitoring
PROMETHEUS_ENABLED=true
LOG_LEVEL=INFO
LOG_FORMAT=json

# Rate Limiting Defaults
DEFAULT_RATE_LIMIT_PER_HOUR=1000
DEFAULT_RATE_LIMIT_PER_MINUTE=100
```

**6.4 Docker Compose Configuration**
Complete `docker-compose.yml` for:
- `apim-app`: FastAPI application (multiple replicas)
- `apim-db`: MySQL 8.0 with init scripts
- `apim-redis`: Redis 7 with persistence
- `apim-nginx`: Nginx reverse proxy with TLS termination
- `apim-prometheus`: Prometheus metrics
- `apim-grafana`: Grafana dashboards

**6.5 Development Setup (Step-by-Step)**
1. Clone repository and create virtual environment
2. Install dependencies: `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and configure
4. Run `docker-compose -f docker-compose.dev.yml up -d` for MySQL and Redis
5. Run database migrations: `alembic upgrade head`
6. Seed initial data: `python -m app.scripts.seed_db`
7. Start development server: `uvicorn app.main:app --reload --port 8000`
8. Access dashboard at `http://localhost:8000/dashboard`
9. Access API docs at `http://localhost:8000/docs`

**6.6 Production Deployment**
- Full Docker Compose production deployment steps
- Kubernetes deployment with Helm chart values
- TLS certificate setup with Let's Encrypt / cert-manager
- Database backup strategy (mysqldump + binlog)
- Redis sentinel configuration for HA

**6.7 Kubernetes Manifests**
Complete YAML for all Kubernetes resources listed in directory structure above, including:
- HorizontalPodAutoscaler: min 2, max 10 replicas, CPU target 70%
- Resource requests/limits per container
- Liveness and readiness probes
- ConfigMap for non-secret configuration
- ExternalSecret or Sealed Secret for credentials

**6.8 CI/CD Pipeline**
GitHub Actions workflow covering:
- Lint: ruff + mypy
- Test: pytest with coverage ≥ 80%
- Security scan: bandit + safety
- Build and push Docker image
- Deploy to staging on merge to `develop`
- Deploy to production on release tag

**6.9 Monitoring Setup**
- Prometheus scrape config for the app
- Pre-built Grafana dashboard JSON for APIM metrics
- Alert rules: error rate > 5%, latency P99 > 1s, DB pool exhaustion

**6.10 T24 TCServer Connection Testing**
Step-by-step guide to test OFS connectivity:
```bash
# Test OFS enquiry via CLI
python -m app.scripts.test_t24 \
  --host $T24_HOST \
  --port $T24_PORT \
  --user $T24_USERNAME \
  --password $T24_PASSWORD \
  --ofs "ENQUIRY,CUSTOMER,READ/TESTUSER/TESTPASS,,@ID=100305"
```

---

## CODE IMPLEMENTATION INSTRUCTIONS

After generating all six documentation files, implement the full system following these rules:

### Implementation Rules
1. **All DB queries must use parameterized statements** — never f-string SQL
2. **All DB passwords encrypted with Fernet** before storing in MySQL
3. **Async-first**: use `async/await` throughout; no blocking I/O on event loop
4. **Connection pooling** for all DB adapters with configurable min/max
5. **Circuit breaker** (tenacity library) on all external connections (DB + T24)
6. **Structured logging** with structlog: include request_id, consumer_id, endpoint on every log line
7. **Type annotations** on all functions; mypy strict mode
8. **Pydantic v2** for all schemas; validate on input, never trust raw request data
9. **OFS messages** must be built through the template engine, never concatenated directly
10. **All admin endpoints** require JWT with admin role; all query endpoints accept API key or JWT

### Adapter Implementation Pattern
Each DB adapter must implement this abstract base:
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

### T24 Connector Implementation
Implement both HTTP and TCP modes:
- **HTTP mode**: POST OFS string to T24 BrowserServlet, parse HTTP response body
- **TCP mode**: Raw socket connection to OFS.SERVER port, send OFS + newline, read until EOF
- Auto-detect T24 response errors by checking `@ERROR.CODE` field
- Parse MULTIVAL character `<` and field separator `;` per T24 spec

### Dashboard Implementation
- Use **FastAPI + Jinja2** for server-rendered dashboard pages
- **AlpineJS** for reactive UI without a build step
- **TailwindCSS CDN** for styling
- **Chart.js** for metrics charts
- Dark mode support via CSS class toggle
- Real-time updates via Server-Sent Events (SSE) for live request feed

---

## DELIVERABLES CHECKLIST

When complete, confirm:
- [ ] `docs/01_PRODUCT_REQUIREMENTS.md` — Full PRD with all FRs, NFRs, acceptance criteria
- [ ] `docs/02_SYSTEM_ARCHITECTURE.md` — Architecture diagrams, tech stack, data flows
- [ ] `docs/03_DASHBOARD_DESIGN.md` — Full design spec with wireframe descriptions
- [ ] `docs/04_API_DEVELOPMENT_SPECS.md` — All endpoints, schemas, OFS spec, error codes
- [ ] `docs/05_DATABASE_SCHEMA.md` — All DDL, indexes, views, stored procedures, seed data
- [ ] `docs/06_DEPLOYMENT.md` — Full deployment guide with Docker, Kubernetes, CI/CD
- [ ] Full Python/FastAPI application code with all adapters implemented
- [ ] MySQL migration scripts via Alembic
- [ ] Dashboard UI (Jinja2 templates + Alpine.js)
- [ ] Unit and integration tests with >80% coverage
- [ ] Docker Compose files (dev + production)
- [ ] Kubernetes manifests
- [ ] `.env.example` with all configuration variables
- [ ] `README.md` with quick-start guide

---

*Generated by: OpenCode Professional Prompt — APIM System v1.0*
*Stack: Python 3.11 · FastAPI · MySQL 8.0 · Redis 7 · Docker · Kubernetes*
*Integrations: MSSQL · Oracle · PostgreSQL · MySQL · MongoDB · Temenos T24 TCServer*
