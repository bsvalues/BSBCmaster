"""
MCP Agent Authentication Adapter

This module provides integration between JWT authentication and the MCP agent system,
allowing agents to authenticate securely and obtain the appropriate permissions.
"""

import logging
from typing import Dict, Any, Optional

from app.auth.jwt import (
    create_mcp_agent_token, verify_password, get_password_hash
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Agent registry for authentication purposes
# In production, this would be stored in a database
AGENT_REGISTRY = {
    "valuation_agent": {
        "agent_id": "valuation_agent",
        "agent_type": "valuation",
        "hashed_secret": get_password_hash("valuation-secret"),
        "description": "Property valuation agent"
    },
    "compliance_agent": {
        "agent_id": "compliance_agent",
        "agent_type": "compliance",
        "hashed_secret": get_password_hash("compliance-secret"),
        "description": "Regulatory compliance agent"
    },
    "data_quality_agent": {
        "agent_id": "data_quality_agent",
        "agent_type": "data_quality",
        "hashed_secret": get_password_hash("data-quality-secret"),
        "description": "Data quality validation agent"
    }
}

class MCPAuthAdapter:
    """
    Adapter class for MCP authentication integration.
    
    This class provides methods for MCP agents to authenticate and
    obtain JWT tokens for API access.
    """
    
    @staticmethod
    def authenticate_agent(agent_id: str, agent_secret: str) -> Optional[Dict[str, Any]]:
        """
        Authenticate an MCP agent using its ID and secret.
        
        Args:
            agent_id: Unique agent ID
            agent_secret: Secret key for the agent
            
        Returns:
            Dict: Agent information if authentication succeeds, None otherwise
        """
        # Check if agent exists
        agent_info = AGENT_REGISTRY.get(agent_id)
        if not agent_info:
            logger.warning(f"Authentication attempt for unknown agent: {agent_id}")
            return None
        
        # Verify agent secret
        if not verify_password(agent_secret, agent_info["hashed_secret"]):
            logger.warning(f"Invalid secret for agent: {agent_id}")
            return None
        
        logger.info(f"Agent authenticated successfully: {agent_id}")
        return agent_info
    
    @staticmethod
    def get_agent_token(agent_id: str, agent_secret: str) -> Optional[str]:
        """
        Get a JWT token for an authenticated MCP agent.
        
        Args:
            agent_id: Unique agent ID
            agent_secret: Secret key for the agent
            
        Returns:
            str: JWT token if authentication succeeds, None otherwise
        """
        # Authenticate agent
        agent_info = MCPAuthAdapter.authenticate_agent(agent_id, agent_secret)
        if not agent_info:
            return None
        
        # Create token
        token = create_mcp_agent_token(
            agent_id=agent_info["agent_id"],
            agent_type=agent_info["agent_type"]
        )
        
        return token
    
    @staticmethod
    def register_agent(agent_id: str, agent_type: str, agent_secret: str, description: str = "") -> Dict[str, Any]:
        """
        Register a new MCP agent in the authentication system.
        
        Args:
            agent_id: Unique agent ID
            agent_type: Type of the agent
            agent_secret: Secret key for the agent
            description: Optional description of the agent
            
        Returns:
            Dict: Registered agent information
        """
        # Check if agent already exists
        if agent_id in AGENT_REGISTRY:
            raise ValueError(f"Agent already registered: {agent_id}")
        
        # Hash the secret
        hashed_secret = get_password_hash(agent_secret)
        
        # Create agent entry
        agent_info = {
            "agent_id": agent_id,
            "agent_type": agent_type,
            "hashed_secret": hashed_secret,
            "description": description
        }
        
        # Add to registry
        AGENT_REGISTRY[agent_id] = agent_info
        
        logger.info(f"Agent registered: {agent_id} ({agent_type})")
        return {k: v for k, v in agent_info.items() if k != "hashed_secret"}
    
    @staticmethod
    def get_agent_info(agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a registered agent.
        
        Args:
            agent_id: Unique agent ID
            
        Returns:
            Dict: Agent information if found, None otherwise
        """
        agent_info = AGENT_REGISTRY.get(agent_id)
        if not agent_info:
            return None
        
        # Return info without the hashed secret
        return {k: v for k, v in agent_info.items() if k != "hashed_secret"}