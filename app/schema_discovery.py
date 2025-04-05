"""
Schema Discovery Module for MCP Assessor Agent API

This module provides enhanced functionality for discovering database schemas,
including table relationships, primary and foreign keys, and column metadata.
It supports PostgreSQL and MSSQL databases.
"""

import logging
import time
from typing import Dict, List, Any, Optional, Tuple, Union
from collections import defaultdict

from sqlalchemy import inspect, MetaData, Table, Column, text
from sqlalchemy.engine import Engine, Connection
from sqlalchemy.exc import SQLAlchemyError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SchemaDiscovery:
    """Class for discovering database schema information."""
    
    def __init__(self, engine: Engine):
        """
        Initialize SchemaDiscovery with a SQLAlchemy engine.
        
        Args:
            engine: SQLAlchemy engine or connection
        """
        self.engine = engine
        self.inspector = inspect(engine)
        self.metadata = MetaData()
        
    def get_all_tables(self) -> List[str]:
        """
        Get all table names in the database.
        
        Returns:
            List of table names
        """
        return self.inspector.get_table_names()
    
    def get_table_details(self, table_name: str) -> Dict[str, Any]:
        """
        Get detailed information about a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Dictionary with table details
        """
        try:
            table_info = {
                "name": table_name,
                "columns": [],
                "primary_keys": [],
                "foreign_keys": [],
                "indexes": [],
                "row_count": self._get_table_row_count(table_name)
            }
            
            # Get column details
            columns = self.inspector.get_columns(table_name)
            for column in columns:
                column_info = {
                    "name": column["name"],
                    "type": str(column["type"]),
                    "nullable": column.get("nullable", True),
                    "default": str(column.get("default", "")) if column.get("default") is not None else None,
                    "comment": column.get("comment", "")
                }
                table_info["columns"].append(column_info)
            
            # Get primary key columns
            pk_constraint = self.inspector.get_pk_constraint(table_name)
            if pk_constraint and "constrained_columns" in pk_constraint:
                table_info["primary_keys"] = pk_constraint["constrained_columns"]
            
            # Get foreign key relationships
            foreign_keys = self.inspector.get_foreign_keys(table_name)
            for fk in foreign_keys:
                fk_info = {
                    "name": fk.get("name"),
                    "constrained_columns": fk.get("constrained_columns", []),
                    "referred_table": fk.get("referred_table"),
                    "referred_columns": fk.get("referred_columns", [])
                }
                table_info["foreign_keys"].append(fk_info)
            
            # Get indexes
            indexes = self.inspector.get_indexes(table_name)
            for idx in indexes:
                idx_info = {
                    "name": idx.get("name"),
                    "columns": idx.get("column_names", []),
                    "unique": idx.get("unique", False)
                }
                table_info["indexes"].append(idx_info)
            
            return table_info
        except SQLAlchemyError as e:
            logger.error(f"Error getting details for table {table_name}: {str(e)}")
            return {
                "name": table_name,
                "error": str(e),
                "columns": [],
                "primary_keys": [],
                "foreign_keys": [],
                "indexes": []
            }
    
    def _get_table_row_count(self, table_name: str) -> int:
        """
        Get the approximate row count for a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Approximate row count
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                return result.scalar() or 0
        except SQLAlchemyError as e:
            logger.warning(f"Error getting row count for table {table_name}: {str(e)}")
            return 0
    
    def get_table_relationships(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get relationships between tables based on foreign keys.
        
        Returns:
            Dictionary mapping table names to lists of relationships
        """
        relationships = defaultdict(list)
        
        # Get all tables
        tables = self.get_all_tables()
        
        # Collect foreign key relationships
        for table_name in tables:
            foreign_keys = self.inspector.get_foreign_keys(table_name)
            
            # Add outgoing relationships
            for fk in foreign_keys:
                referred_table = fk.get("referred_table")
                constrained_columns = fk.get("constrained_columns", [])
                referred_columns = fk.get("referred_columns", [])
                
                if referred_table and constrained_columns and referred_columns:
                    relationships[table_name].append({
                        "direction": "outgoing",
                        "table": referred_table,
                        "columns": list(zip(constrained_columns, referred_columns)),
                        "constraint_name": fk.get("name")
                    })
                    
                    # Add incoming relationship to the referred table
                    relationships[referred_table].append({
                        "direction": "incoming",
                        "table": table_name,
                        "columns": list(zip(referred_columns, constrained_columns)),
                        "constraint_name": fk.get("name")
                    })
        
        return dict(relationships)
    
    def get_column_data_samples(
        self, 
        table_name: str, 
        column_names: Optional[List[str]] = None, 
        limit: int = 10
    ) -> Dict[str, List[Any]]:
        """
        Get sample data for columns in a table.
        
        Args:
            table_name: Name of the table
            column_names: List of column names to sample (None for all columns)
            limit: Maximum number of sample values to return per column
            
        Returns:
            Dictionary mapping column names to lists of sample values
        """
        try:
            # Get all columns if not specified
            if column_names is None:
                columns_info = self.inspector.get_columns(table_name)
                column_names = [col["name"] for col in columns_info]
            
            sample_data = {}
            
            # Query sample data for each column
            with self.engine.connect() as conn:
                for column_name in column_names:
                    query = text(f"SELECT DISTINCT {column_name} FROM {table_name} WHERE {column_name} IS NOT NULL LIMIT :limit")
                    result = conn.execute(query, {"limit": limit})
                    sample_data[column_name] = [row[0] for row in result]
            
            return sample_data
        except SQLAlchemyError as e:
            logger.error(f"Error getting sample data for table {table_name}: {str(e)}")
            return {}
    
    def get_database_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the database schema.
        
        Returns:
            Dictionary with database summary information
        """
        start_time = time.time()
        
        tables = self.get_all_tables()
        table_count = len(tables)
        
        # Get table stats
        table_stats = []
        for table_name in tables:
            try:
                row_count = self._get_table_row_count(table_name)
                column_count = len(self.inspector.get_columns(table_name))
                
                table_stats.append({
                    "name": table_name,
                    "row_count": row_count,
                    "column_count": column_count
                })
            except Exception as e:
                logger.warning(f"Error getting stats for table {table_name}: {str(e)}")
                table_stats.append({
                    "name": table_name,
                    "row_count": 0,
                    "column_count": 0,
                    "error": str(e)
                })
        
        # Get relationships
        relationships = self.get_table_relationships()
        relationship_count = sum(len(rels) for rels in relationships.values())
        
        # Calculate execution time
        execution_time = time.time() - start_time
        
        return {
            "table_count": table_count,
            "tables": table_stats,
            "relationship_count": relationship_count,
            "relationships": relationships,
            "execution_time": execution_time
        }
    
    def get_schema_for_nl(self) -> str:
        """
        Get schema information formatted for natural language to SQL translation.
        
        Returns:
            String representation of schema suitable for NL to SQL
        """
        tables = self.get_all_tables()
        schema_text = "Database Schema:\n\n"
        
        for table_name in tables:
            # Get columns
            columns = self.inspector.get_columns(table_name)
            column_strs = []
            
            for column in columns:
                col_name = column["name"]
                col_type = str(column["type"])
                nullable = "" if column.get("nullable", True) else " NOT NULL"
                column_strs.append(f"{col_name} ({col_type}{nullable})")
            
            # Get primary keys
            pk_constraint = self.inspector.get_pk_constraint(table_name)
            primary_keys = pk_constraint.get("constrained_columns", [])
            pk_str = f", Primary Key: {', '.join(primary_keys)}" if primary_keys else ""
            
            # Get foreign keys
            foreign_keys = self.inspector.get_foreign_keys(table_name)
            fk_strs = []
            
            for fk in foreign_keys:
                constrained_cols = fk.get("constrained_columns", [])
                referred_table = fk.get("referred_table")
                referred_cols = fk.get("referred_columns", [])
                
                if constrained_cols and referred_table and referred_cols:
                    fk_strs.append(
                        f"{', '.join(constrained_cols)} references {referred_table}({', '.join(referred_cols)})"
                    )
            
            fk_str = f", Foreign Keys: {'; '.join(fk_strs)}" if fk_strs else ""
            
            # Add table to schema text
            schema_text += f"Table: {table_name}\n"
            schema_text += f"Columns: {', '.join(column_strs)}{pk_str}{fk_str}\n\n"
        
        return schema_text

def get_schema_discovery_instance(engine: Engine) -> SchemaDiscovery:
    """
    Get a SchemaDiscovery instance with the specified engine.
    
    Args:
        engine: SQLAlchemy engine
        
    Returns:
        SchemaDiscovery instance
    """
    return SchemaDiscovery(engine)