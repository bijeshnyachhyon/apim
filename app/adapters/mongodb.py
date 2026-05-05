# MongoDB Adapter (for target MongoDB databases)
try:
    import motor.motor_asyncio
except ImportError:
    motor = None

from typing import Dict, List, Any, Optional
from datetime import datetime
from app.adapters.base import BaseAdapter, QueryResult, HealthStatus

class MongoDBAdapter(BaseAdapter):
    def __init__(self, name: str, host: str, port: int, database: str, username: str, password: str, pool_min: int = 2, pool_max: int = 20, options: Optional[Dict] = None):
        super().__init__(name, "mongodb", host, port, database, username, password, pool_min, pool_max, options)
        self._client: Optional[Any] = None
        self._auth_source = self.options.get("auth_source", "admin") if self.options else "admin"
        self._replica_set = self.options.get("replica_set") if self.options else None

    async def connect(self) -> None:
        if self._client is None and motor is not None:
            uri = f"mongodb://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}?authSource={self._auth_source}"
            if self._replica_set:
                uri += f"&replicaSet={self._replica_set}"
            self._client = motor.motor_asyncio.AsyncIOMotorClient(
                uri,
                minPoolSize=self.pool_min,
                maxPoolSize=self.pool_max,
            )
            self._connected = True

    async def disconnect(self) -> None:
        if self._client:
            self._client.close()
            self._client = None
            self._connected = False

    async def execute_query(self, query: Dict[str, Any], params: Dict[str, Any]) -> QueryResult:
        if not self._client:
            await self.connect()

        start = self._start_timer()
        db = self._client[self.database]

        # query is expected to be a JSON string or dict with: collection, operation, filter, projection, etc.
        if isinstance(query, str):
            import json
            query_spec = json.loads(query)
        else:
            query_spec = query

        collection_name = query_spec.get("collection")
        operation = query_spec.get("operation", "find")
        filter_spec = query_spec.get("filter", {})
        projection = query_spec.get("projection")
        limit = query_spec.get("limit", 0)
        skip = query_spec.get("skip", 0)
        sort = query_spec.get("sort")

        # Substitute params into filter
        filter_spec = self._substitute_params(filter_spec, params)

        collection = db[collection_name]
        result = []

        if operation == "find":
            cursor = collection.find(filter_spec, projection)
            if skip:
                cursor = cursor.skip(skip)
            if limit:
                cursor = cursor.limit(limit)
            if sort:
                cursor = cursor.sort(sort)
            async for doc in cursor:
                doc["_id"] = str(doc["_id"])  # Convert ObjectId to string
                result.append(doc)
        elif operation == "find_one":
            doc = await collection.find_one(filter_spec, projection)
            if doc:
                doc["_id"] = str(doc["_id"])
                result = [doc]
        elif operation == "aggregate":
            pipeline = query_spec.get("pipeline", [])
            pipeline = self._substitute_params(pipeline, params)
            cursor = collection.aggregate(pipeline)
            async for doc in cursor:
                if "_id" in doc:
                    doc["_id"] = str(doc["_id"])
                result.append(doc)

        execution_time = self._end_timer(start)
        return QueryResult(result, execution_time)

    def _substitute_params(self, obj: Any, params: Dict[str, Any]) -> Any:
        """Recursively substitute {{param}} in query spec."""
        import re
        if isinstance(obj, dict):
            return {k: self._substitute_params(v, params) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._substitute_params(item, params) for item in obj]
        elif isinstance(obj, str):
            # Replace {{param}} with actual value
            def replace(match):
                key = match.group(1)
                return str(params.get(key, match.group(0)))
            return re.sub(r"\{\{(\w+)\}\}", replace, obj)
        return obj

    async def health_check(self) -> HealthStatus:
        try:
            start = self._start_timer()
            if not self._client:
                await self.connect()
            await self._client.admin.command("ping")
            latency = self._end_timer(start)
            return HealthStatus("ok", latency_ms=latency)
        except Exception as e:
            return HealthStatus("error", error_message=str(e))
