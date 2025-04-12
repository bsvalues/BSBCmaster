"""
JWT Authentication Module for MCP Assessor Agent API

This module provides JWT-based authentication for secure access to the API.
"""

import os
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any, Union

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

# Security configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "development-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# OAuth2 token URL
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/token")

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# User models
class UserRole(BaseModel):
    """User role model with permissions."""
    name: str
    permissions: List[str]

class UserInDB(BaseModel):
    """User model with password hash."""
    username: str
    email: str
    full_name: Optional[str] = None
    disabled: bool = False
    hashed_password: str
    roles: List[str] = ["user"]  # Default role is 'user'

class User(BaseModel):
    """User model without password hash."""
    username: str
    email: str
    full_name: Optional[str] = None
    disabled: bool = False
    roles: List[str] = ["user"]

class TokenData(BaseModel):
    """Token data model."""
    username: Optional[str] = None
    roles: List[str] = []
    permissions: List[str] = []
    exp: Optional[datetime] = None

class Token(BaseModel):
    """Token response model."""
    access_token: str
    refresh_token: str
    token_type: str
    expires_at: datetime

# Role definitions with permissions
ROLES = {
    "admin": UserRole(
        name="admin",
        permissions=[
            "read:all",
            "write:all",
            "delete:all",
            "manage:users",
            "manage:system"
        ]
    ),
    "assessor": UserRole(
        name="assessor",
        permissions=[
            "read:all",
            "write:property",
            "write:assessment",
            "read:reports",
            "create:reports"
        ]
    ),
    "user": UserRole(
        name="user",
        permissions=[
            "read:property",
            "read:public"
        ]
    )
}

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Generate a password hash."""
    return pwd_context.hash(password)

def get_user_permissions(user_roles: List[str]) -> List[str]:
    """Get all permissions for a user based on their roles."""
    all_permissions = []
    for role in user_roles:
        if role in ROLES:
            all_permissions.extend(ROLES[role].permissions)
    # Remove duplicates while preserving order
    return list(dict.fromkeys(all_permissions))

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a new JWT access token.
    
    Args:
        data: Data to encode in the token
        expires_delta: Optional expiration time delta
        
    Returns:
        str: JWT token
    """
    to_encode = data.copy()
    
    # Set expiration time
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    
    # Create JWT token
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: Dict[str, Any]) -> str:
    """
    Create a new JWT refresh token with extended lifetime.
    
    Args:
        data: Data to encode in the token
        
    Returns:
        str: JWT refresh token
    """
    to_encode = data.copy()
    
    # Set expiration time - longer for refresh tokens
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    
    # Create JWT refresh token
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_tokens(username: str, roles: List[str]) -> Token:
    """
    Create both access and refresh tokens for a user.
    
    Args:
        username: Username to encode in tokens
        roles: List of user roles
        
    Returns:
        Token: Token response with access and refresh tokens
    """
    # Get permissions based on roles
    permissions = get_user_permissions(roles)
    
    # Create token data
    token_data = {
        "sub": username,
        "roles": roles,
        "permissions": permissions
    }
    
    # Set expiration for access token
    access_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token_expires_at = datetime.utcnow() + access_expires
    
    # Create tokens
    access_token = create_access_token(token_data, expires_delta=access_expires)
    refresh_token = create_refresh_token(token_data)
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_at=access_token_expires_at
    )

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """
    Get the current user from the JWT token.
    
    Args:
        token: JWT token from request
        
    Returns:
        User: Current user
        
    Raises:
        HTTPException: If the token is invalid or the user is not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode the JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Extract data from token
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        
        roles = payload.get("roles", ["user"])
        permissions = payload.get("permissions", [])
        exp = payload.get("exp")
        
        token_data = TokenData(
            username=username,
            roles=roles,
            permissions=permissions,
            exp=datetime.fromtimestamp(exp) if exp else None
        )
    except JWTError:
        raise credentials_exception
    
    # Check if token has expired
    if token_data.exp and token_data.exp < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Here you would typically look up the user in the database
    # For now, we'll create a dummy user with the data from the token
    user = User(
        username=token_data.username,
        email=f"{token_data.username}@example.com",  # Placeholder
        roles=token_data.roles
    )
    
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Get the current active user.
    
    Args:
        current_user: Current user from token
        
    Returns:
        User: Current active user
        
    Raises:
        HTTPException: If the user is disabled
    """
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def user_has_permission(permission: str, current_user: User = Depends(get_current_user)) -> bool:
    """
    Check if the current user has a specific permission.
    
    Args:
        permission: Permission to check
        current_user: Current user from token
        
    Returns:
        bool: True if the user has the permission
    """
    user_permissions = get_user_permissions(current_user.roles)
    
    # Admin role has all permissions
    if "admin" in current_user.roles or "read:all" in user_permissions:
        return True
    
    return permission in user_permissions

def require_permission(permission: str):
    """
    Dependency to require a specific permission.
    
    Args:
        permission: Permission required to access the endpoint
        
    Returns:
        Callable: Dependency function that checks the permission
    """
    async def check_permission(current_user: User = Depends(get_current_user)):
        if not user_has_permission(permission, current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not enough permissions. Required: {permission}"
            )
        return current_user
    
    return check_permission

# Integration with MCP Agent system
def create_mcp_agent_token(agent_id: str, agent_type: str) -> str:
    """
    Create a JWT token for an MCP agent.
    
    Args:
        agent_id: Unique agent identifier
        agent_type: Type of agent
        
    Returns:
        str: JWT token for the agent
    """
    # Define agent-specific permissions based on agent type
    agent_permissions = []
    
    if agent_type == "valuation":
        agent_permissions = ["read:property", "write:assessment"]
    elif agent_type == "compliance":
        agent_permissions = ["read:all", "validate:compliance"]
    elif agent_type == "data_quality":
        agent_permissions = ["read:all", "validate:data"]
    else:
        # Default permissions for unknown agent types
        agent_permissions = ["read:public"]
    
    # Create token data
    token_data = {
        "sub": f"agent:{agent_id}",
        "agent_id": agent_id,
        "agent_type": agent_type,
        "permissions": agent_permissions,
        # No roles for agents, they use direct permissions
    }
    
    # Create token with longer expiration for agents
    token_expires = timedelta(days=30)  # Agents get longer-lived tokens
    return create_access_token(token_data, expires_delta=token_expires)

async def get_current_agent(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """
    Get the current agent from the JWT token.
    
    Args:
        token: JWT token from request
        
    Returns:
        Dict: Agent data
        
    Raises:
        HTTPException: If the token is invalid or not an agent token
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate agent credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode the JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Extract agent data from token
        sub = payload.get("sub", "")
        if not sub.startswith("agent:"):
            # Not an agent token
            raise credentials_exception
        
        agent_id = payload.get("agent_id")
        agent_type = payload.get("agent_type")
        permissions = payload.get("permissions", [])
        
        if not agent_id or not agent_type:
            raise credentials_exception
        
        # Return agent data
        return {
            "agent_id": agent_id,
            "agent_type": agent_type,
            "permissions": permissions
        }
    except JWTError:
        raise credentials_exception

def agent_has_permission(permission: str, current_agent: Dict = Depends(get_current_agent)) -> bool:
    """
    Check if the current agent has a specific permission.
    
    Args:
        permission: Permission to check
        current_agent: Current agent from token
        
    Returns:
        bool: True if the agent has the permission
    """
    agent_permissions = current_agent.get("permissions", [])
    return permission in agent_permissions

def require_agent_permission(permission: str):
    """
    Dependency to require a specific permission for an agent.
    
    Args:
        permission: Permission required to access the endpoint
        
    Returns:
        Callable: Dependency function that checks the permission
    """
    async def check_permission(current_agent: Dict = Depends(get_current_agent)):
        if not agent_has_permission(permission, current_agent):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Agent does not have required permission: {permission}"
            )
        return current_agent
    
    return check_permission