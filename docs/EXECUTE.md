# Execute — How to Use the Centralized API Management System

Complete step-by-step guide to get the system running and execute API queries.

---

## Prerequisites

### Required Software
| Software | Version | Purpose |
|---|---|---|
| Python | 3.11+ | Application runtime |
| MySQL | 8.0+ | Management database |
| Redis | 7.0+ | Rate limiting & cache |
| Docker | 24.0+ | Containerized services (optional) |
| Git | 2.30+ | Version control |

### For T24 Integration
- T24 TCServer hostname, port (default 9089)
- T24 user credentials with OFS permissions
- OFS message version (usually "0")

---

## Step 1: Clone & Setup

```bash
# Clone the repository
git clone <repository-url>
cd apim

# Create virtual environment (recommended)
python -m venv venv

# Activate (Windows)
venv\Scripts\activate
# Activate (macOS/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## Step 2: Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings
notepad .env  # Windows
# nano .env            # macOS/Linux
```

### Minimum Required `.env` Configuration

```env
# Application
APP_ENV=development
APP_HOST=0.0.0.0
APP_PORT=8000
SECRET_KEY=your-256-bit-secret-key-here

# JWT Keys (generate with command below)
JWT_PRIVATE_KEY_PATH=./keys/jwt_private.pem
JWT_PUBLIC_KEY_PATH=./keys/jwt_public.pem

# Management Database
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=apim_db
MYSQL_USER=apim_user
MYSQL_PASSWORD=your-strong-password

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your-redis-password

# Encryption Key (generate with command below)
ENCRYPTION_KEY=your-32-byte-fernet-key

# T24 (if using T24 features)
T24_HOST=tcserver.bank.internal
T24_PORT=9089
T24_USERNAME=your-t24-user
T24_PASSWORD=your-t24-password
```

### Generate JWT RSA Key Pair

```bash
# Create keys directory
mkdir -p keys

# Generate private key
openssl genrsa -out keys/jwt_private.pem 2048

# Generate public key
openssl rsa -in keys/jwt_private.pem -pubout -out keys/jwt_public.pem
```

### Generate Encryption Key

```python
# Run in Python to generate Fernet key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Copy the output to `ENCRYPTION_KEY` in `.env`.

---

## Step 3: Start Infrastructure Services

### Option A: Using Docker (Recommended for Development)

```bash
# Start MySQL and Redis
docker-compose -f docker-compose.dev.yml up -d

# Verify services are running
docker-compose -f docker-compose.dev.yml ps
```

### Option B: Native Installation

**MySQL Setup:**
```bash
# Login to MySQL
mysql -u root -p

# Create database and user
CREATE DATABASE apim_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'apim_user'@'localhost' IDENTIFIED BY 'your-strong-password';
GRANT ALL PRIVILEGES ON apim_db.* TO 'apim_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

**Redis Setup:**
```bash
# On Ubuntu/Debian
sudo apt install redis-server
sudo systemctl enable redis
sudo systemctl start redis

# Verify Redis is running
redis-cli ping  # Should return PONG
```

---

## Step 4: Run Database Migrations

```bash
# Run Alembic migrations
alembic upgrade head

# You should see output like:
# INFO  [alembic.runtime.migration] Context impl MySQLImpl.
# INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
# INFO  [alembic.runtime.migration] Running upgrade  -> 001_initial
```

---

## Step 5: Seed Initial Data

```bash
# Seed the database with sample data
python -m app.scripts.seed_db
```

**Output:**
```
Seeding database...
Generated API Key for Mobile App:
  Full Key (save this!): apim_live_8f3a9b2c1d4e5f6a7b8c9d0e1f2a3b4
  Prefix: apim_live_8f3a9b2c

Generated API Key for Internet Banking:
  Full Key (save this!): apim_live_7e2d8f1a9b0c1d2e3f4a5b6c7d8e9f0
  Prefix: apim_live_7e2d8f1a

Database seeded successfully!
```

⚠️ **Important**: Save the generated API keys! They are shown only once.

---

## Step 6: Start the Application

```bash
# Development mode (with auto-reload)
uvicorn app.main:app --reload --port 8000

# Expected output:
# INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
# INFO:     Started reloader process [12345]
# INFO:     Application startup complete.
```

---

## Step 7: Access the Application

| URL | Description |
|---|---|
| http://localhost:8000/ | API root, version info |
| http://localhost:8000/docs | Swagger UI (API documentation) |
| http://localhost:8000/redoc | ReDoc (alternative API docs) |
| http://localhost:8000/health | Health check endpoint |
| http://localhost:8000/metrics | Prometheus metrics |
| http://localhost:8000/dashboard | Dashboard home |

---

## Step 8: Using the Dashboard

### 8.1 Login to Dashboard

Navigate to `http://localhost:8000/dashboard`

Default admin credentials (from seed):
- **Username**: `admin`
- **Password**: `Admin123!`

After login, you'll see the overview dashboard with KPIs, charts, and alerts.

### 8.2 Dashboard Navigation

```
Sidebar Menu:
├── Overview          → System KPIs, request volume, top consumers
├── Registry
│   ├── Endpoints         → Register and manage API endpoints
│   ├── Data Sources      → Configure database connections
│   └── OFS Templates     → T24 OFS message templates
├── API Keys
│   ├── Keys Management  → Create and revoke API keys
│   └── Consumers        → Manage API consumers
├── Analytics
│   ├── Traffic          → Request volume, latency analysis
│   └── Errors          → Error reports and logs
├── T24               → T24 connection status and OFS testing
├── Audit Logs         → Immutable admin action trail
└── Settings           → Application configuration
```

### 8.3 Create a New Data Source

1. Go to **Registry → Data Sources**
2. Click **+ Add Data Source**
3. Fill in the form:
   - **Name**: `Production PostgreSQL`
   - **DB Type**: `postgresql`
   - **Host**: `pg.prod.internal`
   - **Port**: `5432`
   - **Database**: `banking_db`
   - **Username**: `apim_user`
   - **Password**: `your-password`
   - **Pool Min**: `2`
   - **Pool Max**: `20`
4. Click **Save**
5. Click **Test Connection** to verify

### 8.4 Register an API Endpoint

1. Go to **Registry → Endpoints**
2. Click **+ Add Endpoint**
3. Fill in:
   - **Slug**: `customer-by-id`
   - **Name**: `Get Customer by ID`
   - **Method**: `POST`
   - **Path Pattern**: `/query/customer-by-id`
   - **Data Source**: Select your PostgreSQL data source
   - **Query Template**:
     ```sql
     SELECT * FROM customers WHERE id = :account_id
     ```
   - **Request Schema** (JSON):
     ```json
     { "type": "object", "properties": { "account_id": { "type": "string" } }, "required": ["account_id"] }
     ```
   - **Response Schema** (JSON):
     ```json
     { "type": "object", "properties": { "id": { "type": "string" }, "name": { "type": "string" } } }
     ```
   - **Auth Required**: `Yes`
4. Click **Save**

### 8.5 Create API Key for Consumer

1. Go to **API Keys → Keys Management**
2. Click **+ Create Key**
3. Select Consumer: `Mobile Banking App`
4. Key Name: `Production Key`
5. Set Rate Limits:
   - Per Hour: `5000`
   - Per Minute: `200`
6. Click **Generate Key**
7. **Copy and save the full key** (shown only once):
   ```
   apim_live_8f3a9b2c1d4e5f6a7b8c9d0e1f2a3b4
   ```

---

## Step 9: Making API Requests

### 9.1 Test Health Endpoint

```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-05-05T10:30:00Z",
  "checks": {
    "management_db": "ok",
    "redis": "ok"
  }
}
```

### 9.2 Get JWT Token (Admin)

```bash
curl -X POST http://localhost:8000/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "Admin123!"
  }'
```

**Response:**
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOi...",
    "refresh_token": "eyJhbGciOi...",
    "token_type": "bearer",
    "expires_in": 900
  },
  "error": null
}
```

### 9.3 Execute a Query (Using API Key)

```bash
curl -X POST http://localhost:8000/api/v1/query/customer-by-id \
  -H "X-API-Key: apim_live_8f3a9b2c1d4e5f6a7b8c9d0e1f2a3b4" \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": "100305"
  }'
```

**Response:**
```json
{
  "success": true,
  "data": {
    "records": [
      {
        "id": "100305",
        "name": "John Doe",
        "email": "john@example.com",
        "balance": 1500.00
      }
    ],
    "count": 1,
    "target": "postgresql",
    "execution_time_ms": 45.2
  },
  "meta": {
    "request_id": "req_a1b2c3d4",
    "timestamp": "2026-05-05T10:35:00Z",
    "latency_ms": 45.2
  },
  "error": null
}
```

### 9.4 GET Query (Using Query Parameters)

```bash
curl "http://localhost:8000/api/v1/query/account-balance?account_no=ACC001" \
  -H "X-API-Key: apim_live_8f3a9b2c1d4e5f6a7b8c9d0e1f2a3b4"
```

---

## Step 10: T24 OFS Operations

### 10.1 Test T24 Connection

```bash
curl http://localhost:8000/api/v1/t24/status \
  -H "X-API-Key: apim_live_8f3a9b2c1d4e5f6a7b8c9d0e1f2a3b4"
```

**Response:**
```json
{
  "success": true,
  "data": {
    "connected": true,
    "host": "tcserver.bank.internal",
    "port": 9089
  },
  "error": null
}
```

### 10.2 Run T24 Enquiry

```bash
curl -X POST http://localhost:8000/api/v1/t24/enquiry/customer \
  -H "X-API-Key: apim_live_8f3a9b2c1d4e5f6a7b8c9d0e1f2a3b4" \
  -H "Content-Type: application/json" \
  -d '{
    "variables": {
      "ACCOUNT_NUMBER": "100305"
    }
  }'
```

**Response:**
```json
{
  "success": true,
  "data": {
    "enquiry": "CUSTOMER",
    "record": {
      "@ID": "100305",
      "@RECORD": {
        "NAME": ["John", "Doe"],
        "EMAIL": "john@example.com",
        "PHONE": "+1234567890"
      }
    }
  },
  "meta": { "request_id": "...", "latency_ms": 120.5 },
  "error": null
}
```

### 10.3 Post T24 Transaction

```bash
curl -X POST http://localhost:8000/api/v1/t24/transaction \
  -H "X-API-Key: apim_live_8f3a9b2c1d4e5f6a7b8c9d0e1f2a3b4" \
  -H "Content-Type: application/json" \
  -d '{
    "application": "FUNDS.TRANSFER",
    "variables": {
      "DEBIT_ACCT": "1001",
      "CREDIT_ACCT": "1002",
      "AMOUNT": "500.00",
      "VALUE_DATE": "2026-05-05"
    }
  }'
```

**Response:**
```json
{
  "success": true,
  "data": {
    "transaction_id": "FT123456",
    "application": "FUNDS.TRANSFER",
    "status": "posted"
  },
  "meta": { "request_id": "...", "latency_ms": 250.3 },
  "error": null
}
```

---

## Step 11: Monitoring & Analytics

### 11.1 View Metrics Summary

```bash
curl http://localhost:8000/api/v1/metrics/summary \
  -H "Authorization: Bearer <admin_jwt_token>"
```

### 11.2 Prometheus Metrics

```bash
curl http://localhost:8000/metrics
```

**Sample Output:**
```
# HELP apim_requests_total Total API requests
apim_requests_total{method="POST",endpoint="customer-by-id",status="2xx",target_db="postgresql"} 1500
# HELP apim_request_latency_seconds Request latency
apim_request_latency_seconds_bucket{endpoint="customer-by-id",target_db="postgresql",le="0.1"} 1200
```

### 11.3 Grafana Dashboard

1. Access Grafana at `http://localhost:3000`
2. Default credentials: `admin` / `admin`
3. Add Prometheus data source: `http://apim-prometheus:9090`
4. Import pre-built dashboard from `infrastructure/grafana/dashboards/`

---

## Step 12: Common Workflows

### Workflow 1: Add New Database and Expose as API

```bash
# 1. Add data source via API
curl -X POST http://localhost:8000/api/v1/admin/datasources \
  -H "Authorization: Bearer <admin_jwt>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "New Oracle DB",
    "db_type": "oracle",
    "host": "oracle.prod.internal",
    "port": 1521,
    "database_name": "BANKDB",
    "username": "apim_user",
    "password": "password123",
    "pool_min": 2,
    "pool_max": 20,
    "status": "active"
  }'

# 2. Create endpoint
curl -X POST http://localhost:8000/api/v1/admin/endpoints \
  -H "Authorization: Bearer <admin_jwt>" \
  -H "Content-Type: application/json" \
  -d '{
    "slug": "oracle-customer-search",
    "name": "Oracle Customer Search",
    "http_method": "POST",
    "path_pattern": "/query/oracle-customer-search",
    "data_source_id": <returned_datasource_id>,
    "query_template": "SELECT * FROM customers WHERE name LIKE :search_term",
    "auth_required": true,
    "status": "active"
  }'

# 3. Test via API key
curl -X POST http://localhost:8000/api/v1/query/oracle-customer-search \
  -H "X-API-Key: <your_api_key>" \
  -d '{"search_term": "%John%"}'
```

### Workflow 2: Create T24 OFS Template

```bash
# 1. Create OFS template
curl -X POST http://localhost:8000/api/v1/admin/ofs-templates \
  -H "Authorization: Bearer <admin_jwt>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Account Balance Enquiry",
    "ofs_type": "enquiry",
    "application_name": "ACCOUNT",
    "ofs_message_template": "ENQ.ACCOUNT,ACCOUNT,0/{{T24_USER}}/{{T24_PASS}},,@ID={{ACCOUNT_NUMBER}}",
    "variable_definitions": {
      "ACCOUNT_NUMBER": {"type": "string", "required": true}
    },
    "t24_version": "0",
    "status": "active"
  }'

# 2. Test the template
curl -X POST http://localhost:8000/api/v1/admin/ofs-templates/<template_id>/test \
  -H "Authorization: Bearer <admin_jwt>" \
  -H "Content-Type: application/json" \
  -d '{"ACCOUNT_NUMBER": "ACC001"}'
```

### Workflow 3: Rotate API Key

```bash
# Generate new key
curl -X POST http://localhost:8000/api/v1/auth/api-keys \
  -H "Authorization: Bearer <admin_jwt>" \
  -H "Content-Type: application/json" \
  -d '{
    "consumer_id": <consumer_uuid>,
    "name": "New Production Key",
    "rate_limit_per_hour": 10000,
    "rate_limit_per_minute": 500
  }'

# Revoke old key (after grace period)
curl -X DELETE http://localhost:8000/api/v1/auth/api-keys/<old_key_id> \
  -H "Authorization: Bearer <admin_jwt>"
```

---

## Step 13: Docker Production Deployment

```bash
# 1. Configure production environment
cp .env.example .env.prod
# Edit .env.prod with production values

# 2. Build and start all services
docker-compose -f docker-compose.yml up -d --build

# 3. Run migrations
docker-compose exec apim-app alembic upgrade head

# 4. Seed data (if fresh install)
docker-compose exec apim-app python -m app.scripts.seed_db

# 5. Verify deployment
curl http://localhost/health
```

---

## Step 14: Kubernetes Deployment

```bash
# 1. Create namespace
kubectl apply -f infrastructure/kubernetes/namespace.yaml

# 2. Create secrets (use your actual values)
kubectl create secret generic apim-secrets \
  -n apim-system \
  --from-literal=mysql-password='your-mysql-pass' \
  --from-literal=redis-password='your-redis-pass' \
  --from-literal=secret-key='your-secret-key' \
  --from-literal=encryption-key='your-encryption-key'

# 3. Deploy application
kubectl apply -f infrastructure/kubernetes/

# 4. Check status
kubectl get pods -n apim-system
kubectl get svc -n apim-system
kubectl get ingress -n apim-system
```

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|---|---|
| Database connection failed | Verify MySQL is running: `mysql -u apim_user -p -h localhost` |
| Redis connection failed | Verify Redis: `redis-cli ping` |
| Migration fails | Check `.env` MYSQL_* settings, ensure database exists |
| T24 connection timeout | Verify T24_HOST/PORT, check firewall rules |
| 401 Unauthorized | Check API key is correct, not expired/revoked |
| 429 Too Many Requests | Wait for rate limit window to reset, or increase limits |

### View Logs

```bash
# Docker logs
docker-compose logs -f apim-app

# Kubernetes logs
kubectl logs -f deployment/apim-app -n apim-system

# Structured JSON logs (if STRUCTLOG_ENABLED=true)
# Logs include: request_id, consumer_id, endpoint, latency_ms
```

---

## Quick Reference

### API Endpoint Summary

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| POST | `/api/v1/auth/token` | Get JWT tokens | Username/Pass |
| POST | `/api/v1/auth/refresh` | Refresh JWT | Refresh Token |
| POST | `/api/v1/auth/api-keys` | Create API key | Admin JWT |
| DELETE | `/api/v1/auth/api-keys/{id}` | Revoke API key | Admin JWT |
| POST | `/api/v1/query/{slug}` | Execute query | API Key |
| GET | `/api/v1/query/{slug}` | Execute query (GET) | API Key |
| POST | `/api/v1/t24/enquiry/{name}` | T24 enquiry | API Key |
| POST | `/api/v1/t24/transaction` | T24 transaction | API Key |
| GET | `/api/v1/t24/status` | T24 health | API Key |
| GET | `/api/v1/metrics/*` | Monitoring endpoints | Admin JWT |
| GET | `/health` | Health check | None |
| GET | `/metrics` | Prometheus metrics | None |

### Error Codes Quick Reference

| Code | Meaning |
|---|---|
| APIM_AUTH_001 | Invalid API key |
| APIM_AUTH_002 | Invalid JWT token |
| APIM_DB_001 | Database connection failed |
| APIM_T24_005 | T24 enquiry failed |
| APIM_T24_006 | T24 transaction failed |
| APIM_RATELIMIT_001 | Rate limit exceeded |
