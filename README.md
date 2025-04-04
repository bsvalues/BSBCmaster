# MCP Assessor Agent API

A secure FastAPI intermediary service designed for efficient and safe database querying across MS SQL Server and PostgreSQL databases. This API service allows for secure execution of SQL queries, database schema discovery, and natural language to SQL translation.

## Key Features

- **Multi-Database Support**: Connect to both MS SQL Server and PostgreSQL databases
- **Secure API Access**: API key-based authentication
- **SQL Query Execution**: Execute SQL queries against the configured databases
- **Schema Discovery**: Retrieve database schema information
- **Schema Summarization**: Get a summarized view of database structure
- **Health Check**: Monitor the API and database connection status
- **Natural Language to SQL**: (Simulated) Translate natural language to SQL queries

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