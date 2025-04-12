"""
Supabase Authentication Integration

This module provides integration between the JWT authentication system
and Supabase's authentication service.
"""

import os
import logging
from typing import Dict, Any, Optional, List, Tuple
from app.db.supabase_client import get_supabase_client, is_connected
from app.auth.jwt import get_password_hash, verify_password, create_tokens, Token

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def signup_user(username: str, email: str, password: str, full_name: Optional[str] = None, 
                roles: List[str] = ["user"]) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Sign up a new user in Supabase.
    
    Args:
        username: Username for the new user
        email: Email address for the new user
        password: Password for the new user
        full_name: Optional full name for the new user
        roles: List of roles for the new user (default: ["user"])
        
    Returns:
        Tuple[bool, str, Optional[Dict[str, Any]]]: 
            - Success flag
            - Message
            - User data if successful, None otherwise
    """
    if not is_connected():
        return False, "Supabase client not initialized", None
    
    supabase = get_supabase_client()
    if not supabase:
        return False, "Supabase client not available", None
    
    try:
        # Hash the password for secure storage
        hashed_password = get_password_hash(password)
        
        # Create user data
        user_data = {
            "username": username,
            "email": email,
            "full_name": full_name,
            "hashed_password": hashed_password,
            "roles": roles,
            "disabled": False
        }
        
        # Insert the user into the 'users' table
        response = supabase.table("users").insert(user_data).execute()
        
        if hasattr(response, 'error') and response.error:
            logger.error(f"Error creating user: {response.error}")
            return False, f"Error creating user: {response.error}", None
        
        # Get the created user
        created_user = response.data[0] if response.data else None
        if not created_user:
            return False, "User created but no data returned", None
        
        return True, "User created successfully", created_user
        
    except Exception as e:
        logger.error(f"Exception creating user: {str(e)}")
        return False, f"Exception creating user: {str(e)}", None

def login_user(username: str, password: str) -> Tuple[bool, str, Optional[Token]]:
    """
    Login a user with username and password.
    
    Args:
        username: User's username
        password: User's password
        
    Returns:
        Tuple[bool, str, Optional[Token]]: 
            - Success flag
            - Message
            - Token data if successful, None otherwise
    """
    if not is_connected():
        return False, "Supabase client not initialized", None
    
    supabase = get_supabase_client()
    if not supabase:
        return False, "Supabase client not available", None
    
    try:
        # Get the user from Supabase
        response = supabase.table("users").select("*").eq("username", username).limit(1).single().execute()
        
        if hasattr(response, 'error') and response.error:
            logger.error(f"Error getting user: {response.error}")
            return False, f"Error getting user: {response.error}", None
        
        user_data = response.data
        if not user_data:
            return False, "User not found", None
        
        # Check if the user is disabled
        if user_data.get("disabled", False):
            return False, "User account is disabled", None
        
        # Verify the password
        hashed_password = user_data.get("hashed_password")
        if not hashed_password or not verify_password(password, hashed_password):
            return False, "Invalid password", None
        
        # Get the user's roles
        roles = user_data.get("roles", ["user"])
        
        # Create tokens
        token = create_tokens(username, roles)
        
        return True, "Login successful", token
        
    except Exception as e:
        logger.error(f"Exception logging in user: {str(e)}")
        return False, f"Exception logging in user: {str(e)}", None

def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """
    Get a user by username.
    
    Args:
        username: User's username
        
    Returns:
        Optional[Dict[str, Any]]: User data if found, None otherwise
    """
    if not is_connected():
        logger.error("Cannot get user: Supabase client not initialized")
        return None
    
    supabase = get_supabase_client()
    if not supabase:
        logger.error("Cannot get user: Supabase client not available")
        return None
    
    try:
        response = supabase.table("users").select("*").eq("username", username).limit(1).single().execute()
        
        if hasattr(response, 'error') and response.error:
            logger.error(f"Error getting user {username}: {response.error}")
            return None
        
        return response.data
        
    except Exception as e:
        logger.error(f"Exception getting user {username}: {str(e)}")
        return None

def update_user(username: str, user_data: Dict[str, Any]) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Update a user's information.
    
    Args:
        username: User's username
        user_data: Updated user data
        
    Returns:
        Tuple[bool, str, Optional[Dict[str, Any]]]: 
            - Success flag
            - Message
            - Updated user data if successful, None otherwise
    """
    if not is_connected():
        return False, "Supabase client not initialized", None
    
    supabase = get_supabase_client()
    if not supabase:
        return False, "Supabase client not available", None
    
    try:
        # Remove password from user_data if present (should use change_password instead)
        if "password" in user_data:
            del user_data["password"]
        
        # Update the user
        response = supabase.table("users").update(user_data).eq("username", username).execute()
        
        if hasattr(response, 'error') and response.error:
            logger.error(f"Error updating user {username}: {response.error}")
            return False, f"Error updating user: {response.error}", None
        
        # Get the updated user
        updated_user = response.data[0] if response.data else None
        if not updated_user:
            return False, "User updated but no data returned", None
        
        return True, "User updated successfully", updated_user
        
    except Exception as e:
        logger.error(f"Exception updating user {username}: {str(e)}")
        return False, f"Exception updating user: {str(e)}", None

def change_password(username: str, current_password: str, new_password: str) -> Tuple[bool, str]:
    """
    Change a user's password.
    
    Args:
        username: User's username
        current_password: User's current password
        new_password: User's new password
        
    Returns:
        Tuple[bool, str]: 
            - Success flag
            - Message
    """
    if not is_connected():
        return False, "Supabase client not initialized"
    
    supabase = get_supabase_client()
    if not supabase:
        return False, "Supabase client not available"
    
    try:
        # Get the user
        response = supabase.table("users").select("*").eq("username", username).limit(1).single().execute()
        
        if hasattr(response, 'error') and response.error:
            logger.error(f"Error getting user {username}: {response.error}")
            return False, f"Error getting user: {response.error}"
        
        user_data = response.data
        if not user_data:
            return False, "User not found"
        
        # Verify the current password
        hashed_password = user_data.get("hashed_password")
        if not hashed_password or not verify_password(current_password, hashed_password):
            return False, "Current password is incorrect"
        
        # Hash the new password
        new_hashed_password = get_password_hash(new_password)
        
        # Update the password
        update_response = supabase.table("users").update(
            {"hashed_password": new_hashed_password}
        ).eq("username", username).execute()
        
        if hasattr(update_response, 'error') and update_response.error:
            logger.error(f"Error updating password for user {username}: {update_response.error}")
            return False, f"Error updating password: {update_response.error}"
        
        return True, "Password changed successfully"
        
    except Exception as e:
        logger.error(f"Exception changing password for user {username}: {str(e)}")
        return False, f"Exception changing password: {str(e)}"

def delete_user(username: str) -> Tuple[bool, str]:
    """
    Delete a user.
    
    Args:
        username: User's username
        
    Returns:
        Tuple[bool, str]: 
            - Success flag
            - Message
    """
    if not is_connected():
        return False, "Supabase client not initialized"
    
    supabase = get_supabase_client()
    if not supabase:
        return False, "Supabase client not available"
    
    try:
        # Delete the user
        response = supabase.table("users").delete().eq("username", username).execute()
        
        if hasattr(response, 'error') and response.error:
            logger.error(f"Error deleting user {username}: {response.error}")
            return False, f"Error deleting user: {response.error}"
        
        return True, "User deleted successfully"
        
    except Exception as e:
        logger.error(f"Exception deleting user {username}: {str(e)}")
        return False, f"Exception deleting user: {str(e)}"

def get_users(limit: int = 100, offset: int = 0) -> Tuple[bool, str, List[Dict[str, Any]]]:
    """
    Get a list of users.
    
    Args:
        limit: Maximum number of users to return
        offset: Number of users to skip
        
    Returns:
        Tuple[bool, str, List[Dict[str, Any]]]: 
            - Success flag
            - Message
            - List of users if successful, empty list otherwise
    """
    if not is_connected():
        return False, "Supabase client not initialized", []
    
    supabase = get_supabase_client()
    if not supabase:
        return False, "Supabase client not available", []
    
    try:
        # Get the users
        response = supabase.table("users").select("*").limit(limit).offset(offset).execute()
        
        if hasattr(response, 'error') and response.error:
            logger.error(f"Error getting users: {response.error}")
            return False, f"Error getting users: {response.error}", []
        
        return True, "Users retrieved successfully", response.data or []
        
    except Exception as e:
        logger.error(f"Exception getting users: {str(e)}")
        return False, f"Exception getting users: {str(e)}", []