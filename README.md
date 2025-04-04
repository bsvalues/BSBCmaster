# MCP Assessor Agent API

A secure FastAPI intermediary service designed for efficient and safe database querying across MS SQL Server and PostgreSQL databases. This API service allows for secure execution of SQL queries, database schema discovery, natural language to SQL translation, and interactive data visualization.

## Quick Start

1. Clone the repository
2. Create a `.env` file with the following variables:
   ```
   DATABASE_URL=your_postgresql_connection_string
   PGPORT=your_pg_port
   PGUSER=your_pg_user
   PGPASSWORD=your_pg_password
   PGDATABASE=your_pg_database
   PGHOST=your_pg_host
   API_KEY=your_api_key
   OPENAI_API_KEY=your_openai_api_key
   ```
3. Run the services using one of the following methods:
   - Start both Flask and FastAPI services: `./start_both.sh`
   - Start FastAPI service only: `./start_fastapi_service.sh`

## Accessing the Services

- **Flask Documentation UI**: http://localhost:5000
- **FastAPI Endpoints**: http://localhost:8000
- **API Documentation**: http://localhost:8000/api/docs
- **API Redoc**: http://localhost:8000/api/redoc

## Key Features

- **Multi-Database Support**: Connect to both MS SQL Server and PostgreSQL databases
- **Secure API Access**: API key-based authentication
- **SQL Query Execution**: Execute SQL queries against the configured databases
- **Schema Discovery**: Retrieve database schema information
- **Schema Summarization**: Get a summarized view of database structure
- **Health Check**: Monitor the API and database connection status
- **Natural Language to SQL**: (Simulated) Translate natural language to SQL queries
- **Interactive Data Visualization**: Create charts and visualizations from query results
- **Visual Query Builder**: Build SQL queries through an intuitive visual interface

## Enhanced SQL Injection Protection

The API implements robust SQL injection prevention through several layers of protection:

### 1. Parameterized Queries

All user-supplied queries are processed through a parameter extraction system that identifies:
- String literals (both single and double-quoted)
- Numeric values in WHERE/HAVING/ON clauses
- Other SQL literals

These extracted values are replaced with placeholders and passed separately to the database driver, preventing SQL injection attacks.

### 2. Query Sanitization

Before execution, each query is validated against a list of potentially dangerous SQL operations:
- DROP, DELETE, UPDATE, INSERT, ALTER, TRUNCATE
- CREATE, GRANT, EXEC, EXECUTE, SCHEMA
- Other potentially harmful operations

### 3. Database-Specific Parameter Handling

The API automatically converts parameter placeholders to match the required format for each database:
- `?` placeholders for MS SQL Server
- `%s` placeholders for PostgreSQL

### 4. Sanitized Error Messages

Error messages are sanitized before being returned to the client to prevent information leakage:
- Detailed error information is logged for debugging but not exposed to clients
- Generic error messages are returned to avoid revealing database structure

## Architecture

- **FastAPI Framework**: Modern, high-performance web framework
- **Connection Pooling**: Efficient database connection management for PostgreSQL
- **Context Managers**: Safe resource handling for database connections
- **Pydantic Models**: Request/response validation and API documentation
- **CORS Middleware**: Cross-Origin Resource Sharing configuration

## API Endpoints

- **GET /api/health**: Check the health status of the API and databases
- **POST /api/run-query**: Execute a SQL query
- **POST /api/nl-to-sql**: Convert natural language to SQL
- **GET /api/discover-schema**: Retrieve database schema
- **GET /api/schema-summary**: Get summarized schema information

## Technologies Used

- Python 3.11+
- FastAPI/Starlette
- Flask (for documentation interface)
- pyodbc (MS SQL Server)
- psycopg2 (PostgreSQL)
- Pydantic
- Gunicorn (WSGI/ASGI server)
- Bootstrap (UI framework)
- Chart.js (Data visualization)

## Data Visualization

The API documentation includes a robust data visualization module that allows users to:

- Execute SQL queries and visualize the results
- Create various chart types (bar, line, pie, scatter)
- Customize chart appearance and data mapping
- Export visualization code for integration into applications
- Interactively explore data relationships

## Development and Maintenance

### Environment Setup

1. Check environment variables are properly set:
   ```
   python check_env.py
   ```

2. Install required dependencies:
   ```
   pip install -r requirements.txt
   ```

### Running Services

The application is composed of two services:

1. **Flask Documentation UI** on port 5000
   - Provides the main documentation and user interface
   - Serves as a proxy for API requests to the FastAPI service

2. **FastAPI Backend** on port 8000
   - Handles all API requests
   - Provides database connectivity
   - Implements security features
   - Processes natural language to SQL conversion

### Available Scripts

- `./start_both.sh`: Start both Flask and FastAPI services together
- `./start_fastapi_service.sh`: Start only the FastAPI backend
- `python run_api.py`: Run the FastAPI backend with direct console output
- `python run_services.py`: Run both services in parallel
- `python seed_database.py`: Seed the database with sample data
- `python check_env.py`: Verify environment variables are properly set