#!/usr/bin/env python3
"""
Valuation Agent Demo for Benton County Assessor's Office AI Platform

This script demonstrates the Valuation Agent functionality, including
cost approach, market comparison, and income approach methodologies.
"""

import json
import logging
import time
from typing import Dict, Any, Optional

from mcp.message import Message, MessageType
from mcp.master_control import MasterControlProgram
from mcp.agents.valuation import ValuationAgent
from mcp.agents.valuation.factory import create_valuation_agent, register_valuation_agent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("valuation_demo")


class MockMCP:
    """
    Mock Master Control Program for demonstration purposes.
    
    This class simulates the MCP for standalone agent testing.
    """
    
    def __init__(self):
        """Initialize the Mock MCP."""
        self.agents = {}
        self.messages = []
        self.callbacks = {}
        logger.info("Mock MCP initialized")
    
    def register_agent(self, agent) -> None:
        """Register an agent with the MCP."""
        self.agents[agent.agent_id] = agent
        logger.info(f"Agent {agent.agent_id} registered with Mock MCP")
    
    def send_message(self, message: Message) -> None:
        """Send a message to an agent."""
        self.messages.append(message)
        logger.info(f"Message sent from {message.from_agent_id} to {message.to_agent_id}")
        
        # If recipient is registered, deliver the message
        if message.to_agent_id in self.agents:
            # Call the message handler directly
            self.agents[message.to_agent_id].receive_message(message)
        else:
            logger.warning(f"Agent {message.to_agent_id} not registered, message not delivered")
    
    def register_callback(self, agent_id: str, message_type: MessageType, callback) -> None:
        """Register a callback for a specific message type."""
        key = f"{agent_id}:{message_type.value}"
        self.callbacks[key] = callback
        logger.info(f"Callback registered for {agent_id} and message type {message_type.value}")


def print_json(data: Dict) -> None:
    """Print data as formatted JSON."""
    print(json.dumps(data, indent=2))


def main() -> None:
    """Main function to demonstrate Valuation Agent functionality."""
    print("\n" + "=" * 80)
    print("Benton County Assessor's Office AI Platform - Valuation Agent Demo".center(80))
    print("=" * 80 + "\n")
    
    # Create a mock MCP
    mcp = MockMCP()
    
    # Create the Valuation Agent
    print("Creating Valuation Agent...")
    agent = create_valuation_agent()
    
    # Register agent with mock MCP
    mcp.register_agent(agent)
    print(f"Valuation Agent created with ID: {agent.agent_id}\n")
    
    # Set up message response handling
    def handle_valuation_response(message):
        print("\nReceived valuation response:")
        print_json(message.content)
    
    def handle_trend_analysis_response(message):
        print("\nReceived trend analysis response:")
        print_json(message.content)
    
    def handle_comparative_analysis_response(message):
        print("\nReceived comparative analysis response:")
        print_json(message.content)
    
    # Register callbacks
    mcp.register_callback("client", MessageType.VALUATION_RESPONSE, handle_valuation_response)
    mcp.register_callback("client", MessageType.TREND_ANALYSIS_RESPONSE, handle_trend_analysis_response)
    mcp.register_callback("client", MessageType.COMPARATIVE_ANALYSIS_RESPONSE, handle_comparative_analysis_response)
    
    # Demo 1: Property Valuation Request
    print("Demo 1: Property Valuation Request")
    print("-" * 80)
    
    # Create a valuation request message
    valuation_request = Message(
        from_agent_id="client",
        to_agent_id=agent.agent_id,
        message_type=MessageType.VALUATION_REQUEST,
        content={
            "property_id": 1,  # Assuming we have a property with ID 1
            "methodology": "all"  # Use all valuation methods
        }
    )
    
    # Send the message
    print("Sending valuation request for property ID 1...")
    mcp.send_message(valuation_request)
    
    # Wait for processing
    time.sleep(1)
    
    # Demo 2: Trend Analysis Request
    print("\nDemo 2: Trend Analysis Request")
    print("-" * 80)
    
    # Create a trend analysis request message
    trend_request = Message(
        from_agent_id="client",
        to_agent_id=agent.agent_id,
        message_type=MessageType.TREND_ANALYSIS_REQUEST,
        content={
            "property_id": 1,  # Assuming we have a property with ID 1
            "years": 5  # Analyze 5 years of trends
        }
    )
    
    # Send the message
    print("Sending trend analysis request for property ID 1...")
    mcp.send_message(trend_request)
    
    # Wait for processing
    time.sleep(1)
    
    # Demo 3: Comparative Analysis Request
    print("\nDemo 3: Comparative Analysis Request")
    print("-" * 80)
    
    # Create a comparative analysis request message
    comparative_request = Message(
        from_agent_id="client",
        to_agent_id=agent.agent_id,
        message_type=MessageType.COMPARATIVE_ANALYSIS_REQUEST,
        content={
            "property_id": 1,  # Assuming we have a property with ID 1
            "comparison_property_ids": [2, 3, 4]  # Compare with these properties
        }
    )
    
    # Send the message
    print("Sending comparative analysis request for property ID 1...")
    mcp.send_message(comparative_request)
    
    # Wait for processing
    time.sleep(1)
    
    print("\nDemo completed successfully.\n")


if __name__ == "__main__":
    main()