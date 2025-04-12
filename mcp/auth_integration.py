"""
MCP Agent Authentication Integration

This module provides integration between the MCP agent system and the JWT authentication system.
"""

import os
import json
import logging
import requests
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:5000")
AUTH_URL = f"{API_URL}/api/v1/auth"

class MCPAuthClient:
    """
    Client for MCP agent authentication using JWT.
    
    This class provides methods for MCP agents to authenticate, obtain tokens,
    and make authenticated API requests.
    """
    
    def __init__(self, agent_id: str, agent_type: str, agent_secret: str):
        """
        Initialize the MCP authentication client.
        
        Args:
            agent_id: Unique identifier for the agent
            agent_type: Type of agent (valuation, compliance, data_quality, etc.)
            agent_secret: Secret key for agent authentication
        """
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.agent_secret = agent_secret
        self.token = None
        self.token_type = "bearer"
    
    def authenticate(self) -> bool:
        """
        Authenticate the agent and obtain a JWT token.
        
        Returns:
            bool: True if authentication was successful, False otherwise
        """
        try:
            # Prepare authentication data
            auth_data = {
                "agent_id": self.agent_id,
                "agent_type": self.agent_type,
                "agent_secret": self.agent_secret
            }
            
            # Make authentication request
            response = requests.post(f"{AUTH_URL}/agent-token", json=auth_data)
            
            # Check if authentication was successful
            if response.status_code == 200:
                # Store token
                token_data = response.json()
                self.token = token_data.get("access_token")
                self.token_type = token_data.get("token_type", "bearer")
                
                logger.info(f"Agent authenticated successfully: {self.agent_id}")
                return True
            else:
                logger.error(f"Authentication failed: {response.text}")
                return False
        
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return False
    
    def get_auth_header(self) -> Dict[str, str]:
        """
        Get the authorization header with the JWT token.
        
        Returns:
            Dict: Authorization header
        """
        if not self.token:
            raise ValueError("Agent not authenticated. Call authenticate() first.")
        
        return {"Authorization": f"{self.token_type.capitalize()} {self.token}"}
    
    def make_request(self, method: str, endpoint: str, json_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make an authenticated API request.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            json_data: Optional JSON data for the request
            
        Returns:
            Dict: API response as a dictionary
        """
        if not self.token:
            self.authenticate()
            if not self.token:
                raise ValueError("Authentication failed")
        
        # Construct URL
        url = f"{API_URL}{endpoint}"
        
        # Make request with authentication header
        try:
            response = requests.request(
                method.upper(),
                url,
                headers=self.get_auth_header(),
                json=json_data
            )
            
            # Check if token is invalid (expired, etc.)
            if response.status_code == 401:
                # Try to re-authenticate
                if self.authenticate():
                    # Retry request with new token
                    response = requests.request(
                        method.upper(),
                        url,
                        headers=self.get_auth_header(),
                        json=json_data
                    )
            
            # Return response data
            if response.status_code in (200, 201):
                return response.json()
            else:
                logger.error(f"API request failed: {response.text}")
                return {"error": response.text, "status_code": response.status_code}
        
        except Exception as e:
            logger.error(f"API request error: {str(e)}")
            return {"error": str(e)}


# Example usage
def main():
    """Example usage of MCPAuthClient."""
    # Create auth client
    client = MCPAuthClient(
        agent_id="valuation_agent",
        agent_type="valuation",
        agent_secret="valuation-secret"
    )
    
    # Authenticate
    if client.authenticate():
        logger.info("Authentication successful")
        
        # Make an authenticated request
        response = client.make_request(
            method="POST",
            endpoint="/api/v1/valuation/valuate",
            json_data={"property_id": "123456"}
        )
        
        logger.info(f"API response: {json.dumps(response, indent=2)}")
    else:
        logger.error("Authentication failed")


if __name__ == "__main__":
    main()