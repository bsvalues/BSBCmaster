"""
Agent Module for Benton County Assessor's Office MCP

This module defines the base Agent class and related enumerations for the
AI agent framework, supporting the specialized agents in the system.
"""

import logging
import uuid
from datetime import datetime
from enum import Enum, auto
from typing import Dict, List, Any, Optional, Set, Callable, Union

from mcp.message import MessageType

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AgentStatus(Enum):
    """Status options for agents in the MCP system."""
    ACTIVE = "active"             # Agent is online and operational
    INACTIVE = "inactive"         # Agent is registered but not running
    INITIALIZING = "initializing" # Agent is starting up
    BUSY = "busy"                 # Agent is processing tasks, at capacity
    ERROR = "error"               # Agent is experiencing errors
    MAINTENANCE = "maintenance"   # Agent is in maintenance mode
    TERMINATED = "terminated"     # Agent has been terminated


class AgentType(Enum):
    """Types of specialized agents in the MCP system."""
    DATA_QUALITY = "data-quality"       # Data validation and quality control
    COMPLIANCE = "compliance"           # Regulatory compliance checking
    VALUATION = "valuation"             # Property valuation and assessment
    TAX_INFORMATION = "tax-information" # Tax calculation and information
    WORKFLOW = "workflow"               # Workflow automation
    USER_INTERACTION = "user-interaction" # User interface and interaction
    SYSTEM = "system"                   # System-level operations


class AgentCapability(Enum):
    """Capabilities that agents can provide in the MCP system."""
    # Data Quality capabilities
    DATA_VALIDATION = "data-validation"   # Validates data against rules
    ANOMALY_DETECTION = "anomaly-detection" # Detects data anomalies
    DATA_ENHANCEMENT = "data-enhancement" # Enhances data with additional info
    
    # Compliance capabilities
    REGULATION_CHECK = "regulation-check" # Checks compliance with regulations
    AUDIT_TRAIL = "audit-trail"           # Maintains audit trails
    POLICY_ENFORCEMENT = "policy-enforcement" # Enforces assessment policies
    
    # Valuation capabilities
    PROPERTY_VALUATION = "property-valuation" # Values properties
    COMPARABLE_ANALYSIS = "comparable-analysis" # Analyzes comparable properties
    MARKET_ANALYSIS = "market-analysis"     # Analyzes market trends
    
    # Tax Information capabilities
    TAX_CALCULATION = "tax-calculation"   # Calculates property taxes
    EXEMPTION_PROCESSING = "exemption-processing" # Processes tax exemptions
    TAX_REPORTING = "tax-reporting"       # Generates tax reports
    
    # Workflow capabilities
    TASK_AUTOMATION = "task-automation"   # Automates routine tasks
    WORK_SCHEDULING = "work-scheduling"   # Schedules work assignments
    NOTIFICATION = "notification"         # Sends notifications
    
    # User Interaction capabilities
    QUERY_RESPONSE = "query-response"     # Responds to user queries
    INFORMATION_RETRIEVAL = "information-retrieval" # Retrieves information
    DASHBOARD_GENERATION = "dashboard-generation" # Generates dashboards


class Agent:
    """
    Base Agent class for the MCP system.
    
    This class provides the foundation for all specialized agents in the
    Benton County Assessor's Office AI platform, implementing the core
    functionality required for agent registration, communication, and
    task execution within the MCP orchestration framework.
    """
    
    def __init__(self, agent_id: Optional[str] = None,
                agent_type: AgentType = AgentType.SYSTEM,
                name: str = "Unnamed Agent",
                description: str = "",
                capabilities: Optional[List[AgentCapability]] = None):
        """
        Initialize a new agent with the specified parameters.
        
        Args:
            agent_id: Unique identifier for the agent (generated if not provided)
            agent_type: Type of specialized agent
            name: Human-readable name for the agent
            description: Detailed description of the agent's purpose
            capabilities: List of agent capabilities
        """
        # Basic agent information
        self.agent_id = agent_id or f"{agent_type.value}-{str(uuid.uuid4())[:8]}"
        self.agent_type = agent_type
        self.name = name
        self.description = description
        self.capabilities = set(capabilities or [])
        
        # Agent state
        self.status = AgentStatus.INITIALIZING
        self.creation_time = datetime.utcnow()
        self.last_active_time = self.creation_time
        self.error_count = 0
        self.task_count = 0
        self.message_count = 0
        
        # References to MCP and other components
        self.mcp = None
        self.task_handlers = {}
        self.message_handlers = {}
        
        logger.info(f"Agent {self.name} ({self.agent_id}) initialized with type {self.agent_type.value}")
    
    def register_with_mcp(self, mcp):
        """
        Register this agent with the Master Control Program.
        
        Args:
            mcp: The MasterControlProgram instance
            
        Returns:
            bool: Whether registration was successful
        """
        self.mcp = mcp
        success = mcp.register_agent(self)
        
        if success:
            self.status = AgentStatus.ACTIVE
            logger.info(f"Agent {self.name} registered successfully with MCP")
        else:
            self.status = AgentStatus.ERROR
            logger.error(f"Agent {self.name} failed to register with MCP")
        
        return success
    
    def add_capability(self, capability: AgentCapability):
        """
        Add a capability to this agent.
        
        Args:
            capability: The capability to add
        """
        self.capabilities.add(capability)
        logger.info(f"Added capability {capability.value} to agent {self.name}")
    
    def has_capability(self, capability: AgentCapability) -> bool:
        """
        Check if this agent has a specific capability.
        
        Args:
            capability: The capability to check
            
        Returns:
            bool: Whether the agent has the capability
        """
        return capability in self.capabilities
    
    def register_task_handler(self, task_type: str, handler: Callable):
        """
        Register a handler for a specific type of task.
        
        Args:
            task_type: The type of task
            handler: The function to handle the task
        """
        self.task_handlers[task_type] = handler
        logger.info(f"Registered handler for task type {task_type} on agent {self.name}")
    
    def register_message_handler(self, message_type: Union[str, MessageType], handler: Callable):
        """
        Register a handler for a specific type of message.
        
        Args:
            message_type: The type of message (string or MessageType enum)
            handler: The function to handle the message
        """
        # Convert MessageType enum to string if needed
        if isinstance(message_type, MessageType):
            msg_type_key = message_type.value
        else:
            msg_type_key = message_type
            
        self.message_handlers[msg_type_key] = handler
        logger.info(f"Registered handler for message type {msg_type_key} on agent {self.name}")
    
    def handle_task(self, task):
        """
        Handle a task assigned to this agent.
        
        Args:
            task: The task to handle
            
        Returns:
            dict: The task result
        """
        self.last_active_time = datetime.utcnow()
        self.task_count += 1
        
        if task.task_type in self.task_handlers:
            try:
                self.status = AgentStatus.BUSY
                handler = self.task_handlers[task.task_type]
                result = handler(task)
                self.status = AgentStatus.ACTIVE
                logger.info(f"Agent {self.name} completed task {task.task_id}")
                return result
            except Exception as e:
                self.error_count += 1
                self.status = AgentStatus.ERROR
                logger.error(f"Agent {self.name} failed to handle task {task.task_id}: {str(e)}")
                return {"error": str(e), "status": "failed"}
        else:
            logger.warning(f"Agent {self.name} has no handler for task type {task.task_type}")
            return {"error": f"No handler for task type {task.task_type}", "status": "rejected"}
    
    def handle_message(self, message):
        """
        Handle a message sent to this agent.
        
        Args:
            message: The message to handle
            
        Returns:
            dict: The message response
        """
        self.last_active_time = datetime.utcnow()
        self.message_count += 1
        
        # Get the message type as a string for handler lookup
        msg_type_key = message.message_type.value if isinstance(message.message_type, MessageType) else message.message_type
        
        if msg_type_key in self.message_handlers:
            try:
                handler = self.message_handlers[msg_type_key]
                response = handler(message)
                logger.info(f"Agent {self.name} handled message {message.message_id}")
                return response
            except Exception as e:
                self.error_count += 1
                logger.error(f"Agent {self.name} failed to handle message {message.message_id}: {str(e)}")
                return {"error": str(e), "status": "failed"}
        else:
            logger.warning(f"Agent {self.name} has no handler for message type {msg_type_key}")
            return {"error": f"No handler for message type {msg_type_key}", "status": "rejected"}
    
    def send_message(self, target_agent_id: str, message_type: Union[str, MessageType], payload: Dict[str, Any], correlation_id: Optional[str] = None):
        """
        Send a message to another agent through the MCP.
        
        Args:
            target_agent_id: The ID of the receiving agent
            message_type: The type of message
            payload: The message payload
            correlation_id: Optional correlation ID for related messages
            
        Returns:
            dict: The message sending result
        """
        if not self.mcp:
            logger.error(f"Agent {self.name} tried to send message but is not registered with MCP")
            return {"error": "Not registered with MCP", "status": "failed"}
        
        # Pass the correlation_id as part of the message creation process
        priority = None  # Let the MCP use the default priority
        timeout_seconds = None  # Let the MCP handle timeouts
        return self.mcp.send_message(self.agent_id, target_agent_id, message_type, payload, priority, timeout_seconds)
    
    def assign_task(self, to_agent_id: str, task_type: str, parameters: Dict[str, Any]):
        """
        Assign a task to another agent through the MCP.
        
        Args:
            to_agent_id: The ID of the agent to assign the task to
            task_type: The type of task
            parameters: The task parameters
            
        Returns:
            dict: The task assignment result
        """
        if not self.mcp:
            logger.error(f"Agent {self.name} tried to assign task but is not registered with MCP")
            return {"error": "Not registered with MCP", "status": "failed"}
        
        return self.mcp.create_task(to_agent_id, task_type, parameters, self.agent_id)
    
    def update_status(self, status: AgentStatus):
        """
        Update the status of this agent.
        
        Args:
            status: The new status
        """
        previous_status = self.status
        self.status = status
        self.last_active_time = datetime.utcnow()
        
        logger.info(f"Agent {self.name} status changed from {previous_status.value} to {status.value}")
        
        # Notify MCP of status change
        if self.mcp:
            self.mcp.update_agent_status(self.agent_id, status)
    
    def get_info(self) -> Dict[str, Any]:
        """
        Get information about this agent.
        
        Returns:
            dict: Agent information
        """
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "type": self.agent_type.value,
            "status": self.status.value,
            "capabilities": [capability.value for capability in self.capabilities],
            "creation_time": self.creation_time.isoformat(),
            "last_active_time": self.last_active_time.isoformat(),
            "error_count": self.error_count,
            "task_count": self.task_count,
            "message_count": self.message_count
        }
    
    def shutdown(self):
        """
        Shutdown this agent gracefully.
        """
        logger.info(f"Agent {self.name} is shutting down")
        self.status = AgentStatus.TERMINATED
        
        # Notify MCP
        if self.mcp:
            self.mcp.update_agent_status(self.agent_id, self.status)
            self.mcp.unregister_agent(self.agent_id)
            self.mcp = None