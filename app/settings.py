"""
This module defines application settings loaded from environment variables.
"""

import os
from typing import List, Optional
from pydantic import BaseModel, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables with validation."""
    
    # API information
    API_KEY: str = os.getenv("MCP_API_KEY", "devkey_secure_123")  # Default development key for testing
    APP_NAME: str = "MCP Assessor Agent API"
    VERSION: str = "1.1.0"
    MINIMUM_API_KEY_LENGTH: int = int(os.getenv("MINIMUM_API_KEY_LENGTH", "8"))  # Shorter for development
    
    # Database connection information
    MSSQL_CONN_STR: Optional[str] = os.getenv("MSSQL_CONN_STR")
    POSTGRES_HOST: str = os.getenv("PGHOST", "localhost")
    POSTGRES_PORT: str = os.getenv("PGPORT", "5432")
    POSTGRES_USER: str = os.getenv("PGUSER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("PGPASSWORD", "")
    POSTGRES_DB: str = os.getenv("PGDATABASE", "postgres")
    
    # OpenAI API settings
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    
    @property
    def POSTGRES_CONN_STR(self) -> Optional[str]:
        """Construct the PostgreSQL connection string from individual settings."""
        if any(not val for val in [self.POSTGRES_HOST, self.POSTGRES_USER, self.POSTGRES_DB]):
            return None
        password_section = f":{self.POSTGRES_PASSWORD}" if self.POSTGRES_PASSWORD else ""
        return f"postgresql://{self.POSTGRES_USER}{password_section}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    # Application configuration
    MAX_RESULTS: int = int(os.getenv("MAX_RESULTS", "50"))
    ALLOWED_ORIGINS: List[str] = os.getenv("ALLOWED_ORIGINS", "http://localhost:5000").split(",")
    API_KEY_HEADER_NAME: str = os.getenv("API_KEY_HEADER_NAME", "x-api-key")
    PAGINATION_ENABLED: bool = os.getenv("PAGINATION_ENABLED", "True").lower() in ("true", "1", "yes")
    
    @field_validator("API_KEY")
    def validate_api_key(cls, v):
        """Validate and potentially generate a secure API key."""
        if not v or len(v) < int(os.getenv("MINIMUM_API_KEY_LENGTH", "8")):
            import secrets
            import string
            # Generate a secure API key if the provided one is too short or missing
            alphabet = string.ascii_letters + string.digits
            return ''.join(secrets.choice(alphabet) for _ in range(32))
        return v
    
    @field_validator("ALLOWED_ORIGINS")
    def validate_origins(cls, v):
        """Validate CORS origins."""
        if not v or not v[0]:
            return ["http://localhost:5000"]  # Default localhost origin if none provided
        return v
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True
    }