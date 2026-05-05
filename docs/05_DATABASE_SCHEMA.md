# 05 Database Schema

## 5.1 Schema Overview
- **Database Name**: `apim_db`
- **Engine**: InnoDB
- **Character Set**: `utf8mb4` with `utf8mb4_unicode_ci` collation
- **Naming Convention**: `snake_case` for tables and columns
- **All tables include**: `created_at` (DATETIME(6)), `updated_at` (DATETIME(6)) with automatic timestamps
- **UUIDs**: Stored as `CHAR(36)` for portability and readability
- **Soft Deletes**: Handled via `status` field (active/inactive/revoked) rather than deletion

## 5.2 Complete DDL — All Tables

### `consumers` — API Consumer Organizations
```sql
CREATE TABLE consumers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    uuid CHAR(36) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    status ENUM('active', 'inactive') NOT NULL DEFAULT 'active',
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    INDEX idx_consumers_status (status),
    INDEX idx_consumers_email (email),
    INDEX idx_consumers_uuid (uuid)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

---

### `api_keys` — API Keys Issued to Consumers
```sql
CREATE TABLE api_keys (
    id INT AUTO_INCREMENT PRIMARY KEY,
    uuid CHAR(36) NOT NULL UNIQUE,
    consumer_id INT NOT NULL,
    key_prefix VARCHAR(16) NOT NULL COMMENT 'Visible prefix (e.g., apim_live_8f3a9b2c)',
    key_hash VARCHAR(64) NOT NULL COMMENT 'SHA-256 hash of full key',
    name VARCHAR(255) NOT NULL,
    scopes JSON NULL COMMENT 'Array of allowed scopes',
    rate_limit_per_hour INT NOT NULL DEFAULT 1000,
    rate_limit_per_minute INT NOT NULL DEFAULT 100,
    expires_at DATETIME(6) NULL,
    last_used_at DATETIME(6) NULL,
    status ENUM('active', 'revoked', 'expired') NOT NULL DEFAULT 'active',
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    revoked_at DATETIME(6) NULL,
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    CONSTRAINT fk_api_keys_consumer FOREIGN KEY (consumer_id) REFERENCES consumers(id) ON DELETE RESTRICT,
    INDEX idx_api_keys_consumer (consumer_id),
    INDEX idx_api_keys_prefix (key_prefix),
    INDEX idx_api_keys_hash (key_hash),
    INDEX idx_api_keys_status (status),
    INDEX idx_api_keys_uuid (uuid),
    INDEX idx_api_keys_expires (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

---

### `admin_users` — Dashboard Admin Accounts
```sql
CREATE TABLE admin_users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    uuid CHAR(36) NOT NULL UNIQUE,
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL COMMENT 'bcrypt hash',
    role ENUM('superadmin', 'admin', 'viewer') NOT NULL DEFAULT 'viewer',
    last_login_at DATETIME(6) NULL,
    status ENUM('active', 'locked', 'inactive') NOT NULL DEFAULT 'active',
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    INDEX idx_admin_username (username),
    INDEX idx_admin_email (email),
    INDEX idx_admin_role (role),
    INDEX idx_admin_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

---

### `data_sources` — DB Connection Configurations
```sql
CREATE TABLE data_sources (
    id INT AUTO_INCREMENT PRIMARY KEY,
    uuid CHAR(36) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    db_type ENUM('mssql', 'oracle', 'postgresql', 'mysql', 'mongodb', 't24_tcserver') NOT NULL,
    host VARCHAR(255) NOT NULL,
    port INT NOT NULL,
    database_name VARCHAR(255) NOT NULL,
    username VARCHAR(255) NOT NULL,
    password_encrypted TEXT NOT NULL COMMENT 'Fernet-encrypted password',
    connection_options JSON NULL COMMENT 'Driver-specific options',
    pool_min INT NOT NULL DEFAULT 2,
    pool_max INT NOT NULL DEFAULT 20,
    status ENUM('active', 'inactive', 'error', 'connecting') NOT NULL DEFAULT 'active',
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    INDEX idx_data_sources_type (db_type),
    INDEX idx_data_sources_status (status),
    INDEX idx_data_sources_uuid (uuid)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

---

### `api_endpoints` — Registered API Endpoints
```sql
CREATE TABLE api_endpoints (
    id INT AUTO_INCREMENT PRIMARY KEY,
    uuid CHAR(36) NOT NULL UNIQUE,
    slug VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT NULL,
    http_method ENUM('GET', 'POST', 'PUT', 'DELETE') NOT NULL,
    path_pattern VARCHAR(255) NOT NULL,
    data_source_id INT NULL,
    query_template TEXT NULL COMMENT 'SQL or JSON query template with :param placeholders',
    ofs_template_id INT NULL,
    request_schema JSON NULL COMMENT 'Pydantic schema as JSON',
    response_schema JSON NULL COMMENT 'Expected response schema',
    auth_required BOOLEAN NOT NULL DEFAULT TRUE,
    allowed_scopes JSON NULL COMMENT 'Array of required scopes',
    cache_ttl_seconds INT NOT NULL DEFAULT 0,
    status ENUM('active', 'inactive') NOT NULL DEFAULT 'active',
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    CONSTRAINT fk_endpoints_datasource FOREIGN KEY (data_source_id) REFERENCES data_sources(id) ON DELETE SET NULL,
    CONSTRAINT fk_endpoints_ofs_template FOREIGN KEY (ofs_template_id) REFERENCES ofs_templates(id) ON DELETE SET NULL,
    INDEX idx_endpoints_slug (slug),
    INDEX idx_endpoints_method (http_method),
    INDEX idx_endpoints_status (status),
    INDEX idx_endpoints_datasource (data_source_id),
    INDEX idx_endpoints_uuid (uuid)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

---

### `ofs_templates` — T24 OFS Message Templates
```sql
CREATE TABLE ofs_templates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    uuid CHAR(36) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT NULL,
    ofs_type ENUM('enquiry', 'transaction') NOT NULL,
    application_name VARCHAR(100) NOT NULL COMMENT 'T24 application (e.g., CUSTOMER, FUNDS.TRANSFER)',
    ofs_message_template TEXT NOT NULL COMMENT 'OFS template with {{VARIABLE}} placeholders',
    variable_definitions JSON NOT NULL COMMENT 'Variable names, types, required flags',
    t24_version VARCHAR(20) NOT NULL DEFAULT '0',
    status ENUM('active', 'inactive') NOT NULL DEFAULT 'active',
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    INDEX idx_ofs_templates_name (name),
    INDEX idx_ofs_templates_type (ofs_type),
    INDEX idx_ofs_templates_application (application_name),
    INDEX idx_ofs_templates_status (status),
    INDEX idx_ofs_templates_uuid (uuid)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

---

### `request_logs` — API Request Audit Records (Partitioned by Month)
```sql
CREATE TABLE request_logs (
    id BIGINT AUTO_INCREMENT NOT NULL,
    request_id CHAR(36) NOT NULL COMMENT 'UUID for request tracing',
    api_key_id INT NULL,
    consumer_id INT NULL,
    endpoint_id INT NULL,
    http_method VARCHAR(10) NOT NULL,
    path TEXT NOT NULL,
    query_params JSON NULL,
    request_body_hash VARCHAR(64) NULL COMMENT 'SHA-256 hash of request body',
    target_db_type VARCHAR(50) NULL,
    target_data_source_id INT NULL,
    response_status_code INT NOT NULL,
    response_time_ms INT NULL,
    error_code VARCHAR(50) NULL,
    error_message TEXT NULL,
    client_ip VARCHAR(45) NOT NULL COMMENT 'Supports IPv6',
    user_agent TEXT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (id, created_at),  -- For partitioning
    CONSTRAINT fk_request_logs_api_key FOREIGN KEY (api_key_id) REFERENCES api_keys(id) ON DELETE SET NULL,
    CONSTRAINT fk_request_logs_consumer FOREIGN KEY (consumer_id) REFERENCES consumers(id) ON DELETE SET NULL,
    CONSTRAINT fk_request_logs_endpoint FOREIGN KEY (endpoint_id) REFERENCES api_endpoints(id) ON DELETE SET NULL,
    CONSTRAINT fk_request_logs_datasource FOREIGN KEY (target_data_source_id) REFERENCES data_sources(id) ON DELETE SET NULL,
    INDEX idx_request_logs_request_id (request_id),
    INDEX idx_request_logs_api_key (api_key_id),
    INDEX idx_request_logs_consumer (consumer_id),
    INDEX idx_request_logs_endpoint (endpoint_id),
    INDEX idx_request_logs_status_code (response_status_code),
    INDEX idx_request_logs_error_code (error_code),
    INDEX idx_request_logs_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
PARTITION BY RANGE (YEAR(created_at) * 100 + MONTH(created_at)) (
    PARTITION p202601 VALUES LESS THAN (202602),
    PARTITION p202602 VALUES LESS THAN (202603),
    PARTITION p202603 VALUES LESS THAN (202604),
    PARTITION p202604 VALUES LESS THAN (202605),
    PARTITION p202605 VALUES LESS THAN (202606),
    PARTITION p202606 VALUES LESS THAN (202607),
    PARTITION p202607 VALUES LESS THAN (202608),
    PARTITION p202608 VALUES LESS THAN (202609),
    PARTITION p202609 VALUES LESS THAN (202610),
    PARTITION p202610 VALUES LESS THAN (202611),
    PARTITION p202611 VALUES LESS THAN (202612),
    PARTITION p202612 VALUES LESS THAN (202701),
    PARTITION p_future VALUES LESS THAN MAXVALUE
);
```

---

### `rate_limit_counters` — Redis Fallback Tracking
```sql
CREATE TABLE rate_limit_counters (
    id INT AUTO_INCREMENT PRIMARY KEY,
    api_key_id INT NOT NULL,
    window_start DATETIME(6) NOT NULL COMMENT 'Start of rate limit window',
    window_type ENUM('minute', 'hour') NOT NULL,
    request_count INT NOT NULL DEFAULT 1,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    CONSTRAINT fk_rlc_api_key FOREIGN KEY (api_key_id) REFERENCES api_keys(id) ON DELETE CASCADE,
    INDEX idx_rlc_key_window (api_key_id, window_type, window_start),
    INDEX idx_rlc_cleanup (window_start)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

---

### `audit_trail` — Admin Action Audit Log (Immutable)
```sql
CREATE TABLE audit_trail (
    id INT AUTO_INCREMENT PRIMARY KEY,
    uuid CHAR(36) NOT NULL UNIQUE,
    admin_user_id INT NOT NULL,
    action_type ENUM('CREATE', 'UPDATE', 'DELETE', 'LOGIN', 'LOGOUT', 'KEY_ROTATE', 'TEST') NOT NULL,
    resource_type VARCHAR(50) NOT NULL COMMENT 'e.g., api_endpoint, data_source, api_key',
    resource_id VARCHAR(36) NULL COMMENT 'UUID of affected resource',
    old_value JSON NULL COMMENT 'Previous state (null for CREATE)',
    new_value JSON NULL COMMENT 'New state (null for DELETE)',
    ip_address VARCHAR(45) NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    CONSTRAINT fk_audit_admin_user FOREIGN KEY (admin_user_id) REFERENCES admin_users(id) ON DELETE RESTRICT,
    INDEX idx_audit_admin_user (admin_user_id),
    INDEX idx_audit_action_type (action_type),
    INDEX idx_audit_resource_type (resource_type),
    INDEX idx_audit_resource_id (resource_id),
    INDEX idx_audit_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```
**Note**: No UPDATE or DELETE triggers allowed on this table in production. Audit records are append-only.

---

### `db_connection_health` — Connection Health Check Log
```sql
CREATE TABLE db_connection_health (
    id INT AUTO_INCREMENT PRIMARY KEY,
    data_source_id INT NOT NULL,
    check_timestamp DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    status ENUM('ok', 'error', 'timeout') NOT NULL,
    latency_ms INT NULL,
    error_message TEXT NULL,
    CONSTRAINT fk_dch_datasource FOREIGN KEY (data_source_id) REFERENCES data_sources(id) ON DELETE CASCADE,
    INDEX idx_dch_datasource (data_source_id),
    INDEX idx_dch_timestamp (check_timestamp),
    INDEX idx_dch_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

---

### `consumer_endpoint_permissions` — Explicit Permission Grants
```sql
CREATE TABLE consumer_endpoint_permissions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    consumer_id INT NOT NULL,
    endpoint_id INT NOT NULL,
    granted_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    granted_by INT NOT NULL COMMENT 'Admin user who granted permission',
    CONSTRAINT fk_cep_consumer FOREIGN KEY (consumer_id) REFERENCES consumers(id) ON DELETE CASCADE,
    CONSTRAINT fk_cep_endpoint FOREIGN KEY (endpoint_id) REFERENCES api_endpoints(id) ON DELETE CASCADE,
    CONSTRAINT fk_cep_granted_by FOREIGN KEY (granted_by) REFERENCES admin_users(id) ON DELETE RESTRICT,
    UNIQUE KEY uk_consumer_endpoint (consumer_id, endpoint_id),
    INDEX idx_cep_consumer (consumer_id),
    INDEX idx_cep_endpoint (endpoint_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

## 5.3 Indexes — Justification

| Index | Table | Justification |
|---|---|---|
| `idx_consumers_status` | consumers | Filter consumers by active/inactive status in admin UI |
| `idx_consumers_email` | consumers | Unique lookup for consumer login/identification |
| `idx_api_keys_consumer` | api_keys | Join to consumers, find all keys for a consumer |
| `idx_api_keys_prefix` | api_keys | Fast lookup during auth (prefix-based search) |
| `idx_api_keys_hash` | api_keys | Auth validation (exact match on hash) |
| `idx_api_keys_status` | api_keys | Filter active/revoked keys in admin UI |
| `idx_api_keys_expires` | api_keys | Scheduled job to mark expired keys |
| `idx_admin_username` | admin_users | Login lookup |
| `idx_admin_role` | admin_users | Filter admin users by role |
| `idx_data_sources_type` | data_sources | Filter by DB type in UI |
| `idx_data_sources_status` | data_sources | Show connection status in dashboard |
| `idx_endpoints_slug` | api_endpoints | Fast lookup during request routing |
| `idx_endpoints_datasource` | api_endpoints | Find endpoints by data source |
| `idx_ofs_templates_type` | ofs_templates | Filter enquiry vs transaction templates |
| `idx_ofs_templates_application` | ofs_templates | Find templates by T24 application name |
| `idx_request_logs_api_key` | request_logs | Usage stats per API key |
| `idx_request_logs_consumer` | request_logs | Usage stats per consumer |
| `idx_request_logs_endpoint` | request_logs | Usage stats per endpoint |
| `idx_request_logs_status_code` | request_logs | Error rate analysis |
| `idx_request_logs_error_code` | request_logs | Error breakdown reports |
| `idx_request_logs_created_at` | request_logs | Time-series queries, cleanup |
| `idx_rlc_key_window` | rate_limit_counters | Fast lookup of rate limit counters |
| `idx_audit_admin_user` | audit_trail | Filter audit by admin user |
| `idx_audit_resource_type` | audit_trail | Filter audit by resource type |
| `idx_audit_created_at` | audit_trail | Time-range queries for audit reports |
| `idx_dch_datasource` | db_connection_health | Health history per data source |

## 5.4 Partitioning Strategy

### `request_logs` Partitioning
- **Method**: `RANGE` partitioning on `YEAR(created_at) * 100 + MONTH(created_at)`
- **Partition Size**: One partition per month
- **Future Partitions**: Pre-create 12 months ahead
- **Adding New Partitions**: Monthly cron job
```sql
ALTER TABLE request_logs ADD PARTITION (
    PARTITION p202701 VALUES LESS THAN (202702)
);
```

### Retention Policy
- **Online Retention**: 13 months (for rolling analytics)
- **Archive**: After 13 months, export to cold storage (S3/GCS) as parquet files
- **Purge**: Drop oldest partition after archival
```sql
ALTER TABLE request_logs DROP PARTITION p202601;
```

## 5.5 Views

### `v_active_api_keys` — Active Keys with Consumer Info
```sql
CREATE VIEW v_active_api_keys AS
SELECT
    ak.id,
    ak.uuid,
    ak.key_prefix,
    ak.name AS key_name,
    c.name AS consumer_name,
    c.email AS consumer_email,
    ak.scopes,
    ak.rate_limit_per_hour,
    ak.rate_limit_per_minute,
    ak.last_used_at,
    ak.expires_at,
    ak.created_at
FROM api_keys ak
JOIN consumers c ON ak.consumer_id = c.id
WHERE ak.status = 'active'
  AND (ak.expires_at IS NULL OR ak.expires_at > NOW());
```

---

### `v_endpoint_stats_24h` — Request Stats per Endpoint (24h)
```sql
CREATE VIEW v_endpoint_stats_24h AS
SELECT
    e.id AS endpoint_id,
    e.slug AS endpoint_slug,
    e.name AS endpoint_name,
    COUNT(rl.id) AS request_count,
    AVG(rl.response_time_ms) AS avg_latency_ms,
    COUNT(CASE WHEN rl.response_status_code >= 400 THEN 1 END) AS error_count,
    (COUNT(CASE WHEN rl.response_status_code >= 400 THEN 1 END) / COUNT(rl.id)) * 100 AS error_rate_pct
FROM api_endpoints e
LEFT JOIN request_logs rl ON e.id = rl.endpoint_id
    AND rl.created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
GROUP BY e.id, e.slug, e.name;
```

---

### `v_consumer_usage_summary` — Aggregated Usage per Consumer
```sql
CREATE VIEW v_consumer_usage_summary AS
SELECT
    c.id AS consumer_id,
    c.name AS consumer_name,
    COUNT(DISTINCT ak.id) AS active_key_count,
    COUNT(rl.id) AS total_requests_30d,
    AVG(rl.response_time_ms) AS avg_latency_ms,
    COUNT(CASE WHEN rl.response_status_code >= 400 THEN 1 END) AS error_count_30d
FROM consumers c
LEFT JOIN api_keys ak ON c.id = ak.consumer_id AND ak.status = 'active'
LEFT JOIN request_logs rl ON ak.id = rl.api_key_id
    AND rl.created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
GROUP BY c.id, c.name;
```

## 5.6 Stored Procedures

### `sp_rotate_api_key` — Key Rotation with Grace Period
```sql
DELIMITER $$
CREATE PROCEDURE sp_rotate_api_key(
    IN p_old_key_id INT,
    IN p_grace_period_hours INT
)
BEGIN
    DECLARE v_new_key_id INT;
    DECLARE v_consumer_id INT;
    DECLARE v_new_key_prefix VARCHAR(16);
    DECLARE v_new_key_hash VARCHAR(64);
    DECLARE v_new_key_full VARCHAR(64);

    -- Get consumer_id from old key    SELECT consumer_id INTO v_consumer_id
    FROM api_keys WHERE id = p_old_key_id;

    -- Generate new key (full key returned to caller via OUT param or separate SELECT)
    -- In practice, key generation happens in app layer; this proc handles the rotation logic

    -- Mark old key for expiration after grace period
    UPDATE api_keys
    SET status = 'expired',
        expires_at = DATE_ADD(NOW(), INTERVAL p_grace_period_hours HOUR)
    WHERE id = p_old_key_id AND status = 'active';

    -- Log the rotation in audit trail (admin_user_id would be passed in real usage)
    -- This is a simplified version; in practice, use a trigger or app-level audit

END$$
DELIMITER ;
```

---

### `sp_purge_old_logs` — Automated Log Archival
```sql
DELIMITER $$
CREATE PROCEDURE sp_purge_old_logs(
    IN p_retention_months INT
)
BEGIN
    DECLARE v_cutoff_date DATETIME(6);

    SET v_cutoff_date = DATE_SUB(NOW(), INTERVAL p_retention_months MONTH);

    -- Archive to archive table or external storage (simplified - just delete old logs)
    -- In production: INSERT INTO request_logs_archive SELECT * FROM request_logs WHERE created_at < v_cutoff_date;

    DELETE FROM request_logs
    WHERE created_at < v_cutoff_date
      AND created_at < DATE_SUB(NOW(), INTERVAL 13 MONTH);  -- Safety: never delete last 13 months

    -- Clean up old rate limit counters
    DELETE FROM rate_limit_counters
    WHERE window_start < DATE_SUB(NOW(), INTERVAL 48 HOUR);

    -- Clean up old health check records
    DELETE FROM db_connection_health
    WHERE check_timestamp < DATE_SUB(NOW(), INTERVAL 90 DAY);

END$$
DELIMITER ;
```

## 5.7 Sample Seed Data

### Admin User (Superadmin)
```sql
INSERT INTO admin_users (uuid, username, email, password_hash, role, status)
VALUES (
    UUID(),
    'admin',
    'admin@apim.local',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5ND0.RfpOxG2',  -- password: Admin123!
    'superadmin',
    'active'
);
```

---

### Sample Consumers
```sql
INSERT INTO consumers (uuid, name, description, email, status)
VALUES
    (UUID(), 'Mobile Banking App', 'Consumer for mobile banking application', 'mobile@bank.local', 'active'),
    (UUID(), 'Internet Banking Portal', 'Consumer for web banking portal', 'internet@bank.local', 'active'),
    (UUID(), 'Third-Party Analytics', 'External analytics provider', 'analytics@partner.local', 'active');
```

---

### Sample Data Sources
```sql
-- MSSQL Data Source
INSERT INTO data_sources (uuid, name, db_type, host, port, database_name, username, password_encrypted, connection_options, pool_min, pool_max, status)
VALUES (
    UUID(), 'Production MSSQL', 'mssql', 'mssql.prod.internal', 1433, 'banking_db',
    'apim_user', 'gAAAAABk...',  -- Fernet-encrypted password
    '{"driver": "ODBC Driver 17 for SQL Server", "encrypt": true}',
    2, 20, 'active'
);

-- Oracle Data Source
INSERT INTO data_sources (uuid, name, db_type, host, port, database_name, username, password_encrypted, connection_options, pool_min, pool_max, status)
VALUES (
    UUID(), 'Production Oracle', 'oracle', 'oracle.prod.internal', 1521, 'BANKDB',
    'apim_user', 'gAAAAABk...',
    '{"mode": "thin", "service_name": "BANKDB"}',
    2, 20, 'active'
);

-- PostgreSQL Data Source
INSERT INTO data_sources (uuid, name, db_type, host, port, database_name, username, password_encrypted, connection_options, pool_min, pool_max, status)
VALUES (
    UUID(), 'Production PostgreSQL', 'postgresql', 'pg.prod.internal', 5432, 'banking_db',
    'apim_user', 'gAAAAABk...',
    '{"ssl": true}',
    2, 20, 'active'
);

-- MySQL Data Source
INSERT INTO data_sources (uuid, name, db_type, host, port, database_name, username, password_encrypted, connection_options, pool_min, pool_max, status)
VALUES (
    UUID(), 'Production MySQL', 'mysql', 'mysql.prod.internal', 3306, 'banking_db',
    'apim_user', 'gAAAAABk...',
    '{"charset": "utf8mb4"}',
    2, 20, 'active'
);

-- MongoDB Data Source
INSERT INTO data_sources (uuid, name, db_type, host, port, database_name, username, password_encrypted, connection_options, pool_min, pool_max, status)
VALUES (
    UUID(), 'Production MongoDB', 'mongodb', 'mongo.prod.internal', 27017, 'banking_db',
    'apim_user', 'gAAAAABk...',
    '{"auth_source": "admin", "replica_set": "rs0"}',
    2, 20, 'active'
);

-- T24 TCServer Data Source
INSERT INTO data_sources (uuid, name, db_type, host, port, database_name, username, password_encrypted, connection_options, pool_min, pool_max, status)
VALUES (
    UUID(), 'T24 TCServer Production', 't24_tcserver', 't24.prod.internal', 9089, 'T24',
    'T24USER', 'gAAAAABk...',
    '{"connection_mode": "http", "http_endpoint": "/BrowserWeb/servlet/BrowserServlet", "timeout_seconds": 30, "max_retries": 3}',
    2, 10, 'active'
);
```

---

### Sample API Endpoints
```sql
-- Get these IDs after inserting data sources and OFS templates
-- Assuming data_source_id = 3 (PostgreSQL) and ofs_template_id = 1, 2

INSERT INTO api_endpoints (uuid, slug, name, description, http_method, path_pattern, data_source_id, query_template, ofs_template_id, request_schema, response_schema, auth_required, allowed_scopes, cache_ttl_seconds, status)
VALUES
    -- Endpoint 1: Customer by ID (PostgreSQL)
    (UUID(), 'customer-by-id', 'Get Customer by ID', 'Retrieve customer details by account ID', 'POST', '/query/customer-by-id', 3,
     'SELECT * FROM customers WHERE id = :account_id', NULL,
     '{"type": "object", "properties": {"account_id": {"type": "string"}}, "required": ["account_id"]}',
     '{"type": "object", "properties": {"id": {"type": "string"}, "name": {"type": "string"}, "email": {"type": "string"}}}',
     TRUE, '["customer:read"]', 60, 'active'),

    -- Endpoint 2: Account Balance (MSSQL)
    (UUID(), 'account-balance', 'Get Account Balance', 'Retrieve account balance by account number', 'GET', '/query/account-balance', 1,
     'SELECT account_no, balance, currency FROM accounts WHERE account_no = :account_no', NULL,
     '{"type": "object", "properties": {"account_no": {"type": "string"}}, "required": ["account_no"]}',
     '{"type": "object", "properties": {"account_no": {"type": "string"}, "balance": {"type": "number"}, "currency": {"type": "string"}}}',
     TRUE, '["account:read"]', 30, 'active'),

    -- Endpoint 3: T24 Customer Enquiry
    (UUID(), 't24-customer-enquiry', 'T24 Customer Enquiry', 'Run CUSTOMER enquiry via T24', 'POST', '/t24/enquiry/customer', NULL,
     NULL, 1,
     '{"type": "object", "properties": {"variables": {"type": "object"}}, "required": ["variables"]}',
     '{"type": "object", "properties": {"enquiry": {"type": "string"}, "record": {"type": "object"}}}',
     TRUE, '["t24:enquiry"]', 0, 'active'),

    -- Endpoint 4: T24 Funds Transfer
    (UUID(), 't24-funds-transfer', 'T24 Funds Transfer', 'Post FUNDS.TRANSFER transaction', 'POST', '/t24/transaction', NULL,
     NULL, 2,
     '{"type": "object", "properties": {"application": {"type": "string"}, "variables": {"type": "object"}}, "required": ["application", "variables"]}',
     '{"type": "object", "properties": {"transaction_id": {"type": "string"}, "status": {"type": "string"}}}',
     TRUE, '["t24:transaction"]', 0, 'active'),

    -- Endpoint 5: Transaction History (Oracle)
    (UUID(), 'transaction-history', 'Get Transaction History', 'Retrieve last N transactions for account', 'POST', '/query/transaction-history', 2,
     'SELECT * FROM transactions WHERE account_id = :account_id AND trans_date >= :start_date ORDER BY trans_date DESC LIMIT :limit', NULL,
     '{"type": "object", "properties": {"account_id": {"type": "string"}, "start_date": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["account_id"]}',
     '{"type": "array", "items": {"type": "object"}}',
     TRUE, '["transaction:read"]', 300, 'active');
```

---

### Sample OFS Templates
```sql
INSERT INTO ofs_templates (uuid, name, description, ofs_type, application_name, ofs_message_template, variable_definitions, t24_version, status)
VALUES
    -- Template 1: Customer Enquiry
    (UUID(), 'Customer Enquiry', 'Retrieve customer details via T24 enquiry', 'enquiry', 'CUSTOMER',
     'ENQ.CUSTOMER,CUSTOMER,0/{{T24_USER}}/{{T24_PASS}},,@ID={{ACCOUNT_NUMBER}}',
     '{"ACCOUNT_NUMBER": {"type": "string", "required": true}}',
     '0', 'active'),

    -- Template 2: Funds Transfer Transaction
    (UUID(), 'Funds Transfer', 'Post funds transfer transaction to T24', 'transaction', 'FUNDS.TRANSFER',
     'FUNDS.TRANSFER,FUNDS.TRANSFER,INPUT/{{T24_USER}}/{{T24_PASS}},,DEBIT.ACCT={{DEBIT_ACCT}},CREDIT.ACCT={{CREDIT_ACCT}},AMOUNT={{AMOUNT}},VALUE.DATE={{VALUE_DATE}}',
     '{"DEBIT_ACCT": {"type": "string", "required": true}, "CREDIT_ACCT": {"type": "string", "required": true}, "AMOUNT": {"type": "string", "required": true}, "VALUE_DATE": {"type": "string", "required": false}}',
     '0', 'active');
```

---

### Sample API Keys
```sql
-- Generate actual keys in application; these are placeholder hashes
INSERT INTO api_keys (uuid, consumer_id, key_prefix, key_hash, name, scopes, rate_limit_per_hour, rate_limit_per_minute, status, created_at)
VALUES
    (UUID(), 1, 'apim_live_8f3a9b2c', 'a1b2c3d4e5f6...', 'Mobile App Production Key',
     '["customer:read", "account:read", "transaction:read"]', 5000, 200, 'active', NOW()),
    (UUID(), 2, 'apim_live_7e2d8f1a', 'b2c3d4e5f6a7...', 'Internet Banking Key',
     '["customer:read", "account:read", "t24:enquiry"]', 10000, 500, 'active', NOW()),
    (UUID(), 3, 'apim_live_5c9a3b7e', 'c3d4e5f6a7b8...', 'Analytics Partner Key',
     '["transaction:read"]', 2000, 100, 'active', NOW());
```
