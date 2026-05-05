# Abstract Base Adapter for all database connectors
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime

class QueryResult:
    def __init__(self, records: List[Dict[str, Any]], execution_time_ms: float):
        self.records = records
        self.count = len(records)
        self.execution_time_ms = execution_time_ms

class HealthStatus:
    def __init__(self, status: str, latency_ms: Optional[float] = None, error_message: Optional[str] = None):
        self.status = status  # ok, error, timeout
        self.latency_ms = latency_ms
        self.error_message = error_message

class BaseAdapter(ABC):
    """Abstract base class for all database adapters."""

    def __init__(self, name: str, db_type: str, host: str, port: int, database: str, username: str, password: str, pool_min: int = 2, pool_max: int = 20, options: Optional[Dict] = None):
        self.name = name
        self.db_type = db_type
        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = password
        self.pool_min = pool_min
        self.pool_max = pool_max
        self.options = options or {}
        self._connected = False

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection pool."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close all connections."""
        pass

    @abstractmethod
    async def execute_query(self, query: str, params: Dict[str, Any]) -> QueryResult:
        """Execute a parameterized query and return results."""
        pass

    @abstractmethod
    async def health_check(self) -> HealthStatus:
        """Check connection health."""
        pass

    @property
    def is_connected(self) -> bool:
        return self._connected

    def _start_timer(self) -> datetime:
        return datetime.now()

    def _end_timer(self, start: datetime) -> float:
        return (datetime.now() - start).total_seconds() * 1000
