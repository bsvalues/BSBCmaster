"""
Check Supabase Schemas and Tables

This script checks all schemas and tables in the Supabase database to help
understand where our tables are located and why the REST API can't find them.
"""

import os
import sys
import json
import logging
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import database utilities
from app.db.direct_sql_client import execute_query

def list_all_schemas() -> List[str]:
    """
    List all schemas in the database.
    
    Returns:
        List of schema names
    """
    query = """
    SELECT schema_name 
    FROM information_schema.schemata
    WHERE schema_name NOT LIKE 'pg_%'
    AND schema_name != 'information_schema'
    ORDER BY schema_name
    """
    
    results = execute_query(query, {})
    return [row['schema_name'] for row in results]

def list_tables_in_schema(schema: str) -> List[Dict[str, Any]]:
    """
    List all tables in a specific schema.
    
    Args:
        schema: Schema name
        
    Returns:
        List of table details
    """
    query = f"""
    SELECT 
        table_name,
        table_type
    FROM information_schema.tables
    WHERE table_schema = '{schema}'
    ORDER BY table_name
    """
    
    results = execute_query(query, {})
    return results

def count_rows_in_table(schema: str, table: str) -> int:
    """
    Count rows in a specific table.
    
    Args:
        schema: Schema name
        table: Table name
        
    Returns:
        Row count
    """
    query = f"""
    SELECT COUNT(*) as row_count
    FROM {schema}.{table}
    """
    
    try:
        results = execute_query(query, {})
        return results[0]['row_count'] if results else 0
    except Exception as e:
        logger.error(f"Error counting rows in {schema}.{table}: {str(e)}")
        return -1

def get_table_columns(schema: str, table: str) -> List[Dict[str, Any]]:
    """
    Get column information for a specific table.
    
    Args:
        schema: Schema name
        table: Table name
        
    Returns:
        List of column details
    """
    query = f"""
    SELECT 
        column_name,
        data_type,
        is_nullable,
        column_default
    FROM information_schema.columns
    WHERE table_schema = '{schema}'
    AND table_name = '{table}'
    ORDER BY ordinal_position
    """
    
    results = execute_query(query, {})
    return results

def search_for_table(table_name: str) -> List[Dict[str, Any]]:
    """
    Search for a table across all schemas.
    
    Args:
        table_name: Table name to search for
        
    Returns:
        List of matches with schema information
    """
    query = f"""
    SELECT 
        table_schema,
        table_name,
        table_type
    FROM information_schema.tables
    WHERE table_name = '{table_name}'
    ORDER BY table_schema, table_name
    """
    
    results = execute_query(query, {})
    return results

def main():
    """Main function to check Supabase schemas and tables."""
    logger.info("Checking Supabase schemas and tables...")
    
    # List all schemas
    schemas = list_all_schemas()
    logger.info(f"Found {len(schemas)} schemas:")
    for schema in schemas:
        logger.info(f"  - {schema}")
    
    # For each schema, list tables
    for schema in schemas:
        tables = list_tables_in_schema(schema)
        logger.info(f"Schema '{schema}' has {len(tables)} tables:")
        
        for table in tables:
            table_name = table['table_name']
            table_type = table['table_type']
            row_count = count_rows_in_table(schema, table_name)
            
            row_count_str = str(row_count) if row_count >= 0 else "ERROR"
            logger.info(f"  - {table_name} ({table_type}): {row_count_str} rows")
            
            # For important tables, show column information
            if table_name in ['accounts', 'properties', 'parcels', 'sales', 'improvements']:
                columns = get_table_columns(schema, table_name)
                logger.info(f"    Columns for {schema}.{table_name}:")
                for column in columns:
                    nullable = "NULL" if column['is_nullable'] == 'YES' else "NOT NULL"
                    default = f"DEFAULT {column['column_default']}" if column['column_default'] else ""
                    logger.info(f"      {column['column_name']} {column['data_type']} {nullable} {default}")
    
    # Search for specific tables we're trying to access via the API
    for table_name in ['accounts', 'properties', 'parcels', 'sales', 'improvements']:
        matches = search_for_table(table_name)
        if matches:
            logger.info(f"Found table '{table_name}' in these schemas:")
            for match in matches:
                logger.info(f"  - {match['table_schema']}.{match['table_name']} ({match['table_type']})")
        else:
            logger.info(f"Table '{table_name}' not found in any schema")

if __name__ == "__main__":
    main()