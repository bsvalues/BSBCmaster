"""
JWT Authentication Test Client

This script provides a more comprehensive test of the JWT authentication system,
including the demo routes.
"""

import json
import sys
import logging
import requests
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
API_URL = "http://localhost:5000"
AUTH_URL = f"{API_URL}/api/v1/auth"
DEMO_URL = f"{API_URL}/api/auth/demo"

class JWTAuthClient:
    """
    Client for testing JWT authentication.
    """
    
    def __init__(self):
        self.access_token = None
        self.refresh_token = None
        self.token_type = "bearer"
        self.username = None
        self.roles = []
    
    def login(self, username: str, password: str) -> bool:
        """
        Login with username and password.
        
        Args:
            username: User's username
            password: User's password
            
        Returns:
            bool: True if login was successful, False otherwise
        """
        try:
            # Make login request
            response = requests.post(
                f"{AUTH_URL}/login",
                json={"username": username, "password": password}
            )
            
            # Check if login was successful
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("access_token")
                self.refresh_token = data.get("refresh_token")
                self.token_type = data.get("token_type", "bearer")
                self.username = username
                logger.info(f"Login successful for user: {username}")
                return True
            else:
                logger.error(f"Login failed: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return False
    
    def get_auth_header(self) -> Dict[str, str]:
        """
        Get authorization header with the token.
        
        Returns:
            Dict: Header with authorization token
        """
        if not self.access_token:
            raise ValueError("Not authenticated. Call login() first.")
            
        return {"Authorization": f"{self.token_type.capitalize()} {self.access_token}"}
    
    def get_current_user(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the current user.
        
        Returns:
            Dict: User information if successful, None otherwise
        """
        if not self.access_token:
            logger.error("Not authenticated. Call login() first.")
            return None
            
        try:
            # Make request to /users/me endpoint
            response = requests.get(
                f"{AUTH_URL}/users/me",
                headers=self.get_auth_header()
            )
            
            # Check if request was successful
            if response.status_code == 200:
                data = response.json()
                self.roles = data.get("roles", [])
                logger.info(f"Got current user: {data}")
                return data
            else:
                logger.error(f"Failed to get current user: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting current user: {str(e)}")
            return None
    
    def test_public_route(self) -> Optional[Dict[str, Any]]:
        """
        Test a public route that doesn't require authentication.
        
        Returns:
            Dict: Response data if successful, None otherwise
        """
        try:
            # Make request to public endpoint
            response = requests.get(f"{DEMO_URL}/public")
            
            # Check if request was successful
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Public route access successful: {json.dumps(data, indent=2)}")
                return data
            else:
                logger.error(f"Failed to access public route: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error accessing public route: {str(e)}")
            return None
    
    def test_protected_route(self) -> Optional[Dict[str, Any]]:
        """
        Test a protected route that requires authentication.
        
        Returns:
            Dict: Response data if successful, None otherwise
        """
        if not self.access_token:
            logger.error("Not authenticated. Call login() first.")
            return None
            
        try:
            # Make request to protected endpoint
            response = requests.get(
                f"{DEMO_URL}/protected",
                headers=self.get_auth_header()
            )
            
            # Check if request was successful
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Protected route access successful: {json.dumps(data, indent=2)}")
                return data
            else:
                logger.error(f"Failed to access protected route: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error accessing protected route: {str(e)}")
            return None
    
    def test_admin_route(self) -> Optional[Dict[str, Any]]:
        """
        Test an admin route that requires the manage:users permission.
        
        Returns:
            Dict: Response data if successful, None otherwise
        """
        if not self.access_token:
            logger.error("Not authenticated. Call login() first.")
            return None
            
        try:
            # Make request to admin endpoint
            response = requests.get(
                f"{DEMO_URL}/admin",
                headers=self.get_auth_header()
            )
            
            # Check if request was successful
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Admin route access successful: {json.dumps(data, indent=2)}")
                return data
            else:
                logger.error(f"Failed to access admin route: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error accessing admin route: {str(e)}")
            return None
    
    def test_assessor_route(self) -> Optional[Dict[str, Any]]:
        """
        Test an assessor route that requires the write:assessment permission.
        
        Returns:
            Dict: Response data if successful, None otherwise
        """
        if not self.access_token:
            logger.error("Not authenticated. Call login() first.")
            return None
            
        try:
            # Make request to assessor endpoint
            response = requests.get(
                f"{DEMO_URL}/assessor",
                headers=self.get_auth_header()
            )
            
            # Check if request was successful
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Assessor route access successful: {json.dumps(data, indent=2)}")
                return data
            else:
                logger.error(f"Failed to access assessor route: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error accessing assessor route: {str(e)}")
            return None


def main():
    """Main function to run the test client."""
    logger.info("Starting JWT authentication test client")
    
    # Create client
    client = JWTAuthClient()
    
    # Test public route (should work without authentication)
    client.test_public_route()
    
    # Test admin login
    if not client.login("admin", "admin"):
        logger.error("Admin login failed. Exiting.")
        return
    
    # Get current user
    client.get_current_user()
    
    # Test protected route (should work for any authenticated user)
    client.test_protected_route()
    
    # Test admin route (should work for admin)
    client.test_admin_route()
    
    # Test assessor route (should work for admin, might not work for regular user)
    client.test_assessor_route()
    
    # Now test with assessor user
    client = JWTAuthClient()
    if not client.login("assessor", "assessor"):
        logger.error("Assessor login failed. Exiting.")
        return
    
    # Get current user
    client.get_current_user()
    
    # Test protected route (should work for any authenticated user)
    client.test_protected_route()
    
    # Test admin route (should fail for assessor)
    client.test_admin_route()
    
    # Test assessor route (should work for assessor)
    client.test_assessor_route()
    
    # Now test with regular user
    client = JWTAuthClient()
    if not client.login("user", "user"):
        logger.error("User login failed. Exiting.")
        return
    
    # Get current user
    client.get_current_user()
    
    # Test protected route (should work for any authenticated user)
    client.test_protected_route()
    
    # Test admin route (should fail for regular user)
    client.test_admin_route()
    
    # Test assessor route (should fail for regular user)
    client.test_assessor_route()
    
    logger.info("JWT authentication test client completed")


if __name__ == "__main__":
    main()