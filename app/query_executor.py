"""
This module provides utilities for executing database queries with proper parameterization.
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import psycopg2
import psycopg2.extras
import psycopg2.pool

from app.cache import cache
from app.db import get_db_pool
from app.models import DatabaseType, ParamStyle, ParameterizedSQLQuery, QueryResult
from app.security import verify_sql_query
from app.settings import settings
from app.validators import validate_pagination_params

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def execute_parameterized_query(
    query_request: ParameterizedSQLQuery,
    allow_write: bool = False
) -> Dict[str, Any]:
    """
    Execute a parameterized SQL query safely.
    
    Args:
        query_request: The query request model
        allow_write: Whether to allow write operations
        
    Returns:
        QueryResult model as a dictionary
    """
    start_time = time.time()
    
    # Verify and validate SQL query
    validation_result = verify_sql_query(query_request.query, allow_write)
    
    if not validation_result["valid"]:
        return {
            "status": "error",
            "message": f"SQL validation failed: {', '.join(validation_result['issues'])}",
            "data": [],
            "execution_time": time.time() - start_time,
            "pagination": {
                "page": query_request.page,
                "page_size": query_request.page_size or settings.MAX_RESULTS,
                "total_pages": 0,
                "total_items": 0
            }
        }
    
    # Validate pagination parameters
    pagination_validation = validate_pagination_params(
        query_request.page, 
        query_request.page_size or settings.MAX_RESULTS, 
        settings.MAX_RESULTS
    )
    
    page = pagination_validation["corrected_page"]
    page_size = pagination_validation["corrected_page_size"]
    
    # Add pagination warning if parameters were corrected
    warning = None
    if not pagination_validation["valid"]:
        warning = f"Pagination parameters were adjusted: {', '.join(pagination_validation['issues'])}"
    
    try:
        # Get database connection from pool
        db_pool = await get_db_pool(query_request.db)
        if not db_pool:
            return {
                "status": "error",
                "message": f"Could not connect to {query_request.db.value} database",
                "data": [],
                "execution_time": time.time() - start_time,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total_pages": 0,
                    "total_items": 0
                }
            }
        
        # Calculate pagination
        offset = (page - 1) * page_size
        
        # Add pagination to query if not already present
        query = query_request.query.strip()
        if not query.lower().endswith(("limit", "offset")) and "limit" not in query.lower():
            query += f" LIMIT {page_size} OFFSET {offset}"
        
        # Execute query with parameters
        conn = await db_pool.acquire()
        try:
            async with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                # Execute the query with parameters
                if query_request.param_style == ParamStyle.NAMED:
                    # Use named parameters (:param_name)
                    await cursor.execute(query, query_request.params or {})
                else:
                    # Convert to appropriate parameter style
                    # This would need to be implemented based on the specific param_style
                    await cursor.execute(query, query_request.params or {})
                
                # Fetch results
                rows = await cursor.fetchall()
                
                # Get column types
                column_types = {}
                if cursor.description:
                    for desc in cursor.description:
                        col_name = desc[0]
                        col_type = desc[1]
                        column_types[col_name] = str(col_type)
                
                # Execute count query for pagination info (if SELECT)
                total_items = len(rows)
                total_pages = (total_items + page_size - 1) // page_size
                
                if query.strip().upper().startswith("SELECT"):
                    # Try to extract the count from the query for pagination
                    try:
                        # Create a count query
                        count_query = f"SELECT COUNT(*) FROM ({query.split('LIMIT')[0]}) AS subquery"
                        await cursor.execute(count_query, query_request.params or {})
                        count_result = await cursor.fetchone()
                        if count_result and "count" in count_result:
                            total_items = int(count_result["count"])
                            total_pages = (total_items + page_size - 1) // page_size
                    except Exception as e:
                        logger.warning(f"Could not get total count: {str(e)}")
        finally:
            await db_pool.release(conn)
        
        # Convert rows to list of dictionaries
        data = [dict(row) for row in rows]
        
        # Calculate execution time
        execution_time = time.time() - start_time
        
        return {
            "status": "success",
            "data": data,
            "execution_time": execution_time,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "total_items": total_items
            },
            "column_types": column_types,
            "warning": warning,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        # Log the error
        logger.error(f"Error executing query: {str(e)}")
        
        # Calculate execution time
        execution_time = time.time() - start_time
        
        return {
            "status": "error",
            "message": f"Error executing query: {str(e)}",
            "data": [],
            "execution_time": execution_time,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_pages": 0,
                "total_items": 0
            }
        }

@cache(ttl_seconds=3600)  # Cache for 1 hour
async def get_database_schema(db_type: DatabaseType) -> Dict[str, Any]:
    """
    Get the database schema.
    
    Args:
        db_type: The database type
        
    Returns:
        Database schema information
    """
    start_time = time.time()
    
    try:
        # Get database connection from pool
        db_pool = await get_db_pool(db_type)
        if not db_pool:
            return {
                "status": "error",
                "message": f"Could not connect to {db_type.value} database",
                "db_schema": [],
                "tables": [],
                "execution_time": time.time() - start_time
            }
        
        conn = await db_pool.acquire()
        try:
            # Define schema query based on database type
            if db_type == DatabaseType.POSTGRES:
                # Query for PostgreSQL schema
                schema_query = """
                SELECT 
                    c.table_name,
                    c.column_name,
                    c.data_type,
                    CASE WHEN c.is_nullable = 'YES' THEN true ELSE false END as is_nullable,
                    c.column_default,
                    CASE WHEN pk.constraint_name IS NOT NULL THEN true ELSE false END as is_primary_key,
                    CASE WHEN fk.constraint_name IS NOT NULL THEN true ELSE false END as is_foreign_key,
                    fk.referenced_table_name,
                    fk.referenced_column_name,
                    pgd.description
                FROM 
                    information_schema.columns c
                LEFT JOIN (
                    SELECT 
                        kcu.table_name,
                        kcu.column_name,
                        tc.constraint_name
                    FROM 
                        information_schema.table_constraints tc
                    JOIN 
                        information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
                    WHERE 
                        tc.constraint_type = 'PRIMARY KEY'
                ) pk ON c.table_name = pk.table_name AND c.column_name = pk.column_name
                LEFT JOIN (
                    SELECT 
                        kcu.table_name,
                        kcu.column_name,
                        tc.constraint_name,
                        ccu.table_name as referenced_table_name,
                        ccu.column_name as referenced_column_name
                    FROM 
                        information_schema.table_constraints tc
                    JOIN 
                        information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
                    JOIN 
                        information_schema.constraint_column_usage ccu ON tc.constraint_name = ccu.constraint_name
                    WHERE 
                        tc.constraint_type = 'FOREIGN KEY'
                ) fk ON c.table_name = fk.table_name AND c.column_name = fk.column_name
                LEFT JOIN 
                    pg_catalog.pg_description pgd ON pgd.objoid = (c.table_name::regclass)::oid 
                    AND pgd.objsubid = c.ordinal_position
                WHERE 
                    c.table_schema = 'public'
                ORDER BY 
                    c.table_name, c.ordinal_position;
                """
            else:
                # Query for MS SQL schema (would need to be adjusted for actual MS SQL syntax)
                schema_query = """
                SELECT 
                    table_name, 
                    column_name, 
                    data_type, 
                    is_nullable, 
                    column_default
                FROM 
                    information_schema.columns
                WHERE 
                    table_schema = 'dbo'
                ORDER BY 
                    table_name, ordinal_position;
                """
            
            async with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                # Execute schema query
                await cursor.execute(schema_query)
                rows = await cursor.fetchall()
                
                # Convert rows to SchemaItem objects
                schema_items = []
                tables_dict = {}
                
                for row in rows:
                    # Create SchemaItem
                    schema_item = {
                        "table_name": row["table_name"],
                        "column_name": row["column_name"],
                        "data_type": row["data_type"],
                        "is_nullable": row["is_nullable"],
                        "column_default": row["column_default"],
                        "is_primary_key": row.get("is_primary_key", False),
                        "is_foreign_key": row.get("is_foreign_key", False),
                        "references_table": row.get("referenced_table_name"),
                        "references_column": row.get("referenced_column_name"),
                        "description": row.get("description")
                    }
                    schema_items.append(schema_item)
                    
                    # Add to tables dictionary
                    table_name = row["table_name"]
                    if table_name not in tables_dict:
                        tables_dict[table_name] = {
                            "name": table_name,
                            "description": None,
                            "columns": [],
                            "primary_keys": [],
                            "foreign_keys": {},
                            "row_count": None
                        }
                    
                    # Add column to table
                    tables_dict[table_name]["columns"].append(schema_item)
                    
                    # Add primary key if applicable
                    if row.get("is_primary_key", False):
                        tables_dict[table_name]["primary_keys"].append(row["column_name"])
                    
                    # Add foreign key if applicable
                    if row.get("is_foreign_key", False):
                        tables_dict[table_name]["foreign_keys"][row["column_name"]] = {
                            "references_table": row["referenced_table_name"],
                            "references_column": row["referenced_column_name"]
                        }
                
                # Get row counts for each table
                table_names = list(tables_dict.keys())
                for table_name in table_names:
                    try:
                        await cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                        count_result = await cursor.fetchone()
                        if count_result and "count" in count_result:
                            tables_dict[table_name]["row_count"] = int(count_result["count"])
                    except Exception as e:
                        logger.warning(f"Could not get row count for table {table_name}: {str(e)}")
        finally:
            await db_pool.release(conn)
        
        # Calculate execution time
        execution_time = time.time() - start_time
        
        return {
            "status": "success",
            "db_schema": schema_items,
            "tables": list(tables_dict.values()),
            "execution_time": execution_time
        }
    
    except Exception as e:
        # Log the error
        logger.error(f"Error getting database schema: {str(e)}")
        
        # Calculate execution time
        execution_time = time.time() - start_time
        
        return {
            "status": "error",
            "message": f"Error getting database schema: {str(e)}",
            "db_schema": [],
            "tables": [],
            "execution_time": execution_time
        }