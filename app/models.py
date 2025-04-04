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
    page: Optional[int] = Field(
        1, 
        description="Page number for paginated results (starting from 1)",
        ge=1
    )
    page_size: Optional[int] = Field(
        None, 
        description="Number of records per page, if None uses settings.MAX_RESULTS",
        gt=0
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "db": "postgres",
                "query": "SELECT id, name FROM parcels",
                "page": 1,
                "page_size": 25
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
class PaginationMetadata(BaseModel):
    """Model for pagination metadata."""
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of records per page")
    total_records: int = Field(..., description="Total number of records matching the query")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")
    next_page: Optional[int] = Field(None, description="Next page number, if available")
    prev_page: Optional[int] = Field(None, description="Previous page number, if available")

class QueryResult(BaseModel):
    """Model for SQL query execution results."""
    status: str = Field(..., description="Status of the query execution ('success' or 'error')")
    data: List[Dict[str, Any]] = Field(..., description="The query results as a list of records")
    count: int = Field(..., description="Total number of records matching the query")
    pagination: Optional[PaginationMetadata] = Field(
        None, 
        description="Pagination metadata for the query results"
    )
    
class SQLTranslation(BaseModel):
    """Model for natural language to SQL translation results."""
    status: str
    sql: str
    
class SchemaResponse(BaseModel):
    """Model for database schema information."""
    status: str
    db_schema: List[Dict[str, Any]]
    count: int = Field(..., description="Total number of schema items")
    pagination: Optional[PaginationMetadata] = Field(
        None, 
        description="Pagination metadata for the schema results"
    )
    
class SchemaSummary(BaseModel):
    """Model for summarized schema information."""
    status: str
    summary: List[str]
    count: int = Field(..., description="Total number of tables in summary")
    pagination: Optional[PaginationMetadata] = Field(
        None, 
        description="Pagination metadata for the schema summary results"
    )
    
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
