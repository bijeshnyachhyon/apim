# Core Settings and Configuration
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
import os

class Settings(BaseSettings):
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    # Application
    APP_ENV: str = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    APP_DEBUG: bool = False
    APP_LOG_LEVEL: str = "INFO"
    APP_LOG_FORMAT: str = "json"

    # Security
    SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "RS256"
    JWT_PRIVATE_KEY_PATH: Optional[str] = None
    JWT_PUBLIC_KEY_PATH: Optional[str] = None
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # API Key
    API_KEY_PREFIX: str = "apim_live_"
    API_KEY_HASH_ALGORITHM: str = "sha256"

    # Encryption (Fernet key for credential storage)
    ENCRYPTION_KEY: str = ""

    # Management MySQL Database
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_DATABASE: str = "apim_db"
    MYSQL_USER: str = "apim_user"
    MYSQL_PASSWORD: str = ""
    MYSQL_POOL_SIZE: int = 20
    MYSQL_MAX_OVERFLOW: int = 10
    MYSQL_ECHO: bool = False

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0
    REDIS_POOL_SIZE: int = 50

    # Temenos T24
    T24_HOST: Optional[str] = None
    T24_PORT: int = 9089
    T24_USERNAME: Optional[str] = None
    T24_PASSWORD: Optional[str] = None
    T24_OFS_VERSION: str = "0"
    T24_CONNECTION_MODE: str = "http"  # http or tcp
    T24_HTTP_ENDPOINT: str = "/BrowserWeb/servlet/BrowserServlet"
    T24_TIMEOUT_SECONDS: int = 30
    T24_MAX_RETRIES: int = 3

    # Monitoring
    PROMETHEUS_ENABLED: bool = True
    PROMETHEUS_PORT: int = 9090
    METRICS_ENABLED: bool = True
    STRUCTLOG_ENABLED: bool = True

    # Rate Limiting
    DEFAULT_RATE_LIMIT_PER_HOUR: int = 1000
    DEFAULT_RATE_LIMIT_PER_MINUTE: int = 100
    GLOBAL_RATE_LIMIT_PER_MINUTE: int = 10000

    # CORS
    CORS_ORIGINS: List[str] = Field(default_factory=lambda: ["*"])
    CORS_CREDENTIALS: bool = True
    CORS_METHODS: List[str] = Field(default_factory=lambda: ["GET", "POST", "PUT", "DELETE"])
    CORS_HEADERS: List[str] = Field(default_factory=lambda: ["*"])

    # Dashboard
    DASHBOARD_ENABLED: bool = True
    DASHBOARD_PATH: str = "/dashboard"
    DASHBOARD_SECRET_KEY: str = ""

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v

    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+aiomysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"

    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


settings = Settings()
