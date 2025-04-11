"""
Master Control Program for Benton County Assessor's Office

This module implements the central orchestration system for the AI agent framework,
managing agent registration, communication, task assignment, and system monitoring.
"""

import logging
import os
import json
import time
import threading
import queue
from datetime import datetime
from typing import Dict, List, Any, Optional, Set, Callable, Tuple, Union
from collections import defaultdict

from .agent import Agent, AgentStatus, AgentType
from .message import Message, MessageType, MessagePriority
from .task import Task, TaskStatus, TaskPriority

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MasterControlProgram:
    """
    Master Control Program (MCP) for the Benton County Assessor's Office AI platform.
    
    The MCP serves as the central orchestration system for the multi-agent AI framework,
    coordinating agent interactions, managing system-wide state, routing messages,
    and allocating tasks to specialized agents based on their capabilities.
    """
    
    def __init__(self, storage_dir: Optional[str] = None):
        """
        Initialize the Master Control Program.
        
        Args:
            storage_dir: Directory to store MCP state (defaults to 'mcp_data')
        """
        # Storage configuration
        self.storage_dir = storage_dir or os.path.join(os.getcwd(), 'mcp_data')
        os.makedirs(self.storage_dir, exist_ok=True)
        
        # System state
        self.started_at = datetime.utcnow()
        self.is_running = False
        self.status = "initializing"
        
        # Agent registry
        self.agents = {}  # agent_id -> Agent object
        self.agent_registry = {}  # agent_id -> agent registration info
        self.agent_status = {}  # agent_id -> AgentStatus
        self.agent_types = defaultdict(set)  # agent_type -> set of agent_ids
        self.capabilities = defaultdict(set)  # capability -> set of agent_ids
        
        # Message management
        self.message_log = []  # List of all messages
        self.pending_messages = {}  # message_id -> Message object
        self.undelivered_messages = defaultdict(list)  # to_agent_id -> list of Message objects
        self.message_count = 0
        
        # Task management
        self.tasks = {}  # task_id -> Task object
        self.pending_tasks = defaultdict(list)  # to_agent_id -> list of Task objects
        self.completed_tasks = []  # List of completed/failed task IDs
        self.task_count = 0
        
        # Monitoring and statistics
        self.agent_metrics = defaultdict(lambda: defaultdict(int))  # agent_id -> metric -> value
        self.system_metrics = defaultdict(int)  # metric -> value
        self.heartbeat_status = {}  # agent_id -> last heartbeat time
        
        # Processing queues and threads
        self.message_queue = queue.PriorityQueue()
        self.task_queue = queue.PriorityQueue()
        self.main_thread = None
        self.threads = []
        self.stop_event = threading.Event()
        
        logger.info("Master Control Program initialized")
    
    def start(self):
        """Start the MCP system and its processing threads."""
        if self.is_running:
            logger.warning("MCP is already running")
            return
        
        self.is_running = True
        self.status = "running"
        
        # Start processing threads
        self.stop_event.clear()
        
        # Message processing thread
        message_thread = threading.Thread(
            target=self._process_message_queue,
            name="MCP-MessageProcessor"
        )
        message_thread.daemon = True
        self.threads.append(message_thread)
        message_thread.start()
        
        # Task processing thread
        task_thread = threading.Thread(
            target=self._process_task_queue,
            name="MCP-TaskProcessor"
        )
        task_thread.daemon = True
        self.threads.append(task_thread)
        task_thread.start()
        
        # Heartbeat monitoring thread
        heartbeat_thread = threading.Thread(
            target=self._monitor_heartbeats,
            name="MCP-HeartbeatMonitor"
        )
        heartbeat_thread.daemon = True
        self.threads.append(heartbeat_thread)
        heartbeat_thread.start()
        
        logger.info("Master Control Program started")
    
    def stop(self):
        """Stop the MCP system and its processing threads."""
        if not self.is_running:
            logger.warning("MCP is not running")
            return
        
        logger.info("Stopping Master Control Program...")
        
        # Signal all threads to stop
        self.stop_event.set()
        
        # Wait for all threads to finish
        for thread in self.threads:
            thread.join(timeout=5.0)
            if thread.is_alive():
                logger.warning(f"Thread {thread.name} did not terminate cleanly")
        
        self.threads = []
        self.is_running = False
        self.status = "stopped"
        
        logger.info("Master Control Program stopped")
    
    def register_agent(self, agent: Agent) -> bool:
        """
        Register an agent with the MCP.
        
        Args:
            agent: The agent to register
            
        Returns:
            bool: Whether registration was successful
        """
        agent_id = agent.agent_id
        
        if agent_id in self.agents:
            logger.warning(f"Agent {agent_id} is already registered")
            return False
        
        # Add agent to registry
        self.agents[agent_id] = agent
        self.agent_status[agent_id] = agent.status
        self.agent_types[agent.agent_type.value].add(agent_id)
        
        # Register agent capabilities
        for capability in agent.capabilities:
            self.capabilities[capability.value].add(agent_id)
        
        # Store agent registration info
        self.agent_registry[agent_id] = {
            "agent_id": agent_id,
            "name": agent.name,
            "type": agent.agent_type.value,
            "capabilities": [capability.value for capability in agent.capabilities],
            "status": agent.status.value,
            "registered_at": datetime.utcnow().isoformat()
        }
        
        # Initialize agent metrics
        self.agent_metrics[agent_id]["tasks_processed"] = 0
        self.agent_metrics[agent_id]["messages_processed"] = 0
        self.agent_metrics[agent_id]["errors"] = 0
        
        # Record last heartbeat time
        self.heartbeat_status[agent_id] = datetime.utcnow()
        
        # Update system metrics
        self.system_metrics["total_agents"] += 1
        self.system_metrics[f"agents_{agent.agent_type.value}"] += 1
        
        logger.info(f"Agent {agent.name} ({agent_id}) registered with MCP")
        
        # Deliver any pending messages for this agent
        if agent_id in self.undelivered_messages:
            for message in self.undelivered_messages[agent_id]:
                self._deliver_message(message)
            self.undelivered_messages[agent_id] = []
        
        return True
    
    def unregister_agent(self, agent_id: str) -> bool:
        """
        Unregister an agent from the MCP.
        
        Args:
            agent_id: ID of the agent to unregister
            
        Returns:
            bool: Whether unregistration was successful
        """
        if agent_id not in self.agents:
            logger.warning(f"Agent {agent_id} is not registered")
            return False
        
        agent = self.agents[agent_id]
        
        # Remove agent from registry
        del self.agents[agent_id]
        del self.agent_status[agent_id]
        self.agent_types[agent.agent_type.value].remove(agent_id)
        
        # Unregister agent capabilities
        for capability in agent.capabilities:
            if agent_id in self.capabilities[capability.value]:
                self.capabilities[capability.value].remove(agent_id)
        
        # Update agent registry info
        if agent_id in self.agent_registry:
            self.agent_registry[agent_id]["status"] = "unregistered"
            self.agent_registry[agent_id]["unregistered_at"] = datetime.utcnow().isoformat()
        
        # Remove heartbeat status
        if agent_id in self.heartbeat_status:
            del self.heartbeat_status[agent_id]
        
        # Update system metrics
        self.system_metrics["total_agents"] -= 1
        self.system_metrics[f"agents_{agent.agent_type.value}"] -= 1
        
        logger.info(f"Agent {agent.name} ({agent_id}) unregistered from MCP")
        return True
    
    def update_agent_status(self, agent_id: str, status: AgentStatus) -> bool:
        """
        Update the status of an agent.
        
        Args:
            agent_id: ID of the agent
            status: New agent status
            
        Returns:
            bool: Whether the update was successful
        """
        if agent_id not in self.agents:
            logger.warning(f"Agent {agent_id} is not registered")
            return False
        
        agent = self.agents[agent_id]
        previous_status = agent.status
        
        # Update agent status
        agent.status = status
        self.agent_status[agent_id] = status
        
        # Update agent registry
        self.agent_registry[agent_id]["status"] = status.value
        self.agent_registry[agent_id]["last_status_change"] = datetime.utcnow().isoformat()
        
        # Record last heartbeat time
        self.heartbeat_status[agent_id] = datetime.utcnow()
        
        logger.info(f"Agent {agent.name} ({agent_id}) status changed from {previous_status.value} to {status.value}")
        return True
    
    def send_message(self, source_agent_id: str, to_agent_id: str,
                    message_type: Union[str, MessageType],
                    payload: Dict[str, Any],
                    priority: Optional[MessagePriority] = None,
                    timeout_seconds: Optional[int] = None) -> Dict[str, Any]:
        """
        Send a message from one agent to another.
        
        Args:
            source_agent_id: ID of the sending agent
            to_agent_id: ID of the receiving agent
            message_type: Type of message
            payload: Message content
            priority: Message priority (default: NORMAL)
            timeout_seconds: Optional timeout for the message
            
        Returns:
            dict: Message sending result including message_id
        """
        # Convert string message type to MessageType enum if needed
        if isinstance(message_type, str):
            try:
                message_type = MessageType(message_type)
            except ValueError:
                message_type = MessageType.CUSTOM
        
        # Set default priority if not specified
        if priority is None:
            priority = MessagePriority.NORMAL
        
        # Create message
        message = Message(
            source_agent_id=source_agent_id,
            to_agent_id=to_agent_id,
            message_type=message_type,
            payload=payload,
            priority=priority,
            timeout_seconds=timeout_seconds
        )
        
        # Add message to log
        self.message_log.append(message)
        self.pending_messages[message.message_id] = message
        self.message_count += 1
        
        # Place message in queue with priority
        priority_value = self._get_priority_value(priority)
        self.message_queue.put((priority_value, message))
        
        logger.info(f"Message {message.message_id} from {source_agent_id} to {to_agent_id} queued")
        
        return {
            "message_id": message.message_id,
            "status": "queued",
            "timestamp": message.created_at.isoformat()
        }
    
    def broadcast_message(self, source_agent_id: str, message_type: Union[str, MessageType],
                        payload: Dict[str, Any],
                        agent_type: Optional[AgentType] = None,
                        priority: Optional[MessagePriority] = None) -> Dict[str, Any]:
        """
        Broadcast a message to multiple agents.
        
        Args:
            source_agent_id: ID of the sending agent
            message_type: Type of message
            payload: Message content
            agent_type: Optional filter for agent type
            priority: Message priority (default: NORMAL)
            
        Returns:
            dict: Broadcast result including message IDs
        """
        # Get target agents
        if agent_type:
            target_agents = list(self.agent_types.get(agent_type.value, set()))
        else:
            target_agents = list(self.agents.keys())
        
        # Remove sender from recipients
        if source_agent_id in target_agents:
            target_agents.remove(source_agent_id)
        
        # Send message to each target agent
        message_ids = []
        for to_agent_id in target_agents:
            result = self.send_message(
                source_agent_id=source_agent_id,
                to_agent_id=to_agent_id,
                message_type=message_type,
                payload=payload,
                priority=priority
            )
            message_ids.append(result["message_id"])
        
        return {
            "message_ids": message_ids,
            "recipient_count": len(message_ids),
            "status": "broadcast_queued"
        }
    
    def create_task(self, to_agent_id: str, task_type: str,
                  parameters: Dict[str, Any],
                  source_agent_id: Optional[str] = None,
                  priority: Optional[TaskPriority] = None,
                  timeout_seconds: Optional[int] = None) -> Dict[str, Any]:
        """
        Create a task for an agent.
        
        Args:
            to_agent_id: ID of the agent to assign the task to
            task_type: Type of task
            parameters: Task parameters
            source_agent_id: ID of the agent creating the task (optional)
            priority: Task priority (default: NORMAL)
            timeout_seconds: Optional timeout for the task
            
        Returns:
            dict: Task creation result including task_id
        """
        # Set default priority if not specified
        if priority is None:
            priority = TaskPriority.NORMAL
        
        # Create task
        task = Task(
            to_agent_id=to_agent_id,
            task_type=task_type,
            parameters=parameters,
            source_agent_id=source_agent_id,
            priority=priority,
            timeout_seconds=timeout_seconds
        )
        
        # Store task
        self.tasks[task.task_id] = task
        self.task_count += 1
        
        # Place task in queue with priority
        priority_value = self._get_priority_value(priority)
        self.task_queue.put((priority_value, task))
        
        logger.info(f"Task {task.task_id} of type {task_type} created for agent {to_agent_id}")
        
        return {
            "task_id": task.task_id,
            "status": "created",
            "timestamp": task.created_at.isoformat()
        }
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get the status of a task.
        
        Args:
            task_id: ID of the task
            
        Returns:
            dict: Task status information
        """
        if task_id not in self.tasks:
            return {
                "task_id": task_id,
                "status": "unknown",
                "error": "Task not found"
            }
        
        task = self.tasks[task_id]
        return {
            "task_id": task_id,
            "status": task.status.value,
            "to_agent_id": task.to_agent_id,
            "source_agent_id": task.source_agent_id,
            "task_type": task.task_type,
            "created_at": task.created_at.isoformat(),
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "result": task.result,
            "error_message": task.error_message
        }
    
    def cancel_task(self, task_id: str, reason: str = "Cancelled by system") -> Dict[str, Any]:
        """
        Cancel a task.
        
        Args:
            task_id: ID of the task to cancel
            reason: Reason for cancellation
            
        Returns:
            dict: Task cancellation result
        """
        if task_id not in self.tasks:
            return {
                "task_id": task_id,
                "status": "error",
                "error": "Task not found"
            }
        
        task = self.tasks[task_id]
        
        # Check if task can be cancelled
        if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            return {
                "task_id": task_id,
                "status": task.status.value,
                "error": f"Task cannot be cancelled in {task.status.value} state"
            }
        
        # Cancel the task
        task.cancel(reason)
        
        # Move to completed tasks if not already there
        if task_id not in self.completed_tasks:
            self.completed_tasks.append(task_id)
        
        # Remove from pending tasks if present
        agent_id = task.to_agent_id
        if agent_id in self.pending_tasks:
            self.pending_tasks[agent_id] = [t for t in self.pending_tasks[agent_id] if t.task_id != task_id]
        
        logger.info(f"Task {task_id} cancelled: {reason}")
        
        return {
            "task_id": task_id,
            "status": "cancelled",
            "reason": reason
        }
    
    def find_agent_by_capability(self, capability: str) -> Optional[str]:
        """
        Find an available agent with the specified capability.
        
        Args:
            capability: The capability to look for
            
        Returns:
            str: ID of an available agent with the capability, or None if not found
        """
        if capability not in self.capabilities:
            logger.warning(f"No agents with capability: {capability}")
            return None
        
        # Find available agents with the capability
        available_agents = []
        for agent_id in self.capabilities[capability]:
            if agent_id in self.agent_status:
                status = self.agent_status[agent_id]
                if status in [AgentStatus.ACTIVE, AgentStatus.INITIALIZING]:
                    available_agents.append(agent_id)
        
        if not available_agents:
            logger.warning(f"No available agents with capability: {capability}")
            return None
        
        # For now, simply return the first available agent
        # In a more sophisticated implementation, we could use agent metrics
        # to balance load or select the most appropriate agent
        return available_agents[0]
    
    def find_agents_by_type(self, agent_type: AgentType) -> List[str]:
        """
        Find all agents of a specific type.
        
        Args:
            agent_type: The agent type to look for
            
        Returns:
            list: List of agent IDs with the specified type
        """
        return list(self.agent_types.get(agent_type.value, set()))
    
    def get_agent_info(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a registered agent.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            dict: Agent information or None if not found
        """
        if agent_id not in self.agent_registry:
            return None
        
        agent_info = self.agent_registry[agent_id].copy()
        
        # Add metrics
        if agent_id in self.agent_metrics:
            agent_info["metrics"] = dict(self.agent_metrics[agent_id])
        
        # Add last heartbeat time
        if agent_id in self.heartbeat_status:
            agent_info["last_heartbeat"] = self.heartbeat_status[agent_id].isoformat()
        
        return agent_info
    
    def list_agents(self, agent_type: Optional[str] = None,
                  status: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List registered agents, optionally filtered by type and status.
        
        Args:
            agent_type: Optional filter for agent type
            status: Optional filter for agent status
            
        Returns:
            list: List of agent information dictionaries
        """
        agents = []
        
        for agent_id, agent_info in self.agent_registry.items():
            # Apply filters
            if agent_type and agent_info["type"] != agent_type:
                continue
            
            if status and agent_info["status"] != status:
                continue
            
            # Get complete agent info
            complete_info = self.get_agent_info(agent_id)
            if complete_info:
                agents.append(complete_info)
        
        return agents
    
    def get_message(self, message_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a message.
        
        Args:
            message_id: ID of the message
            
        Returns:
            dict: Message information or None if not found
        """
        if message_id not in self.pending_messages and not any(m.message_id == message_id for m in self.message_log):
            return None
        
        # Find message
        message = self.pending_messages.get(message_id)
        if not message:
            # Search in message log
            for m in self.message_log:
                if m.message_id == message_id:
                    message = m
                    break
        
        if not message:
            return None
        
        return message.to_dict()
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a task.
        
        Args:
            task_id: ID of the task
            
        Returns:
            dict: Task information or None if not found
        """
        if task_id not in self.tasks:
            return None
        
        return self.tasks[task_id].to_dict()
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        Get the current system status.
        
        Returns:
            dict: System status information
        """
        current_time = datetime.utcnow()
        uptime_seconds = (current_time - self.started_at).total_seconds()
        
        agent_counts = {
            status.value: sum(1 for s in self.agent_status.values() if s == status)
            for status in AgentStatus
        }
        
        agent_type_counts = {
            agent_type: len(agents)
            for agent_type, agents in self.agent_types.items()
        }
        
        return {
            "status": self.status,
            "started_at": self.started_at.isoformat(),
            "current_time": current_time.isoformat(),
            "uptime_seconds": uptime_seconds,
            "registered_agents": len(self.agents),
            "agent_status_counts": agent_counts,
            "agent_type_counts": agent_type_counts,
            "messages_processed": self.message_count,
            "tasks_processed": self.task_count,
            "metrics": dict(self.system_metrics)
        }
    
    def _process_message_queue(self):
        """Process messages in the message queue."""
        logger.info("Message queue processor started")
        
        while not self.stop_event.is_set():
            try:
                # Get next message from queue with timeout to allow checking stop event
                try:
                    priority, message = self.message_queue.get(timeout=1.0)
                    self.message_queue.task_done()
                except queue.Empty:
                    continue
                
                # Check if message has expired
                if message.is_expired():
                    logger.warning(f"Discarding expired message {message.message_id}")
                    if message.message_id in self.pending_messages:
                        del self.pending_messages[message.message_id]
                    continue
                
                # Deliver message to recipient
                self._deliver_message(message)
                
            except Exception as e:
                logger.error(f"Error processing message queue: {str(e)}")
        
        logger.info("Message queue processor stopped")
    
    def _deliver_message(self, message):
        """
        Deliver a message to its recipient agent.
        
        Args:
            message: The Message object to deliver
        """
        to_agent_id = message.to_agent_id
        
        # Check if recipient agent is registered
        if to_agent_id not in self.agents:
            logger.warning(f"Message {message.message_id} recipient {to_agent_id} not registered")
            self.undelivered_messages[to_agent_id].append(message)
            return
        
        agent = self.agents[to_agent_id]
        
        # Mark message as delivered
        message.mark_delivered()
        
        # Call the agent's handle_message method
        try:
            response = agent.handle_message(message)
            message.mark_processed()
            
            # Update agent metrics
            self.agent_metrics[to_agent_id]["messages_processed"] += 1
            
            # Handle response if needed
            if message.message_id in self.pending_messages:
                del self.pending_messages[message.message_id]
            
            logger.debug(f"Message {message.message_id} delivered to {to_agent_id}")
            
        except Exception as e:
            logger.error(f"Error delivering message {message.message_id} to {to_agent_id}: {str(e)}")
            self.agent_metrics[to_agent_id]["errors"] += 1
    
    def _process_task_queue(self):
        """Process tasks in the task queue."""
        logger.info("Task queue processor started")
        
        while not self.stop_event.is_set():
            try:
                # Get next task from queue with timeout to allow checking stop event
                try:
                    priority, task = self.task_queue.get(timeout=1.0)
                    self.task_queue.task_done()
                except queue.Empty:
                    continue
                
                # Assign and queue task
                self._assign_task(task)
                
            except Exception as e:
                logger.error(f"Error processing task queue: {str(e)}")
        
        logger.info("Task queue processor stopped")
    
    def _assign_task(self, task):
        """
        Assign a task to its target agent.
        
        Args:
            task: The Task object to assign
        """
        to_agent_id = task.to_agent_id
        
        # Check if target agent is registered
        if to_agent_id not in self.agents:
            logger.warning(f"Task {task.task_id} target agent {to_agent_id} not registered")
            # Store task for later assignment when agent registers
            self.pending_tasks[to_agent_id].append(task)
            return
        
        agent = self.agents[to_agent_id]
        
        # Mark task as assigned
        task.assign()
        
        # Add to agent's pending tasks
        self.pending_tasks[to_agent_id].append(task)
        
        # Create message to notify agent of task assignment
        message = Message(
            source_agent_id="mcp",
            to_agent_id=to_agent_id,
            message_type=MessageType.TASK_ASSIGNMENT,
            payload={
                "task_id": task.task_id,
                "task_type": task.task_type,
                "parameters": task.parameters
            },
            priority=MessagePriority.HIGH
        )
        
        # Place message in queue
        priority_value = self._get_priority_value(MessagePriority.HIGH)
        self.message_queue.put((priority_value, message))
        
        logger.info(f"Task {task.task_id} assigned to agent {to_agent_id}")
    
    def _monitor_heartbeats(self):
        """Monitor agent heartbeats."""
        logger.info("Heartbeat monitor started")
        
        while not self.stop_event.is_set():
            try:
                # Check agent heartbeats
                current_time = datetime.utcnow()
                for agent_id, last_heartbeat in list(self.heartbeat_status.items()):
                    # Skip if agent is not registered
                    if agent_id not in self.agents:
                        continue
                    
                    # Get agent status
                    status = self.agent_status[agent_id]
                    
                    # Skip inactive agents
                    if status in [AgentStatus.INACTIVE, AgentStatus.TERMINATED]:
                        continue
                    
                    # Check heartbeat age
                    heartbeat_age = (current_time - last_heartbeat).total_seconds()
                    
                    # Warning threshold: 30 seconds
                    if heartbeat_age > 30 and status != AgentStatus.ERROR:
                        logger.warning(f"Agent {agent_id} heartbeat is {heartbeat_age:.1f} seconds old")
                    
                    # Error threshold: 60 seconds
                    if heartbeat_age > 60 and status not in [AgentStatus.ERROR, AgentStatus.MAINTENANCE]:
                        logger.error(f"Agent {agent_id} heartbeat timeout after {heartbeat_age:.1f} seconds")
                        self.update_agent_status(agent_id, AgentStatus.ERROR)
                
                # Sleep for a while
                time.sleep(10)
                
            except Exception as e:
                logger.error(f"Error monitoring heartbeats: {str(e)}")
                time.sleep(5)
        
        logger.info("Heartbeat monitor stopped")
    
    def _get_priority_value(self, priority):
        """
        Convert priority enum to numeric priority value for queues.
        
        Args:
            priority: Priority enum (MessagePriority or TaskPriority)
            
        Returns:
            int: Numeric priority value (lower = higher priority)
        """
        priority_map = {
            "critical": 0,
            "high": 1,
            "normal": 2,
            "low": 3,
            "background": 4
        }
        
        priority_value = priority_map.get(priority.value, 2)
        return priority_value
    
    def _save_state(self):
        """Save the MCP state to storage."""
        try:
            state = {
                "started_at": self.started_at.isoformat(),
                "status": self.status,
                "agent_registry": self.agent_registry,
                "system_metrics": dict(self.system_metrics),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            state_path = os.path.join(self.storage_dir, "mcp_state.json")
            with open(state_path, "w") as f:
                json.dump(state, f, indent=2)
            
            logger.debug("MCP state saved to storage")
            
        except Exception as e:
            logger.error(f"Error saving MCP state: {str(e)}")
    
    def _load_state(self):
        """Load the MCP state from storage."""
        state_path = os.path.join(self.storage_dir, "mcp_state.json")
        
        if not os.path.exists(state_path):
            logger.info("No saved MCP state found")
            return
        
        try:
            with open(state_path, "r") as f:
                state = json.load(f)
            
            # Restore basic state
            self.started_at = datetime.fromisoformat(state["started_at"])
            self.status = state["status"]
            
            # Restore agent registry
            self.agent_registry = state["agent_registry"]
            
            # Restore system metrics
            for metric, value in state["system_metrics"].items():
                self.system_metrics[metric] = value
            
            logger.info("MCP state loaded from storage")
            
        except Exception as e:
            logger.error(f"Error loading MCP state: {str(e)}")
    
    def __del__(self):
        """Cleanup when object is deleted."""
        if self.is_running:
            self.stop()
        
        # Save state
        self._save_state()