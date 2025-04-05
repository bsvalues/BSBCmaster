"""
This module defines the data models for the API.
"""

import re
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any, Union, Set

from pydantic import BaseModel, Field, validator


class DatabaseType(str, Enum):
    """Supported database types."""
    POSTGRES = "postgres"
    MSSQL = "mssql"


class ParamStyle(str, Enum):
    """SQL parameter styles."""
    NAMED = "named"        # :param
    QMARK = "qmark"        # ?
    FORMAT = "format"      # %s
    NUMERIC = "numeric"    # :1


class SecurityLevel(str, Enum):
    """Security levels for query validation."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


class ParameterizedSQLQuery(BaseModel):
    """Parameterized SQL query request model."""
    db: DatabaseType = Field(..., description="Database to use")
    query: str = Field(..., description="SQL query to execute with parameter placeholders")
    params: Optional[Union[Dict[str, Any], List[Any]]] = Field({}, description="Parameters for the query (dict for named, list for qmark)")
    param_style: ParamStyle = Field(ParamStyle.NAMED, description="Parameter style to use")
    page: int = Field(1, ge=1, description="Page number (starting from 1)")
    page_size: Optional[int] = Field(50, ge=1, le=1000, description="Number of records per page")
    
    @validator('params')
    def validate_params(cls, v, values):
        """Validate that parameters match the parameter style and query."""
        if v is None:
            return {}
            
        if 'query' not in values or not values['query']:
            return v
            
        query = values['query']
        param_style = values.get('param_style', ParamStyle.NAMED)
        
        # For named parameters, params should be a dict
        if param_style == ParamStyle.NAMED:
            # Make sure params is a dict for named parameters
            if not isinstance(v, dict):
                raise ValueError("For named parameter style, params must be a dictionary")
                
            # Find all named parameters in the query
            param_matches = set()
            
            # Match :param style
            colon_params = re.findall(r':(\w+)', query)
            param_matches.update(colon_params)
            
            # Match @param style
            at_params = re.findall(r'@(\w+)', query)
            param_matches.update(at_params)
            
            # Check if all parameters in the query are provided
            missing_params = [param for param in param_matches if param not in v]
            if missing_params:
                missing_list = ", ".join(missing_params)
                raise ValueError(f"Missing parameters: {missing_list}")
                
        # For qmark style, params should be a list
        elif param_style == ParamStyle.QMARK:
            # Make sure params is a list for qmark parameters
            if not isinstance(v, list):
                raise ValueError("For qmark parameter style, params must be a list")
                
            # Count question mark placeholders
            placeholder_count = query.count('?')
            
            if placeholder_count != len(v):
                raise ValueError(f"Parameter count mismatch: {placeholder_count} placeholders, {len(v)} values")
        
        return v
    
    @validator('query')
    def validate_query(cls, v):
        """Validate that the query is not empty and is a valid SQL query."""
        if not v or not v.strip():
            raise ValueError("Query cannot be empty")
            
        # Check for basic SQL syntax
        v = v.strip()
        
        # Simple validation to ensure query starts with SELECT, INSERT, UPDATE, DELETE, etc.
        valid_starters = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'WITH', 'CREATE', 'ALTER', 'DROP', 'TRUNCATE']
        if not any(v.upper().startswith(starter) for starter in valid_starters):
            raise ValueError("Query must start with a valid SQL statement (SELECT, INSERT, UPDATE, etc.)")
            
        return v


class SQLQuery(BaseModel):
    """SQL query request model."""
    db: DatabaseType = Field(..., description="Database to use")
    query: str = Field(..., description="SQL query to execute")
    params: Optional[List[Any]] = Field(None, description="Query parameters")
    page: int = Field(1, ge=1, description="Page number (starting from 1)")
    page_size: Optional[int] = Field(50, ge=1, le=1000, description="Number of records per page")


class NLPrompt(BaseModel):
    """Natural language prompt request model."""
    db: DatabaseType = Field(..., description="Database to use")
    prompt: str = Field(..., min_length=3, max_length=1000, description="Natural language query to translate to SQL")
    include_schema: bool = Field(True, description="Whether to include schema in response")


class QueryResult(BaseModel):
    """SQL query result model."""
    status: str = Field(..., description="Success or error status")
    data: List[Dict[str, Any]] = Field(..., description="Query results as a list of dictionaries")
    execution_time: float = Field(..., description="Query execution time in seconds")
    pagination: Dict[str, Any] = Field(..., description="Pagination metadata")
    column_types: Optional[Dict[str, str]] = Field(None, description="Column data types")
    warning: Optional[str] = Field(None, description="Warnings about the query")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of query execution")


class SQLTranslation(BaseModel):
    """Natural language to SQL translation result model."""
    status: str = Field(..., description="Success or error status")
    sql: str = Field(..., description="Translated SQL query")
    explanation: str = Field(..., description="Explanation of the SQL query")
    parameters: Dict[str, str] = Field({}, description="Description of parameters that need values")
    execution_time: Optional[float] = Field(None, description="Translation execution time in seconds")
    confidence: Optional[float] = Field(None, description="Confidence score of translation (0-1)")


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
    description: Optional[str] = Field(None, description="Column description or comment")


class TableItem(BaseModel):
    """Table information model."""
    name: str = Field(..., description="Table name")
    description: Optional[str] = Field(None, description="Table description")
    columns: List[SchemaItem] = Field([], description="Columns in the table")
    primary_keys: List[str] = Field([], description="Primary key column names")
    foreign_keys: Dict[str, Dict[str, str]] = Field({}, description="Foreign key relationships")
    row_count: Optional[int] = Field(None, description="Approximate number of rows in the table")


class SchemaResponse(BaseModel):
    """Database schema response model."""
    status: str = Field(..., description="Success or error status")
    db_schema: List[SchemaItem] = Field(..., description="Database schema information")
    tables: List[TableItem] = Field([], description="Detailed table information")
    execution_time: Optional[float] = Field(None, description="Execution time in seconds")


class SchemaSummary(BaseModel):
    """Database schema summary response model."""
    status: str = Field(..., description="Success or error status")
    summary: List[str] = Field(..., description="List of table names")
    table_counts: Dict[str, int] = Field({}, description="Number of records in each table")
    relationships: List[Dict[str, str]] = Field([], description="Relationships between tables")


class DatabaseInfo(BaseModel):
    """Database connection information."""
    name: str = Field(..., description="Database name")
    type: str = Field(..., description="Database type")
    version: str = Field(..., description="Database version")
    connected: bool = Field(..., description="Connection status")
    tables: List[str] = Field([], description="Available tables")
    error: Optional[str] = Field(None, description="Error message if connection failed")


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Success or error status")
    message: str = Field(..., description="Health check message")
    database_status: Dict[str, bool] = Field(..., description="Database connection status")
    databases: List[DatabaseInfo] = Field([], description="Detailed database information")
    api_version: str = Field(..., description="API version")
    uptime: float = Field(..., description="API uptime in seconds")


class ErrorResponse(BaseModel):
    """Error response model."""
    status: str = Field("error", description="Error status")
    message: str = Field(..., description="Error message")
    code: int = Field(..., description="HTTP status code")
    details: Optional[Dict[str, Any]] = Field(None, description="Error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of the error")