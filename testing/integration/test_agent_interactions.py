"""
Integration Tests for Agent Interactions

This module tests the interactions between the Master Control Program (MCP)
and various agent types, ensuring proper communication and coordination.
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
from mcp.agents.data_quality_agent import DataQualityAgent
from mcp.agents.compliance_agent import ComplianceAgent
from data_quality.validator import DataValidator
from testing.test_config import TestConfig
from testing.test_utils import TestUtils
from agent_coordination.coordinator import AgentCoordinator


class TestAgentInteractions(unittest.TestCase):
    """Integration tests for interactions between agents."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment once before all tests."""
        # Initialize test configuration
        cls.config = TestConfig()
        
        # Initialize test utilities
        cls.utils = TestUtils(cls.config)
        
        # Prepare test directory
        cls.test_dir = cls.utils.prepare_test_directory("agent_interactions_tests")
        
        # Set up logging
        cls.logger = logging.getLogger("test_agent_interactions")
        
        # Start the MCP
        cls.logger.info("Starting MCP for integration tests")
        cls.mcp = MasterControlProgram()
        cls.mcp.start()
        
        # Create the agent coordinator
        cls.coordinator = AgentCoordinator(cls.mcp)
        cls.coordinator.start()
        
        # Load authentic test data
        cls.test_properties = cls.utils.extract_authentic_property_data(count=5)
    
    def setUp(self):
        """Set up before each test."""
        # Create fresh agents for each test
        self.data_quality_agent = DataQualityAgent(
            name="Test Data Quality Agent",
            description="Data quality agent for testing"
        )
        
        self.compliance_agent = ComplianceAgent(
            name="Test Compliance Agent",
            description="Compliance agent for testing"
        )
        
        # Register agents with MCP
        self.data_quality_agent.register_with_mcp(self.mcp)
        self.compliance_agent.register_with_mcp(self.mcp)
        
        # Register agent capabilities with coordinator
        self.coordinator.register_agent_capabilities(
            self.data_quality_agent.agent_id,
            ["validate_data", "detect_anomalies", "enhance_data"]
        )
        
        self.coordinator.register_agent_capabilities(
            self.compliance_agent.agent_id,
            ["check_compliance", "verify_exemption", "create_audit_record"]
        )
        
        # Wait for agents to initialize
        time.sleep(0.2)
    
    def test_data_quality_task_execution(self):
        """Test data quality task execution through MCP."""
        if not self.test_properties:
            self.skipTest("No authentic property data available for testing")
            return
        
        # Get a test property
        test_property = self.test_properties[0]
        
        # Create a validation task
        task_result = self.mcp.create_task(
            to_agent_id=self.data_quality_agent.agent_id,
            task_type="validate_entity",
            parameters={
                "entity_type": "property",
                "data": test_property
            },
            from_agent_id="test_integration"
        )
        
        # Check task creation
        self.assertIn("task_id", task_result)
        task_id = task_result["task_id"]
        
        # Wait for task to complete
        max_wait = 10  # seconds
        start_time = time.time()
        task_status = None
        
        while time.time() - start_time < max_wait:
            task_status = self.mcp.get_task_status(task_id)
            if task_status.get("status") == "completed":
                break
            time.sleep(0.2)
        
        # Check that task completed
        self.assertIsNotNone(task_status)
        self.assertEqual(task_status.get("status"), "completed")
        
        # Check task result
        result = task_status.get("result", {})
        self.assertIn("valid", result)
        self.assertIn("errors", result)
        self.assertIn("warnings", result)
        
        # Save test results
        self.utils.save_test_results(
            {
                "task_id": task_id,
                "task_type": "validate_entity",
                "property_data": test_property,
                "validation_result": result
            },
            "data_quality_task",
            self.test_dir
        )
    
    def test_compliance_task_execution(self):
        """Test compliance task execution through MCP."""
        # Create a tax data sample
        tax_data = {
            "city": "Richland",
            "assessed_value": 350000,
            "tax_amount": 3800,
            "tax_year": 2024
        }
        
        # Create a compliance check task
        task_result = self.mcp.create_task(
            to_agent_id=self.compliance_agent.agent_id,
            task_type="check_compliance",
            parameters={
                "compliance_type": "tax_calculation",
                "data": tax_data
            },
            from_agent_id="test_integration"
        )
        
        # Check task creation
        self.assertIn("task_id", task_result)
        task_id = task_result["task_id"]
        
        # Wait for task to complete
        max_wait = 10  # seconds
        start_time = time.time()
        task_status = None
        
        while time.time() - start_time < max_wait:
            task_status = self.mcp.get_task_status(task_id)
            if task_status.get("status") == "completed":
                break
            time.sleep(0.2)
        
        # Check that task completed
        self.assertIsNotNone(task_status)
        self.assertEqual(task_status.get("status"), "completed")
        
        # Check task result
        result = task_status.get("result", {})
        self.assertIn("compliant", result)
        self.assertIn("issues", result)
        
        # Save test results
        self.utils.save_test_results(
            {
                "task_id": task_id,
                "task_type": "check_compliance",
                "tax_data": tax_data,
                "compliance_result": result
            },
            "compliance_task",
            self.test_dir
        )
    
    def test_agent_coordination(self):
        """Test agent coordination through the coordinator."""
        if not self.test_properties:
            self.skipTest("No authentic property data available for testing")
            return
        
        # Get a test property
        test_property = self.test_properties[0]
        
        # Record agent performance metrics
        self.coordinator.performance_tracker.record_metric(
            self.data_quality_agent.agent_id,
            "success_rate",
            0.95
        )
        
        self.coordinator.performance_tracker.record_metric(
            self.compliance_agent.agent_id,
            "success_rate",
            0.90
        )
        
        # Request validation through coordinator
        validation_message_id = self.coordinator.send_message(
            from_agent_id="test_integration",
            to_agent_id=self.data_quality_agent.agent_id,
            message_type=MessageType.VALIDATION_REQUEST,
            payload={
                "entity_type": "property",
                "data": test_property
            }
        )
        
        # Wait for processing
        time.sleep(0.5)
        
        # Request compliance check through coordinator
        compliance_message_id = self.coordinator.send_message(
            from_agent_id="test_integration",
            to_agent_id=self.compliance_agent.agent_id,
            message_type=MessageType.COMPLIANCE_REQUEST,
            payload={
                "compliance_type": "property_classification",
                "data": test_property
            }
        )
        
        # Wait for processing
        time.sleep(0.5)
        
        # Get system status
        coordinator_status = self.coordinator.get_system_status()
        
        # Save test results
        self.utils.save_test_results(
            {
                "validation_message_id": validation_message_id,
                "compliance_message_id": compliance_message_id,
                "coordinator_status": coordinator_status,
                "performance_metrics": {
                    "data_quality_agent": self.coordinator.get_agent_performance(
                        self.data_quality_agent.agent_id
                    ),
                    "compliance_agent": self.coordinator.get_agent_performance(
                        self.compliance_agent.agent_id
                    )
                }
            },
            "agent_coordination",
            self.test_dir
        )
    
    def test_inter_agent_communication(self):
        """Test communication between agents."""
        if not self.test_properties:
            self.skipTest("No authentic property data available for testing")
            return
        
        # Get a test property
        test_property = self.test_properties[0]
        
        # Data Quality Agent validates property first
        validate_task_result = self.mcp.create_task(
            to_agent_id=self.data_quality_agent.agent_id,
            task_type="validate_entity",
            parameters={
                "entity_type": "property",
                "data": test_property
            },
            from_agent_id="test_integration"
        )
        
        validate_task_id = validate_task_result["task_id"]
        
        # Wait for validation to complete
        max_wait = 10  # seconds
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            task_status = self.mcp.get_task_status(validate_task_id)
            if task_status.get("status") == "completed":
                break
            time.sleep(0.2)
        
        # Get validation result
        validation_result = self.mcp.get_task_status(validate_task_id).get("result", {})
        
        # Now have Data Quality Agent send the result to Compliance Agent
        message_result = self.mcp.send_message(
            from_agent_id=self.data_quality_agent.agent_id,
            to_agent_id=self.compliance_agent.agent_id,
            message_type=MessageType.DATA_UPDATE,
            content={
                "property_data": test_property,
                "validation_result": validation_result
            }
        )
        
        message_id = message_result["message_id"]
        
        # Wait for message processing
        time.sleep(0.5)
        
        # Now Compliance Agent checks compliance based on validated data
        compliance_task_result = self.mcp.create_task(
            to_agent_id=self.compliance_agent.agent_id,
            task_type="check_compliance",
            parameters={
                "compliance_type": "property_classification",
                "data": test_property,
                "validation_result": validation_result
            },
            from_agent_id=self.data_quality_agent.agent_id
        )
        
        compliance_task_id = compliance_task_result["task_id"]
        
        # Wait for compliance check to complete
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            task_status = self.mcp.get_task_status(compliance_task_id)
            if task_status.get("status") == "completed":
                break
            time.sleep(0.2)
        
        # Get compliance result
        compliance_result = self.mcp.get_task_status(compliance_task_id).get("result", {})
        
        # Save test results
        self.utils.save_test_results(
            {
                "property_data": test_property,
                "validation": {
                    "task_id": validate_task_id,
                    "result": validation_result
                },
                "inter_agent_message": {
                    "message_id": message_id,
                    "from_agent_id": self.data_quality_agent.agent_id,
                    "to_agent_id": self.compliance_agent.agent_id
                },
                "compliance": {
                    "task_id": compliance_task_id,
                    "result": compliance_result
                }
            },
            "inter_agent_communication",
            self.test_dir
        )
    
    def test_experience_sharing(self):
        """Test experience sharing through the replay buffer."""
        # Record experiences in the replay buffer
        for i in range(5):
            self.coordinator.record_experience(
                agent_id=self.data_quality_agent.agent_id,
                state={"data_quality": i},
                action={"action_type": "validate", "id": f"action_{i}"},
                reward=0.8 + (i * 0.04),  # Increasing rewards
                next_state={"data_quality": i + 1},
                done=(i == 4)  # Last one is done
            )
        
        for i in range(3):
            self.coordinator.record_experience(
                agent_id=self.compliance_agent.agent_id,
                state={"compliance": i},
                action={"action_type": "check", "id": f"action_{i}"},
                reward=0.7 + (i * 0.05),  # Increasing rewards
                next_state={"compliance": i + 1},
                done=(i == 2)  # Last one is done
            )
        
        # Sample from the replay buffer
        experiences, indices, weights = self.coordinator.replay_buffer.sample(batch_size=4)
        
        # Check that we got experiences
        self.assertEqual(len(experiences), 4)
        self.assertEqual(len(indices), 4)
        self.assertEqual(len(weights), 4)
        
        # Update priorities
        self.coordinator.replay_buffer.update_priorities(
            indices=indices,
            priorities=[1.2, 1.0, 1.5, 0.8]  # Example priorities
        )
        
        # Get replay buffer stats
        buffer_stats = self.coordinator.replay_buffer.get_stats()
        
        # Save test results
        self.utils.save_test_results(
            {
                "experiences_added": 8,
                "experiences_sampled": len(experiences),
                "sampled_experience_example": experiences[0].to_dict() if experiences else None,
                "buffer_stats": buffer_stats
            },
            "experience_sharing",
            self.test_dir
        )
    
    def tearDown(self):
        """Clean up after each test."""
        # Deregister agents
        self.mcp.deregister_agent(self.data_quality_agent.agent_id)
        self.mcp.deregister_agent(self.compliance_agent.agent_id)
    
    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests."""
        # Stop the coordinator
        cls.coordinator.stop()
        
        # Stop the MCP
        cls.mcp.stop()
        
        # Generate test report
        test_results = []
        # In a real implementation, we would collect all test results here
        
        # For demonstration purposes, create a simple report
        report = {
            "test_class": "TestAgentInteractions",
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