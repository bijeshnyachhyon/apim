# 01 Product Requirements Document (PRD)

## 1.1 Executive Summary
### Product Vision
Provide a unified, secure, and observable entry point for enterprise third-party applications to access disparate data sources (MS SQL Server, Oracle, PostgreSQL, MySQL, MongoDB) and Temenos T24 core banking systems via standardized REST APIs.

### Mission
Simplify integration complexity, enforce security and compliance, and provide centralized management, monitoring, and analytics for all API-driven data access across the organization.

### Value Proposition
- Eliminates point-to-point integration between third parties and backend systems
- Enforces consistent authentication, rate limiting, and audit logging across all data access
- Provides a single pane of glass for API management, usage analytics, and health monitoring
- Reduces time-to-market for new API integrations by 60% through reusable endpoint templates

### Target Users
- Enterprise IT teams managing internal and external API consumers
- Third-party integration developers building applications on top of organizational data
- Banking system integrators connecting to Temenos T24 core banking
- Database Administrators (DBAs) managing backend data source connectivity
- Security/Compliance Officers ensuring regulatory adherence

## 1.2 Stakeholder & User Personas
### API Consumer (Third-Party Developer)
- **Role**: Builds applications that consume organizational data via APIs
- **Goals**: Quickly discover available endpoints, get API keys, test queries, monitor usage
- **Pain Points**: Fragmented API documentation, inconsistent auth mechanisms, no visibility into rate limits or errors

### API Administrator (Internal IT)
- **Role**: Manages API registry, consumer onboarding, security policies
- **Goals**: Register new endpoints, rotate API keys, configure rate limits, monitor system health
- **Pain Points**: Manual configuration of multiple backend systems, no centralized audit trail

### Database Administrator (DBA)
- **Role**: Manages backend database connections and performance
- **Goals**: Configure connection pools, monitor query latency, troubleshoot connectivity issues
- **Pain Points**: No visibility into API-driven DB load, difficulty tracing problematic queries

### Temenos T24 Integration Specialist
- **Role**: Manages T24 OFS messaging and core banking integrations
- **Goals**: Create OFS templates, test enquiry/transaction messages, monitor T24 connectivity
- **Pain Points**: Fragmented OFS tooling, no centralized audit of T24 API calls

### Security/Compliance Officer
- **Role**: Ensures API access meets regulatory and security standards
- **Goals**: Audit all API activity, enforce rate limits, manage IP allowlists/blocklists
- **Pain Points**: Disparate audit logs across systems, no centralized compliance reporting

## 1.3 Functional Requirements (FR)
### FR-AUTH: Authentication & Authorization
1. Generate secure API keys with prefix-visible format `apim_live_xxxx` and SHA-256 hashed storage
2. Validate JWT tokens (RS256 algorithm) for admin and consumer access
3. Support OAuth2 authorization code flow for third-party consumers
4. Enforce role-based access control (RBAC) with roles: superadmin, admin, viewer, consumer
5. Rotate API keys with configurable grace periods
6. Revoke API keys instantly with immediate effect

### FR-GATEWAY: API Gateway Core
1. Route incoming requests to target backend (DB or T24) based on registered endpoint configuration
2. Transform protocol between REST HTTP and backend-specific protocols (ODBC, Oracle Call Interface, etc.)
3. Validate all incoming request payloads against registered endpoint schemas
4. Normalize responses from disparate backends to standardized JSON envelope
5. Enforce request payload size limits (default 10MB)
6. Handle CORS preflight requests for web-based consumers

### FR-DB-MSSQL: MS SQL Server Integration
1. Execute dynamic queries on MS SQL Server using parameterized pyodbc/aioodbc calls
2. Maintain async connection pools with configurable min/max sizes
3. Automatically reconnect on connection failures with exponential backoff
4. Parse and return query results as structured JSON
5. Log all MSSQL queries with latency metrics and error details

### FR-DB-ORACLE: Oracle DB Integration
1. Execute queries on Oracle DB using oracledb with connection pooling
2. Support both thin and thick Oracle client modes
3. Handle Oracle-specific data types (CLOB, BLOB, TIMESTAMP) in responses
4. Implement connection health checks with automatic recovery
5. Enforce parameterized queries to prevent SQL injection

### FR-DB-POSTGRES: PostgreSQL Integration
1. Execute async queries using asyncpg driver with connection pooling
2. Support PostgreSQL-specific features (JSONB, arrays) in query templates
3. Handle async transaction management for multi-statement queries
4. Monitor connection pool health and latency

### FR-DB-MYSQL: MySQL Integration
1. Execute async queries using aiomysql driver with connection pooling
2. Support MySQL 8.0+ features (window functions, CTEs) in query templates
3. Handle connection failover for replicated MySQL setups
4. Log slow queries (>200ms) to audit trail

### FR-DB-MONGO: MongoDB Integration
1. Execute async CRUD operations using Motor driver
2. Support MongoDB aggregation pipelines in query templates
3. Manage connection pools to MongoDB replica sets
4. Handle BSON data type conversion to JSON

### FR-T24: Temenos T24 TCServer Integration
1. Build OFS messages from configurable templates with variable substitution
2. Connect to T24 TCServer via HTTP POST or raw TCP socket
3. Execute OFS enquiries (read-only) and parse XML/delimited responses
4. Post OFS transactions (read-write) and parse success/error MULTIVAL responses
5. Handle T24 authentication via embedded user/password in OFS header
6. Implement retry policy (3 retries, exponential backoff) for network errors
7. Normalize T24 responses to JSON with `@ID`, `@RECORD`, `@ERROR` fields

### FR-ADMIN: Administration & Management
1. Register new API endpoints with method, path, target data source, query/OFS template
2. Onboard new API consumers with customizable rate limits and scopes
3. Manage full API key lifecycle: create, rotate, revoke, list
4. Configure data source connections per database type with encrypted credential storage
5. Manage OFS message templates with versioning and testing

### FR-MONITOR: Monitoring & Analytics
1. Log all API requests with request ID, consumer ID, endpoint, latency, status code
2. Track error rates and categorize errors by type (auth, db, t24, validation)
3. Expose real-time metrics: request volume, latency percentiles, error rates
4. Configure alert thresholds for error rates, latency, and connection failures
5. Generate usage reports per consumer, endpoint, and data source

### FR-RATELIMIT: Rate Limiting
1. Enforce per-API key rate limits (default 1000 req/hour, 100 req/minute)
2. Enforce per-endpoint rate limits with override capabilities
3. Return standard rate limit headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
4. Store rate limit counters in Redis for distributed consistency
5. Fall back to MySQL rate limit tracking if Redis is unavailable

### FR-AUDIT: Audit & Compliance
1. Maintain immutable audit trail for all admin actions (create, update, delete endpoints/keys/consumers)
2. Log all API requests with full context (IP, user agent, request body hash)
3. Prevent modification or deletion of audit logs (append-only design)
4. Support audit log export for compliance reporting
5. Retain audit logs for 13 months with automated archival

## 1.4 Non-Functional Requirements (NFR)
### Performance
- P99 latency < 200ms for database queries
- P99 latency < 500ms for T24 OFS operations
- Support 10,000 concurrent API consumers
- Throughput: 5,000 requests per second (aggregate)

### Availability
- 99.9% uptime SLA (excluding planned maintenance)
- Graceful degradation: continue serving cached responses if backend is unavailable
- Automatic failover for Redis and MySQL management DB

### Security
- TLS 1.3 for all external and internal communication
- AES-256 encryption at rest for stored credentials and audit logs
- OWASP API Security Top 10 compliance (2023)
- Regular security scans (SAST, DAST) in CI/CD pipeline
- API key hashes stored with SHA-256, no plaintext credential storage

### Scalability
- Horizontal scaling via stateless FastAPI workers
- Redis for distributed rate limiting and session caching
- Kubernetes HPA for automatic worker scaling based on CPU/latency
- Connection pooling for all backend databases to prevent resource exhaustion

### Observability
- Structured JSON logging with request ID, consumer ID, endpoint in every log line
- Prometheus metrics endpoint for scraping
- OpenTelemetry tracing for end-to-end request flow visibility
- Pre-built Grafana dashboards for system health and API usage
- ELK Stack integration for centralized log analysis

## 1.5 Out of Scope (Phase 2)
- GraphQL API support
- Real-time WebSocket streaming for API responses
- Native gRPC endpoint support
- Multi-region active-active deployment (Phase 3)
- Built-in billing/monetization for API consumers

## 1.6 Acceptance Criteria
### FR-AUTH
- [ ] API key generation returns prefix-visible key with SHA-256 hash stored in MySQL
- [ ] JWT tokens with invalid signatures are rejected with 401 Unauthorized
- [ ] OAuth2 flow returns valid access/refresh tokens for authorized consumers
- [ ] Admin endpoints reject requests without `superadmin` or `admin` role

### FR-GATEWAY
- [ ] Requests to registered endpoints are routed to correct backend data source
- [ ] Invalid request payloads are rejected with 400 Bad Request and validation errors
- [ ] Responses from all backends are normalized to standardized JSON envelope
- [ ] Payloads exceeding 10MB are rejected with 413 Payload Too Large

### FR-DB-* (All Database Adapters)
- [ ] Parameterized queries only: no SQL injection possible via request params
- [ ] Connection pool metrics are exposed via `/metrics` endpoint
- [ ] Failed connections trigger automatic retry with exponential backoff
- [ ] Query latency is logged for every database request

### FR-T24
- [ ] OFS messages are built from templates with variable substitution (no direct concatenation)
- [ ] T24 enquiry requests return parsed JSON with `@RECORD` data
- [ ] T24 transaction requests return success/error status with `@ERROR.CODE` if applicable
- [ ] 3 retries with exponential backoff are attempted for network errors

### FR-ADMIN
- [ ] New endpoints can be registered with all required fields via admin API
- [ ] API keys can be created, rotated, and revoked via admin UI and API
- [ ] Data source connections are tested before being saved to registry

### FR-MONITOR
- [ ] All requests are logged to `request_logs` table with latency and status
- [ ] Prometheus metrics endpoint returns valid histogram and counter data
- [ ] Grafana dashboard displays real-time request volume and error rates

### FR-RATELIMIT
- [ ] Exceeding per-key rate limit returns 429 Too Many Requests with rate limit headers
- [ ] Rate limit counters reset correctly at the end of the time window
- [ ] Redis-backed rate limiting works across multiple FastAPI workers

### FR-AUDIT
- [ ] All admin actions are logged to `audit_trail` table with old/new values
- [ ] Audit logs cannot be modified or deleted via API or UI
- [ ] Audit log export returns valid CSV/JSON with all required fields
