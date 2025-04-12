"""
Test script for the JWT authentication implementation.

This script tests the JWT authentication endpoints and token validation.
"""

import json
import requests
import logging
import sys
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
API_URL = "http://localhost:5000"  # Flask app running on default port
AUTH_URL = f"{API_URL}/api/v1/auth"
USERNAME = "admin"
PASSWORD = "admin"

def test_login():
    """Test the login endpoint with username and password."""
    logger.info(f"Testing login with username: {USERNAME}")
    
    response = requests.post(
        f"{AUTH_URL}/login",
        json={"username": USERNAME, "password": PASSWORD}
    )
    
    logger.info(f"Response status code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        logger.info(f"Login successful: {json.dumps(data, indent=2)}")
        return data
    else:
        logger.error(f"Login failed: {response.text}")
        return None

def test_token_endpoint():
    """Test the OAuth2 token endpoint."""
    logger.info(f"Testing OAuth2 token endpoint with username: {USERNAME}")
    
    response = requests.post(
        f"{AUTH_URL}/token",
        data={"username": USERNAME, "password": PASSWORD},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    logger.info(f"Response status code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        logger.info(f"Token obtained successfully: {json.dumps(data, indent=2)}")
        return data
    else:
        logger.error(f"Failed to get token: {response.text}")
        return None

def test_me_endpoint(token):
    """Test the /users/me endpoint with the token."""
    logger.info("Testing /users/me endpoint with token")
    
    response = requests.get(
        f"{AUTH_URL}/users/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    logger.info(f"Response status code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        logger.info(f"User data: {json.dumps(data, indent=2)}")
        return data
    else:
        logger.error(f"Failed to get user data: {response.text}")
        return None

def test_agent_token():
    """Test the agent token endpoint."""
    logger.info("Testing agent token endpoint")
    
    agent_data = {
        "agent_id": "test_agent",
        "agent_type": "data_quality",
        "agent_secret": "agent-secret-key"
    }
    
    response = requests.post(
        f"{AUTH_URL}/agent-token",
        json=agent_data
    )
    
    logger.info(f"Response status code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        logger.info(f"Agent token obtained: {json.dumps(data, indent=2)}")
        return data
    else:
        logger.error(f"Failed to get agent token: {response.text}")
        return None

def main():
    """Main function to run all tests."""
    logger.info("Testing JWT authentication implementation")
    
    # Test login
    login_data = test_login()
    
    if login_data:
        # Test /users/me endpoint with token
        test_me_endpoint(login_data.get("access_token"))
    
    # Test OAuth2 token endpoint
    token_data = test_token_endpoint()
    
    if token_data:
        # Test /users/me endpoint with token from OAuth2 endpoint
        test_me_endpoint(token_data.get("access_token"))
    
    # Test agent token endpoint
    agent_token_data = test_agent_token()
    
    logger.info("Authentication testing completed")

if __name__ == "__main__":
    main()