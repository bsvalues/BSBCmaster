import os
import json
import logging
from openai import OpenAI
from typing import Optional, Dict, Any

logger = logging.getLogger("mcp_assessor_api")

class OpenAIService:
    """Service for OpenAI API interactions including natural language to SQL conversion."""
    
    def __init__(self):
        """Initialize the OpenAI client with the API key from environment variables."""
        self.api_key = os.environ.get("OPENAI_API_KEY")
        self.client = None
        self.initialized = False
        self.initialize()
    
    def initialize(self) -> bool:
        """Initialize the OpenAI client if the API key is available."""
        if not self.api_key:
            logger.warning("OpenAI API key not provided. Natural language to SQL conversion will not be available.")
            return False
        
        try:
            self.client = OpenAI(api_key=self.api_key)
            self.initialized = True
            logger.info("OpenAI client initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {str(e)}")
            return False
    
    def is_available(self) -> bool:
        """Check if the OpenAI service is available for use."""
        return self.initialized and self.client is not None
    
    def nl_to_sql(self, prompt: str, db_type: str, schema_info: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Convert natural language to SQL using OpenAI's API.
        
        Args:
            prompt: The natural language prompt to convert to SQL
            db_type: The type of database (postgres or mssql)
            schema_info: Optional database schema information to guide the AI
            
        Returns:
            str: The translated SQL query or None if translation fails
        """
        if not self.is_available():
            logger.warning("OpenAI service not available. Cannot convert natural language to SQL.")
            return None
        
        try:
            # Prepare the system message with database context
            system_message = self._create_system_message(db_type, schema_info)
            
            # Prepare user prompt with schema context if available
            user_prompt = self._create_user_prompt(prompt, schema_info)
            
            # Call the OpenAI API
            response = self.client.chat.completions.create(
                model="gpt-4o",  # The newest OpenAI model is "gpt-4o" which was released May 13, 2024.
                                  # Do not change this unless explicitly requested by the user
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            # Parse the response
            result = json.loads(response.choices[0].message.content)
            
            if "sql" in result:
                logger.info(f"Successfully translated natural language to SQL: {result['sql']}")
                return result["sql"]
            else:
                logger.warning(f"Unexpected response format from OpenAI: {result}")
                return None
                
        except Exception as e:
            logger.error(f"Error in OpenAI NL to SQL translation: {str(e)}")
            return None
    
    def _create_system_message(self, db_type: str, schema_info: Optional[Dict[str, Any]] = None) -> str:
        """Create the system message for the OpenAI API with database context."""
        db_dialect = "PostgreSQL" if db_type == "postgres" else "Microsoft SQL Server"
        
        message = (
            f"You are an expert SQL query generator for {db_dialect} databases. "
            f"Your task is to translate natural language questions into valid SQL queries. "
            f"Follow these rules:\n"
            f"1. Only generate SQL code that is compatible with {db_dialect} syntax.\n"
            f"2. Make queries efficient and targeted.\n"
            f"3. Include appropriate LIMIT clauses to prevent returning too many rows.\n"
            f"4. For aggregations, include appropriate GROUP BY clauses.\n"
            f"5. Format the SQL query properly with indentation for readability.\n"
            f"6. Respond in JSON format with a single 'sql' field containing the query.\n\n"
        )
        
        # If schema information is provided, include it in the system message
        if schema_info and isinstance(schema_info, dict) and "tables" in schema_info:
            message += "Database schema information:\n"
            for table_name, columns in schema_info["tables"].items():
                message += f"Table: {table_name}\n"
                for column in columns:
                    column_name = column.get("column_name", "unknown")
                    data_type = column.get("data_type", "unknown")
                    message += f"- {column_name} ({data_type})\n"
                message += "\n"
        
        return message
    
    def _create_user_prompt(self, prompt: str, schema_info: Optional[Dict[str, Any]] = None) -> str:
        """Create the user prompt for the OpenAI API with context from the schema if available."""
        user_prompt = f"Convert this question to SQL: '{prompt}'"
        
        # Add hint about available tables if schema info is provided
        if schema_info and isinstance(schema_info, dict) and "tables" in schema_info:
            table_names = list(schema_info["tables"].keys())
            user_prompt += f"\n\nAvailable tables: {', '.join(table_names)}"
        
        user_prompt += "\n\nRespond with a JSON object containing the SQL query in the 'sql' field."
        return user_prompt

# Create a global instance of the OpenAI service
openai_service = OpenAIService()