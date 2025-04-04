"""
This module provides settings for the FastAPI application.
"""

import os
from typing import Optional, List

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class CacheSettings(BaseModel):
    """Cache settings."""
    DEFAULT_TTL: int = 300  # Default time-to-live in seconds
    SCHEMA_CACHE_TTL: int = 3600  # Schema cache TTL (1 hour)
    QUERY_CACHE_TTL: int = 60  # Query results cache TTL (1 minute)
    ENABLED: bool = True  # Whether caching is enabled


class RateLimitSettings(BaseModel):
    """Rate limit settings."""
    ENABLED: bool = True
    DEFAULT_RATE: int = 100  # Requests per time window
    TIME_WINDOW: int = 60  # Time window in seconds
    BY_ENDPOINT: bool = True  # Whether to apply rate limiting per endpoint
    BYPASS_RATE_LIMIT_WITH_API_KEY: bool = True  # Whether to bypass rate limit with API key


class LoggingSettings(BaseModel):
    """Logging settings."""
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE: str = "fastapi.log"
    CONSOLE_LOGGING: bool = True
    FILE_LOGGING: bool = True
    REQUEST_LOGGING: bool = True


class OpenAISettings(BaseModel):
    """OpenAI settings."""
    API_KEY: Optional[str] = None
    MODEL: str = "gpt-4o"  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024
    MAX_TOKENS: int = 500
    TEMPERATURE: float = 0.0  # More deterministic for SQL generation
    TIMEOUT: int = 60  # Timeout in seconds


class Settings(BaseSettings):
    """Application settings."""
    # API settings
    API_TITLE: str = "MCP Assessor Agent API"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "A secure FastAPI intermediary service for efficient and safe database querying"
    API_PREFIX: str = "/api"
    
    # Security settings
    API_KEY_HEADER_NAME: str = "X-API-Key"
    API_KEY_MIN_LENGTH: int = 32  # Increased for better security
    API_KEY: str = os.environ.get("API_KEY", "b6212a0ff43102f608553e842293eba0ec013ff6926459f96fba31d0fabacd2e")
    ALLOWED_ORIGINS: List[str] = Field(default_factory=lambda: ["*"])
    
    # Database settings
    DB_POSTGRES_URL: str = os.environ.get("DATABASE_URL", "")
    DB_MSSQL_URL: Optional[str] = os.environ.get("MSSQL_URL", None)
    DB_CONNECTION_TIMEOUT: int = 10  # Seconds to wait for DB connection
    DB_POOL_SIZE: int = 10  # Maximum number of connections in pool
    DB_POOL_RECYCLE: int = 300  # Recycle connections after 5 minutes
    
    # Performance settings
    MAX_RESULTS: int = 100
    TIMEOUT_SECONDS: int = 30
    
    # Feature settings
    CACHE: CacheSettings = CacheSettings()
    RATE_LIMIT: RateLimitSettings = RateLimitSettings()
    LOGGING: LoggingSettings = LoggingSettings()
    OPENAI: OpenAISettings = OpenAISettings(API_KEY=os.environ.get("OPENAI_API_KEY", None))
    
    # These fields are used by the Flask app but needed for env parsing
    flask_app: Optional[str] = Field(default=None, description="Flask application path")
    flask_port: Optional[str] = Field(default=None, description="Flask port")
    fastapi_port: Optional[str] = Field(default=None, description="FastAPI port")
    fastapi_url: Optional[str] = Field(default=None, description="FastAPI URL")
    debug: Optional[bool] = Field(default=None, description="Debug mode")
    
    model_config = {
        "env_file": ".env",
        "env_nested_delimiter": "__",  # For nested settings, e.g. CACHE__ENABLED=false
        "extra": "allow"  # Allow extra fields not defined in the model
    }


# Create settings instance
settings = Settings()