# MCP Assessor Agent API - JWT Authentication System

## Overview

This document provides an overview of the JWT authentication system implemented for the MCP Assessor Agent API. This system is part of Phase 3 (Security Enhancements) of the project, focused on implementing robust security features.

## Architecture

The JWT authentication system is built on the following components:

1. **Core JWT Module** (`app/auth/jwt.py`): The core JWT implementation with token generation, validation, and role-based permissions.
2. **Authentication Routes** (`app/auth/routes.py`): API endpoints for authentication, including login, token refresh, and user management.
3. **MCP Authentication Adapter** (`app/auth/mcp_adapter.py`): Integration between the JWT system and MCP agents.
4. **Authentication Protection** (`app/auth/protect.py`): Middleware and decorators for protecting routes.
5. **Demo Routes** (`app/auth/demo_routes.py`): Example routes demonstrating different protection levels.

## Features

- **JWT-based token authentication**: Industry-standard secure authentication using JSON Web Tokens.
- **Role-based access control**: Different user roles with specific permissions.
- **Agent authentication**: Special authentication flow for MCP agents based on agent types.
- **Token refresh**: Support for refreshing tokens without requiring re-authentication.
- **Protection decorators**: Simple decorators for protecting API routes with authentication and permission checks.

## User Roles and Permissions

The system defines the following user roles:

- **admin**: Full system access, including user management
- **assessor**: Access to property data and assessment functionality
- **user**: Limited access to public property information

Each role has specific permissions that determine what actions the user can perform.

## Authentication Flows

### User Authentication Flow

1. The user submits their username and password to `/api/v1/auth/login` or `/api/v1/auth/token` (OAuth2 compatible)
2. The server verifies the credentials and, if valid, issues an access token and refresh token
3. The client includes the access token in the `Authorization` header for subsequent requests
4. The token is verified for each protected request and the user's permissions are checked
5. When the access token expires, the client can use the refresh token to obtain a new access token

### Agent Authentication Flow

1. The agent submits its ID, type, and secret to `/api/v1/auth/agent-token`
2. The server verifies the credentials and, if valid, issues an access token specific to the agent
3. The agent includes the token in the `Authorization` header for subsequent requests
4. The token is verified for each protected request and the agent's permissions are checked

## API Endpoints

### Authentication Endpoints

- `POST /api/v1/auth/login`: Login with username and password
- `POST /api/v1/auth/token`: OAuth2 compatible token endpoint
- `POST /api/v1/auth/refresh`: Refresh an access token using a refresh token
- `GET /api/v1/auth/users/me`: Get the current user's information
- `POST /api/v1/auth/users`: Create a new user (admin only)
- `POST /api/v1/auth/agent-token`: Obtain a token for an agent

### Demo Endpoints

- `GET /api/auth/demo/public`: Public route that doesn't require authentication
- `GET /api/auth/demo/protected`: Protected route that requires authentication
- `GET /api/auth/demo/admin`: Admin route that requires the manage:users permission
- `GET /api/auth/demo/assessor`: Assessor route that requires the write:assessment permission
- `GET /api/auth/demo/valuation-agent`: Route that requires a valuation agent

## Protection Decorators

The system provides the following decorators for protecting routes:

- `@auth_required`: Requires user authentication
- `@permission_required(permission)`: Requires a specific permission
- `@agent_type_required(agent_type)`: Requires a specific agent type

## Integration with MCP

The JWT authentication system is integrated with the MCP (Master Control Program) agent system, allowing agents to authenticate and access API endpoints based on their type and permissions.

A client library is provided for MCP agents to authenticate:

```python
# Example usage with MCP agent
from mcp.auth_integration import MCPAuthClient

# Create client
client = MCPAuthClient(
    agent_id="valuation_agent",
    agent_type="valuation",
    agent_secret="agent-secret"
)

# Authenticate
if client.authenticate():
    # Make authenticated request
    response = client.make_request(
        method="POST",
        endpoint="/api/v1/valuation/valuate",
        json_data={"property_id": "123456"}
    )
```

## Security Considerations

- Access tokens have a short expiration time (30 minutes by default)
- Refresh tokens have a longer expiration time (7 days by default) but can only be used to obtain new access tokens
- Passwords are hashed using bcrypt, a secure one-way hashing algorithm
- Token verification checks the token's signature, expiration time, and issuer
- Permissions are checked for each protected endpoint
- In production, HTTPS should be used for all communication

## Configuration

The JWT authentication system is configured using environment variables:

- `JWT_SECRET_KEY`: Secret key for JWT signing (default: development-secret-key-change-in-production)
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Expiration time for access tokens in minutes (default: 30)
- `REFRESH_TOKEN_EXPIRE_DAYS`: Expiration time for refresh tokens in days (default: 7)

## Testing

Two test scripts are provided to test the JWT authentication system:

- `test_auth.py`: Basic testing of the authentication endpoints
- `test_jwt_client.py`: Comprehensive testing of all authentication features, including the demo routes

## Further Development

Future enhancements to the JWT authentication system may include:

1. Database-backed user and agent storage
2. Token revocation and blacklisting
3. Multi-factor authentication
4. Rate limiting for authentication endpoints
5. Audit logging for authentication events

## Conclusion

The JWT authentication system provides a secure, flexible, and standards-compliant authentication solution for the MCP Assessor Agent API. It supports both human users and MCP agents, with role-based access control and fine-grained permissions.