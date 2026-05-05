# MSSQL Adapter (for target MS SQL Server databases)
try:
    import aioodbc
    import pyodbc
except ImportError:
    aioodbc = None
    pyodbc = None

from typing import Dict, List, Any, Optional
from datetime import datetime
from app.adapters.base import BaseAdapter, QueryResult, HealthStatus

class MSSQLAdapter(BaseAdapter):
    def __init__(self, name: str, host: str, port: int, database: str, username: str, password: str, pool_min: int = 2, pool_max: int = 20, options: Optional[Dict] = None):
        super().__init__(name, "mssql", host, port, database, username, password, pool_min, pool_max, options)
        self._pool: Optional[any] = None
        self._driver = self.options.get("driver", "ODBC Driver 17 for SQL Server") if self.options else "ODBC Driver 17 for SQL Server"

    async def connect(self) -> None:
        if self._pool is None and aioodbc is not None:
            conn_str = (
                f"DRIVER={{{self._driver}}};"
                f"SERVER={self.host},{self.port};"
                f"DATABASE={self.database};"
                f"UID={self.username};"
                f"PWD={self.password};"
                "Encrypt=yes;" if self.options and self.options.get("encrypt") else ""
            )
            self._pool = await aioodbc.create_pool(
                dsn=conn_str,
                minsize=self.pool_min,
                maxsize=self.pool_max,
            )
            self._connected = True

    async def disconnect(self) -> None:
        if self._pool:
            self._pool.close()
            await self._pool.wait_closed()
            self._pool = None
            self._connected = False

    async def execute_query(self, query: str, params: Dict[str, Any]) -> QueryResult:
        if not self._pool:
            await self.connect()

        start = self._start_timer()
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # Convert :param to ? for pyodbc
                converted_query, values = self._convert_params(query, params)
                await cursor.execute(converted_query, *values)
                rows = await cursor.fetchall()
                columns = [column[0] for column in cursor.description]
                result = []
                for row in rows:
                    row_dict = dict(zip(columns, row))
                    # Convert datetime to ISO
                    for key, value in row_dict.items():
                        if isinstance(value, datetime):
                            row_dict[key] = value.isoformat()
                    result.append(row_dict)
                execution_time = self._end_timer(start)
                return QueryResult(result, execution_time)

    def _convert_params(self, query: str, params: Dict[str, Any]) -> tuple[str, list]:
        import re
        sorted_params = sorted(params.items(), key=lambda x: query.index(f":{x[0]}") if f":{x[0]}" in query else len(query))
        values = []
        new_query = query
        for name, value in sorted_params:
            placeholder = f":{name}"
            if placeholder in new_query:
                new_query = new_query.replace(placeholder, "?", 1)
                values.append(value)
        return new_query, values

    async def health_check(self) -> HealthStatus:
        try:
            start = self._start_timer()
            if not self._pool:
                await self.connect()
            async with self._pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SELECT 1")
                    await cursor.fetchone()
            latency = self._end_timer(start)
            return HealthStatus("ok", latency_ms=latency)
        except Exception as e:
            return HealthStatus("error", error_message=str(e))
