"""
Unit Tests for Master Control Program (MCP)

This module provides comprehensive unit tests for the MCP,
ensuring that agent registration, message routing, and task management
function correctly.
"""

import unittest
import logging
import os
import json
import sys
import time
from typing import Dict, Any, List, Optional

# Add parent directory to path to facilitate imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from mcp.master_control import MasterControlProgram
from mcp.message import MessageType, MessagePriority
from mcp.task import TaskPriority
from testing.test_config import TestConfig
from testing.test_utils import TestUtils


class MockAgent:
    """Mock agent for testing MCP interactions."""
    
    def __init__(self, agent_id, agent_type="test"):
        """Initialize mock agent."""
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.messages_received = []
        self.tasks_received = []
    
    def register_with_mcp(self, mcp):
        """Register this agent with the MCP."""
        self.mcp = mcp
        return mcp.register_agent(self.agent_id, self)
    
    def receive_message(self, message):
        """Receive a message from the MCP."""
        self.messages_received.append(message)
        return {"status": "received", "message_id": message.get("message_id")}
    
    def process_task(self, task):
        """Process a task from the MCP."""
        self.tasks_received.append(task)
        return {"status": "processing", "task_id": task.get("task_id")}
    
    def get_agent_status(self):
        """Get agent status."""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "messages_received": len(self.messages_received),
            "tasks_received": len(self.tasks_received),
            "status": "active"
        }


class TestMCP(unittest.TestCase):
    """Unit tests for the Master Control Program (MCP)."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment once before all tests."""
        # Initialize test configuration
        cls.config = TestConfig()
        
        # Initialize test utilities
        cls.utils = TestUtils(cls.config)
        
        # Prepare test directory
        cls.test_dir = cls.utils.prepare_test_directory("mcp_unit_tests")
        
        # Set up logging
        cls.logger = logging.getLogger("test_mcp")
    
    def setUp(self):
        """Set up before each test."""
        # Create a fresh MCP for each test
        self.mcp = MasterControlProgram()
        self.mcp.start()
        
        # Create mock agents
        self.agent1 = MockAgent("agent1", "data_quality")
        self.agent2 = MockAgent("agent2", "compliance")
        self.agent3 = MockAgent("agent3", "valuation")
    
    def tearDown(self):
        """Clean up after each test."""
        # Stop the MCP
        self.mcp.stop()
    
    def test_mcp_initialization(self):
        """Test that the MCP initializes correctly."""
        # Check that MCP is running
        self.assertTrue(self.mcp.is_running)
        
        # Check that MCP has empty agent registry
        self.assertEqual(len(self.mcp.list_agents()), 0)
    
    def test_agent_registration(self):
        """Test agent registration with the MCP."""
        # Register agents
        self.agent1.register_with_mcp(self.mcp)
        self.agent2.register_with_mcp(self.mcp)
        
        # Check that agents are registered
        agents = self.mcp.list_agents()
        self.assertEqual(len(agents), 2)
        
        # Check agent details
        agent_ids = [a.get("agent_id") for a in agents]
        self.assertIn(self.agent1.agent_id, agent_ids)
        self.assertIn(self.agent2.agent_id, agent_ids)
        
        # Register a third agent
        self.agent3.register_with_mcp(self.mcp)
        
        # Check that all agents are registered
        agents = self.mcp.list_agents()
        self.assertEqual(len(agents), 3)
        
        # Save test results
        self.utils.save_test_results(
            {
                "agents_registered": [a.get("agent_id") for a in agents],
                "agent_types": [a.get("type") for a in agents]
            },
            "agent_registration",
            self.test_dir
        )
    
    def test_message_sending(self):
        """Test sending messages between agents via the MCP."""
        # Register agents
        self.agent1.register_with_mcp(self.mcp)
        self.agent2.register_with_mcp(self.mcp)
        
        # Send a message from agent1 to agent2
        message_result = self.mcp.send_message(
            from_agent_id=self.agent1.agent_id,
            to_agent_id=self.agent2.agent_id,
            message_type=MessageType.DATA_UPDATE,
            content={"data": "test_data"}
        )
        
        # Check that message was sent
        self.assertIn("message_id", message_result)
        self.assertIn("status", message_result)
        self.assertEqual(message_result["status"], "sent")
        
        # Wait for message to be processed
        time.sleep(0.1)
        
        # Check that agent2 received the message
        self.assertEqual(len(self.agent2.messages_received), 1)
        
        received_message = self.agent2.messages_received[0]
        self.assertEqual(received_message["from_agent_id"], self.agent1.agent_id)
        self.assertEqual(received_message["to_agent_id"], self.agent2.agent_id)
        self.assertEqual(received_message["message_type"], MessageType.DATA_UPDATE.name)
        self.assertEqual(received_message["content"]["data"], "test_data")
        
        # Save test results
        self.utils.save_test_results(
            {
                "message_sent": {
                    "from_agent_id": self.agent1.agent_id,
                    "to_agent_id": self.agent2.agent_id,
                    "message_type": MessageType.DATA_UPDATE.name,
                    "content": {"data": "test_data"}
                },
                "message_received": received_message
            },
            "message_sending",
            self.test_dir
        )
    
    def test_task_creation(self):
        """Test task creation and assignment via the MCP."""
        # Register agents
        self.agent1.register_with_mcp(self.mcp)
        self.agent2.register_with_mcp(self.mcp)
        
        # Create a task for agent2
        task_result = self.mcp.create_task(
            to_agent_id=self.agent2.agent_id,
            task_type="validate_data",
            parameters={"data": "test_data"},
            from_agent_id=self.agent1.agent_id,
            priority=TaskPriority.NORMAL
        )
        
        # Check that task was created
        self.assertIn("task_id", task_result)
        self.assertIn("status", task_result)
        self.assertEqual(task_result["status"], "created")
        
        # Wait for task to be processed
        time.sleep(0.1)
        
        # Check that agent2 received the task
        self.assertEqual(len(self.agent2.tasks_received), 1)
        
        received_task = self.agent2.tasks_received[0]
        self.assertEqual(received_task["to_agent_id"], self.agent2.agent_id)
        self.assertEqual(received_task["from_agent_id"], self.agent1.agent_id)
        self.assertEqual(received_task["task_type"], "validate_data")
        self.assertEqual(received_task["parameters"]["data"], "test_data")
        
        # Save test results
        self.utils.save_test_results(
            {
                "task_created": {
                    "to_agent_id": self.agent2.agent_id,
                    "task_type": "validate_data",
                    "parameters": {"data": "test_data"},
                    "from_agent_id": self.agent1.agent_id
                },
                "task_received": received_task
            },
            "task_creation",
            self.test_dir
        )
    
    def test_task_status_tracking(self):
        """Test tracking task status through the MCP."""
        # Register agents
        self.agent1.register_with_mcp(self.mcp)
        self.agent2.register_with_mcp(self.mcp)
        
        # Create a task for agent2
        task_result = self.mcp.create_task(
            to_agent_id=self.agent2.agent_id,
            task_type="validate_data",
            parameters={"data": "test_data"},
            from_agent_id=self.agent1.agent_id
        )
        
        task_id = task_result["task_id"]
        
        # Wait for task to be processed
        time.sleep(0.1)
        
        # Check initial task status
        task_status = self.mcp.get_task_status(task_id)
        self.assertEqual(task_status["status"], "processing")
        
        # Update task status (simulating agent2 completing the task)
        self.mcp.update_task_status(
            task_id=task_id,
            status="completed",
            result={"validation_result": "data is valid"}
        )
        
        # Check updated task status
        task_status = self.mcp.get_task_status(task_id)
        self.assertEqual(task_status["status"], "completed")
        self.assertEqual(task_status["result"]["validation_result"], "data is valid")
        
        # Save test results
        self.utils.save_test_results(
            {
                "task_id": task_id,
                "initial_status": "processing",
                "final_status": task_status
            },
            "task_status_tracking",
            self.test_dir
        )
    
    def test_broadcast_message(self):
        """Test broadcasting messages to all agents."""
        # Register agents
        self.agent1.register_with_mcp(self.mcp)
        self.agent2.register_with_mcp(self.mcp)
        self.agent3.register_with_mcp(self.mcp)
        
        # Broadcast a message
        broadcast_result = self.mcp.broadcast_message(
            from_agent_id="mcp",
            message_type=MessageType.SYSTEM_NOTIFICATION,
            content={"notification": "system update"}
        )
        
        # Check that broadcast was sent
        self.assertIn("message_ids", broadcast_result)
        self.assertEqual(len(broadcast_result["message_ids"]), 3)  # One for each agent
        
        # Wait for messages to be processed
        time.sleep(0.1)
        
        # Check that all agents received the message
        self.assertEqual(len(self.agent1.messages_received), 1)
        self.assertEqual(len(self.agent2.messages_received), 1)
        self.assertEqual(len(self.agent3.messages_received), 1)
        
        # Check message content for each agent
        for agent in [self.agent1, self.agent2, self.agent3]:
            message = agent.messages_received[0]
            self.assertEqual(message["from_agent_id"], "mcp")
            self.assertEqual(message["message_type"], MessageType.SYSTEM_NOTIFICATION.name)
            self.assertEqual(message["content"]["notification"], "system update")
        
        # Save test results
        self.utils.save_test_results(
            {
                "broadcast_message": {
                    "from_agent_id": "mcp",
                    "message_type": MessageType.SYSTEM_NOTIFICATION.name,
                    "content": {"notification": "system update"}
                },
                "received_by_agents": [self.agent1.agent_id, self.agent2.agent_id, self.agent3.agent_id]
            },
            "broadcast_message",
            self.test_dir
        )
    
    def test_system_status(self):
        """Test getting system status from the MCP."""
        # Register agents
        self.agent1.register_with_mcp(self.mcp)
        self.agent2.register_with_mcp(self.mcp)
        
        # Send some messages and create some tasks
        self.mcp.send_message(
            from_agent_id=self.agent1.agent_id,
            to_agent_id=self.agent2.agent_id,
            message_type=MessageType.DATA_UPDATE,
            content={"data": "test_data"}
        )
        
        self.mcp.create_task(
            to_agent_id=self.agent2.agent_id,
            task_type="validate_data",
            parameters={"data": "test_data"},
            from_agent_id=self.agent1.agent_id
        )
        
        # Wait for processing
        time.sleep(0.1)
        
        # Get system status
        status = self.mcp.get_system_status()
        
        # Check status structure
        self.assertIn("agents", status)
        self.assertIn("messages", status)
        self.assertIn("tasks", status)
        self.assertIn("uptime", status)
        
        # Check agent count
        self.assertEqual(status["agents"]["count"], 2)
        
        # Check message count (at least 1)
        self.assertGreaterEqual(status["messages"]["total_sent"], 1)
        
        # Check task count (at least 1)
        self.assertGreaterEqual(status["tasks"]["total_created"], 1)
        
        # Save test results
        self.utils.save_test_results(
            {
                "system_status": status
            },
            "system_status",
            self.test_dir
        )
    
    def test_agent_deregistration(self):
        """Test agent deregistration from the MCP."""
        # Register agents
        self.agent1.register_with_mcp(self.mcp)
        self.agent2.register_with_mcp(self.mcp)
        
        # Check initial agent count
        self.assertEqual(len(self.mcp.list_agents()), 2)
        
        # Deregister agent1
        deregister_result = self.mcp.deregister_agent(self.agent1.agent_id)
        
        # Check deregistration result
        self.assertTrue(deregister_result["success"])
        
        # Check updated agent count
        self.assertEqual(len(self.mcp.list_agents()), 1)
        
        # Verify remaining agent is agent2
        remaining_agent = self.mcp.list_agents()[0]
        self.assertEqual(remaining_agent["agent_id"], self.agent2.agent_id)
        
        # Try to send a message to the deregistered agent
        message_result = self.mcp.send_message(
            from_agent_id=self.agent2.agent_id,
            to_agent_id=self.agent1.agent_id,
            message_type=MessageType.DATA_UPDATE,
            content={"data": "test_data"}
        )
        
        # Check that message sending failed
        self.assertEqual(message_result["status"], "error")
        
        # Save test results
        self.utils.save_test_results(
            {
                "deregistered_agent": self.agent1.agent_id,
                "deregistration_result": deregister_result,
                "remaining_agents": [a["agent_id"] for a in self.mcp.list_agents()],
                "message_to_deregistered_agent": message_result
            },
            "agent_deregistration",
            self.test_dir
        )
    
    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests."""
        # Generate test report
        test_results = []
        # In a real implementation, we would collect all test results here
        
        # For demonstration purposes, create a simple report
        report = {
            "test_class": "TestMCP",
            "test_count": len([m for m in dir(cls) if m.startswith('test_')]),
            "test_dir": cls.test_dir,
            "timestamp": os.path.basename(cls.test_dir).split('_')[-1]
        }
        
        # Save report
        report_path = os.path.join(cls.test_dir, "test_report.json")
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        cls.logger.info(f"Test report saved to {report_path}")


if __name__ == '__main__':
    unittest.main()