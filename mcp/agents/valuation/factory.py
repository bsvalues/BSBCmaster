"""
Valuation Agent Factory for Benton County Assessor's Office AI Platform

This module provides factory functions for creating and registering
Valuation Agents with the Master Control Program.
"""

import logging
from typing import Dict, Any, Optional

from mcp.master_control import MasterControlProgram
from mcp.agents.valuation.agent import ValuationAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("valuation_factory")


def create_valuation_agent(config: Optional[Dict[str, Any]] = None) -> ValuationAgent:
    """
    Create a Valuation Agent with the specified configuration.
    
    Args:
        config: Configuration for the Valuation Agent
        
    Returns:
        ValuationAgent instance
    """
    agent_config = config or {}
    
    # Extract configuration values with defaults
    agent_id = agent_config.get("agent_id", "valuation_agent")
    
    logger.info(f"Creating Valuation Agent with ID: {agent_id}")
    
    # Create the agent
    agent = ValuationAgent(agent_id=agent_id, **agent_config)
    
    return agent


def register_valuation_agent(mcp: MasterControlProgram, config: Optional[Dict[str, Any]] = None) -> ValuationAgent:
    """
    Create and register a Valuation Agent with the MCP.
    
    Args:
        mcp: Master Control Program instance
        config: Configuration for the Valuation Agent
        
    Returns:
        Registered ValuationAgent instance
    """
    # Create the agent
    agent = create_valuation_agent(config)
    
    # Register with MCP
    mcp.register_agent(agent)
    
    logger.info(f"Registered Valuation Agent with MCP: {agent.agent_id}")
    
    return agent