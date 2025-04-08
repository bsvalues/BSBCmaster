"""OpenAI service for natural language processing"""

import os
import json
import logging
import time
import asyncio
from typing import Dict, Any, Optional

from app.cache import cache
from app.settings import settings
from app.validators import validate_natural_language_prompt

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = None

def initialize_openai_client():
    """Initialize the OpenAI client."""
    global client
    if client is not None:
        return

    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.OPENAI.API_KEY)
        logger.info("OpenAI client initialized successfully")
    except Exception as e:
        logger.error(f"OpenAI client initialization failed: {str(e)}")

initialize_openai_client()

@cache(ttl_seconds=300)
async def translate_nl_to_sql(
    prompt: str,
    db_type: str,
    schema_info: str
) -> Dict[str, Any]:
    """Translate natural language to SQL."""
    try:
        if not client:
            initialize_openai_client()

        if not client:
            logger.warning("OpenAI client unavailable")
            return {
                "status": "error",
                "message": "Translation service unavailable",
                "sql": None
            }

        # Validate prompt
        validation = validate_natural_language_prompt(prompt)
        if not validation["valid"]:
            return {
                "status": "error",
                "message": f"Invalid prompt: {validation['issues']}",
                "sql": None
            }

        # Create system message
        system_message = f"""
        Translate natural language to {db_type} SQL.
        Schema: {schema_info}
        """

        response = await asyncio.wait_for(
            asyncio.to_thread(
                client.chat.completions.create,
                model=settings.OPENAI.MODEL,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            ),
            timeout=10.0
        )

        result = {
            "status": "success",
            "sql": response.choices[0].message.content,
            "explanation": "Translated query"
        }

        return result

    except Exception as e:
        logger.error(f"Translation error: {str(e)}")
        return {
            "status": "error",
            "message": f"Translation failed: {str(e)}",
            "sql": None
        }

async def fallback_nl_to_sql(
    prompt: str, 
    db_type: str, 
    schema_info: str
) -> Dict[str, Any]:
    """
    Fallback translation when OpenAI is not available.
    
    Args:
        prompt: The natural language prompt
        db_type: The database type (postgres or mssql)
        schema_info: Schema information to provide context
        
    Returns:
        Dictionary containing:
            - sql: A basic SQL query based on keywords
            - explanation: An explanation of the fallback mechanism
            - parameters: Extracted parameters (if any)
    """
    logger.info("Using fallback NL to SQL translation")
    
    # Convert prompt to lowercase for easier parsing
    prompt_lower = prompt.lower()
    
    # Default to SELECT * FROM parcels
    sql = "SELECT * FROM parcels LIMIT 100"
    explanation = "Fallback query to retrieve all parcels with a limit of 100."
    parameters = {}
    
    # Look for table names in the prompt
    tables = []
    if "parcel" in prompt_lower or "address" in prompt_lower:
        tables.append("parcels")
    if "propert" in prompt_lower or "house" in prompt_lower or "building" in prompt_lower:
        tables.append("properties")
    if "sale" in prompt_lower or "sold" in prompt_lower or "transaction" in prompt_lower:
        tables.append("sales")
    
    # Look for potential filter conditions
    conditions = []
    
    # Check for city mentions
    if "city" in prompt_lower:
        city_param = "city_name"
        parameters[city_param] = "City name to filter by"
        conditions.append(f"city LIKE :{city_param}")
    
    # Check for state mentions
    if "state" in prompt_lower:
        state_param = "state_name"
        parameters[state_param] = "State name to filter by"
        conditions.append(f"state = :{state_param}")
    
    # Check for price/value mentions
    if "price" in prompt_lower or "value" in prompt_lower:
        value_param = "min_value"
        parameters[value_param] = "Minimum property value"
        conditions.append(f"total_value > :{value_param}")
    
    # Check for recent/latest mentions
    if "recent" in prompt_lower or "latest" in prompt_lower:
        if "sales" in tables:
            date_param = "min_date"
            parameters[date_param] = "Minimum date for recent sales"
            conditions.append(f"sale_date >= :{date_param}")
    
    # Generate a basic query based on the prompt analysis
    if len(tables) == 1:
        # Simple query on a single table
        sql = f"SELECT * FROM {tables[0]}"
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " LIMIT 100"
        explanation = f"Basic query to retrieve data from {tables[0]} table with filtering."
    elif len(tables) > 1:
        # Join query for multiple tables
        primary_table = tables[0]
        sql = f"SELECT * FROM {primary_table}"
        
        # Add joins
        if "parcels" in tables and "properties" in tables:
            if primary_table == "parcels":
                sql += " LEFT JOIN properties ON parcels.id = properties.parcel_id"
            else:
                sql += " LEFT JOIN parcels ON properties.parcel_id = parcels.id"
        
        if "parcels" in tables and "sales" in tables:
            if primary_table == "parcels":
                sql += " LEFT JOIN sales ON parcels.id = sales.parcel_id"
            else:
                sql += " LEFT JOIN parcels ON sales.parcel_id = parcels.id"
        
        # Add conditions if any
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        
        sql += " LIMIT 100"
        explanation = f"Basic query joining {', '.join(tables)} tables with filtering."
    
    # Add a note about the fallback
    explanation += " (This is a fallback query as the AI translation service is unavailable)"
    
    return {
        "sql": sql,
        "explanation": explanation,
        "parameters": parameters
    }

@cache(ttl_seconds=3600)  # Cache for 1 hour
async def generate_schema_summary(schema_info: str) -> Dict[str, Any]:
    """
    Generate a summary of the database schema using OpenAI.
    
    Args:
        schema_info: Detailed schema information
        
    Returns:
        Dictionary containing:
            - summary: Summary of the schema
            - tables: List of tables with descriptions
            - relationships: List of relationships between tables
    """
    if client is None:
        initialize_openai_client()
    
    if client is None:
        return {
            "status": "error",
            "message": "OpenAI client not available",
            "summary": "Database contains tables for real estate assessment data including parcels, properties, and sales.",
            "tables": [
                {"name": "parcels", "description": "Main assessment records for real estate parcels"},
                {"name": "properties", "description": "Physical property characteristics"},
                {"name": "sales", "description": "Property sale transaction history"}
            ],
            "relationships": [
                {"from": "parcels", "to": "properties", "type": "one-to-many"},
                {"from": "parcels", "to": "sales", "type": "one-to-many"}
            ]
        }
    
    try:
        system_message = f"""
        You are a database expert specializing in real estate property assessment systems. 
        Analyze the following database schema and provide a comprehensive summary that will help 
        users understand how to query this database for property assessment information.
        
        {schema_info}
        
        Include the following in your analysis:
        
        1. The overall purpose and organization of this database
           - Primary function in property assessments
           - Key business processes supported
           - Information architecture overview
        
        2. Key tables and their business functions
           - Main tables and their core purpose
           - Important fields with data types
           - Business meaning of each major table
           - Primary and foreign key relationships
        
        3. Data relationships and integrity
           - How tables connect to form a complete view of properties
           - One-to-many and many-to-many relationships
           - Referential integrity constraints
           - Business meaning of relationships
        
        4. Analytical capabilities
           - Valuable metrics and KPIs available
           - Time-series analysis possibilities
           - Comparative assessment options
           - Valuation trend analysis approaches
        
        5. Query patterns and visualization opportunities
           - Common business questions this data can answer
           - Suggested JOIN patterns for different analyses
           - Fields suitable for grouping and aggregation
           - Data visualization recommendations
           - Query optimization suggestions
        
        Response format:
        {{
            "summary": "Concise summary of the database and its purpose",
            
            "tables": [
                {{
                    "name": "table_name", 
                    "description": "Detailed description of purpose and role in property assessment", 
                    "key_fields": [
                        {{
                            "name": "field_name",
                            "type": "data_type",
                            "description": "Business meaning and usage of this field",
                            "importance": "high/medium/low"
                        }}
                    ],
                    "business_purpose": "How this table is used in property assessment workflows",
                    "example_queries": [
                        "Example of a simple query for this table"
                    ]
                }},
                ...
            ],
            
            "relationships": [
                {{
                    "from": "table_name", 
                    "to": "related_table", 
                    "type": "one-to-many", 
                    "join_fields": "table1.field = table2.field",
                    "description": "Business meaning of this relationship",
                    "example_join": "Example SQL showing how to join these tables"
                }},
                ...
            ],
            
            "common_queries": [
                {{
                    "purpose": "Business question this query answers",
                    "tables_involved": ["table1", "table2"],
                    "description": "What this query accomplishes in business terms",
                    "key_fields": ["field1", "field2"],
                    "sql_pattern": "SQL pattern to answer this business question",
                    "visualization": "Suggestion for visualizing these results"
                }},
                ...
            ],
            
            "data_quality_considerations": [
                "Important notes about potential data quality issues",
                ...
            ],
            
            "analytics_recommendations": [
                {{
                    "analysis_type": "Type of analysis possible",
                    "description": "What insights this analysis provides",
                    "required_fields": ["field1", "field2"],
                    "business_value": "How this analysis benefits property assessment"
                }},
                ...
            ]
        }}
        
        Return ONLY valid JSON.
        """
        
        response = await asyncio.wait_for(
            asyncio.to_thread(
                client.chat.completions.create,
                model=settings.OPENAI.MODEL,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": "Summarize this database schema"}
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=1000
            ),
            timeout=settings.OPENAI.TIMEOUT
        )
        
        # Parse the JSON response
        result_text = response.choices[0].message.content
        result = json.loads(result_text)
        
        # Add status
        result["status"] = "success"
        
        return result
    except Exception as e:
        logger.error(f"Error generating schema summary: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "summary": "Database contains tables for real estate assessment data including parcels, properties, and sales.",
            "tables": [
                {"name": "parcels", "description": "Main assessment records for real estate parcels"},
                {"name": "properties", "description": "Physical property characteristics"},
                {"name": "sales", "description": "Property sale transaction history"}
            ],
            "relationships": [
                {"from": "parcels", "to": "properties", "type": "one-to-many"},
                {"from": "parcels", "to": "sales", "type": "one-to-many"}
            ]
        }