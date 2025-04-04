#!/bin/bash
# Start Application - Improved workflow script for MCP Assessor Agent API
# This script runs both Flask and FastAPI services, ensuring proper environment configuration

# Load environment variables if .env file exists
if [ -f .env ]; then
  echo "Loading environment variables from .env file..."
  export $(grep -v '^#' .env | xargs)
fi

# Ensure environment variables are set
if [ -z "$DATABASE_URL" ]; then
  echo "ERROR: DATABASE_URL environment variable is not set. Please set it in the .env file."
  exit 1
fi

# Set default API key if not provided
if [ -z "$API_KEY" ]; then
  echo "WARNING: API_KEY environment variable is not set. Using default key."
  export API_KEY="mcp_assessor_api_default_key_2024_secure_random_token_987654321"
fi

# Check if OpenAI API key is set
if [ -z "$OPENAI_API_KEY" ]; then
  echo "WARNING: OPENAI_API_KEY environment variable is not set. Natural language to SQL translation will use fallback mode."
else
  echo "OpenAI API key is set. Natural language to SQL translation will be available."
fi

# Set service URLs and ports
export FLASK_PORT=5000
export FASTAPI_PORT=8000
export FASTAPI_URL="http://0.0.0.0:$FASTAPI_PORT"

# Check if database is accessible
echo "Checking database connection..."
python -c "
import os
import psycopg2
try:
    conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
    cursor = conn.cursor()
    cursor.execute('SELECT 1')
    print('Database connection successful')
    conn.close()
except Exception as e:
    print(f'Database connection failed: {e}')
    exit(1)
"

if [ $? -ne 0 ]; then
  echo "ERROR: Failed to connect to the database. Please check your DATABASE_URL."
  exit 1
fi

# Create database tables if they don't exist
echo "Initializing database..."
python -c "
from app_setup import create_tables_before_first_request
create_tables_before_first_request()
print('Database tables initialized')
"

if [ $? -ne 0 ]; then
  echo "ERROR: Failed to initialize database tables."
  exit 1
fi

# Seed the database if it's empty
echo "Checking if database needs seeding..."
python -c "
from models import Parcel
count = Parcel.query.count()
if count == 0:
    print('Database is empty, seeding recommended')
    exit(1)
else:
    print(f'Database contains {count} parcels')
    exit(0)
"

if [ $? -ne 0 ]; then
  echo "Seeding database with sample data..."
  python seed_database.py
  
  if [ $? -ne 0 ]; then
    echo "WARNING: Failed to seed database with sample data."
  else
    echo "Database seeded successfully."
  fi
fi

# Start the workflow manager
echo "Starting MCP Assessor Agent API services..."
python workflow.py