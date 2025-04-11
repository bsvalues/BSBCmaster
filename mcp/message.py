"""
Message Module for Benton County Assessor's Office MCP

This module defines the Message class and related enumerations for the
inter-agent communication system within the MCP framework.
"""

import logging
import uuid
import json
from datetime import datetime
from enum import Enum, auto
from typing import Dict, List, Any, Optional, Union

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MessageType(Enum):
    """Types of messages that can be exchanged between agents."""
    # Control messages
    REGISTRATION = "registration"       # Agent registration with MCP
    STATUS_UPDATE = "status-update"     # Agent status updates
    HEARTBEAT = "heartbeat"             # Regular check-in message
    
    # Data messages
    DATA_REQUEST = "data-request"       # Request for specific data
    DATA_RESPONSE = "data-response"     # Response with requested data
    DATA_UPDATE = "data-update"         # Update to existing data
    
    # Task messages
    TASK_ASSIGNMENT = "task-assignment" # Assignment of tasks
    TASK_STATUS = "task-status"         # Status update on tasks
    TASK_RESULT = "task-result"         # Results from completed tasks
    
    # Validation messages
    VALIDATION_REQUEST = "validation-request" # Request for data validation
    VALIDATION_RESPONSE = "validation-response" # Validation results
    
    # Compliance messages
    COMPLIANCE_CHECK = "compliance-check" # Request for compliance check
    COMPLIANCE_REPORT = "compliance-report" # Compliance check results
    
    # Valuation messages
    VALUATION_REQUEST = "valuation-request" # Request for property valuation
    VALUATION_RESPONSE = "valuation-response" # Valuation results
    TREND_ANALYSIS_REQUEST = "trend-analysis-request" # Request for property value trend analysis
    TREND_ANALYSIS_RESPONSE = "trend-analysis-response" # Trend analysis results
    COMPARATIVE_ANALYSIS_REQUEST = "comparative-analysis-request" # Request for comparative property analysis
    COMPARATIVE_ANALYSIS_RESPONSE = "comparative-analysis-response" # Comparative analysis results
    
    # Alert messages
    ALERT = "alert"                     # Important system alerts
    ERROR = "error"                     # Error notifications
    WARNING = "warning"                 # Warning notifications
    
    # User interaction messages
    USER_QUERY = "user-query"           # User query to the system
    USER_RESPONSE = "user-response"     # Response to user queries
    
    # Workflow messages
    WORKFLOW_START = "workflow-start"   # Start of a workflow
    WORKFLOW_STEP = "workflow-step"     # Individual workflow step
    WORKFLOW_END = "workflow-end"       # End of a workflow
    
    # Custom message type
    CUSTOM = "custom"                   # Custom message type


class MessagePriority(Enum):
    """Priority levels for messages in the MCP system."""
    CRITICAL = "critical"   # Highest priority, requires immediate attention
    HIGH = "high"           # High priority
    NORMAL = "normal"       # Normal priority
    LOW = "low"             # Low priority
    BACKGROUND = "background" # Lowest priority, process when idle


class Message:
    """
    Message class for inter-agent communication in the MCP system.
    
    This class represents messages exchanged between agents, providing
    a structured communication protocol with message tracking, prioritization,
    and delivery confirmation.
    """
    
    def __init__(self, source_agent_id: str, to_agent_id: str,
                message_type: MessageType = MessageType.CUSTOM,
                payload: Union[Dict[str, Any], None] = None,
                priority: MessagePriority = MessagePriority.NORMAL,
                message_id: Optional[str] = None,
                correlation_id: Optional[str] = None,
                timeout_seconds: Optional[int] = None):
        """
        Initialize a new message with the specified parameters.
        
        Args:
            source_agent_id: ID of the sending agent
            to_agent_id: ID of the receiving agent
            message_type: Type of message
            payload: Message content as a dictionary
            priority: Message priority
            message_id: Unique identifier for the message (generated if not provided)
            correlation_id: ID linking related messages (for request/response tracking)
            timeout_seconds: Optional timeout for the message in seconds
        """
        self.message_id = message_id or str(uuid.uuid4())
        self.correlation_id = correlation_id
        self.source_agent_id = source_agent_id
        self.to_agent_id = to_agent_id
        self.message_type = message_type
        self.payload = {} if payload is None else payload
        self.priority = priority
        
        # Message metadata
        self.created_at = datetime.utcnow()
        self.delivered_at = None
        self.processed_at = None
        self.response_id = None
        
        # Message timeout
        self.timeout_seconds = timeout_seconds
        self.expired = False
        
        logger.debug(f"Created message {self.message_id} from {source_agent_id} to {to_agent_id}")
    
    def mark_delivered(self):
        """Mark the message as delivered to the recipient."""
        self.delivered_at = datetime.utcnow()
        logger.debug(f"Message {self.message_id} marked as delivered")
    
    def mark_processed(self):
        """Mark the message as processed by the recipient."""
        self.processed_at = datetime.utcnow()
        logger.debug(f"Message {self.message_id} marked as processed")
    
    def set_response(self, response_message_id: str):
        """
        Set the ID of the response message.
        
        Args:
            response_message_id: ID of the response message
        """
        self.response_id = response_message_id
        logger.debug(f"Message {self.message_id} has response {response_message_id}")
    
    def is_expired(self) -> bool:
        """
        Check if the message has expired based on its timeout.
        
        Returns:
            bool: Whether the message has expired
        """
        if self.timeout_seconds is None:
            return False
        
        if self.expired:
            return True
        
        # Check if current time exceeds timeout
        elapsed_seconds = (datetime.utcnow() - self.created_at).total_seconds()
        self.expired = elapsed_seconds > self.timeout_seconds
        
        if self.expired:
            logger.warning(f"Message {self.message_id} has expired after {elapsed_seconds} seconds")
        
        return self.expired
    
    def create_response(self, payload: Dict[str, Any],
                      message_type: Optional[MessageType] = None,
                      priority: Optional[MessagePriority] = None) -> 'Message':
        """
        Create a response message to this message.
        
        Args:
            payload: Content of the response
            message_type: Type of response message (default: derives appropriate response type)
            priority: Priority of response message (default: same as original message)
            
        Returns:
            Message: The response message
        """
        if message_type is None:
            # Derive appropriate response type
            if self.message_type == MessageType.DATA_REQUEST:
                response_type = MessageType.DATA_RESPONSE
            elif self.message_type == MessageType.VALIDATION_REQUEST:
                response_type = MessageType.VALIDATION_RESPONSE
            elif self.message_type == MessageType.COMPLIANCE_CHECK:
                response_type = MessageType.COMPLIANCE_REPORT
            elif self.message_type == MessageType.VALUATION_REQUEST:
                response_type = MessageType.VALUATION_RESPONSE
            elif self.message_type == MessageType.TREND_ANALYSIS_REQUEST:
                response_type = MessageType.TREND_ANALYSIS_RESPONSE
            elif self.message_type == MessageType.COMPARATIVE_ANALYSIS_REQUEST:
                response_type = MessageType.COMPARATIVE_ANALYSIS_RESPONSE
            elif self.message_type == MessageType.USER_QUERY:
                response_type = MessageType.USER_RESPONSE
            else:
                response_type = self.message_type
        else:
            response_type = message_type
        
        response = Message(
            source_agent_id=self.to_agent_id,
            to_agent_id=self.source_agent_id,
            message_type=response_type,
            payload=payload,
            priority=priority or self.priority,
            correlation_id=self.message_id
        )
        
        self.set_response(response.message_id)
        return response
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert message to a dictionary representation.
        
        Returns:
            dict: Dictionary representation of the message
        """
        return {
            "message_id": self.message_id,
            "correlation_id": self.correlation_id,
            "source_agent_id": self.source_agent_id,
            "to_agent_id": self.to_agent_id,
            "message_type": self.message_type.value,
            "payload": self.payload,
            "priority": self.priority.value,
            "created_at": self.created_at.isoformat(),
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "response_id": self.response_id,
            "timeout_seconds": self.timeout_seconds,
            "expired": self.expired
        }
    
    def to_json(self) -> str:
        """
        Convert message to JSON string.
        
        Returns:
            str: JSON representation of the message
        """
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """
        Create a message from a dictionary representation.
        
        Args:
            data: Dictionary representation of the message
            
        Returns:
            Message: The reconstructed message
        """
        # Handle backward compatibility with from_agent_id and content keys
        source_agent_id = data.get("source_agent_id", data.get("from_agent_id"))
        payload = data.get("payload", data.get("content"))
        
        message = cls(
            source_agent_id=source_agent_id,
            to_agent_id=data["to_agent_id"],
            message_type=MessageType(data["message_type"]),
            payload=payload,
            priority=MessagePriority(data["priority"]),
            message_id=data["message_id"],
            correlation_id=data.get("correlation_id"),
            timeout_seconds=data.get("timeout_seconds")
        )
        
        # Set message metadata
        message.created_at = datetime.fromisoformat(data["created_at"])
        
        if data.get("delivered_at"):
            message.delivered_at = datetime.fromisoformat(data["delivered_at"])
        
        if data.get("processed_at"):
            message.processed_at = datetime.fromisoformat(data["processed_at"])
        
        message.response_id = data.get("response_id")
        message.expired = data.get("expired", False)
        
        return message
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Message':
        """
        Create a message from a JSON string.
        
        Args:
            json_str: JSON representation of the message
            
        Returns:
            Message: The reconstructed message
        """
        data = json.loads(json_str)
        return cls.from_dict(data)