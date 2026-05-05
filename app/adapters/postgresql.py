# PostgreSQL Adapter (for target PostgreSQL databases)
import asyncpg
from typing import Dict, List, Any, Optional
from datetime import datetime
from app.adapters.base import BaseAdapter, QueryResult, HealthStatus

class PostgreSQLAdapter(BaseAdapter):
    def __init__(self, name: str, host: str, port: int, database: str, username: str, password: str, pool_min: int = 2, pool_max: int = 20, options: Optional[Dict] = None):
        super().__init__(name, "postgresql", host, port, database, username, password, pool_min, pool_max, options)
        self._pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> None:
        if self._pool is None:
            ssl = self.options.get("ssl", False) if self.options else False
            self._pool = await asyncpg.create_pool(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.username,
                password=self.password,
                min_size=self.pool_min,
                max_size=self.pool_max,
                ssl=ssl,
            )
            self._connected = True

    async def disconnect(self) -> None:
        if self._pool:
            await self._pool.close()
            self._pool = None
            self._connected = False

    async def execute_query(self, query: str, params: Dict[str, Any]) -> QueryResult:
        if not self._pool:
            await self.connect()

        start = self._start_timer()
        async with self._pool.acquire() as conn:
            # Convert named params to positional ($1, $2, ...)
            # asyncpg uses $1, $2 style, not named params
            # We need to convert :param to $1, $2 based on order
            converted_query, values = self._convert_params(query, params)
            rows = await conn.fetch(converted_query, *values)
            execution_time = self._end_timer(start)

            # Convert Record objects to dicts
            result = [dict(r) for r in rows]
            # Convert datetime/date to ISO strings
            for row in result:
                for key, value in row.items():
                    if isinstance(value, datetime):
                        row[key] = value.isoformat()
            return QueryResult(result, execution_time)

    def _convert_params(self, query: str, params: Dict[str, Any]) -> tuple[str, list]:
        """Convert named params (:param) to positional ($1, $2) for asyncpg."""
        import re
        sorted_params = sorted(params.items(), key=lambda x: query.index(f":{x[0]}") if f":{x[0]}" in query else len(query))
        values = []
        new_query = query
        idx = 1
        for name, value in sorted_params:
            placeholder = f":{name}"
            if placeholder in new_query:
                new_query = new_query.replace(placeholder, f"${idx}", 1)
                values.append(value)
                idx += 1
        return new_query, values

    async def health_check(self) -> HealthStatus:
        try:
            start = self._start_timer()
            if not self._pool:
                await self.connect()
            async with self._pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            latency = self._end_timer(start)
            return HealthStatus("ok", latency_ms=latency)
        except Exception as e:
            return HealthStatus("error", error_message=str(e))
