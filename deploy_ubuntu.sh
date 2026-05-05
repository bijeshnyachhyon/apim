#!/bin/bash
# ==============================================================================
# APIM - Centralized API Management System
# Ubuntu Server Deployment Script
# Repository: https://github.com/bijeshnyachyon/apim
# ==============================================================================
# Usage:
#   chmod +x deploy_ubuntu.sh
#   # For GitHub authentication (if repo is private):
#   export GITHUB_TOKEN=ghp_xxxxxxxxxxxx
#   sudo -E ./deploy_ubuntu.sh [--docker|--native|--k8s] [--prod|--dev]
# ==============================================================================

set -e
export DEBIAN_FRONTEND=noninteractive

# Colors (only work in bash, fallback for sh)
if [ -n "$BASH_VERSION" ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    NC='\033[0m'
else
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    NC=''
fi

# Configuration
REPO_URL="https://github.com/bijeshnyachhyon/apim.git"
APP_DIR="/opt/apim"
APP_ENV="development"
DEPLOY_MODE="native"
BRANCH="main"

# Generate credentials
DB_NAME="apim_db"
DB_USER="apim_user"
DB_PASSWORD=$(openssl rand -base64 24 | tr -d "=+/" | cut -c1-20)
REDIS_PASSWORD=$(openssl rand -base64 16 | tr -d "=+/" | cut -c1-16)
JWT_SECRET=$(openssl rand -base64 32 | tr -d "\n")
FERNET_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>/dev/null || echo "changeme$(openssl rand -base64 24)")

LOG_FILE="/var/log/apim_deploy.log"

# ==============================================================================
# Utility Functions
# ==============================================================================

log() {
    printf "${GREEN}[+]${NC} %s\n" "$1" | tee -a "$LOG_FILE"
}

warn() {
    printf "${YELLOW}[!]${NC} %s\n" "$1" | tee -a "$LOG_FILE"
}

error() {
    printf "${RED}[-]${NC} %s\n" "$1" | tee -a "$LOG_FILE" >&2
}

info() {
    printf "${BLUE}[i]${NC} %s\n" "$1" | tee -a "$LOG_FILE"
}

check_root() {
    if [ "$(id -u)" -ne 0 ]; then
        error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# ==============================================================================
# Parse Arguments
# ==============================================================================

while [ $# -gt 0 ]; do
    case $1 in
        --docker)
            DEPLOY_MODE="docker"
            shift
            ;;
        --native)
            DEPLOY_MODE="native"
            shift
            ;;
        --k8s|--kubernetes)
            DEPLOY_MODE="k8s"
            shift
            ;;
        --prod|--production)
            APP_ENV="production"
            BRANCH="main"
            shift
            ;;
        --dev|--development)
            APP_ENV="development"
            BRANCH="develop"
            shift
            ;;
        --branch)
            BRANCH="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [--docker|--native|--k8s] [--prod|--dev] [--branch <name>]"
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# ==============================================================================
# Main Deployment Steps
# ==============================================================================

log "Starting APIM deployment from GitHub: $REPO_URL"
log "Deployment Mode: $DEPLOY_MODE"
log "Environment: $APP_ENV"
log "Branch: $BRANCH"

# Step 1: System Dependencies
log "Step 1: Installing system dependencies..."
check_root
apt-get update -y

# Detect Python version
if command -v python3 >/dev/null 2>&1; then
    PYTHON_VERSION=$(python3 --version 2>/dev/null | grep -oP '\d+\.\d+' || echo "3.12")
else
    PYTHON_VERSION="3.12"
fi

log "Detected Python version: $PYTHON_VERSION"

# Install Python packages based on version
apt-get install -y curl wget git build-essential software-properties-common \
    apt-transport-https ca-certificates gnupg lsb-release openssl \
    python3 python3-dev python3-venv python3-pip \
    default-libmysqlclient-dev pkg-config libssl-dev gcc make systemd jq

log "System dependencies installed."

# Step 2: MySQL
log "Step 2: Installing MySQL..."
if command -v mysql >/dev/null 2>&1; then
    info "MySQL already installed"
else
    apt-get install -y mysql-server mysql-client
    
    # Handle MySQL service name variations
    if systemctl list-unit-files 2>/dev/null | grep -q "^mysql.service"; then
        MYSQL_SVC="mysql"
    elif systemctl list-unit-files 2>/dev/null | grep -q "^mysqld.service"; then
        MYSQL_SVC="mysqld"
    else
        MYSQL_SVC="mysql"
    fi
    
    systemctl start ${MYSQL_SVC}
    systemctl enable ${MYSQL_SVC} || true
    
    mysql -u root <<EOSQL
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '${DB_PASSWORD}';
FLUSH PRIVILEGES;
EOSQL
    
    mysql -u root -p"${DB_PASSWORD}" <<EOSQL
CREATE DATABASE IF NOT EXISTS ${DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASSWORD}';
GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO '${DB_USER}'@'localhost';
FLUSH PRIVILEGES;
EOSQL
fi
log "MySQL setup completed."

# Step 3: Redis
log "Step 3: Installing Redis..."
if command -v redis-server >/dev/null 2>&1; then
    info "Redis already installed"
else
    apt-get install -y redis-server
    sed -i "s/^# requirepass .*/requirepass ${REDIS_PASSWORD}/" /etc/redis/redis.conf || true
    sed -i "s/^appendonly .*/appendonly yes/" /etc/redis/redis.conf || true
    
    # Handle redis service - try multiple approaches
    systemctl daemon-reload 2>/dev/null || true
    
    # Try to find the correct service name
    if systemctl list-unit-files 2>/dev/null | grep -q "^redis-server.service"; then
        REDIS_SVC="redis-server"
    elif systemctl list-unit-files 2>/dev/null | grep -q "^redis.service"; then
        REDIS_SVC="redis"
    else
        REDIS_SVC="redis-server"
    fi
    
    systemctl start ${REDIS_SVC} || true
    systemctl enable ${REDIS_SVC} 2>/dev/null || systemctl enable ${REDIS_SVC}.service 2>/dev/null || true
fi
log "Redis setup completed."

# Step 4: Docker (if needed)
if [ "$DEPLOY_MODE" = "docker" ] || [ "$DEPLOY_MODE" = "k8s" ]; then
    log "Step 4: Installing Docker..."
    if ! command -v docker >/dev/null 2>&1; then
        install -m 0755 -d /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
        chmod a+r /etc/apt/keyrings/docker.gpg
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list
        apt-get update -y
        apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
        systemctl start docker
        systemctl enable docker
    fi
    log "Docker installed."
fi

# Step 5: Clone Application
log "Step 5: Setting up application..."

# Disable Git credential prompting (GitHub no longer supports password auth)
export GIT_TERMINAL_PROMPT=0
# Unset credential helpers that might cause prompts
unset GIT_ASKPASS
git config --global --unset credential.helper 2>/dev/null || true

# Check if GITHUB_TOKEN is available for authentication
if [ -n "$GITHUB_TOKEN" ]; then
    # Extract repo path from URL (remove https://)
    REPO_PATH=$(echo "$REPO_URL" | sed 's|https://||')
    AUTH_REPO_URL="https://${GITHUB_TOKEN}@${REPO_PATH}"
    info "Using GitHub token for authentication"
else
    AUTH_REPO_URL="$REPO_URL"
fi

mkdir -p "$APP_DIR"
cd "$APP_DIR"

if [ -d "$APP_DIR/.git" ]; then
    log "Repository exists. Pulling latest changes..."
    git fetch origin || warn "Failed to fetch from remote"
    git checkout "$BRANCH" 2>/dev/null || git checkout -b "$BRANCH" 2>/dev/null || true
    git pull origin "$BRANCH" 2>/dev/null || warn "Failed to pull from remote"
elif [ -f "$APP_DIR/requirements.txt" ]; then
    log "Application files already present (local deployment). Initializing git..."
    git init
    git checkout -b "$BRANCH" 2>/dev/null || true
else
    log "Cloning repository from GitHub..."
    
    # Check if repo is accessible first
    info "Checking repository accessibility..."
    if curl -s --head "$REPO_URL" | grep -q "200 OK\|301\|302"; then
        info "Repository is accessible"
    else
        warn "Repository might not exist or is not accessible"
        warn "URL: $REPO_URL"
    fi
    
    # Clone with no auth prompt
    info "Cloning from branch: $BRANCH"
    info "Clone URL: $AUTH_REPO_URL"
    
    # Try to get default branch from GitHub API
    DEFAULT_BRANCH=$(curl -s "https://api.github.com/repos/bijeshnyachhyon/apim" | grep -o '"default_branch": "[^"]*"' | cut -d'"' -f4 || echo "$BRANCH")
    info "GitHub reports default branch: $DEFAULT_BRANCH"
    
    # Try clone and capture output
    # Note: Cloning into "." requires the directory to be empty
    info "Cloning into: $APP_DIR"
    info "Directory contents before clone:"
    ls -la . 2>&1 | tee -a "$LOG_FILE"
    
    CLONE_OUTPUT=$(GIT_TERMINAL_PROMPT=0 git clone -b "$DEFAULT_BRANCH" "$AUTH_REPO_URL" . 2>&1)
    CLONE_EXIT=$?
    echo "$CLONE_OUTPUT" | tee -a "$LOG_FILE"
    
    info "Directory contents after clone:"
    ls -la . 2>&1 | tee -a "$LOG_FILE"
    
    if [ $CLONE_EXIT -eq 0 ]; then
        log "Repository cloned successfully."
        # Verify key files exist
        if [ ! -f "requirements.txt" ]; then
            error "Repository cloned but requirements.txt not found!"
            error "Files in directory:"
            ls -la . 2>&1 | tee -a "$LOG_FILE"
            error "Checking if clone went into subdirectory..."
            if [ -d "apim" ]; then
                error "Clone created 'apim' subdirectory! Moving files..."
                mv apim/* . 2>/dev/null || true
                mv apim/.git . 2>/dev/null || true
                rm -rf apim 2>/dev/null || true
            fi
            error "The repository might be empty or branch '$DEFAULT_BRANCH' doesn't exist."
            error "Please ensure:"
            error "1. Repository has files: $REPO_URL"
            error "2. Branch '$DEFAULT_BRANCH' exists"
            exit 1
        fi
    elif [ -n "$GITHUB_TOKEN" ]; then
        warn "Failed with token. Repository might not exist or token lacks access."
        warn "Ensure repo exists at: $REPO_URL"
        warn "Ensure token has 'repo' scope"
        exit 1
    else
        warn "Failed to clone. Try:"
        warn "1. Make sure repo exists: $REPO_URL"
        warn "2. Or use token: export GITHUB_TOKEN=ghp_xxxx && sudo -E ./deploy_ubuntu.sh --native"
        exit 1
    fi
fi

# Install Python deps
if [ "$DEPLOY_MODE" = "native" ]; then
    if [ ! -d "$APP_DIR/venv" ]; then
        log "Creating virtual environment..."
        python3 -m venv venv
    fi
    source venv/bin/activate
    pip install -r requirements.txt
fi

log "Application setup completed."

# Step 6: Generate Keys & Config
log "Step 6: Generating keys and configuring environment..."
cd "$APP_DIR"
mkdir -p keys

# JWT Keys
openssl genrsa -out keys/jwt_private.pem 2048 2>/dev/null
openssl rsa -in keys/jwt_private.pem -pubout -out keys/jwt_public.pem 2>/dev/null

# Create .env file
log "Creating .env file..."
cat > .env <<EOF
APP_ENV=$APP_ENV
APP_HOST=0.0.0.0
APP_PORT=8000
APP_DEBUG=$( [ "$APP_ENV" = "development" ] && echo "true" || echo "false" )
APP_LOG_LEVEL=INFO
APP_LOG_FORMAT=json
SECRET_KEY=$JWT_SECRET
JWT_ALGORITHM=RS256
JWT_PRIVATE_KEY_PATH=$APP_DIR/keys/jwt_private.pem
JWT_PUBLIC_KEY_PATH=$APP_DIR/keys/jwt_public.pem
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
API_KEY_PREFIX=apim_live_
API_KEY_HASH_ALGORITHM=sha256
ENCRYPTION_KEY=$FERNET_KEY
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=$DB_NAME
MYSQL_USER=$DB_USER
MYSQL_PASSWORD=$DB_PASSWORD
MYSQL_POOL_SIZE=20
MYSQL_MAX_OVERFLOW=10
MYSQL_ECHO=false
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=$REDIS_PASSWORD
REDIS_DB=0
REDIS_POOL_SIZE=50
T24_HOST=tcserver.bank.internal
T24_PORT=9089
T24_USERNAME=your-t24-user
T24_PASSWORD=your-t24-password
T24_OFS_VERSION=0
T24_CONNECTION_MODE=http
T24_HTTP_ENDPOINT=/BrowserWeb/servlet/BrowserServlet
T24_TIMEOUT_SECONDS=30
T24_MAX_RETRIES=3
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090
METRICS_ENABLED=true
STRUCTLOG_ENABLED=true
DEFAULT_RATE_LIMIT_PER_HOUR=1000
DEFAULT_RATE_LIMIT_PER_MINUTE=100
GLOBAL_RATE_LIMIT_PER_MINUTE=10000
CORS_ORIGINS=["*"]
CORS_CREDENTIALS=true
CORS_METHODS=["GET", "POST", "PUT", "DELETE"]
CORS_HEADERS=["*"]
DASHBOARD_ENABLED=true
DASHBOARD_PATH=/dashboard
DASHBOARD_SECRET_KEY=$JWT_SECRET
EOF
chmod 600 .env
log "Environment configured."

# Step 7: Database Migration
log "Step 7: Running database migrations..."
cd "$APP_DIR"
if [ "$DEPLOY_MODE" = "native" ]; then
    source venv/bin/activate
    python3 -m alembic -c migrations/alembic.ini upgrade head 2>/dev/null || true
else
    docker compose -f docker-compose.yml exec -T apim-app alembic upgrade head 2>/dev/null || \
    docker compose -f docker-compose.dev.yml exec -T apim-app alembic upgrade head 2>/dev/null || true
fi
log "Migrations completed."

# Step 8: Seed Database
log "Step 8: Seeding database..."
if [ "$DEPLOY_MODE" = "native" ]; then
    source venv/bin/activate
    python3 -m app.scripts.seed_db 2>/dev/null || true
else
    docker compose exec -T apim-app python3 -m app.scripts.seed_db 2>/dev/null || true
fi
log "Database seeded."

# Step 9: Start Services
if [ "$DEPLOY_MODE" = "native" ]; then
    log "Step 9: Creating systemd service..."
    cat > /etc/systemd/system/apim.service <<EOF
[Unit]
Description=Centralized API Management System
After=network.target mysql.service redis.service

[Service]
Type=simple
User=root
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"
ExecStart=$APP_DIR/venv/bin/gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --access-logfile /var/log/apim_access.log --error-logfile /var/log/apim_error.log --log-level info
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    systemctl daemon-reload
    systemctl enable apim.service
    systemctl start apim.service
    sleep 3
    systemctl status apim.service --no-pager || true
fi

if [ "$DEPLOY_MODE" = "docker" ]; then
    log "Step 9: Starting Docker services..."
    cd "$APP_DIR"
    if [ "$APP_ENV" = "production" ]; then
        docker compose -f docker-compose.yml up -d --build
    else
        docker compose -f docker-compose.dev.yml up -d --build
    fi
    sleep 10
    docker compose ps
fi

# Step 10: Verify
log "Step 10: Verifying deployment..."
sleep 2
if curl -s http://localhost:8000/health 2>/dev/null | grep -q "healthy\|degraded"; then
    log "Health check passed!"
else
    warn "Health check failed or service not reachable yet"
fi

# ==============================================================================
# Print Summary
# ==============================================================================

echo ""
printf "${GREEN}========================================${NC}\n"
printf "${GREEN}    APIM Deployment Complete!${NC}\n"
printf "${GREEN}========================================${NC}\n"
echo ""
printf "${BLUE}Deployment Mode:${NC} $DEPLOY_MODE\n"
printf "${BLUE}Environment:${NC}     $APP_ENV\n"
printf "${BLUE}Branch:${NC}         $BRANCH\n"
echo ""
printf "${YELLOW}Database Credentials:${NC}\n"
echo "  Database:   $DB_NAME"
echo "  User:       $DB_USER"
echo "  Password:   $DB_PASSWORD"
echo ""
printf "${YELLOW}Redis Password:${NC}   $REDIS_PASSWORD\n"
echo ""
printf "${YELLOW}Access URLs:${NC}\n"
echo "  Dashboard:  http://$(hostname -I | awk '{print $1}'):8000/dashboard"
echo "  API Docs:  http://$(hostname -I | awk '{print $1}'):8000/docs"
echo "  Health:     http://$(hostname -I | awk '{print $1}'):8000/health"
echo ""
printf "${YELLOW}Next Steps:${NC}\n"
echo "  1. Configure T24 settings in $APP_DIR/.env"
echo "  2. Access dashboard and login with: admin / Admin123!"
echo "  3. Save the API keys shown during seed process"
echo "  4. Check logs: journalctl -u apim.service -f"
echo ""
printf "${GREEN}========================================${NC}\n"
