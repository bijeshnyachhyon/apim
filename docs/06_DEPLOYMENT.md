# 06 Deployment Guide

## 6.1 Prerequisites
### Infrastructure
- **OS**: Ubuntu 22.04 LTS (production server) or macOS/Windows with Docker Desktop (development)
- **CPU**: 4+ cores recommended for production (2+ cores for development)
- **RAM**: 8GB+ for production (4GB for development)
- **Disk**: 50GB+ SSD for production (20GB for development)

### Software
- **Docker**: 24.0+ (for containerized deployment)
- **Docker Compose**: v2.20+ (for local development)
- **Python**: 3.11+ (for local development without Docker)
- **MySQL**: 8.0+ (if running management DB natively)
- **Redis**: 7.0+ (if running cache natively)
- **kubectl**: 1.28+ (for Kubernetes deployment)
- **Helm**: 3.12+ (for Kubernetes deployment)

### Temenos T24 Requirements
- **TCServer Host**: Hostname/IP of T24 TCServer
- **TCServer Port**: Typically 9089 (TCP) or 8080 (HTTP Servlet)
- **T24 User Credentials**: Valid T24 user with enquiry/transaction permissions
- **OFS Message Version**: Typically "0" for modern T24 versions

## 6.2 Repository Structure
```
apim/
├── docs/                    # All MD documentation files
│   ├── 01_PRODUCT_REQUIREMENTS.md
│   ├── 02_SYSTEM_ARCHITECTURE.md
│   ├── 03_DASHBOARD_DESIGN.md
│   ├── 04_API_DEVELOPMENT_SPECS.md
│   ├── 05_DATABASE_SCHEMA.md
│   └── 06_DEPLOYMENT.md
├── app/
│   ├── main.py              # FastAPI app entry point
│   ├── core/
│   │   ├── config.py        # Settings via pydantic-settings
│   │   ├── security.py      # JWT, API key hashing
│   │   └── dependencies.py  # FastAPI dependency injection
│   ├── api/
│   │   ├── v1/
│   │   │   ├── auth.py     # Authentication endpoints
│   │   │   ├── query.py    # Query execution endpoints
│   │   │   ├── t24.py      # T24 OFS endpoints
│   │   │   ├── admin/
│   │   │   │   ├── endpoints.py
│   │   │   │   ├── datasources.py
│   │   │   │   ├── consumers.py
│   │   │   │   └── ofs_templates.py
│   │   │   ├── metrics.py  # Monitoring endpoints
│   │   │   └── admin.py   # Admin management endpoints
│   │   └── deps.py         # API dependencies
│   ├── adapters/
│   │   ├── base.py          # Abstract DB adapter
│   │   ├── mssql.py        # MSSQL adapter
│   │   ├── oracle.py       # Oracle adapter
│   │   ├── postgresql.py   # PostgreSQL adapter
│   │   ├── mysql.py        # MySQL adapter
│   │   ├── mongodb.py      # MongoDB adapter
│   │   └── t24/
│   │       ├── connector.py  # TCServer HTTP/TCP connector
│   │       ├── ofs_builder.py
│   │       └── ofs_parser.py
│   ├── models/
│   │   ├── db/              # SQLAlchemy ORM models
│   │   │   ├── base.py
│   │   │   ├── consumer.py
│   │   │   ├── api_key.py
│   │   │   ├── admin_user.py
│   │   │   ├── data_source.py
│   │   │   ├── endpoint.py
│   │   │   ├── ofs_template.py
│   │   │   ├── request_log.py
│   │   │   ├── audit_trail.py
│   │   │   └── ...
│   │   └── schemas/         # Pydantic request/response schemas
│   │       ├── auth.py
│   │       ├── query.py
│   │       ├── t24.py
│   │       ├── admin.py
│   │       └── ...
│   ├── services/
│   │   ├── routing.py       # Routing engine
│   │   ├── rate_limiter.py  # Rate limiting service
│   │   ├── audit.py         # Audit logging service
│   │   ├── metrics.py       # Metrics collection
│   │   └── encryption.py    # Fernet encryption service
│   ├── dashboard/
│   │   ├── routes.py        # Dashboard HTML routes
│   │   ├── templates/       # Jinja2 HTML templates
│   │   │   ├── base.html
│   │   │   ├── dashboard/
│   │   │   │   ├── overview.html
│   │   │   │   ├── endpoints.html
│   │   │   │   ├── datasources.html
│   │   │   │   ├── api_keys.html
│   │   │   │   ├── consumers.html
│   │   │   │   ├── t24.html
│   │   │   │   ├── analytics.html
│   │   │   │   ├── audit.html
│   │   │   │   └── settings.html
│   │   └── static/          # CSS, JS assets
│   │       ├── css/
│   │       │   └── main.css
│   │       └── js/
│   │           ├── dashboard.js
│   │           ├── charts.js
│   │           └── alpine-components.js
│   ├── db/
│   │   ├── session.py       # SQLAlchemy async session
│   │   └── init_db.py      # DB initialization
│   ├── scripts/
│   │   ├── seed_db.py      # Seed sample data
│   │   └── test_t24.py     # T24 connection test script
│   └── tests/
│       ├── unit/
│       │   ├── test_adapters.py
│       │   ├── test_auth.py
│       │   └── test_ofs_parser.py
│       ├── integration/
│       │   ├── test_query_endpoints.py
│       │   ├── test_t24_endpoints.py
│       │   └── test_admin_endpoints.py
│       └── conftest.py
├── migrations/
│   └── alembic/
│       ├── env.py
│       ├── script.py.mako
│       └── versions/
│           ├── 001_initial.py
│           ├── 002_add_ofs_templates.py
│           └── ...
├── infrastructure/
│   ├── docker/
│   │   ├── Dockerfile
│   │   ├── Dockerfile.dev
│   │   ├── entrypoint.sh
│   │   └── nginx.conf
│   ├── docker-compose.yml
│   ├── docker-compose.dev.yml
│   └── kubernetes/
│       ├── namespace.yaml
│       ├── deployment.yaml
│       ├── service.yaml
│       ├── ingress.yaml
│       ├── configmap.yaml
│       ├── secret.yaml
│       ├── hpa.yaml
│       └── prometheus/
│           └── servicemonitor.yaml
├── .env.example
├── requirements.txt
├── pyproject.toml
├── Makefile
└── README.md
```

## 6.3 Environment Variables
### `.env.example`
```env
# ===================
# Application Settings
# ===================
APP_ENV=development
APP_HOST=0.0.0.0
APP_PORT=8000
APP_DEBUG=true
APP_LOG_LEVEL=INFO
APP_LOG_FORMAT=json

# ===================
# Security
# ===================
SECRET_KEY=generate-256-bit-key-here
JWT_ALGORITHM=RS256
JWT_PRIVATE_KEY_PATH=/app/keys/jwt_private.pem
JWT_PUBLIC_KEY_PATH=/app/keys/jwt_public.pem
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# API Key settings
API_KEY_PREFIX=apim_live_
API_KEY_HASH_ALGORITHM=sha256

# Encryption (for stored DB credentials)
ENCRYPTION_KEY=generate-32-byte-fernet-key-here

# ===================
# Management MySQL Database
# ===================
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=apim_db
MYSQL_USER=apim_user
MYSQL_PASSWORD=strong-password-here
MYSQL_POOL_SIZE=20
MYSQL_MAX_OVERFLOW=10
MYSQL_ECHO=false

# ===================
# Redis (Rate Limiting & Cache)
# ===================
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=redis-password-here
REDIS_DB=0
REDIS_POOL_SIZE=50

# ===================
# Temenos T24 TCServer
# ===================
T24_HOST=tcserver.bank.internal
T24_PORT=9089
T24_USERNAME=T24USER
T24_PASSWORD=T24-password-here
T24_OFS_VERSION=0
T24_CONNECTION_MODE=http  # http or tcp
T24_HTTP_ENDPOINT=/BrowserWeb/servlet/BrowserServlet
T24_TIMEOUT_SECONDS=30
T24_MAX_RETRIES=3

# ===================
# Monitoring & Observability
# ===================
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090
METRICS_ENABLED=true
STRUCTLOG_ENABLED=true
LOG_LEVEL=INFO
LOG_FORMAT=json

# ===================
# Rate Limiting Defaults
# ===================
DEFAULT_RATE_LIMIT_PER_HOUR=1000
DEFAULT_RATE_LIMIT_PER_MINUTE=100
GLOBAL_RATE_LIMIT_PER_MINUTE=10000

# ===================
# CORS Settings
# ===================
CORS_ORIGINS=["http://localhost:3000", "https://api.yourdomain.com"]
CORS_CREDENTIALS=true
CORS_METHODS=["GET", "POST", "PUT", "DELETE"]
CORS_HEADERS=["*"]

# ===================
# Dashboard
# ===================
DASHBOARD_ENABLED=true
DASHBOARD_PATH=/dashboard
DASHBOARD_SECRET_KEY=dashboard-secret-here
```

## 6.4 Docker Compose Configuration

### `docker-compose.yml` (Production)
```yaml
version: '3.8'

services:
  apim-app:
    build:
      context: .
      dockerfile: infrastructure/docker/Dockerfile
    container_name: apim-app
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      APP_ENV: production
      APP_HOST: 0.0.0.0
      APP_PORT: 8000
      MYSQL_HOST: apim-db
      MYSQL_PORT: 3306
      MYSQL_DATABASE: ${MYSQL_DATABASE}
      MYSQL_USER: ${MYSQL_USER}
      MYSQL_PASSWORD: ${MYSQL_PASSWORD}
      REDIS_HOST: apim-redis
      REDIS_PORT: 6379
      REDIS_PASSWORD: ${REDIS_PASSWORD}
      SECRET_KEY: ${SECRET_KEY}
      ENCRYPTION_KEY: ${ENCRYPTION_KEY}
      T24_HOST: ${T24_HOST}
      T24_PORT: ${T24_PORT}
      T24_USERNAME: ${T24_USERNAME}
      T24_PASSWORD: ${T24_PASSWORD}
    depends_on:
      apim-db:
        condition: service_healthy
      apim-redis:
        condition: service_started
    volumes:
      - ./keys:/app/keys:ro
    networks:
      - apim-network
    deploy:
      replicas: 3

  apim-db:
    image: mysql:8.0
    container_name: apim-db
    restart: unless-stopped
    ports:
      - "3306:3306"
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      MYSQL_DATABASE: ${MYSQL_DATABASE}
      MYSQL_USER: ${MYSQL_USER}
      MYSQL_PASSWORD: ${MYSQL_PASSWORD}
    volumes:
      - mysql-data:/var/lib/mysql
      - ./migrations/mysql/init.sql:/docker-entrypoint-initdb.d/init.sql
    command: >
      --default-authentication-plugin=mysql_native_password
      --character-set-server=utf8mb4
      --collation-server=utf8mb4_unicode_ci
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      timeout: 20s
      retries: 10
    networks:
      - apim-network

  apim-redis:
    image: redis:7-alpine
    container_name: apim-redis
    restart: unless-stopped
    ports:
      - "6379:6379"
    command: redis-server --requirepass ${REDIS_PASSWORD} --appendonly yes
    volumes:
      - redis-data:/data
    networks:
      - apim-network

  apim-nginx:
    image: nginx:alpine
    container_name: apim-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./infrastructure/docker/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./infrastructure/docker/ssl:/etc/nginx/ssl:ro
    depends_on:
      - apim-app
    networks:
      - apim-network

  apim-prometheus:
    image: prom/prometheus:latest
    container_name: apim-prometheus
    restart: unless-stopped
    ports:
      - "9090:9090"
    volumes:
      - ./infrastructure/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus-data:/prometheus
    networks:
      - apim-network

  apim-grafana:
    image: grafana/grafana:latest
    container_name: apim-grafana
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_USER: ${GRAFANA_USER}
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD}
      GF_INSTALL_PLUGINS: grafana-piechart-panel
    volumes:
      - grafana-data:/var/lib/grafana
      - ./infrastructure/grafana/dashboards:/etc/grafana/provisioning/dashboards:ro
    networks:
      - apim-network

volumes:
  mysql-data:
  redis-data:
  prometheus-data:
  grafana-data:

networks:
  apim-network:
    driver: bridge
```

### `docker-compose.dev.yml` (Development)
```yaml
version: '3.8'

services:
  apim-app-dev:
    build:
      context: .
      dockerfile: infrastructure/docker/Dockerfile.dev
    container_name: apim-app-dev
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      APP_ENV: development
      APP_DEBUG: "true"
      MYSQL_HOST: apim-db-dev
      MYSQL_PORT: 3306
      MYSQL_DATABASE: ${MYSQL_DATABASE}
      MYSQL_USER: ${MYSQL_USER}
      MYSQL_PASSWORD: ${MYSQL_PASSWORD}
      REDIS_HOST: apim-redis-dev
      REDIS_PORT: 6379
      REDIS_PASSWORD: ${REDIS_PASSWORD}
    volumes:
      - ./app:/app/app:cached
      - ./migrations:/app/migrations:cached
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    depends_on:
      - apim-db-dev
      - apim-redis-dev
    networks:
      - apim-dev-network

  apim-db-dev:
    image: mysql:8.0
    container_name: apim-db-dev
    environment:
      MYSQL_ROOT_PASSWORD: rootpass
      MYSQL_DATABASE: apim_db
      MYSQL_USER: apim_user
      MYSQL_PASSWORD: devpass
    ports:
      - "3307:3306"
    volumes:
      - mysql-dev-data:/var/lib/mysql
    networks:
      - apim-dev-network

  apim-redis-dev:
    image: redis:7-alpine
    container_name: apim-redis-dev
    ports:
      - "6380:6379"
    networks:
      - apim-dev-network

volumes:
  mysql-dev-data:

networks:
  apim-dev-network:
    driver: bridge
```

### `infrastructure/docker/Dockerfile`
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ /app/app/
COPY migrations/ /app/migrations/

# Create keys directory
RUN mkdir -p /app/keys

# Run migrations and start app
COPY infrastructure/docker/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

## 6.5 Development Setup (Step-by-Step)

### Step 1: Clone Repository
```bash
git clone https://github.com/yourorg/apim.git
cd apim
```

### Step 2: Create Virtual Environment (Optional - can use Docker)
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment
```bash
cp .env.example .env
# Edit .env with your local configuration
```

### Step 5: Start Infrastructure Services
```bash
docker-compose -f docker-compose.dev.yml up -d
```

### Step 6: Run Database Migrations
```bash
alembic upgrade head
```

### Step 7: Seed Initial Data
```bash
python -m app.scripts.seed_db
```

### Step 8: Start Development Server
```bash
uvicorn app.main:app --reload --port 8000
```

### Step 9: Access the Application
- **Dashboard**: http://localhost:8000/dashboard
- **API Documentation**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health
- **Metrics**: http://localhost:8000/metrics

## 6.6 Production Deployment

### Docker Compose Production Deployment
```bash
# 1. Copy environment file
cp .env.example .env.prod
# Edit .env.prod with production values (use strong passwords!)

# 2. Build and start services
docker-compose -f docker-compose.yml up -d --build

# 3. Run migrations
docker-compose exec apim-app alembic upgrade head

# 4. Seed initial data (if fresh install)
docker-compose exec apim-app python -m app.scripts.seed_db

# 5. Verify deployment
curl http://localhost/health
```

### Kubernetes Deployment

#### `infrastructure/kubernetes/namespace.yaml`
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: apim-system
```

#### `infrastructure/kubernetes/configmap.yaml`
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: apim-config
  namespace: apim-system
data:
  APP_ENV: "production"
  APP_HOST: "0.0.0.0"
  APP_PORT: "8000"
  MYSQL_HOST: "apim-db.apim-system.svc.cluster.local"
  MYSQL_PORT: "3306"
  REDIS_HOST: "apim-redis.apim-system.svc.cluster.local"
  REDIS_PORT: "6379"
  LOG_LEVEL: "INFO"
  LOG_FORMAT: "json"
  PROMETHEUS_ENABLED: "true"
  DEFAULT_RATE_LIMIT_PER_HOUR: "1000"
  DEFAULT_RATE_LIMIT_PER_MINUTE: "100"
```

#### `infrastructure/kubernetes/secret.yaml`
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: apim-secrets
  namespace: apim-system
type: Opaque
stringData:
  MYSQL_DATABASE: "apim_db"
  MYSQL_USER: "apim_user"
  MYSQL_PASSWORD: "<from-vault>"
  REDIS_PASSWORD: "<from-vault>"
  SECRET_KEY: "<generate-256-bit>"
  ENCRYPTION_KEY: "<generate-32-byte-fernet>"
  T24_HOST: "tcserver.bank.internal"
  T24_USERNAME: "T24USER"
  T24_PASSWORD: "<from-vault>"
```

#### `infrastructure/kubernetes/deployment.yaml`
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: apim-app
  namespace: apim-system
spec:
  replicas: 3
  selector:
    matchLabels:
      app: apim-app
  template:
    metadata:
      labels:
        app: apim-app
    spec:
      containers:
      - name: apim-app
        image: yourregistry/apim:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: apim-config
        - secretRef:
            name: apim-secrets
        resources:
          requests:
            cpu: "500m"
            memory: "512Mi"
          limits:
            cpu: "2000m"
            memory: "2Gi"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
```

#### `infrastructure/kubernetes/service.yaml`
```yaml
apiVersion: v1
kind: Service
metadata:
  name: apim-service
  namespace: apim-system
spec:
  selector:
    app: apim-app
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP
```

#### `infrastructure/kubernetes/ingress.yaml`
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: apim-ingress
  namespace: apim-system
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/rate-limit: "10000"
spec:
  tls:
  - hosts:
    - api.yourdomain.com
    secretName: apim-tls
  rules:
  - host: api.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: apim-service
            port:
              number: 80
```

#### `infrastructure/kubernetes/hpa.yaml`
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: apim-hpa
  namespace: apim-system
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: apim-app
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 100
        periodSeconds: 30
```

### Deploy to Kubernetes
```bash
# 1. Create namespace
kubectl apply -f infrastructure/kubernetes/namespace.yaml

# 2. Create configmap and secret
kubectl apply -f infrastructure/kubernetes/configmap.yaml
kubectl apply -f infrastructure/kubernetes/secret.yaml

# 3. Deploy application
kubectl apply -f infrastructure/kubernetes/deployment.yaml
kubectl apply -f infrastructure/kubernetes/service.yaml
kubectl apply -f infrastructure/kubernetes/ingress.yaml
kubectl apply -f infrastructure/kubernetes/hpa.yaml

# 4. Check deployment status
kubectl get pods -n apim-system
kubectl get svc -n apim-system
kubectl get ingress -n apim-system
```

## 6.7 CI/CD Pipeline (GitHub Actions)

### `.github/workflows/deploy.yml`
```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'
    - name: Install dependencies
      run: pip install ruff mypy
    - name: Lint with ruff
      run: ruff check app/
    - name: Type check with mypy
      run: mypy app/ --strict

  test:
    runs-on: ubuntu-latest
    services:
      mysql:
        image: mysql:8.0
        env:
          MYSQL_ROOT_PASSWORD: testpass
          MYSQL_DATABASE: test_apim_db
          MYSQL_USER: test_user
          MYSQL_PASSWORD: testpass
        ports:
          - 3306:3306
        options: >-
          --health-cmd="mysqladmin ping"
          --health-interval=10s
          --health-timeout=5s
          --health-retries=5
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
    steps:
    - uses: actions/checkout@v4
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'
    - name: Install dependencies
      run: pip install -r requirements.txt
    - name: Run tests with coverage
      run: pytest app/tests/ --cov=app --cov-report=xml --cov-fail-under=80
    - name: Upload coverage
      uses: codecov/codecov-action@v4

  security:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - name: Run bandit
      run: pip install bandit && bandit -r app/ -f json -o bandit-report.json
    - name: Run safety
      run: pip install safety && safety check

  build:
    needs: [lint, test, security]
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
    - uses: actions/checkout@v4
    - name: Log in to Container Registry
      uses: docker/login-action@v3
      with:
        registry: ${{ env.REGISTRY }}
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}
    - name: Build and push Docker image
      uses: docker/build-push-action@v5
      with:
        context: .
        file: infrastructure/docker/Dockerfile
        push: true
        tags: |
          ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:latest
          ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}

  deploy-staging:
    if: github.ref == 'refs/heads/develop'
    needs: build
    runs-on: ubuntu-latest
    steps:
    - name: Deploy to staging
      run: echo "Deploy to staging server via SSH or kubectl"

  deploy-production:
    if: startsWith(github.ref, 'refs/tags/v')
    needs: build
    runs-on: ubuntu-latest
    steps:
    - name: Deploy to production
      run: echo "Deploy to production via kubectl or Helm"
```

## 6.8 Monitoring Setup

### Prometheus Configuration (`infrastructure/prometheus/prometheus.yml`)
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'apim-app'
    static_configs:
      - targets: ['apim-app:8000']
    metrics_path: '/metrics'

  - job_name: 'apim-db'
    static_configs:
      - targets: ['apim-db:3306']

  - job_name: 'apim-redis'
    static_configs:
      - targets: ['apim-redis:6379']
```

### Alert Rules (`infrastructure/prometheus/alerts.yml`)
```yaml
groups:
  - name: apim_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(apim_requests_total{status=~"5.."}[5m]) / rate(apim_requests_total[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "APIM error rate > 5% for 5 minutes"

      - alert: HighLatency
        expr: histogram_quantile(0.99, rate(apim_request_latency_seconds_bucket[5m])) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "APIM P99 latency > 1s"

      - alert: DBPoolExhaustion
        expr: apim_db_pool_active_connections / apim_db_pool_max_size > 0.9
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Database connection pool > 90% utilized"

      - alert: T24ConnectionDown
        expr: apim_t24_health_status != 1
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "T24 TCServer connection is down"
```

## 6.9 T24 TCServer Connection Testing

### Test Script: `app/scripts/test_t24.py`
```python
#!/usr/bin/env python3
import asyncio
import os
import sys
from app.adapters.t24.connector import T24Connector
from app.core.config import Settings

async def test_t24_connection(host, port, username, password, mode='http', endpoint='/BrowserWeb/servlet/BrowserServlet'):
    """Test T24 TCServer connectivity and OFS message execution."""
    settings = Settings()
    connector = T24Connector(
        host=host,
        port=port,
        username=username,
        password=password,
        mode=mode,
        http_endpoint=endpoint,
        timeout=30
    )

    print(f"Testing T24 connection to {host}:{port} (mode: {mode})...")

    # Test 1: Connection check
    try:
        is_connected = await connector.test_connection()
        if is_connected:
            print("✓ Connection successful")
        else:
            print("✗ Connection failed")
            return False
    except Exception as e:
        print(f"✗ Connection error: {e}")
        return False

    # Test 2: Simple OFS enquiry
    test_ofs = f"ENQ.CUSTOMER,CUSTOMER,0/{username}/{password},,@ID=100305"
    print(f"\nTesting OFS enquiry: {test_ofs[:50]}...")

    try:
        response = await connector.send_ofs(test_ofs)
        print(f"✓ OFS response received:")
        print(response[:500])
        return True
    except Exception as e:
        print(f"✗ OFS error: {e}")
        return False

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Test T24 TCServer connection')
    parser.add_argument('--host', required=True, help='T24 host')
    parser.add_argument('--port', type=int, default=9089, help='T24 port')
    parser.add_argument('--user', required=True, help='T24 username')
    parser.add_argument('--password', required=True, help='T24 password')
    parser.add_argument('--mode', choices=['http', 'tcp'], default='http', help='Connection mode')
    parser.add_argument('--endpoint', default='/BrowserWeb/servlet/BrowserServlet', help='HTTP endpoint')
    args = parser.parse_args()

    success = asyncio.run(test_t24_connection(
        args.host, args.port, args.user, args.password, args.mode, args.endpoint
    ))
    sys.exit(0 if success else 1)
```

### Run T24 Test
```bash
# From command line
python -m app.scripts.test_t24 \
  --host $T24_HOST \
  --port $T24_PORT \
  --user $T24_USERNAME \
  --password $T24_PASSWORD \
  --mode http

# Or using Docker
docker-compose exec apim-app python -m app.scripts.test_t24 \
  --host tcserver.bank.internal \
  --port 9089 \
  --user T24USER \
  --password T24PASS \
  --mode tcp
```

## 6.10 Database Backup Strategy

### MySQL Backup Script
```bash
#!/bin/bash
# backup_mysql.sh
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/mysql"
mkdir -p $BACKUP_DIR

# Full backup
mysqldump -h $MYSQL_HOST -u $MYSQL_USER -p$MYSQL_PASSWORD \
  --single-transaction --routines --triggers --events \
  $MYSQL_DATABASE > $BACKUP_DIR/apim_db_$DATE.sql

# Compress
gzip $BACKUP_DIR/apim_db_$DATE.sql

# Upload to S3 (optional)
# aws s3 cp $BACKUP_DIR/apim_db_$DATE.sql.gz s3://your-bucket/backups/

# Keep only last 30 days
find $BACKUP_DIR -name "apim_db_*.sql.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_DIR/apim_db_$DATE.sql.gz"
```

### Binary Log Archival (Point-in-Time Recovery)
```bash
# Enable binlog in MySQL config
# my.cnf:
# log-bin=/var/log/mysql/mysql-bin.log
# binlog_format=ROW
# expire_logs_days=7

# Archive binlogs daily
mysql -u $MYSQL_USER -p$MYSQL_PASSWORD -e "FLUSH BINARY LOGS;"
```
