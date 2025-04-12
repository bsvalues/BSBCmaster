"""
Authentication routes for MCP Assessor Agent API.

This module provides API endpoints for authentication, including login, token refresh,
and user management.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field

from app.auth.jwt import (
    Token, User, create_tokens, verify_password, get_password_hash,
    get_current_active_user, create_mcp_agent_token
)

# Create API router
router = APIRouter(prefix="/auth", tags=["authentication"])

# Mock user database - would be replaced with actual database in production
fake_users_db = {
    "admin": {
        "username": "admin",
        "email": "admin@example.com",
        "full_name": "Administrator",
        "hashed_password": get_password_hash("admin"),  # Don't use this in production!
        "disabled": False,
        "roles": ["admin"]
    },
    "assessor": {
        "username": "assessor",
        "email": "assessor@example.com",
        "full_name": "County Assessor",
        "hashed_password": get_password_hash("assessor"),  # Don't use this in production!
        "disabled": False,
        "roles": ["assessor"]
    },
    "user": {
        "username": "user",
        "email": "user@example.com",
        "full_name": "Regular User",
        "hashed_password": get_password_hash("user"),  # Don't use this in production!
        "disabled": False,
        "roles": ["user"]
    }
}

# Request and response models
class LoginRequest(BaseModel):
    """Login request model."""
    username: str
    password: str

class UserResponse(BaseModel):
    """User response model."""
    username: str
    email: str
    full_name: str = None
    roles: List[str] = Field(default_factory=list)

class CreateUserRequest(BaseModel):
    """Create user request model."""
    username: str
    email: str
    password: str
    full_name: str = None
    roles: List[str] = Field(default_factory=lambda: ["user"])

class AgentTokenRequest(BaseModel):
    """Agent token request model."""
    agent_id: str
    agent_type: str
    agent_secret: str = Field(..., description="Secret key for agent authentication")

class AgentTokenResponse(BaseModel):
    """Agent token response model."""
    access_token: str
    token_type: str
    agent_id: str
    agent_type: str

# Routes
@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    OAuth2 compatible token login, get an access token for future requests.
    """
    user = fake_users_db.get(form_data.username)
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create tokens
    token = create_tokens(form_data.username, user["roles"])
    return token

@router.post("/login", response_model=Token)
async def login(login_data: LoginRequest):
    """
    Login with username and password, get an access token for future requests.
    """
    user = fake_users_db.get(login_data.username)
    if not user or not verify_password(login_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is disabled
    if user.get("disabled", False):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled",
        )
    
    # Create tokens
    token = create_tokens(login_data.username, user["roles"])
    return token

@router.post("/refresh", response_model=Token)
async def refresh_token(token: str):
    """
    Refresh an access token using a refresh token.
    """
    # This would verify the refresh token and issue a new access token
    # For simplicity, this is a placeholder
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Token refresh not implemented yet",
    )

@router.get("/users/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """
    Get the current user's information.
    """
    return UserResponse(
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        roles=current_user.roles
    )

@router.post("/users", response_model=UserResponse)
async def create_user(
    user_data: CreateUserRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new user (admin only).
    """
    # Check if user has permission to create users
    if "admin" not in current_user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    # Check if username already exists
    if user_data.username in fake_users_db:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )
    
    # Create user
    hashed_password = get_password_hash(user_data.password)
    fake_users_db[user_data.username] = {
        "username": user_data.username,
        "email": user_data.email,
        "full_name": user_data.full_name,
        "hashed_password": hashed_password,
        "disabled": False,
        "roles": user_data.roles
    }
    
    return UserResponse(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        roles=user_data.roles
    )

# MCP Agent specific authentication
@router.post("/agent-token", response_model=AgentTokenResponse)
async def create_agent_token(request: AgentTokenRequest):
    """
    Create a JWT token for an MCP agent.
    """
    # In production, this would verify the agent_secret against a database
    # For now, we'll use a simple check
    AGENT_SECRET = "agent-secret-key"  # This would be stored securely
    
    if request.agent_secret != AGENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid agent secret",
        )
    
    # Create agent token
    token = create_mcp_agent_token(request.agent_id, request.agent_type)
    
    return AgentTokenResponse(
        access_token=token,
        token_type="bearer",
        agent_id=request.agent_id,
        agent_type=request.agent_type
    )