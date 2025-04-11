"""
Performance Tests for Master Control Program (MCP)

This module tests the performance characteristics of the MCP,
particularly under high message and task volumes.
"""

import unittest
import logging
import os
import json
import sys
import time
import concurrent.futures
from typing import Dict, Any, List, Optional
import statistics

# Add parent directory to path to facilitate imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from mcp.master_control import MasterControlProgram
from mcp.message import MessageType, MessagePriority
from mcp.task import TaskPriority
from testing.test_config import TestConfig
from testing.test_utils import TestUtils


class MockPerformanceAgent:
    """Mock agent for performance testing."""
    
    def __init__(self, agent_id, agent_type="performance"):
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
        # Simulate processing time
        time.sleep(0.001)
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


class TestMCPPerformance(unittest.TestCase):
    """Performance tests for the Master Control Program (MCP)."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment once before all tests."""
        # Initialize test configuration
        cls.config = TestConfig()
        
        # Initialize test utilities
        cls.utils = TestUtils(cls.config)
        
        # Prepare test directory
        cls.test_dir = cls.utils.prepare_test_directory("mcp_performance_tests")
        
        # Set up logging
        cls.logger = logging.getLogger("test_mcp_performance")
        
        # Start the MCP
        cls.logger.info("Starting MCP for performance tests")
        cls.mcp = MasterControlProgram()
        cls.mcp.start()
        
        # Create and register sender agents
        cls.sender_agents = [
            MockPerformanceAgent(f"sender_{i}", "sender")
            for i in range(10)
        ]
        
        # Create and register receiver agents
        cls.receiver_agents = [
            MockPerformanceAgent(f"receiver_{i}", "receiver")
            for i in range(10)
        ]
        
        # Register all agents
        for agent in cls.sender_agents + cls.receiver_agents:
            agent.register_with_mcp(cls.mcp)
        
        # Wait for agents to register
        time.sleep(0.5)
    
    def test_message_throughput(self):
        """Test message throughput performance."""
        # Number of messages to send
        num_messages = 1000
        
        # Clear previous messages
        for agent in self.receiver_agents:
            agent.messages_received = []
        
        # Start timer
        start_time = time.time()
        
        # Send messages in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            
            for i in range(num_messages):
                sender_agent = self.sender_agents[i % len(self.sender_agents)]
                receiver_agent = self.receiver_agents[i % len(self.receiver_agents)]
                
                future = executor.submit(
                    self.mcp.send_message,
                    from_agent_id=sender_agent.agent_id,
                    to_agent_id=receiver_agent.agent_id,
                    message_type=MessageType.DATA_UPDATE,
                    content={"data": f"message_{i}"}
                )
                
                futures.append(future)
            
            # Wait for all messages to be sent
            results = [future.result() for future in futures]
        
        # End timer for message sending
        send_end_time = time.time()
        send_duration = send_end_time - start_time
        
        # Wait for messages to be processed
        time.sleep(2)
        
        # End timer for total processing
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Count received messages
        total_received = sum(len(agent.messages_received) for agent in self.receiver_agents)
        
        # Calculate throughput
        send_throughput = num_messages / send_duration if send_duration > 0 else 0
        total_throughput = total_received / total_duration if total_duration > 0 else 0
        
        # Calculate success rate
        success_rate = (total_received / num_messages) * 100 if num_messages > 0 else 0
        
        # Log results
        self.logger.info(f"Message throughput test results:")
        self.logger.info(f"  Messages sent: {num_messages}")
        self.logger.info(f"  Messages received: {total_received}")
        self.logger.info(f"  Send duration: {send_duration:.4f} seconds")
        self.logger.info(f"  Total duration: {total_duration:.4f} seconds")
        self.logger.info(f"  Send throughput: {send_throughput:.2f} messages/second")
        self.logger.info(f"  Total throughput: {total_throughput:.2f} messages/second")
        self.logger.info(f"  Success rate: {success_rate:.2f}%")
        
        # Save test results
        self.utils.save_test_results(
            {
                "test_type": "message_throughput",
                "messages_sent": num_messages,
                "messages_received": total_received,
                "send_duration": send_duration,
                "total_duration": total_duration,
                "send_throughput": send_throughput,
                "total_throughput": total_throughput,
                "success_rate": success_rate
            },
            "message_throughput",
            self.test_dir
        )
        
        # Assert success criteria
        self.assertGreaterEqual(success_rate, 90.0)  # At least 90% success rate
        self.assertGreaterEqual(send_throughput, 100.0)  # At least 100 messages/second
    
    def test_task_throughput(self):
        """Test task throughput performance."""
        # Number of tasks to create
        num_tasks = 500
        
        # Clear previous tasks
        for agent in self.receiver_agents:
            agent.tasks_received = []
        
        # Tasks to track
        task_ids = []
        
        # Start timer
        start_time = time.time()
        
        # Create tasks in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            
            for i in range(num_tasks):
                sender_agent = self.sender_agents[i % len(self.sender_agents)]
                receiver_agent = self.receiver_agents[i % len(self.receiver_agents)]
                
                future = executor.submit(
                    self.mcp.create_task,
                    to_agent_id=receiver_agent.agent_id,
                    task_type="performance_test",
                    parameters={"data": f"task_{i}"},
                    from_agent_id=sender_agent.agent_id
                )
                
                futures.append(future)
            
            # Wait for all tasks to be created
            results = [future.result() for future in futures]
            
            # Collect task IDs
            task_ids = [result["task_id"] for result in results if "task_id" in result]
        
        # End timer for task creation
        create_end_time = time.time()
        create_duration = create_end_time - start_time
        
        # Wait for tasks to be processed
        time.sleep(2)
        
        # End timer for total processing
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Count received tasks
        total_received = sum(len(agent.tasks_received) for agent in self.receiver_agents)
        
        # Calculate throughput
        create_throughput = num_tasks / create_duration if create_duration > 0 else 0
        total_throughput = total_received / total_duration if total_duration > 0 else 0
        
        # Calculate success rate
        success_rate = (total_received / num_tasks) * 100 if num_tasks > 0 else 0
        
        # Check task statuses
        task_statuses = []
        for task_id in task_ids[:100]:  # Check a sample of tasks
            status = self.mcp.get_task_status(task_id)
            task_statuses.append(status.get("status"))
        
        # Log results
        self.logger.info(f"Task throughput test results:")
        self.logger.info(f"  Tasks created: {num_tasks}")
        self.logger.info(f"  Tasks received: {total_received}")
        self.logger.info(f"  Create duration: {create_duration:.4f} seconds")
        self.logger.info(f"  Total duration: {total_duration:.4f} seconds")
        self.logger.info(f"  Create throughput: {create_throughput:.2f} tasks/second")
        self.logger.info(f"  Total throughput: {total_throughput:.2f} tasks/second")
        self.logger.info(f"  Success rate: {success_rate:.2f}%")
        
        # Save test results
        self.utils.save_test_results(
            {
                "test_type": "task_throughput",
                "tasks_created": num_tasks,
                "tasks_received": total_received,
                "create_duration": create_duration,
                "total_duration": total_duration,
                "create_throughput": create_throughput,
                "total_throughput": total_throughput,
                "success_rate": success_rate,
                "task_status_sample": task_statuses
            },
            "task_throughput",
            self.test_dir
        )
        
        # Assert success criteria
        self.assertGreaterEqual(success_rate, 90.0)  # At least 90% success rate
        self.assertGreaterEqual(create_throughput, 50.0)  # At least 50 tasks/second
    
    def test_message_latency(self):
        """Test message delivery latency."""
        # Number of messages to send
        num_messages = 100
        
        # Clear previous messages
        for agent in self.receiver_agents:
            agent.messages_received = []
        
        # Message timestamps for latency measurement
        send_times = {}
        
        # Send messages and record timestamp
        for i in range(num_messages):
            sender_agent = self.sender_agents[i % len(self.sender_agents)]
            receiver_agent = self.receiver_agents[i % len(self.receiver_agents)]
            
            start_time = time.time()
            
            result = self.mcp.send_message(
                from_agent_id=sender_agent.agent_id,
                to_agent_id=receiver_agent.agent_id,
                message_type=MessageType.DATA_UPDATE,
                content={"data": f"latency_message_{i}", "timestamp": start_time}
            )
            
            send_times[result["message_id"]] = start_time
        
        # Wait for messages to be processed
        time.sleep(1)
        
        # Calculate latencies
        latencies = []
        
        for agent in self.receiver_agents:
            for message in agent.messages_received:
                message_id = message.get("message_id")
                if message_id in send_times:
                    send_time = send_times[message_id]
                    receive_time = message.get("content", {}).get("timestamp")
                    
                    if receive_time:
                        latency = (receive_time - send_time) * 1000  # Convert to ms
                        latencies.append(latency)
        
        if latencies:
            # Calculate statistics
            avg_latency = statistics.mean(latencies)
            min_latency = min(latencies)
            max_latency = max(latencies)
            p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
            p99_latency = sorted(latencies)[int(len(latencies) * 0.99)]
            
            # Log results
            self.logger.info(f"Message latency test results:")
            self.logger.info(f"  Messages sent: {num_messages}")
            self.logger.info(f"  Latencies measured: {len(latencies)}")
            self.logger.info(f"  Average latency: {avg_latency:.2f} ms")
            self.logger.info(f"  Min latency: {min_latency:.2f} ms")
            self.logger.info(f"  Max latency: {max_latency:.2f} ms")
            self.logger.info(f"  P95 latency: {p95_latency:.2f} ms")
            self.logger.info(f"  P99 latency: {p99_latency:.2f} ms")
            
            # Save test results
            self.utils.save_test_results(
                {
                    "test_type": "message_latency",
                    "messages_sent": num_messages,
                    "latencies_measured": len(latencies),
                    "average_latency_ms": avg_latency,
                    "min_latency_ms": min_latency,
                    "max_latency_ms": max_latency,
                    "p95_latency_ms": p95_latency,
                    "p99_latency_ms": p99_latency
                },
                "message_latency",
                self.test_dir
            )
            
            # Assert latency requirements
            self.assertLess(avg_latency, 50.0)  # Average latency less than 50ms
            self.assertLess(p95_latency, 100.0)  # 95% of messages under 100ms
        else:
            self.logger.warning("No latency measurements collected")
            self.fail("No latency measurements collected")
    
    def test_concurrent_load(self):
        """Test MCP performance under concurrent load."""
        # Number of operations to perform
        num_operations = 1000
        
        # Operation mix (70% messages, 30% tasks)
        num_messages = int(num_operations * 0.7)
        num_tasks = num_operations - num_messages
        
        # Clear previous messages and tasks
        for agent in self.receiver_agents:
            agent.messages_received = []
            agent.tasks_received = []
        
        # Start timer
        start_time = time.time()
        
        # Perform operations in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = []
            
            # Submit message operations
            for i in range(num_messages):
                sender_agent = self.sender_agents[i % len(self.sender_agents)]
                receiver_agent = self.receiver_agents[i % len(self.receiver_agents)]
                
                future = executor.submit(
                    self.mcp.send_message,
                    from_agent_id=sender_agent.agent_id,
                    to_agent_id=receiver_agent.agent_id,
                    message_type=MessageType.DATA_UPDATE,
                    content={"data": f"concurrent_message_{i}"}
                )
                
                futures.append(future)
            
            # Submit task operations
            for i in range(num_tasks):
                sender_agent = self.sender_agents[i % len(self.sender_agents)]
                receiver_agent = self.receiver_agents[i % len(self.receiver_agents)]
                
                future = executor.submit(
                    self.mcp.create_task,
                    to_agent_id=receiver_agent.agent_id,
                    task_type="concurrent_test",
                    parameters={"data": f"concurrent_task_{i}"},
                    from_agent_id=sender_agent.agent_id
                )
                
                futures.append(future)
            
            # Wait for all operations to complete
            results = [future.result() for future in futures]
        
        # End timer for operation submission
        submit_end_time = time.time()
        submit_duration = submit_end_time - start_time
        
        # Wait for operations to be processed
        time.sleep(2)
        
        # End timer for total processing
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Count received messages and tasks
        total_messages_received = sum(len(agent.messages_received) for agent in self.receiver_agents)
        total_tasks_received = sum(len(agent.tasks_received) for agent in self.receiver_agents)
        
        # Calculate throughput
        operation_throughput = num_operations / submit_duration if submit_duration > 0 else 0
        
        # Calculate success rates
        message_success_rate = (total_messages_received / num_messages) * 100 if num_messages > 0 else 0
        task_success_rate = (total_tasks_received / num_tasks) * 100 if num_tasks > 0 else 0
        
        # Get system status
        system_status = self.mcp.get_system_status()
        
        # Log results
        self.logger.info(f"Concurrent load test results:")
        self.logger.info(f"  Total operations: {num_operations}")
        self.logger.info(f"  Messages sent: {num_messages}")
        self.logger.info(f"  Tasks created: {num_tasks}")
        self.logger.info(f"  Messages received: {total_messages_received}")
        self.logger.info(f"  Tasks received: {total_tasks_received}")
        self.logger.info(f"  Submit duration: {submit_duration:.4f} seconds")
        self.logger.info(f"  Total duration: {total_duration:.4f} seconds")
        self.logger.info(f"  Operation throughput: {operation_throughput:.2f} ops/second")
        self.logger.info(f"  Message success rate: {message_success_rate:.2f}%")
        self.logger.info(f"  Task success rate: {task_success_rate:.2f}%")
        
        # Save test results
        self.utils.save_test_results(
            {
                "test_type": "concurrent_load",
                "total_operations": num_operations,
                "messages_sent": num_messages,
                "tasks_created": num_tasks,
                "messages_received": total_messages_received,
                "tasks_received": total_tasks_received,
                "submit_duration": submit_duration,
                "total_duration": total_duration,
                "operation_throughput": operation_throughput,
                "message_success_rate": message_success_rate,
                "task_success_rate": task_success_rate,
                "system_status": system_status
            },
            "concurrent_load",
            self.test_dir
        )
        
        # Assert success criteria
        self.assertGreaterEqual(message_success_rate, 90.0)  # At least 90% message success
        self.assertGreaterEqual(task_success_rate, 90.0)  # At least 90% task success
        self.assertGreaterEqual(operation_throughput, 100.0)  # At least 100 ops/second
    
    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests."""
        # Deregister all agents
        for agent in cls.sender_agents + cls.receiver_agents:
            cls.mcp.deregister_agent(agent.agent_id)
        
        # Stop the MCP
        cls.mcp.stop()
        
        # Generate performance report
        test_results = []
        # In a real implementation, we would collect all test results here
        
        # For demonstration purposes, create a simple report
        report = {
            "test_class": "TestMCPPerformance",
            "test_count": len([m for m in dir(cls) if m.startswith('test_')]),
            "test_dir": cls.test_dir,
            "timestamp": os.path.basename(cls.test_dir).split('_')[-1]
        }
        
        # Save report
        report_path = os.path.join(cls.test_dir, "performance_report.json")
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        cls.logger.info(f"Performance report saved to {report_path}")


if __name__ == '__main__':
    unittest.main()