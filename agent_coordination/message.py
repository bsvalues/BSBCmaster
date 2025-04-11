"""
Message Module for Agent Coordination

This module defines the standardized message format for communication
between agents, the MCP, and the coordination system.
"""

from enum import Enum, auto
from dataclasses import dataclass
from typing import Dict, Any, Optional
import json
import uuid
from datetime import datetime


class MessageType(Enum):
    """Types of messages that can be sent between agents."""
    ACTION = auto()
    ERROR = auto()
    RESULT = auto()
    STATUS_UPDATE = auto()
    HELP_REQUEST = auto()
    TASK_DELEGATION = auto()
    TRAINING_UPDATE = auto()
    POLICY_UPDATE = auto()


@dataclass
class CoordinationMessage:
    """
    Standardized message format for agent communication.
    
    Attributes:
        agent_id: Unique identifier of the sender agent
        message_id: Unique identifier for this message
        timestamp: ISO 8601 datetime when the message was created
        message_type: Type of message (from MessageType enum)
        payload: The actual content of the message
        recipient_id: Optional identifier of the intended recipient
    """
    agent_id: str
    message_type: MessageType
    payload: Dict[str, Any]
    recipient_id: Optional[str] = None
    message_id: str = None
    timestamp: str = None
    
    def __post_init__(self):
        """Initialize message_id and timestamp if not provided."""
        if self.message_id is None:
            self.message_id = str(uuid.uuid4())
        
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat() + 'Z'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the message to a dictionary format."""
        return {
            "message_id": self.message_id,
            "agent_id": self.agent_id,
            "timestamp": self.timestamp,
            "message_type": self.message_type.name,
            "payload": self.payload,
            "recipient_id": self.recipient_id
        }
    
    def to_json(self) -> str:
        """Convert the message to a JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CoordinationMessage':
        """Create a message from a dictionary."""
        # Convert string message_type back to enum
        data = data.copy()  # Create a copy to avoid modifying the original
        data['message_type'] = MessageType[data['message_type']]
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'CoordinationMessage':
        """Create a message from a JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def __str__(self) -> str:
        """String representation of the message."""
        return (f"Message {self.message_id} from {self.agent_id} "
                f"to {self.recipient_id or 'all'} "
                f"of type {self.message_type.name}")