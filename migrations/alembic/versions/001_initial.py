"""Initial migration - create all tables

Revision ID: 001
Revises: 
Create Date: 2026-05-05 10:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # consumers table
    op.create_table(
        'consumers',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('uuid', sa.CHAR(36), nullable=False, unique=True, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('status', sa.Enum('active', 'inactive', name='consumer_status'), nullable=False, default='active'),
        sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', mysql.DATETIME(fsp=6), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Index('idx_consumers_status', 'status'),
        sa.Index('idx_consumers_email', 'email'),
        sa.Index('idx_consumers_uuid', 'uuid'),
    )

    # admin_users table
    op.create_table(
        'admin_users',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('uuid', sa.CHAR(36), nullable=False, unique=True),
        sa.Column('username', sa.String(100), nullable=False, unique=True, index=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('role', sa.Enum('superadmin', 'admin', 'viewer', name='admin_role'), nullable=False, default='viewer'),
        sa.Column('last_login_at', mysql.DATETIME(fsp=6), nullable=True),
        sa.Column('status', sa.Enum('active', 'locked', 'inactive', name='admin_status'), nullable=False, default='active'),
        sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', mysql.DATETIME(fsp=6), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Index('idx_admin_username', 'username'),
        sa.Index('idx_admin_email', 'email'),
        sa.Index('idx_admin_role', 'role'),
        sa.Index('idx_admin_status', 'status'),
    )

    # data_sources table
    op.create_table(
        'data_sources',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('uuid', sa.CHAR(36), nullable=False, unique=True, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('db_type', sa.Enum('mssql', 'oracle', 'postgresql', 'mysql', 'mongodb', 't24_tcserver', name='db_type'), nullable=False, index=True),
        sa.Column('host', sa.String(255), nullable=False),
        sa.Column('port', sa.Integer(), nullable=False),
        sa.Column('database_name', sa.String(255), nullable=False),
        sa.Column('username', sa.String(255), nullable=False),
        sa.Column('password_encrypted', sa.Text(), nullable=False),
        sa.Column('connection_options', sa.JSON(), nullable=True),
        sa.Column('pool_min', sa.Integer(), nullable=False, default=2),
        sa.Column('pool_max', sa.Integer(), nullable=False, default=20),
        sa.Column('status', sa.Enum('active', 'inactive', 'error', 'connecting', name='ds_status'), nullable=False, default='active'),
        sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', mysql.DATETIME(fsp=6), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Index('idx_data_sources_type', 'db_type'),
        sa.Index('idx_data_sources_status', 'status'),
        sa.Index('idx_data_sources_uuid', 'uuid'),
    )

    # api_keys table
    op.create_table(
        'api_keys',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('uuid', sa.CHAR(36), nullable=False, unique=True, index=True),
        sa.Column('consumer_id', sa.Integer(), sa.ForeignKey('consumers.id', ondelete='RESTRICT'), nullable=False, index=True),
        sa.Column('key_prefix', sa.String(16), nullable=False, index=True),
        sa.Column('key_hash', sa.String(64), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('scopes', sa.JSON(), nullable=True),
        sa.Column('rate_limit_per_hour', sa.Integer(), nullable=False, default=1000),
        sa.Column('rate_limit_per_minute', sa.Integer(), nullable=False, default=100),
        sa.Column('expires_at', mysql.DATETIME(fsp=6), nullable=True),
        sa.Column('last_used_at', mysql.DATETIME(fsp=6), nullable=True),
        sa.Column('status', sa.Enum('active', 'revoked', 'expired', name='api_key_status'), nullable=False, default='active'),
        sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=False, server_default=sa.func.now()),
        sa.Column('revoked_at', mysql.DATETIME(fsp=6), nullable=True),
        sa.Column('updated_at', mysql.DATETIME(fsp=6), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Index('idx_api_keys_consumer', 'consumer_id'),
        sa.Index('idx_api_keys_prefix', 'key_prefix'),
        sa.Index('idx_api_keys_hash', 'key_hash'),
        sa.Index('idx_api_keys_status', 'status'),
        sa.Index('idx_api_keys_uuid', 'uuid'),
        sa.Index('idx_api_keys_expires', 'expires_at'),
    )

    # api_endpoints table
    op.create_table(
        'api_endpoints',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('uuid', sa.CHAR(36), nullable=False, unique=True, index=True),
        sa.Column('slug', sa.String(100), nullable=False, unique=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('http_method', sa.Enum('GET', 'POST', 'PUT', 'DELETE', name='http_method'), nullable=False),
        sa.Column('path_pattern', sa.String(255), nullable=False),
        sa.Column('data_source_id', sa.Integer(), sa.ForeignKey('data_sources.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('query_template', sa.Text(), nullable=True),
        sa.Column('ofs_template_id', sa.Integer(), sa.ForeignKey('ofs_templates.id', ondelete='SET NULL'), nullable=True),
        sa.Column('request_schema', sa.JSON(), nullable=True),
        sa.Column('response_schema', sa.JSON(), nullable=True),
        sa.Column('auth_required', sa.Boolean(), nullable=False, default=True),
        sa.Column('allowed_scopes', sa.JSON(), nullable=True),
        sa.Column('cache_ttl_seconds', sa.Integer(), nullable=False, default=0),
        sa.Column('status', sa.Enum('active', 'inactive', name='endpoint_status'), nullable=False, default='active'),
        sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', mysql.DATETIME(fsp=6), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Index('idx_endpoints_slug', 'slug'),
        sa.Index('idx_endpoints_method', 'http_method'),
        sa.Index('idx_endpoints_status', 'status'),
        sa.Index('idx_endpoints_datasource', 'data_source_id'),
        sa.Index('idx_endpoints_uuid', 'uuid'),
    )

    # ofs_templates table
    op.create_table(
        'ofs_templates',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('uuid', sa.CHAR(36), nullable=False, unique=True, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('ofs_type', sa.Enum('enquiry', 'transaction', name='ofs_type'), nullable=False, index=True),
        sa.Column('application_name', sa.String(100), nullable=False, index=True),
        sa.Column('ofs_message_template', sa.Text(), nullable=False),
        sa.Column('variable_definitions', sa.JSON(), nullable=False),
        sa.Column('t24_version', sa.String(20), nullable=False, default='0'),
        sa.Column('status', sa.Enum('active', 'inactive', name='ofs_status'), nullable=False, default='active'),
        sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', mysql.DATETIME(fsp=6), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Index('idx_ofs_templates_name', 'name'),
        sa.Index('idx_ofs_templates_type', 'ofs_type'),
        sa.Index('idx_ofs_templates_application', 'application_name'),
        sa.Index('idx_ofs_templates_status', 'status'),
        sa.Index('idx_ofs_templates_uuid', 'uuid'),
    )

    # Add foreign key after ofs_templates is created
    op.create_foreign_key('fk_endpoints_ofs_template', 'api_endpoints', 'ofs_templates', ['ofs_template_id'], ['id'], ondelete='SET NULL')

    # request_logs table (partitioned)
    op.create_table(
        'request_logs',
        sa.Column('id', sa.BIGINT(), primary_key=True, autoincrement=True),
        sa.Column('request_id', sa.CHAR(36), nullable=False, index=True),
        sa.Column('api_key_id', sa.Integer(), sa.ForeignKey('api_keys.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('consumer_id', sa.Integer(), sa.ForeignKey('consumers.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('endpoint_id', sa.Integer(), sa.ForeignKey('api_endpoints.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('http_method', sa.String(10), nullable=False),
        sa.Column('path', sa.Text(), nullable=False),
        sa.Column('query_params', sa.JSON(), nullable=True),
        sa.Column('request_body_hash', sa.String(64), nullable=True),
        sa.Column('target_db_type', sa.String(50), nullable=True),
        sa.Column('target_data_source_id', sa.Integer(), sa.ForeignKey('data_sources.id', ondelete='SET NULL'), nullable=True),
        sa.Column('response_status_code', sa.Integer(), nullable=False, index=True),
        sa.Column('response_time_ms', sa.Integer(), nullable=True),
        sa.Column('error_code', sa.String(50), nullable=True, index=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('client_ip', sa.String(45), nullable=False),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=False, server_default=sa.func.now(), index=True),
        sa.Index('idx_request_logs_api_key', 'api_key_id'),
        sa.Index('idx_request_logs_consumer', 'consumer_id'),
        sa.Index('idx_request_logs_endpoint', 'endpoint_id'),
        sa.Index('idx_request_logs_status_code', 'response_status_code'),
        sa.Index('idx_request_logs_error_code', 'error_code'),
    )

    # Partition by range on created_at
    op.execute("""
        ALTER TABLE request_logs
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
        )
    """)

    # rate_limit_counters table
    op.create_table(
        'rate_limit_counters',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('api_key_id', sa.Integer(), sa.ForeignKey('api_keys.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('window_start', mysql.DATETIME(fsp=6), nullable=False, index=True),
        sa.Column('window_type', sa.Enum('minute', 'hour', name='window_type'), nullable=False),
        sa.Column('request_count', sa.Integer(), nullable=False, default=1),
        sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=False, server_default=sa.func.now()),
        sa.Index('idx_rlc_key_window', 'api_key_id', 'window_type', 'window_start'),
        sa.Index('idx_rlc_cleanup', 'window_start'),
    )

    # audit_trail table
    op.create_table(
        'audit_trail',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('uuid', sa.CHAR(36), nullable=False, unique=True),
        sa.Column('admin_user_id', sa.Integer(), sa.ForeignKey('admin_users.id', ondelete='RESTRICT'), nullable=False, index=True),
        sa.Column('action_type', sa.Enum('CREATE', 'UPDATE', 'DELETE', 'LOGIN', 'LOGOUT', 'KEY_ROTATE', 'TEST', name='action_type'), nullable=False, index=True),
        sa.Column('resource_type', sa.String(50), nullable=False, index=True),
        sa.Column('resource_id', sa.String(36), nullable=True, index=True),
        sa.Column('old_value', sa.JSON(), nullable=True),
        sa.Column('new_value', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=False),
        sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=False, server_default=sa.func.now(), index=True),
        sa.Index('idx_audit_admin_user', 'admin_user_id'),
        sa.Index('idx_audit_action_type', 'action_type'),
        sa.Index('idx_audit_resource_type', 'resource_type'),
        sa.Index('idx_audit_resource_id', 'resource_id'),
        sa.Index('idx_audit_created_at', 'created_at'),
    )

    # db_connection_health table
    op.create_table(
        'db_connection_health',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('data_source_id', sa.Integer(), sa.ForeignKey('data_sources.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('check_timestamp', mysql.DATETIME(fsp=6), nullable=False, server_default=sa.func.now(), index=True),
        sa.Column('status', sa.Enum('ok', 'error', 'timeout', name='health_status'), nullable=False),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Index('idx_dch_datasource', 'data_source_id'),
        sa.Index('idx_dch_timestamp', 'check_timestamp'),
        sa.Index('idx_dch_status', 'status'),
    )

    # consumer_endpoint_permissions table
    op.create_table(
        'consumer_endpoint_permissions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('consumer_id', sa.Integer(), sa.ForeignKey('consumers.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('endpoint_id', sa.Integer(), sa.ForeignKey('api_endpoints.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('granted_at', mysql.DATETIME(fsp=6), nullable=False, server_default=sa.func.now()),
        sa.Column('granted_by', sa.Integer(), sa.ForeignKey('admin_users.id', ondelete='RESTRICT'), nullable=False),
        sa.Index('uk_consumer_endpoint', 'consumer_id', 'endpoint_id', unique=True),
        sa.Index('idx_cep_consumer', 'consumer_id'),
        sa.Index('idx_cep_endpoint', 'endpoint_id'),
    )

def downgrade():
    op.drop_table('consumer_endpoint_permissions')
    op.drop_table('db_connection_health')
    op.drop_table('audit_trail')
    op.drop_table('rate_limit_counters')
    op.drop_table('request_logs')
    op.drop_table('ofs_templates')
    op.drop_table('api_endpoints')
    op.drop_table('api_keys')
    op.drop_table('data_sources')
    op.drop_table('admin_users')
    op.drop_table('consumers')
