"""
This module provides OpenAI integration for natural language to SQL translation.
"""

import json
import logging
import os
from typing import Dict, Any, Optional

import openai
from app.settings import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
openai_api_key = settings.OPENAI_API_KEY
client = None
if openai_api_key:
    try:
        client = openai.OpenAI(api_key=openai_api_key)
        logger.info("OpenAI client initialized")
    except Exception as e:
        logger.error(f"Error initializing OpenAI client: {str(e)}")

async def translate_nl_to_sql(
    prompt: str, 
    db_type: str, 
    schema_info: str
) -> Optional[Dict[str, Any]]:
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
    """
    if not client:
        logger.warning("OpenAI client not available, using fallback translation")
        return fallback_nl_to_sql(prompt, db_type, schema_info)
        
    try:
        # Create a system message with the schema information
        system_message = f"""
        You are an expert SQL translator for {db_type.upper()} databases.
        Translate natural language queries to SQL based on the following schema:

        {schema_info}

        Please follow these guidelines:
        - Generate ONLY {db_type.upper()} SQL syntax
        - Include appropriate JOINs when needed
        - Use proper column and table names from the schema
        - Format the SQL query with proper indentation
        - Provide a brief explanation of the query
        
        Response format:
        {{
            "sql": "Your SQL query here",
            "explanation": "Brief explanation of what the query does"
        }}
        
        Return ONLY valid JSON.
        """
        
        # Call the OpenAI API
        response = client.chat.completions.create(
            model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024. do not change this unless explicitly requested by the user
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": f"Translate this to SQL: {prompt}"}
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=500
        )
        
        # Parse the JSON response
        result_text = response.choices[0].message.content
        result = json.loads(result_text)
        
        # Log the result
        logger.info(f"OpenAI translation: {result['sql']}")
        
        return result
    except Exception as e:
        logger.error(f"Error translating natural language to SQL: {str(e)}")
        return fallback_nl_to_sql(prompt, db_type, schema_info)

def fallback_nl_to_sql(
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
    """
    logger.info("Using fallback NL to SQL translation")
    
    # Convert prompt to lowercase for easier parsing
    prompt_lower = prompt.lower()
    
    # Default to SELECT * FROM parcels
    sql = "SELECT * FROM parcels LIMIT 100"
    explanation = "Fallback query to retrieve all parcels with a limit of 100."
    
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
    if "city" in prompt_lower:
        conditions.append("city LIKE '%City%'")
    if "state" in prompt_lower:
        conditions.append("state = 'State'")
    if "price" in prompt_lower or "value" in prompt_lower:
        conditions.append("total_value > 0")
    if "recent" in prompt_lower or "latest" in prompt_lower:
        if "sales" in tables:
            conditions.append("sale_date >= CURRENT_DATE - INTERVAL '1 year'")
    
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
        "explanation": explanation
    }