"""
This module defines the Pydantic models for API requests and responses.
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="API status: 'success' or 'error'")
    message: str = Field(..., description="Status message")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    database_status: Dict[str, bool] = Field(
        ..., 
        description="Status of database connections: {'postgres': bool, 'mssql': bool}"
    )


class PaginationMetadata(BaseModel):
    """Pagination metadata for query results."""
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of records per page")
    total_items: int = Field(..., description="Total number of items matching the query")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")


class QueryResult(BaseModel):
    """SQL query result model with pagination."""
    data: List[Dict[str, Any]] = Field(..., description="Query result data")
    pagination: PaginationMetadata = Field(..., description="Pagination metadata")
    columns: List[str] = Field(..., description="Column names in the result set")
    query: str = Field(..., description="The executed SQL query")
    execution_time: float = Field(..., description="Query execution time in seconds")


class SQLQuery(BaseModel):
    """SQL query request model."""
    db: str = Field(..., description="Database to query: 'postgres' or 'mssql'", pattern="^(postgres|mssql)$")
    query: str = Field(..., description="SQL query to execute")
    page: int = Field(1, description="Page number for paginated results (starting from 1)")
    page_size: Optional[int] = Field(None, description="Number of records per page")
    

class NLPrompt(BaseModel):
    """Natural language to SQL prompt model."""
    db: str = Field(..., description="Target database type: 'postgres' or 'mssql'", pattern="^(postgres|mssql)$")
    prompt: str = Field(..., description="Natural language query prompt")
    

class SQLTranslation(BaseModel):
    """SQL translation response model."""
    query: str = Field(..., description="Translated SQL query")
    explanation: str = Field(..., description="Explanation of the translated query")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    status: str = Field("success", description="Translation status")


class SchemaColumnInfo(BaseModel):
    """Database column information."""
    name: str = Field(..., description="Column name")
    type: str = Field(..., description="Data type")
    is_primary: bool = Field(False, description="Whether the column is a primary key")
    is_nullable: bool = Field(True, description="Whether the column can be NULL")
    default: Optional[str] = Field(None, description="Default value, if any")
    description: Optional[str] = Field(None, description="Column description")


class SchemaRelationship(BaseModel):
    """Relationship between database tables."""
    table: str = Field(..., description="Referenced table name")
    from_column: str = Field(..., description="Column in source table")
    to_column: str = Field(..., description="Column in referenced table")
    type: str = Field(..., description="Relationship type (e.g., 'one-to-many')")


class SchemaTable(BaseModel):
    """Database table schema information."""
    name: str = Field(..., description="Table name")
    schema: str = Field("public", description="Schema name")
    columns: List[SchemaColumnInfo] = Field(..., description="List of columns")
    relationships: List[SchemaRelationship] = Field(default_factory=list, description="Table relationships")
    row_count: Optional[int] = Field(None, description="Approximate row count")
    description: Optional[str] = Field(None, description="Table description")


class SchemaResponse(BaseModel):
    """Full database schema response."""
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    database: str = Field(..., description="Database type ('postgres' or 'mssql')")
    tables: List[SchemaTable] = Field(..., description="List of tables in the schema")


class TableSummary(BaseModel):
    """Simplified table information for schema summary."""
    name: str = Field(..., description="Table name")
    column_count: int = Field(..., description="Number of columns")
    row_count: Optional[int] = Field(None, description="Approximate row count")
    description: Optional[str] = Field(None, description="Table description")


class SchemaSummary(BaseModel):
    """Summary of database schema."""
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    database: str = Field(..., description="Database type ('postgres' or 'mssql')")
    table_count: int = Field(..., description="Total number of tables")
    tables: List[TableSummary] = Field(..., description="List of tables with basic info")
    filtered: bool = Field(False, description="Whether the results were filtered")