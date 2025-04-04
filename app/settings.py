"""
This module provides settings for the FastAPI application.
"""

import os
from typing import Optional

from pydantic import BaseModel
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    # API settings
    API_TITLE: str = "MCP Assessor Agent API"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "A secure FastAPI intermediary service for efficient and safe database querying"
    API_PREFIX: str = "/api"
    
    # Security settings
    API_KEY_HEADER_NAME: str = "X-API-Key"
    API_KEY_MIN_LENGTH: int = 16
    API_KEY: str = os.environ.get("API_KEY", "mcp_assessor_api_default_key_2024")
    
    # Database settings
    DB_POSTGRES_URL: str = os.environ.get("DATABASE_URL", "")
    DB_MSSQL_URL: Optional[str] = os.environ.get("MSSQL_URL", None)
    
    # Performance settings
    MAX_RESULTS: int = 100
    TIMEOUT_SECONDS: int = 30
    
    # OpenAI settings
    OPENAI_API_KEY: Optional[str] = os.environ.get("OPENAI_API_KEY", None)
    
    class Config:
        env_file = ".env"


# Create settings instance
settings = Settings()