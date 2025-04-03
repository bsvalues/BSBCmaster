import os
import secrets
import logging
from typing import List, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger("mcp_assessor_api")

class Settings(BaseSettings):
    """Application settings loaded from environment variables with validation."""
    
    # API configuration
    API_KEY: str = os.getenv("MCP_API_KEY", "")
    APP_NAME: str = "MCP Assessor Agent API"
    
    # Database configuration
    MSSQL_CONN_STR: Optional[str] = os.getenv("MSSQL_CONN_STR")
    POSTGRES_HOST: str = os.getenv("PGHOST", "localhost")
    POSTGRES_PORT: str = os.getenv("PGPORT", "5432")
    POSTGRES_USER: str = os.getenv("PGUSER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("PGPASSWORD", "")
    POSTGRES_DB: str = os.getenv("PGDATABASE", "postgres")
    
    # Build Postgres connection string
    @property
    def POSTGRES_CONN_STR(self) -> Optional[str]:
        if all([self.POSTGRES_HOST, self.POSTGRES_USER, self.POSTGRES_PASSWORD, self.POSTGRES_DB]):
            return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        return os.getenv("DATABASE_URL")
    
    # API settings
    MAX_RESULTS: int = int(os.getenv("MAX_RESULTS", "50"))
    ALLOWED_ORIGINS: List[str] = os.getenv("ALLOWED_ORIGINS", "http://localhost:5000").split(",")
    
    # Validators
    @field_validator("API_KEY")
    def validate_api_key(cls, v):
        """Validate and potentially generate a secure API key."""
        if not v or len(v) < 32:
            if not v:
                logger.warning("No API key defined. Generating a secure random key.")
            else:
                logger.warning("API key too short. Generating a secure random key.")
            return secrets.token_urlsafe(48)
        return v
    
    @field_validator("ALLOWED_ORIGINS")
    def validate_origins(cls, v):
        """Validate CORS origins."""
        if not v or v == [""]:
            logger.warning("No CORS origins specified. Setting to localhost only.")
            return ["http://localhost:5000"]
        return v
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True
    }

# Create a global settings instance
settings = Settings()

# Log configuration warnings for missing database connections
if not settings.MSSQL_CONN_STR:
    logger.warning("MS SQL connection string not provided")
    
if not settings.POSTGRES_CONN_STR:
    logger.warning("PostgreSQL connection string not provided")
