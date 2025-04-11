"""
Integration Tests for Valuation Agent

This module contains integration tests for the Valuation Agent component
interacting with the Master Control Program and other agents.
"""

import unittest
import logging
import time
from unittest.mock import MagicMock, patch
from datetime import datetime

from mcp.master_control import MasterControlProgram
from mcp.message import Message, MessageType
from mcp.agents.valuation import ValuationAgent
from mcp.agents.valuation.factory import create_valuation_agent, register_valuation_agent
from core.config import CoreConfig

# Disable logging during tests
logging.disable(logging.CRITICAL)


class TestValuationIntegration(unittest.TestCase):
    """Test suite for integration of Valuation Agent with MCP."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a mock MCP
        self.mcp = MagicMock()
        self.mcp.register_agent = MagicMock()
        self.mcp.send_message = MagicMock()
        
        # Create the Valuation Agent
        self.agent = ValuationAgent("test_valuation_agent")
        
        # Mock the send_message method for testing
        self.agent.send_message = MagicMock()
        
        # Register the agent with the MCP
        self.agent.register_with_mcp(self.mcp)
    
    def tearDown(self):
        """Clean up test fixtures."""
        pass
    
    def test_register_with_factory(self):
        """Test registering a Valuation Agent using the factory."""
        mcp = MagicMock()
        
        # Create and register agent with factory
        agent = register_valuation_agent(mcp)
        
        # Verify that agent was registered with MCP
        mcp.register_agent.assert_called_once()
        self.assertEqual(agent.agent_id, "valuation_agent")
    
    def test_create_with_factory(self):
        """Test creating a Valuation Agent using the factory."""
        # Create agent with factory
        agent = create_valuation_agent()
        
        # Verify agent properties
        self.assertEqual(agent.agent_id, "valuation_agent")
        self.assertIsNotNone(agent.metadata)
        self.assertIn("cost_approach", agent.metadata["capabilities"])
    
    def test_create_with_custom_config(self):
        """Test creating a Valuation Agent with custom configuration."""
        # Create agent with custom config
        config = {
            "agent_id": "custom_valuation_agent",
            "debug_mode": True
        }
        
        agent = create_valuation_agent(config)
        
        # Verify agent properties
        self.assertEqual(agent.agent_id, "custom_valuation_agent")
    
    @patch('mcp.agents.valuation.agent.ValuationAgent._handle_valuation_request')
    def test_receive_valuation_request(self, mock_handle_valuation):
        """Test receiving and processing a valuation request."""
        # Create a valuation request message
        message = Message(
            from_agent_id="client",
            to_agent_id="test_valuation_agent",
            message_type=MessageType.VALUATION_REQUEST,
            content={
                "property_id": 1,
                "methodology": "all"
            }
        )
        
        # Receive the message
        self.agent.receive_message(message)
        
        # Verify that handler was called
        mock_handle_valuation.assert_called_once_with(message)
    
    @patch('mcp.agents.valuation.agent.ValuationAgent._handle_trend_analysis_request')
    def test_receive_trend_analysis_request(self, mock_handle_trend):
        """Test receiving and processing a trend analysis request."""
        # Create a trend analysis request message
        message = Message(
            from_agent_id="client",
            to_agent_id="test_valuation_agent",
            message_type=MessageType.TREND_ANALYSIS_REQUEST,
            content={
                "property_id": 1,
                "years": 5
            }
        )
        
        # Receive the message
        self.agent.receive_message(message)
        
        # Verify that handler was called
        mock_handle_trend.assert_called_once_with(message)
    
    @patch('mcp.agents.valuation.agent.ValuationAgent._handle_comparative_analysis_request')
    def test_receive_comparative_analysis_request(self, mock_handle_comparative):
        """Test receiving and processing a comparative analysis request."""
        # Create a comparative analysis request message
        message = Message(
            from_agent_id="client",
            to_agent_id="test_valuation_agent",
            message_type=MessageType.COMPARATIVE_ANALYSIS_REQUEST,
            content={
                "property_id": 1,
                "comparison_property_ids": [2, 3, 4]
            }
        )
        
        # Receive the message
        self.agent.receive_message(message)
        
        # Verify that handler was called
        mock_handle_comparative.assert_called_once_with(message)
    
    def test_send_message_through_mcp(self):
        """Test sending a message through the MCP."""
        # Create a test MCP
        mcp = MagicMock()
        
        # Create an agent and connect it to the MCP
        agent = ValuationAgent("test_agent")
        agent.mcp = mcp
        
        # Create and send a response message
        agent.send_message(
            message_type=MessageType.VALUATION_RESPONSE,
            target_agent_id="client",
            payload={
                "success": True,
                "property_id": 1,
                "results": {"cost_approach": {"total_value": 350000}}
            },
            correlation_id="test_correlation"
        )
        
        # Verify that MCP's send_message was called
        mcp.send_message.assert_called_once()
        
        # Verify message properties
        args, kwargs = mcp.send_message.call_args
        message = args[0]
        
        self.assertEqual(message.from_agent_id, "test_agent")
        self.assertEqual(message.to_agent_id, "client")
        self.assertEqual(message.message_type, MessageType.VALUATION_RESPONSE)
        self.assertEqual(message.correlation_id, "test_correlation")
        self.assertEqual(message.content["property_id"], 1)
        self.assertTrue(message.content["success"])


if __name__ == '__main__':
    unittest.main()