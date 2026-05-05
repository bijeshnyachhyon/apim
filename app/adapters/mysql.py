# MySQL Adapter (for target MySQL databases)
import aiomysql
from typing import Dict, List, Any, Optional
from datetime import datetime
from app.adapters.base import BaseAdapter, QueryResult, HealthStatus

class MySQLAdapter(BaseAdapter):
    def __init__(self, name: str, host: str, port: int, database: str, username: str, password: str, pool_min: int = 2, pool_max: int = 20, options: Optional[Dict] = None):
        super().__init__(name, "mysql", host, port, database, username, password, pool_min, pool_max, options)
        self._pool: Optional[aiomysql.Pool] = None

    async def connect(self) -> None:
        if self._pool is None:
            self._pool = await aiomysql.create_pool(
                host=self.host,
                port=self.port,
                db=self.database,
                user=self.username,
                password=self.password,
                minsize=self.pool_min,
                maxsize=self.pool_max,
                autocommit=True,
                charset=self.options.get("charset", "utf8mb4") if self.options else "utf8mb4",
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
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(query, params)
                rows = await cursor.fetchall()
                # Convert datetime objects to ISO strings for JSON serialization
                for row in rows:
                    for key, value in row.items():
                        if isinstance(value, datetime):
                            row[key] = value.isoformat()
                execution_time = self._end_timer(start)
                return QueryResult(list(rows), execution_time)

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
