# Oracle Adapter (for target Oracle databases)
try:
    import oracledb
except ImportError:
    oracledb = None

from typing import Dict, List, Any, Optional
from datetime import datetime
from app.adapters.base import BaseAdapter, QueryResult, HealthStatus

class OracleAdapter(BaseAdapter):
    def __init__(self, name: str, host: str, port: int, database: str, username: str, password: str, pool_min: int = 2, pool_max: int = 20, options: Optional[Dict] = None):
        super().__init__(name, "oracle", host, port, database, username, password, pool_min, pool_max, options)
        self._pool: Optional[any] = None
        self._mode = self.options.get("mode", "thin") if self.options else "thin"
        self._service_name = self.options.get("service_name") if self.options else None

    async def connect(self) -> None:
        if self._pool is None and oracledb is not None:
            dsn = f"{self.host}:{self.port}/{self.database}"
            if self._service_name:
                dsn = f"{self.host}:{self.port}/{self._service_name}"

            self._pool = oracledb.create_pool(
                user=self.username,
                password=self.password,
                dsn=dsn,
                min=self.pool_min,
                max=self.pool_max,
                mode=oracledb.AUTH_MODE_DEFAULT,
            )
            self._connected = True

    async def disconnect(self) -> None:
        if self._pool:
            self._pool.close()
            self._pool = None
            self._connected = False

    async def execute_query(self, query: str, params: Dict[str, Any]) -> QueryResult:
        if not self._pool:
            await self.connect()

        start = self._start_timer()
        async with self._pool.acquire() as conn:
            cursor = conn.cursor()
            try:
                # Convert :param to :1, :2 for oracledb
                converted_query, values = self._convert_params(query, params)
                await cursor.execute(converted_query, values)
                rows = await cursor.fetchall()

                # Get column names
                columns = [col[0].lower() for col in cursor.description]
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
            finally:
                cursor.close()

    def _convert_params(self, query: str, params: Dict[str, Any]) -> tuple[str, list]:
        import re
        sorted_params = sorted(params.items(), key=lambda x: query.index(f":{x[0]}") if f":{x[0]}" in query else len(query))
        values = []
        new_query = query
        idx = 1
        for name, value in sorted_params:
            placeholder = f":{name}"
            if placeholder in new_query:
                new_query = new_query.replace(placeholder, f":{idx}", 1)
                values.append(value)
                idx += 1
        return new_query, values

    async def health_check(self) -> HealthStatus:
        try:
            start = self._start_timer()
            if not self._pool:
                await self.connect()
            async with self._pool.acquire() as conn:
                cursor = conn.cursor()
                await cursor.execute("SELECT 1 FROM DUAL")
                await cursor.fetchone()
                cursor.close()
            latency = self._end_timer(start)
            return HealthStatus("ok", latency_ms=latency)
        except Exception as e:
            return HealthStatus("error", error_message=str(e))
