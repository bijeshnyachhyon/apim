# Adapter Factory - creates appropriate DB adapter based on type
from typing import Dict, Optional, Type
from app.adapters.base import BaseAdapter
from app.adapters.mssql import MSSQLAdapter
from app.adapters.oracle import OracleAdapter
from app.adapters.postgresql import PostgreSQLAdapter
from app.adapters.mysql import MySQLAdapter
from app.adapters.mongodb import MongoDBAdapter

class AdapterFactory:
    """Factory to create database adapters based on db_type."""

    @staticmethod
    def create_adapter(
        name: str,
        db_type: str,
        host: str,
        port: int,
        database: str,
        username: str,
        password: str,
        pool_min: int = 2,
        pool_max: int = 20,
        options: Optional[Dict] = None
    ) -> BaseAdapter:
        db_type = db_type.lower()

        if db_type == "mssql":
            return MSSQLAdapter(name, host, port, database, username, password, pool_min, pool_max, options)
        elif db_type == "oracle":
            return OracleAdapter(name, host, port, database, username, password, pool_min, pool_max, options)
        elif db_type == "postgresql":
            return PostgreSQLAdapter(name, host, port, database, username, password, pool_min, pool_max, options)
        elif db_type == "mysql":
            return MySQLAdapter(name, host, port, database, username, password, pool_min, pool_max, options)
        elif db_type == "mongodb":
            return MongoDBAdapter(name, host, port, database, username, password, pool_min, pool_max, options)
        else:
            raise ValueError(f"Unsupported database type: {db_type}")
