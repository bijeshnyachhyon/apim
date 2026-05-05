# Seed script to populate initial data
import asyncio
import os
import sys
from datetime import datetime

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.core.security import hash_password, generate_api_key
from app.db.session import engine, AsyncSessionLocal
from app.models.db.base import (
    Consumer, AdminUser, DataSource, ApiEndpoint, OsfTemplate, ApiKey
)
from app.services.encryption import encrypt_password

async def seed_database():
    """Seed initial data for development."""
    async with AsyncSessionLocal() as db:
        # Check if already seeded
        from sqlalchemy import select, func
        count = await db.scalar(select(func.count()).select_from(Consumer))
        if count > 0:
            print("Database already seeded. Skipping...")
            return

        print("Seeding database...")

        # 1. Admin User (Superadmin)
        admin = AdminUser(
            uuid="admin-0000-0000-0000-000000000001",
            username="admin",
            email="admin@apim.local",
            password_hash=hash_password("Admin123!"),
            role="superadmin",
            status="active",
        )
        db.add(admin)

        # 2. Sample Consumers
        consumer1 = Consumer(
            uuid="cons-1000-0000-0000-000000000001",
            name="Mobile Banking App",
            description="Consumer for mobile banking application",
            email="mobile@bank.local",
            status="active",
        )
        consumer2 = Consumer(
            uuid="cons-2000-0000-0000-000000000002",
            name="Internet Banking Portal",
            description="Consumer for web banking portal",
            email="internet@bank.local",
            status="active",
        )
        consumer3 = Consumer(
            uuid="cons-3000-0000-0000-000000000003",
            name="Third-Party Analytics",
            description="External analytics provider",
            email="analytics@partner.local",
            status="active",
        )
        db.add_all([consumer1, consumer2, consumer3])
        await db.flush()

        # 3. Data Sources (passwords encrypted)
        ds_postgres = DataSource(
            uuid="ds-1000-0000-0000-000000000001",
            name="Production PostgreSQL",
            db_type="postgresql",
            host="pg.prod.internal",
            port=5432,
            database_name="banking_db",
            username="apim_user",
            password_encrypted=encrypt_password("pg_password_here"),
            connection_options={"ssl": True},
            pool_min=2,
            pool_max=20,
        )
        ds_mssql = DataSource(
            uuid="ds-2000-0000-0000-000000000002",
            name="Production MSSQL",
            db_type="mssql",
            host="mssql.prod.internal",
            port=1433,
            database_name="banking_db",
            username="apim_user",
            password_encrypted=encrypt_password("mssql_password_here"),
            connection_options={"driver": "ODBC Driver 17 for SQL Server"},
            pool_min=2,
            pool_max=20,
        )
        ds_t24 = DataSource(
            uuid="ds-6000-0000-0000-000000000006",
            name="T24 TCServer Production",
            db_type="t24_tcserver",
            host="t24.prod.internal",
            port=9089,
            database_name="T24",
            username="T24USER",
            password_encrypted=encrypt_password("t24_password_here"),
            connection_options={
                "connection_mode": "http",
                "http_endpoint": "/BrowserWeb/servlet/BrowserServlet",
                "timeout_seconds": 30,
                "max_retries": 3,
            },
            pool_min=2,
            pool_max=10,
        )
        db.add_all([ds_postgres, ds_mssql, ds_t24])
        await db.flush()

        # 4. OFS Templates
        ofs_enquiry = OsfTemplate(
            uuid="ofs-1000-0000-0000-000000000001",
            name="Customer Enquiry",
            description="Retrieve customer details via T24 enquiry",
            ofs_type="enquiry",
            application_name="CUSTOMER",
            ofs_message_template="ENQ.CUSTOMER,CUSTOMER,0/{{T24_USER}}/{{T24_PASS}},,@ID={{ACCOUNT_NUMBER}}",
            variable_definitions={
                "ACCOUNT_NUMBER": {"type": "string", "required": True}
            },
            t24_version="0",
            status="active",
        )
        ofs_transaction = OsfTemplate(
            uuid="ofs-2000-0000-0000-000000000002",
            name="Funds Transfer",
            description="Post funds transfer transaction to T24",
            ofs_type="transaction",
            application_name="FUNDS.TRANSFER",
            ofs_message_template="FUNDS.TRANSFER,FUNDS.TRANSFER,INPUT/{{T24_USER}}/{{T24_PASS}},,DEBIT.ACCT={{DEBIT_ACCT}},CREDIT.ACCT={{CREDIT_ACCT}},AMOUNT={{AMOUNT}},VALUE.DATE={{VALUE_DATE}}",
            variable_definitions={
                "DEBIT_ACCT": {"type": "string", "required": True},
                "CREDIT_ACCT": {"type": "string", "required": True},
                "AMOUNT": {"type": "string", "required": True},
                "VALUE_DATE": {"type": "string", "required": False},
            },
            t24_version="0",
            status="active",
        )
        db.add_all([ofs_enquiry, ofs_transaction])
        await db.flush()

        # 5. API Endpoints
        ep1 = ApiEndpoint(
            uuid="ep-1000-0000-0000-000000000001",
            slug="customer-by-id",
            name="Get Customer by ID",
            description="Retrieve customer details by account ID",
            http_method="POST",
            path_pattern="/query/customer-by-id",
            data_source_id=ds_postgres.id,
            query_template="SELECT * FROM customers WHERE id = :account_id",
            request_schema={"type": "object", "properties": {"account_id": {"type": "string"}}, "required": ["account_id"]},
            response_schema={"type": "object", "properties": {"id": {"type": "string"}, "name": {"type": "string"}}},
            auth_required=True,
            allowed_scopes=["customer:read"],
            cache_ttl_seconds=60,
            status="active",
        )
        ep2 = ApiEndpoint(
            uuid="ep-2000-0000-0000-000000000002",
            slug="t24-customer-enquiry",
            name="T24 Customer Enquiry",
            description="Run CUSTOMER enquiry via T24",
            http_method="POST",
            path_pattern="/t24/enquiry/customer",
            data_source_id=None,
            query_template=None,
            ofs_template_id=ofs_enquiry.id,
            request_schema={"type": "object", "properties": {"variables": {"type": "object"}}, "required": ["variables"]},
            response_schema={"type": "object", "properties": {"enquiry": {"type": "string"}, "record": {"type": "object"}}},
            auth_required=True,
            allowed_scopes=["t24:enquiry"],
            status="active",
        )
        ep3 = ApiEndpoint(
            uuid="ep-3000-0000-0000-000000000003",
            slug="t24-funds-transfer",
            name="T24 Funds Transfer",
            description="Post FUNDS.TRANSFER transaction",
            http_method="POST",
            path_pattern="/t24/transaction",
            data_source_id=None,
            query_template=None,
            ofs_template_id=ofs_transaction.id,
            request_schema={"type": "object", "properties": {"application": {"type": "string"}, "variables": {"type": "object"}}, "required": ["application", "variables"]},
            response_schema={"type": "object", "properties": {"transaction_id": {"type": "string"}, "status": {"type": "string"}}},
            auth_required=True,
            allowed_scopes=["t24:transaction"],
            status="active",
        )
        db.add_all([ep1, ep2, ep3])
        await db.flush()

        # 6. API Keys (generate with proper hashing)
        full_key1, prefix1, hash1 = generate_api_key()
        key1 = ApiKey(
            uuid="key-1000-0000-0000-000000000001",
            consumer_id=consumer1.id,
            key_prefix=prefix1,
            key_hash=hash1,
            name="Mobile App Production Key",
            scopes=["customer:read", "account:read"],
            rate_limit_per_hour=5000,
            rate_limit_per_minute=200,
            status="active",
        )
        print(f"\nGenerated API Key for Mobile App:")
        print(f"  Full Key (save this!): {full_key1}")
        print(f"  Prefix: {prefix1}")

        full_key2, prefix2, hash2 = generate_api_key()
        key2 = ApiKey(
            uuid="key-2000-0000-0000-000000000002",
            consumer_id=consumer2.id,
            key_prefix=prefix2,
            key_hash=hash2,
            name="Internet Banking Key",
            scopes=["customer:read", "t24:enquiry"],
            rate_limit_per_hour=10000,
            rate_limit_per_minute=500,
            status="active",
        )
        print(f"\nGenerated API Key for Internet Banking:")
        print(f"  Full Key (save this!): {full_key2}")
        print(f"  Prefix: {prefix2}")

        db.add_all([key1, key2])

        await db.commit()
        print("\nDatabase seeded successfully!")

if __name__ == "__main__":
    asyncio.run(seed_database())
