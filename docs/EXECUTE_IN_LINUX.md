# Execute — How to Run APIM on Linux

Complete step-by-step guide to get the Centralized API Management System running on Linux (Ubuntu/Debian/CentOS/RHEL).

---

## Prerequisites (Linux)

### Required Software
| Software | Version | Install Command (Ubuntu/Debian) |
|---|---|---|
| Python | 3.11+ | `sudo apt install python3.11 python3.11-venv python3.11-dev` |
| MySQL | 8.0+ | `sudo apt install mysql-server` |
| Redis | 7.0+ | `sudo apt install redis-server` |
| Docker | 24.0+ | See: https://docs.docker.com/engine/install/ubuntu/ |
| Git | 2.30+ | `sudo apt install git` |
| OpenSSL | 3.0+ | `sudo apt install openssl` |

### For T24 Integration
- T24 TCServer hostname/IP, port (default 9089)
- T24 user credentials with OFS permissions
- OFS message version (usually "0")

---

## Step 1: Clone & Setup

```bash
# Clone the repository
git clone <repository-url>
cd apim

# Create virtual environment (recommended)
python3.11 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

---

## Step 2: Install System Dependencies

### Ubuntu/Debian
```bash
sudo apt update
sudo apt install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    python3.11-dev \
    libssl-dev \
    curl \
    build-essential
```

### CentOS/RHEL
```bash
sudo dnf install -y \
    gcc \
    mysql-devel \
    pkgconfig \
    python3.11-devel \
    openssl-devel \
    curl \
    make \
    automake
```

---

## Step 3: Install Python Dependencies

```bash
pip install -r requirements.txt

# Verify installation
python -c "import fastapi, sqlalchemy, aiomysql, httpx; print('All dependencies installed!')"
```

---

## Step 4: Configure Environment

### 4.1 Copy Example Environment File
```bash
cp .env.example .env
```

### 4.2 Edit Environment File
```bash
nano .env
# or use vim:
# vim .env
```

### 4.3 Minimum Required `.env` Configuration
```env
# Application
APP_ENV=development
APP_HOST=0.0.0.0
APP_PORT=8000
SECRET_KEY=your-256-bit-secret-key-here-min-32-chars!!

# JWT Keys (generate with commands in Step 5)
JWT_ALGORITHM=RS256
JWT_PRIVATE_KEY_PATH=./keys/jwt_private.pem
JWT_PUBLIC_KEY_PATH=./keys/jwt_public.pem
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

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

# Encryption Key (generate with command in Step 5)
ENCRYPTION_KEY=your-32-byte-fernet-key-base64==

# T24 (if using T24 features)
T24_HOST=tcserver.bank.internal
T24_PORT=9089
T24_USERNAME=your-t24-user
T24_PASSWORD=your-t24-password
```

---

## Step 5: Generate Keys

### 5.1 Generate JWT RSA Key Pair
```bash
# Create keys directory
mkdir -p keys

# Generate private key (2048-bit RSA)
openssl genrsa -out keys/jwt_private.pem 2048

# Extract public key
openssl rsa -in keys/jwt_private.pem -pubout -out keys/jwt_public.pem

# Verify keys were created
ls -la keys/
```

### 5.2 Generate Fernet Encryption Key
```bash
# Generate and display Fernet key
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Copy the output and paste it into `ENCRYPTION_KEY=` in your `.env` file.

---

## Step 6: Start Infrastructure Services

### Option A: Using Docker (Recommended for Development)

```bash
# Start MySQL and Redis containers
docker-compose -f docker-compose.dev.yml up -d

# Verify services are running
docker-compose -f docker-compose.dev.yml ps

# Check logs
docker-compose -f docker-compose.dev.yml logs -f
```

### Option B: Native Installation

#### MySQL Setup
```bash
# Start MySQL service
sudo systemctl start mysql
sudo systemctl enable mysql

# Secure MySQL installation (set root password)
sudo mysql_secure_installation

# Login to MySQL
sudo mysql -u root -p

# Run these SQL commands:
CREATE DATABASE apim_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'apim_user'@'localhost' IDENTIFIED BY 'your-strong-password';
GRANT ALL PRIVILEGES ON apim_db.* TO 'apim_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

#### Redis Setup
```bash
# Start Redis service
sudo systemctl start redis
sudo systemctl enable redis

# Verify Redis is running
redis-cli ping
# Should return: PONG
```

---

## Step 7: Run Database Migrations

```bash
# Run Alembic migrations
cd /path/to/apim
source venv/bin/activate
alembic upgrade head
```

**Expected Output:**
```
INFO  [alembic.runtime.migration] Context impl MySQLImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 001_initial
```

---

## Step 8: Seed Initial Data

```bash
# Seed the database with sample data
python -m app.scripts.seed_db
```

**Expected Output:**
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

## Step 9: Start the Application

### Development Mode (with auto-reload)
```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Start with hot-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Expected Output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using StatReload
INFO:     Application startup complete.
```

### Production Mode
```bash
# Using gunicorn with uvicorn workers
gunicorn app.main:app \
    -w 4 \
    -k uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --access-logfile - \
    --error-logfile -
```

---

## Step 10: Access the Application

| URL | Description |
|---|---|
| http://localhost:8000/ | API root, version info |
| http://localhost:8000/docs | Swagger UI (API documentation) |
| http://localhost:8000/redoc | ReDoc (alternative API docs) |
| http://localhost:8000/health | Health check endpoint |
| http://localhost:8000/metrics | Prometheus metrics |
| http://localhost:8000/dashboard | Dashboard home |

### Test Health Endpoint
```bash
curl http://localhost:8000/health
```

**Expected Response:**
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

---

## Step 11: Using the Dashboard

### 11.1 Login to Dashboard
Navigate to: `http://localhost:8000/dashboard`

Default admin credentials (from seed):
- **Username**: `admin`
- **Password**: `Admin123!`

### 11.2 Dashboard Navigation
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

---

## Step 12: Making API Requests

### 12.1 Get JWT Token (Admin)
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

### 12.2 Execute a Query (Using API Key)
```bash
curl -X POST http://localhost:8000/api/v1/query/customer-by-id \
  -H "X-API-Key: apim_live_8f3a9b2c1d4e5f6a7b8c9d0e1f2a3b4" \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": "100305"
  }'
```

### 12.3 Test T24 Enquiry
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

---

## Step 13: Monitoring & Analytics

### 13.1 View Metrics Summary
```bash
# Get JWT token first (see 12.1), then:
curl http://localhost:8000/api/v1/metrics/summary \
  -H "Authorization: Bearer <your_jwt_token>"
```

### 13.2 Prometheus Metrics
```bash
curl http://localhost:8000/metrics
```

**Sample Output:**
```
# HELP apim_requests_total Total API requests
apim_requests_total{method="POST",endpoint="customer-by-id",status="2xx",target_db="postgresql"} 1500
# HELP apim_request_latency_seconds Request latency in seconds
apim_request_latency_seconds_bucket{endpoint="customer-by-id",target_db="postgresql",le="0.1"} 1200
```

---

## Step 14: Docker Production Deployment

### 14.1 Configure Production Environment
```bash
cp .env.example .env.prod
nano .env.prod
# Edit with production values (strong passwords, production hosts)
```

### 14.2 Build and Start All Services
```bash
# Build and start in detached mode
docker-compose up -d --build

# Check status
docker-compose ps

# View logs
docker-compose logs -f apim-app
```

### 14.3 Run Migrations in Container
```bash
docker-compose exec apim-app alembic upgrade head
```

### 14.4 Seed Data (if fresh install)
```bash
docker-compose exec apim-app python -m app.scripts.seed_db
```

### 14.5 Verify Deployment
```bash
curl http://localhost/health
```

---

## Step 15: Kubernetes Deployment

### 15.1 Create Namespace
```bash
kubectl apply -f infrastructure/kubernetes/namespace.yaml
```

### 15.2 Create Secrets
```bash
kubectl create secret generic apim-secrets \
  -n apim-system \
  --from-literal=mysql-password='your-mysql-pass' \
  --from-literal=redis-password='your-redis-pass' \
  --from-literal=secret-key='your-secret-key' \
  --from-literal=encryption-key='your-encryption-key'
```

### 15.3 Deploy Application
```bash
kubectl apply -f infrastructure/kubernetes/
```

### 15.4 Check Deployment Status
```bash
kubectl get pods -n apim-system
kubectl get svc -n apim-system
kubectl get ingress -n apim-system
```

---

## Step 16: Using systemd (Linux Service)

### Create systemd Service File
```bash
sudo nano /etc/systemd/system/apim.service
```

**Paste this configuration:**
```ini
[Unit]
Description=Centralized API Management System
After=network.target mysql.service redis.service

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/apim
Environment="PATH=/path/to/apim/venv/bin"
ExecStart=/path/to/apim/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Enable and Start Service
```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable apim.service

# Start service
sudo systemctl start apim.service

# Check status
sudo systemctl status apim.service

# View logs
sudo journalctl -u apim.service -f
```

---

## Step 17: Common Workflows

### Workflow 1: Add New Database and Expose as API

```bash
# 1. Add data source via API (get JWT token first)
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

---

## Troubleshooting (Linux-Specific)

### Issue: `ModuleNotFoundError: No module named '...'`
```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: `Can't connect to MySQL server`
```bash
# Check if MySQL is running
sudo systemctl status mysql

# Check MySQL bind address
sudo nano /etc/mysql/mysql.conf.d/mysqld.cnf
# Ensure: bind-address = 127.0.0.1 or 0.0.0.0

# Restart MySQL
sudo systemctl restart mysql
```

### Issue: `Redis connection refused`
```bash
# Check if Redis is running
sudo systemctl status redis

# Check Redis config
sudo nano /etc/redis/redis.conf
# Ensure: bind 127.0.0.1 or 0.0.0.0

# Restart Redis
sudo systemctl restart redis

# Test connection
redis-cli ping
```

### Issue: `Permission denied` for keys directory
```bash
# Fix permissions
chmod 700 keys/
chmod 600 keys/*
```

### Issue: `uvicorn: command not found`
```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Or use full path
/path/to/apim/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Issue: `ALEMBIC command not found`
```bash
# Use module syntax
python -m alembic.config.main upgrade head

# Or ensure virtual environment is activated
source venv/bin/activate
alembic upgrade head
```

### View Application Logs
```bash
# If running with systemd
sudo journalctl -u apim.service -n 100 --no-pager

# If running in Docker
docker-compose logs -f apim-app

# If running manually
# Logs appear in terminal output
```

---

## Quick Reference

### Useful Linux Commands for APIM

| Task | Command |
|---|---|
| Check Python version | `python3 --version` |
| Activate venv | `source venv/bin/activate` |
| Start MySQL | `sudo systemctl start mysql` |
| Stop MySQL | `sudo systemctl stop mysql` |
| Start Redis | `sudo systemctl start redis` |
| Check Redis | `redis-cli ping` |
| View running processes | `ps aux | grep uvicorn` |
| Kill process on port 8000 | `sudo kill $(sudo lsof -t -i:8000)` |
| View open ports | `sudo ss -tulpn | grep 8000` |
| Check disk space | `df -h` |
| Check memory | `free -h` |

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
