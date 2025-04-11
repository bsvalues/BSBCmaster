"""
Message Module for Benton County Assessor's Office AI Platform

This module defines the standardized message format for communication
between the Core, MCP, and Agent Army.
"""

import json
import uuid
import time
from enum import Enum, auto
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime


class EventType(Enum):
    """Types of events that can be sent between agents."""
    COMMAND = auto()
    EVENT = auto()
    QUERY = auto()
    RESPONSE = auto()
    ERROR = auto()
    STATUS_UPDATE = auto()
    ASSISTANCE_REQUESTED = auto()


class Priority(Enum):
    """Priority levels for messages."""
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    CRITICAL = auto()


@dataclass
class Message:
    """
    Standard message format for agent communication.
    
    This class defines the standard message format that all agents
    must use when communicating with each other.
    
    Attributes:
        message_id: Unique identifier for this message
        correlation_id: Identifier to track related messages in a workflow
        source_agent_id: Identifier of the sender agent
        target_agent_id: Identifier of the recipient agent (or "broadcast")
        timestamp: ISO 8601 datetime when the message was created
        event_type: Type of event (from EventType enum)
        payload: The actual content of the message
        metadata: Additional metadata for the message
    """
    source_agent_id: str
    target_agent_id: str
    event_type: EventType
    payload: Dict[str, Any]
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + 'Z')
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize any missing fields with default values."""
        # Convert event_type to enum if it's a string
        if isinstance(self.event_type, str):
            try:
                self.event_type = EventType[self.event_type]
            except KeyError:
                raise ValueError(f"Invalid event type: {self.event_type}")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the message to a dictionary.
        
        Returns:
            Dictionary representation of the message
        """
        result = asdict(self)
        
        # Convert enum to string
        result["event_type"] = self.event_type.name
        
        return result
    
    def to_json(self) -> str:
        """
        Convert the message to a JSON string.
        
        Returns:
            JSON string representation of the message
        """
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """
        Create a message from a dictionary.
        
        Args:
            data: Dictionary representation of a message
            
        Returns:
            Message instance
        """
        # Make a copy to avoid modifying the original
        message_data = data.copy()
        
        # Convert event_type string to enum
        if "event_type" in message_data and isinstance(message_data["event_type"], str):
            try:
                message_data["event_type"] = EventType[message_data["event_type"]]
            except KeyError:
                raise ValueError(f"Invalid event type: {message_data['event_type']}")
        
        return cls(**message_data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Message':
        """
        Create a message from a JSON string.
        
        Args:
            json_str: JSON string representation of a message
            
        Returns:
            Message instance
        """
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def set_priority(self, priority: Union[Priority, str]) -> None:
        """
        Set the priority of the message.
        
        Args:
            priority: Priority level (from Priority enum or string)
        """
        if isinstance(priority, str):
            try:
                priority = Priority[priority]
            except KeyError:
                raise ValueError(f"Invalid priority: {priority}")
        
        self.metadata["priority"] = priority.name
    
    def get_priority(self) -> Optional[Priority]:
        """
        Get the priority of the message.
        
        Returns:
            Priority level or None if not set
        """
        priority_str = self.metadata.get("priority")
        if priority_str is None:
            return None
        
        try:
            return Priority[priority_str]
        except KeyError:
            return None
    
    def set_ttl(self, seconds: int) -> None:
        """
        Set the time-to-live for the message.
        
        Args:
            seconds: Number of seconds the message is valid
        """
        self.metadata["ttl"] = seconds
    
    def get_ttl(self) -> Optional[int]:
        """
        Get the time-to-live for the message.
        
        Returns:
            TTL in seconds or None if not set
        """
        return self.metadata.get("ttl")
    
    def is_expired(self) -> bool:
        """
        Check if the message has expired based on TTL.
        
        Returns:
            True if the message has expired, False otherwise
        """
        ttl = self.get_ttl()
        if ttl is None:
            return False
        
        try:
            timestamp = datetime.fromisoformat(self.timestamp.rstrip('Z'))
            now = datetime.utcnow()
            elapsed = (now - timestamp).total_seconds()
            
            return elapsed > ttl
        except Exception:
            return False


class CommandMessage(Message):
    """Message containing a command to be executed by the recipient."""
    
    def __init__(self, source_agent_id: str, target_agent_id: str, 
                command_name: str, parameters: Dict[str, Any] = None,
                correlation_id: Optional[str] = None,
                priority: Optional[Priority] = None):
        """
        Initialize a command message.
        
        Args:
            source_agent_id: Identifier of the sender agent
            target_agent_id: Identifier of the recipient agent
            command_name: Name of the command to execute
            parameters: Parameters for the command
            correlation_id: Identifier to track related messages
            priority: Priority level for the message
        """
        payload = {
            "command_name": command_name,
            "parameters": parameters or {}
        }
        
        super().__init__(
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_id,
            event_type=EventType.COMMAND,
            payload=payload,
            correlation_id=correlation_id
        )
        
        if priority is not None:
            self.set_priority(priority)


class ResponseMessage(Message):
    """Message containing a response to a previous message."""
    
    def __init__(self, source_agent_id: str, target_agent_id: str,
                status: str, result: Any = None, 
                original_message_id: Optional[str] = None,
                correlation_id: Optional[str] = None):
        """
        Initialize a response message.
        
        Args:
            source_agent_id: Identifier of the sender agent
            target_agent_id: Identifier of the recipient agent
            status: Status of the response ("success", "failure", etc.)
            result: Result data
            original_message_id: ID of the message being responded to
            correlation_id: Identifier to track related messages
        """
        payload = {
            "status": status,
            "result": result
        }
        
        metadata = {}
        if original_message_id:
            metadata["original_message_id"] = original_message_id
        
        super().__init__(
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_id,
            event_type=EventType.RESPONSE,
            payload=payload,
            correlation_id=correlation_id,
            metadata=metadata
        )


class ErrorMessage(Message):
    """Message containing an error report."""
    
    def __init__(self, source_agent_id: str, target_agent_id: str,
                error_code: str, error_message: str,
                details: Optional[Dict[str, Any]] = None,
                original_message_id: Optional[str] = None,
                correlation_id: Optional[str] = None):
        """
        Initialize an error message.
        
        Args:
            source_agent_id: Identifier of the sender agent
            target_agent_id: Identifier of the recipient agent
            error_code: Error code
            error_message: Error message
            details: Additional error details
            original_message_id: ID of the message that caused the error
            correlation_id: Identifier to track related messages
        """
        payload = {
            "error_code": error_code,
            "error_message": error_message,
            "details": details or {}
        }
        
        metadata = {}
        if original_message_id:
            metadata["original_message_id"] = original_message_id
        
        super().__init__(
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_id,
            event_type=EventType.ERROR,
            payload=payload,
            correlation_id=correlation_id,
            metadata=metadata
        )


class StatusUpdateMessage(Message):
    """Message containing a status update from an agent."""
    
    def __init__(self, source_agent_id: str, target_agent_id: str,
                status: str, metrics: Optional[Dict[str, Any]] = None,
                correlation_id: Optional[str] = None):
        """
        Initialize a status update message.
        
        Args:
            source_agent_id: Identifier of the sender agent
            target_agent_id: Identifier of the recipient agent
            status: Status of the agent ("active", "idle", etc.)
            metrics: Performance metrics
            correlation_id: Identifier to track related messages
        """
        payload = {
            "status": status,
            "metrics": metrics or {}
        }
        
        super().__init__(
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_id,
            event_type=EventType.STATUS_UPDATE,
            payload=payload,
            correlation_id=correlation_id
        )


class AssistanceRequestMessage(Message):
    """Message requesting assistance from another agent."""
    
    def __init__(self, source_agent_id: str, target_agent_id: str,
                assistance_type: str, context: Dict[str, Any] = None,
                urgency: str = "normal",
                correlation_id: Optional[str] = None):
        """
        Initialize an assistance request message.
        
        Args:
            source_agent_id: Identifier of the sender agent
            target_agent_id: Identifier of the recipient agent
            assistance_type: Type of assistance needed
            context: Contextual information for the request
            urgency: Urgency of the request ("low", "normal", "high", "critical")
            correlation_id: Identifier to track related messages
        """
        payload = {
            "assistance_type": assistance_type,
            "context": context or {},
            "urgency": urgency
        }
        
        # Set priority based on urgency
        priority_map = {
            "low": Priority.LOW,
            "normal": Priority.MEDIUM,
            "high": Priority.HIGH,
            "critical": Priority.CRITICAL
        }
        
        super().__init__(
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_id,
            event_type=EventType.ASSISTANCE_REQUESTED,
            payload=payload,
            correlation_id=correlation_id
        )
        
        priority = priority_map.get(urgency.lower(), Priority.MEDIUM)
        self.set_priority(priority)