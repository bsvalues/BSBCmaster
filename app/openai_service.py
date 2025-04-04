"""
This module provides OpenAI integration for natural language to SQL translation.
"""

import json
import logging
import os
import time
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Union

from app.cache import cache
from app.settings import settings
from app.validators import validate_natural_language_prompt

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = None

def initialize_openai_client():
    """Initialize the OpenAI client if not already initialized."""
    global client
    
    if client is not None:
        return
    
    openai_api_key = settings.OPENAI.API_KEY
    if not openai_api_key:
        logger.warning("OpenAI API key not set. Natural language translation will be unavailable.")
        return
    
    try:
        import openai
        client = openai.OpenAI(api_key=openai_api_key)
        logger.info("OpenAI client initialized successfully")
    except ImportError:
        logger.error("Failed to import openai module. Please ensure it's installed.")
    except Exception as e:
        logger.error(f"Error initializing OpenAI client: {str(e)}")

# Initialize client at module load time
initialize_openai_client()

@cache(ttl_seconds=300)  # Cache results for 5 minutes
async def translate_nl_to_sql(
    prompt: str, 
    db_type: str, 
    schema_info: str
) -> Dict[str, Any]:
    """
    Translate natural language to SQL using OpenAI.
    
    Args:
        prompt: The natural language prompt
        db_type: The database type (postgres or mssql)
        schema_info: Schema information to provide context
        
    Returns:
        Dictionary containing:
            - sql: The translated SQL query
            - explanation: An explanation of the SQL query
            - parameters: Extracted parameters (if any)
            - status: Status of the translation (success, error)
    """
    # Validate the natural language prompt
    validation = validate_natural_language_prompt(prompt)
    if not validation["valid"]:
        return {
            "status": "error",
            "message": f"Invalid prompt: {', '.join(validation['issues'])}",
            "sql": None,
            "explanation": None,
            "parameters": {}
        }
    
    # Initialize OpenAI client if not already initialized
    if client is None:
        initialize_openai_client()
    
    # Check if client is initialized
    if client is None:
        logger.warning("OpenAI client not available, using fallback translation")
        result = await fallback_nl_to_sql(prompt, db_type, schema_info)
        result["status"] = "fallback"
        return result
        
    try:
        # Create a system message with the schema information
        system_message = f"""
        You are an expert SQL translator for {db_type.upper()} databases specializing in real estate assessment data.
        Translate natural language queries to SQL based on the following schema:

        {schema_info}

        CONTEXT ABOUT REAL ESTATE DATA:
        - Parcels table contains the main assessment records with unique parcel_id, address, and valuation data
        - Properties table contains physical characteristics like square_footage, bedrooms, bathrooms
        - Sales table contains historical sale transactions with sale_date and sale_price
        - Properties and Sales both link to Parcels via parcel_id foreign key
        - Recent sales typically means sales from the last year
        - High-value properties are usually those with total_value > 500000
        - Standard report periods are current year, last year, or last 5 years

        Please follow these guidelines:
        - Generate ONLY {db_type.upper()} SQL syntax
        - Include appropriate JOINs when needed
        - Use proper column and table names from the schema
        - Format the SQL query with proper indentation
        - Use parameterized queries with placeholders (like :param) for user input values
        - Provide a brief explanation of the query including business context
        - Identify extractable parameters from the query with appropriate data types
        - For date ranges, use proper date functions appropriate for {db_type.upper()}
        - When calculating averages or totals, handle NULL values appropriately
        - Include proper ORDER BY clauses for meaningful sorting
        - For queries expected to return many rows, include LIMIT :limit parameter
        
        Response format:
        {{
            "sql": "Your SQL query here",
            "explanation": "Detailed explanation of what the query does and business context",
            "parameters": {{
                "param1": "description of parameter 1 with expected data type",
                "param2": "description of parameter 2 with expected data type",
                ...
            }}
        }}
        
        Return ONLY valid JSON.
        """
        
        # Start timing
        start_time = time.time()
        
        # Call the OpenAI API with timeout
        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    client.chat.completions.create,
                    model=settings.OPENAI.MODEL,
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": f"Translate this to SQL: {prompt}"}
                    ],
                    response_format={"type": "json_object"},
                    temperature=settings.OPENAI.TEMPERATURE,
                    max_tokens=settings.OPENAI.MAX_TOKENS
                ),
                timeout=settings.OPENAI.TIMEOUT
            )
        except asyncio.TimeoutError:
            logger.error(f"OpenAI API timeout after {settings.OPENAI.TIMEOUT} seconds")
            result = await fallback_nl_to_sql(prompt, db_type, schema_info)
            result["status"] = "timeout"
            return result
        
        # Calculate execution time
        execution_time = time.time() - start_time
        
        # Parse the JSON response
        result_text = response.choices[0].message.content
        result = json.loads(result_text)
        
        # Add status and execution time
        result["status"] = "success"
        result["execution_time"] = execution_time
        
        # Ensure parameters field exists
        if "parameters" not in result:
            result["parameters"] = {}
        
        # Log the result
        logger.info(f"OpenAI translation completed in {execution_time:.2f}s: {result['sql'][:100]}...")
        
        return result
    except Exception as e:
        logger.error(f"Error translating natural language to SQL: {str(e)}")
        result = await fallback_nl_to_sql(prompt, db_type, schema_info)
        result["status"] = "error"
        result["error"] = str(e)
        return result

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
        Analyze the following database schema and provide a comprehensive summary.
        
        {schema_info}
        
        Include the following in your analysis:
        1. The overall purpose and organization of this database
        2. Key tables and their business functions in property assessment
        3. Important relationships between tables
        4. Key fields that would be useful for queries and reporting
        5. Suggestions for common query patterns based on this schema
        
        Response format:
        {{
            "summary": "Overall summary of the database in 1-2 sentences",
            "tables": [
                {{
                    "name": "table_name", 
                    "description": "Detailed description of purpose and role in property assessment", 
                    "key_fields": ["field1", "field2"],
                    "business_purpose": "How this table is used in property assessment workflows"
                }},
                ...
            ],
            "relationships": [
                {{
                    "from": "table_name", 
                    "to": "related_table", 
                    "type": "one-to-many", 
                    "description": "Business meaning of this relationship"
                }},
                ...
            ],
            "common_queries": [
                {{
                    "purpose": "Description of query purpose",
                    "tables_involved": ["table1", "table2"],
                    "typical_fields": ["field1", "field2"]
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