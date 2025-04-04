"""
This module defines the data models for the API.
"""

from enum import Enum
from typing import List, Optional, Dict, Any, Union

from pydantic import BaseModel, Field


class DatabaseType(str, Enum):
    """Supported database types."""
    POSTGRES = "postgres"
    MSSQL = "mssql"


class SQLQuery(BaseModel):
    """SQL query request model."""
    db: DatabaseType = Field(..., description="Database to use")
    query: str = Field(..., description="SQL query to execute")
    params: Optional[List[Any]] = Field(None, description="Query parameters")
    page: Optional[int] = Field(1, ge=1, description="Page number (starting from 1)")
    page_size: Optional[int] = Field(None, ge=1, description="Number of records per page")


class NLPrompt(BaseModel):
    """Natural language prompt request model."""
    db: DatabaseType = Field(..., description="Database to use")
    prompt: str = Field(..., description="Natural language query to translate to SQL")


class QueryResult(BaseModel):
    """SQL query result model."""
    status: str = Field(..., description="Success or error status")
    data: List[Dict[str, Any]] = Field(..., description="Query results as a list of dictionaries")
    execution_time: float = Field(..., description="Query execution time in seconds")
    pagination: Dict[str, Any] = Field(..., description="Pagination metadata")


class SQLTranslation(BaseModel):
    """Natural language to SQL translation result model."""
    status: str = Field(..., description="Success or error status")
    sql: str = Field(..., description="Translated SQL query")
    explanation: str = Field(..., description="Explanation of the SQL query")


class SchemaItem(BaseModel):
    """Database schema item model."""
    table_name: str = Field(..., description="Table name")
    column_name: str = Field(..., description="Column name")
    data_type: str = Field(..., description="Data type of column")
    is_nullable: bool = Field(..., description="Whether the column can be null")
    column_default: Optional[str] = Field(None, description="Default value for column")
    is_primary_key: bool = Field(False, description="Whether the column is a primary key")
    is_foreign_key: bool = Field(False, description="Whether the column is a foreign key")
    references_table: Optional[str] = Field(None, description="Referenced table for foreign keys")
    references_column: Optional[str] = Field(None, description="Referenced column for foreign keys")


class SchemaResponse(BaseModel):
    """Database schema response model."""
    status: str = Field(..., description="Success or error status")
    db_schema: List[SchemaItem] = Field(..., description="Database schema information")


class SchemaSummary(BaseModel):
    """Database schema summary response model."""
    status: str = Field(..., description="Success or error status")
    summary: List[str] = Field(..., description="List of table names")


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Success or error status")
    message: str = Field(..., description="Health check message")
    database_status: Dict[str, bool] = Field(..., description="Database connection status")