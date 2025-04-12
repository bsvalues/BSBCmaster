# JWT Authentication Documentation

## Overview

This document describes the JWT (JSON Web Token) authentication system implemented for the MCP Assessor Agent API. The authentication system provides secure access to API endpoints for both human users and automated agents.

## Features

- **JWT-based authentication**: Secure token-based authentication using industry-standard JWT
- **Role-based access control**: Different user roles with specific permissions
- **Agent authentication**: Special authentication flow for MCP agents
- **Token refresh**: Support for refreshing tokens without requiring re-authentication
- **Secure password storage**: Passwords are hashed using bcrypt

## User Authentication

### User Roles and Permissions

The system defines the following user roles:

- **admin**: Full system access, including user management
- **assessor**: Access to property data and assessment functionality
- **user**: Limited access to public property information

Each role has specific permissions that determine what actions the user can perform.

### Authentication Flow

1. The user submits their username and password to `/api/v1/auth/login` or `/api/v1/auth/token` (OAuth2 compatible)
2. The server verifies the credentials and, if valid, issues an access token and refresh token
3. The client includes the access token in the `Authorization` header for subsequent requests
4. The token is verified for each protected request and the user's permissions are checked
5. When the access token expires, the client can use the refresh token to obtain a new access token

### API Endpoints

- `POST /api/v1/auth/login`: Login with username and password
- `POST /api/v1/auth/token`: OAuth2 compatible token endpoint
- `POST /api/v1/auth/refresh`: Refresh an access token using a refresh token
- `GET /api/v1/auth/users/me`: Get the current user's information
- `POST /api/v1/auth/users`: Create a new user (admin only)

## Agent Authentication

### Agent Types

The system supports different types of agents, each with specific permissions:

- **valuation**: Performs property valuation calculations
- **compliance**: Validates regulatory compliance
- **data_quality**: Validates and enhances data quality

### Agent Authentication Flow

1. The agent submits its ID, type, and secret to `/api/v1/auth/agent-token`
2. The server verifies the credentials and, if valid, issues an access token specific to the agent
3. The agent includes the token in the `Authorization` header for subsequent requests
4. The token is verified for each protected request and the agent's permissions are checked

### API Endpoints

- `POST /api/v1/auth/agent-token`: Obtain a token for an agent

## Integration with MCP Agent System

The JWT authentication system is integrated with the MCP (Master Control Program) agent system, allowing agents to authenticate and access API endpoints based on their type and permissions.

The `MCPAuthAdapter` class provides methods for:

- Authenticating MCP agents using ID and secret
- Obtaining JWT tokens for authenticated agents
- Registering new agents in the system
- Retrieving agent information

## Security Considerations

- Access tokens have a short expiration time (30 minutes by default)
- Refresh tokens have a longer expiration time (7 days by default) but can only be used to obtain new access tokens
- Passwords are hashed using bcrypt, a secure one-way hashing algorithm
- Token verification checks the token's signature, expiration time, and issuer
- Permissions are checked for each protected endpoint
- In production, HTTPS should be used for all communication

## Usage Examples

### User Login

```python
import requests

# User login
response = requests.post(
    "http://localhost:5000/api/v1/auth/login",
    json={"username": "admin", "password": "admin"}
)

# Get the tokens
tokens = response.json()
access_token = tokens["access_token"]

# Use the token for a protected endpoint
response = requests.get(
    "http://localhost:5000/api/v1/auth/users/me",
    headers={"Authorization": f"Bearer {access_token}"}
)
```

### Agent Authentication

```python
import requests

# Agent authentication
response = requests.post(
    "http://localhost:5000/api/v1/auth/agent-token",
    json={
        "agent_id": "valuation_agent",
        "agent_type": "valuation",
        "agent_secret": "agent-secret-key"
    }
)

# Get the token
token_data = response.json()
access_token = token_data["access_token"]

# Use the token for a protected endpoint
response = requests.post(
    "http://localhost:5000/api/v1/valuation/valuate",
    json={"property_id": "123456"},
    headers={"Authorization": f"Bearer {access_token}"}
)
```

## Configuration Options

The following environment variables can be used to configure the authentication system:

- `JWT_SECRET_KEY`: Secret key for JWT signing (default: development-secret-key-change-in-production)
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Expiration time for access tokens in minutes (default: 30)
- `REFRESH_TOKEN_EXPIRE_DAYS`: Expiration time for refresh tokens in days (default: 7)

In production, be sure to set a strong, unique `JWT_SECRET_KEY` and use HTTPS for all communication.