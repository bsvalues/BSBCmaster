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
    API_KEY: str = os.getenv("MCP_API_KEY", "devkey_secure_123")  # Default development key for testing
    APP_NAME: str = "MCP Assessor Agent API"
    VERSION: str = "1.1.0"
    MINIMUM_API_KEY_LENGTH: int = int(os.getenv("MINIMUM_API_KEY_LENGTH", "8"))  # Shorter for development
    
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
    API_KEY_HEADER_NAME: str = os.getenv("API_KEY_HEADER_NAME", "x-api-key")
    PAGINATION_ENABLED: bool = os.getenv("PAGINATION_ENABLED", "True").lower() in ("true", "1", "yes")
    
    # Validators
    @field_validator("API_KEY")
    def validate_api_key(cls, v):
        """Validate and potentially generate a secure API key."""
        min_length = 8  # Use a reasonable minimum length for development
        
        if not v or len(v) < min_length:
            if not v:
                logger.warning(f"No API key defined. Generating a secure random key of length {min_length*1.5} characters.")
            else:
                logger.warning(f"API key too short (minimum: {min_length} chars). Generating a secure random key.")
                logger.info(f"Consider setting a strong API key with the MCP_API_KEY environment variable.")
            return secrets.token_urlsafe(min_length * 2)  # Extra length for security
        return v
    
    @field_validator("ALLOWED_ORIGINS")
    def validate_origins(cls, v):
        """Validate CORS origins."""
        if not v or v == [""]:
            logger.warning("No CORS origins specified. Setting to localhost only.")
            return ["http://localhost:5000"]
        
        # Log the allowed origins for security audit
        logger.info(f"CORS allowed origins: {', '.join(v)}")
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
