# SQLAlchemy ORM Models
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum, JSON, Index, CHAR, BIGINT
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.session import Base

class TimeStampedModel:
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

class Consumer(Base, TimeStampedModel):
    __tablename__ = "consumers"

    id = Column(Integer, primary_key=True)
    uuid = Column(CHAR(36), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    status = Column(Enum("active", "inactive", name="consumer_status"), nullable=False, default="active")

    api_keys = relationship("ApiKey", back_populates="consumer")
    permissions = relationship("ConsumerEndpointPermission", back_populates="consumer")

class ApiKey(Base, TimeStampedModel):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True)
    uuid = Column(CHAR(36), unique=True, nullable=False, index=True)
    consumer_id = Column(Integer, ForeignKey("consumers.id", ondelete="RESTRICT"), nullable=False, index=True)
    key_prefix = Column(String(16), nullable=False, index=True)
    key_hash = Column(String(64), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    scopes = Column(JSON, nullable=True)
    rate_limit_per_hour = Column(Integer, nullable=False, default=1000)
    rate_limit_per_minute = Column(Integer, nullable=False, default=100)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(Enum("active", "revoked", "expired", name="api_key_status"), nullable=False, default="active")
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    consumer = relationship("Consumer", back_populates="api_keys")
    request_logs = relationship("RequestLog", back_populates="api_key")
    permissions = relationship("ConsumerEndpointPermission", back_populates="api_key")

class AdminUser(Base, TimeStampedModel):
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True)
    uuid = Column(CHAR(36), unique=True, nullable=False)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum("superadmin", "admin", "viewer", name="admin_role"), nullable=False, default="viewer")
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(Enum("active", "locked", "inactive", name="admin_status"), nullable=False, default="active")

    audit_trails = relationship("AuditTrail", back_populates="admin_user")
    granted_permissions = relationship("ConsumerEndpointPermission", foreign_keys="ConsumerEndpointPermission.granted_by", back_populates="granted_by_user")

class DataSource(Base, TimeStampedModel):
    __tablename__ = "data_sources"

    id = Column(Integer, primary_key=True)
    uuid = Column(CHAR(36), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    db_type = Column(Enum("mssql", "oracle", "postgresql", "mysql", "mongodb", "t24_tcserver", name="db_type"), nullable=False, index=True)
    host = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False)
    database_name = Column(String(255), nullable=False)
    username = Column(String(255), nullable=False)
    password_encrypted = Column(Text, nullable=False)
    connection_options = Column(JSON, nullable=True)
    pool_min = Column(Integer, nullable=False, default=2)
    pool_max = Column(Integer, nullable=False, default=20)
    status = Column(Enum("active", "inactive", "error", "connecting", name="ds_status"), nullable=False, default="active")

    endpoints = relationship("ApiEndpoint", back_populates="data_source")
    ofs_templates = relationship("OsfTemplate", back_populates="data_source")
    health_checks = relationship("DbConnectionHealth", back_populates="data_source")

class ApiEndpoint(Base, TimeStampedModel):
    __tablename__ = "api_endpoints"

    id = Column(Integer, primary_key=True)
    uuid = Column(CHAR(36), unique=True, nullable=False, index=True)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    http_method = Column(Enum("GET", "POST", "PUT", "DELETE", name="http_method"), nullable=False)
    path_pattern = Column(String(255), nullable=False)
    data_source_id = Column(Integer, ForeignKey("data_sources.id", ondelete="SET NULL"), nullable=True, index=True)
    query_template = Column(Text, nullable=True)
    ofs_template_id = Column(Integer, ForeignKey("ofs_templates.id", ondelete="SET NULL"), nullable=True)
    request_schema = Column(JSON, nullable=True)
    response_schema = Column(JSON, nullable=True)
    auth_required = Column(Boolean, nullable=False, default=True)
    allowed_scopes = Column(JSON, nullable=True)
    cache_ttl_seconds = Column(Integer, nullable=False, default=0)
    status = Column(Enum("active", "inactive", name="endpoint_status"), nullable=False, default="active")

    data_source = relationship("DataSource", back_populates="endpoints")
    ofs_template = relationship("OsfTemplate", back_populates="endpoints")
    request_logs = relationship("RequestLog", back_populates="endpoint")
    permissions = relationship("ConsumerEndpointPermission", back_populates="endpoint")

class OsfTemplate(Base, TimeStampedModel):
    __tablename__ = "ofs_templates"

    id = Column(Integer, primary_key=True)
    uuid = Column(CHAR(36), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    ofs_type = Column(Enum("enquiry", "transaction", name="ofs_type"), nullable=False, index=True)
    application_name = Column(String(100), nullable=False, index=True)
    ofs_message_template = Column(Text, nullable=False)
    variable_definitions = Column(JSON, nullable=False)
    t24_version = Column(String(20), nullable=False, default="0")
    status = Column(Enum("active", "inactive", name="ofs_status"), nullable=False, default="active")

    endpoints = relationship("ApiEndpoint", back_populates="ofs_template")
    data_source = relationship("DataSource", back_populates="ofs_templates")

class RequestLog(Base, TimeStampedModel):
    __tablename__ = "request_logs"

    id = Column(BIGINT, primary_key=True, autoincrement=True)
    request_id = Column(CHAR(36), nullable=False, index=True)
    api_key_id = Column(Integer, ForeignKey("api_keys.id", ondelete="SET NULL"), nullable=True, index=True)
    consumer_id = Column(Integer, ForeignKey("consumers.id", ondelete="SET NULL"), nullable=True, index=True)
    endpoint_id = Column(Integer, ForeignKey("api_endpoints.id", ondelete="SET NULL"), nullable=True, index=True)
    http_method = Column(String(10), nullable=False)
    path = Column(Text, nullable=False)
    query_params = Column(JSON, nullable=True)
    request_body_hash = Column(String(64), nullable=True)
    target_db_type = Column(String(50), nullable=True)
    target_data_source_id = Column(Integer, ForeignKey("data_sources.id", ondelete="SET NULL"), nullable=True)
    response_status_code = Column(Integer, nullable=False, index=True)
    response_time_ms = Column(Integer, nullable=True)
    error_code = Column(String(50), nullable=True, index=True)
    error_message = Column(Text, nullable=True)
    client_ip = Column(String(45), nullable=False)
    user_agent = Column(Text, nullable=True)

    api_key = relationship("ApiKey", back_populates="request_logs")
    consumer = relationship("Consumer", back_populates="request_logs")
    endpoint = relationship("ApiEndpoint", back_populates="request_logs")
    target_data_source = relationship("DataSource", back_populates="health_checks")

class RateLimitCounter(Base, TimeStampedModel):
    __tablename__ = "rate_limit_counters"

    id = Column(Integer, primary_key=True)
    api_key_id = Column(Integer, ForeignKey("api_keys.id", ondelete="CASCADE"), nullable=False, index=True)
    window_start = Column(DateTime(timezone=True), nullable=False, index=True)
    window_type = Column(Enum("minute", "hour", name="window_type"), nullable=False)
    request_count = Column(Integer, nullable=False, default=1)

class AuditTrail(Base):
    __tablename__ = "audit_trail"

    id = Column(Integer, primary_key=True)
    uuid = Column(CHAR(36), unique=True, nullable=False)
    admin_user_id = Column(Integer, ForeignKey("admin_users.id", ondelete="RESTRICT"), nullable=False, index=True)
    action_type = Column(Enum("CREATE", "UPDATE", "DELETE", "LOGIN", "LOGOUT", "KEY_ROTATE", "TEST", name="action_type"), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False, index=True)
    resource_id = Column(String(36), nullable=True, index=True)
    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    admin_user = relationship("AdminUser", back_populates="audit_trails")

class DbConnectionHealth(Base, TimeStampedModel):
    __tablename__ = "db_connection_health"

    id = Column(Integer, primary_key=True)
    data_source_id = Column(Integer, ForeignKey("data_sources.id", ondelete="CASCADE"), nullable=False, index=True)
    check_timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    status = Column(Enum("ok", "error", "timeout", name="health_status"), nullable=False)
    latency_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)

    data_source = relationship("DataSource", back_populates="health_checks")

class ConsumerEndpointPermission(Base, TimeStampedModel):
    __tablename__ = "consumer_endpoint_permissions"

    id = Column(Integer, primary_key=True)
    consumer_id = Column(Integer, ForeignKey("consumers.id", ondelete="CASCADE"), nullable=False, index=True)
    endpoint_id = Column(Integer, ForeignKey("api_endpoints.id", ondelete="CASCADE"), nullable=False, index=True)
    granted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    granted_by = Column(Integer, ForeignKey("admin_users.id", ondelete="RESTRICT"), nullable=False)

    consumer = relationship("Consumer", back_populates="permissions")
    endpoint = relationship("ApiEndpoint", back_populates="permissions")
    api_key = relationship("ApiKey", back_populates="permissions")
    granted_by_user = relationship("AdminUser", back_populates="granted_permissions")

    __table_args__ = (
        Index("uk_consumer_endpoint", consumer_id, endpoint_id, unique=True),
    )
