# Centralized API Management System (APIM)

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.11+-green)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111.0-009688)

Production-grade Centralized API Gateway & Management Platform built with **Python (FastAPI)** and **MySQL**, supporting multi-database integration and **Temenos T24 TCServer OFS messaging**.

---

## Features

### Core Capabilities
- **Single Entry Point**: Unified REST API gateway for all third-party applications
- **Multi-Database Support**: MS SQL Server, Oracle, PostgreSQL, MySQL, MongoDB
- **T24 TCServer Integration**: OFS message builder, enquiry execution, transaction posting
- **Authentication**: JWT (RS256) + API Key (SHA-256 hashed)
- **Rate Limiting**: Per-key and per-endpoint limits with Redis backing
- **Audit Trail**: Immutable audit logging for all admin actions and API requests
- **Dashboard**: Web-based admin UI with real-time analytics

### Security & Compliance
- TLS 1.3 support
- AES-256 encryption for stored credentials (Fernet)
- OWASP API Security Top 10 compliance
- Structured JSON logging with structlog
- Parameterized queries (SQL injection prevention)

### Observability
- Prometheus metrics endpoint (`/metrics`)
- Grafana dashboards for API analytics
- Request tracing with unique request IDs
- P99 latency < 200ms (DB queries), < 500ms (T24)

---

## Quick Start

### Prerequisites
- Python 3.11+
- MySQL 8.0+
- Redis 7.0+
- (Optional) Docker Desktop

### 1. Clone & Install
```bash
git clone <repository-url>
cd apim
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your database, Redis, and T24 settings
```

### 3. Generate Keys
```bash
# Generate JWT RSA key pair
mkdir -p keys
openssl genrsa -out keys/jwt_private.pem 2048
openssl rsa -in keys/jwt_private.pem -pubout -out keys/jwt_public.pem

# Generate Fernet encryption key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Copy output to ENCRYPTION_KEY in .env
```

### 4. Start Infrastructure
```bash
# With Docker
docker-compose -f docker-compose.dev.yml up -d

# Or native MySQL/Redis installation
# See docs/EXECUTE.md for details
```

### 5. Run Migrations & Seed
```bash
alembic upgrade head
python -m app.scripts.seed_db
# Save the generated API keys from the output!
```

### 6. Start Application
```bash
uvicorn app.main:app --reload --port 8000
```

### 7. Access
| URL | Description |
|---|---|
| http://localhost:8000/docs | Swagger API Documentation |
| http://localhost:8000/dashboard | Admin Dashboard |
| http://localhost:8000/health | Health Check |

---

## Documentation

| Document | Description |
|---|---|
| `docs/01_PRODUCT_REQUIREMENTS.md` | Product Requirements (PRD) |
| `docs/02_SYSTEM_ARCHITECTURE.md` | System Architecture & Data Flows |
| `docs/03_DASHBOARD_DESIGN.md` | Dashboard UI/UX Design |
| `docs/04_API_DEVELOPMENT_SPECS.md` | API Endpoint Specifications |
| `docs/05_DATABASE_SCHEMA.md` | MySQL Schema (DDL, Views, Procedures) |
| `docs/06_DEPLOYMENT.md` | Docker, Kubernetes, CI/CD Guide |
| `docs/EXECUTE.md` | Step-by-Step Usage Guide |

---

## API Overview

### Authentication
```bash
# Get JWT token
curl -X POST http://localhost:8000/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "Admin123!"}'
```

### Query Execution
```bash
# Execute registered endpoint
curl -X POST http://localhost:8000/api/v1/query/customer-by-id \
  -H "X-API-Key: apim_live_xxxx" \
  -d '{"account_id": "100305"}'
```

### T24 OFS Operations
```bash
# T24 Enquiry
curl -X POST http://localhost:8000/api/v1/t24/enquiry/customer \
  -H "X-API-Key: apim_live_xxxx" \
  -d '{"variables": {"ACCOUNT_NUMBER": "100305"}}'

# T24 Transaction
curl -X POST http://localhost:8000/api/v1/t24/transaction \
  -H "X-API-Key: apim_live_xxxx" \
  -d '{"application": "FUNDS.TRANSFER", "variables": {...}}'
```

---

## Project Structure

```
apim/
├── app/
│   ├── main.py              # FastAPI application entry
│   ├── core/                # Config, security, dependencies
│   ├── api/v1/             # API route handlers
│   ├── adapters/            # DB adapters (MSSQL, Oracle, PG, MySQL, Mongo)
│   │   └── t24/             # T24 TCServer connector
│   ├── models/              # SQLAlchemy ORM + Pydantic schemas
│   ├── services/            # Business logic (routing, audit, metrics)
│   ├── dashboard/           # Jinja2 templates + static assets
│   └── db/                 # Session management
├── docs/                   # Documentation (6 MD files)
├── migrations/              # Alembic database migrations
├── infrastructure/
│   ├── docker/             # Dockerfile, nginx config, SSL
│   └── kubernetes/         # K8s manifests (deployment, service, ingress)
├── .env.example            # Environment variables template
├── requirements.txt        # Python dependencies
└── README.md
```

---

## Deployment

### Docker Compose (Development)
```bash
docker-compose -f docker-compose.dev.yml up -d
```

### Docker Compose (Production)
```bash
docker-compose up -d --build
```

### Kubernetes
```bash
kubectl apply -f infrastructure/kubernetes/namespace.yaml
kubectl apply -f infrastructure/kubernetes/
```

---

## Testing

```bash
# Run all tests with coverage
pytest app/tests/ --cov=app --cov-report=html

# Run specific test types
pytest app/tests/unit/ -v
pytest app/tests/integration/ -v
```

---

## License

[Your License Here]

---

## Support

For issues and feature requests, please use the GitHub issue tracker.
