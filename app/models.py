from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Annotated
from pydantic.functional_validators import BeforeValidator

# Request models with validation
class SQLQuery(BaseModel):
    """Model for SQL query execution requests."""
    db: str = Field(
        ..., 
        description="Database type (mssql or postgres)",
        pattern='^(mssql|postgres)$'
    )
    query: str = Field(
        ..., 
        description="SQL query to execute",
        min_length=1,
        max_length=5000
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "db": "postgres",
                "query": "SELECT id, name FROM parcels LIMIT 10"
            }
        }
    }

class NLPrompt(BaseModel):
    """Model for natural language to SQL translation requests."""
    db: str = Field(
        ..., 
        description="Database type (mssql or postgres)",
        pattern='^(mssql|postgres)$'
    )
    prompt: str = Field(
        ..., 
        description="Natural language query",
        min_length=1,
        max_length=1000
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "db": "postgres",
                "prompt": "Find all parcels with a total value over $500,000"
            }
        }
    }

class SchemaFilter(BaseModel):
    """Model for schema filtering options."""
    prefix: Optional[str] = Field(
        None, 
        description="Optional table name prefix filter",
        max_length=50
    )

# Response models
class QueryResult(BaseModel):
    """Model for SQL query execution results."""
    status: str
    data: List[Dict[str, Any]]
    count: int
    truncated: bool
    
class SQLTranslation(BaseModel):
    """Model for natural language to SQL translation results."""
    status: str
    sql: str
    
class SchemaResponse(BaseModel):
    """Model for database schema information."""
    status: str
    db_schema: List[Dict[str, Any]]
    
class SchemaSummary(BaseModel):
    """Model for summarized schema information."""
    status: str
    summary: List[str]
    
class HealthResponse(BaseModel):
    """Model for API health check response."""
    status: str
    db_connections: Dict[str, bool]

class ErrorResponse(BaseModel):
    """Model for error responses."""
    status: str = "error"
    detail: str
    
class SuccessResponse(BaseModel):
    """Model for generic success responses."""
    status: str = "success"
    message: str
