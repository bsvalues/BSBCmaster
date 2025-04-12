"""
Core Module for Benton County Assessor's Office AI Platform

This module serves as the central hub for the AI platform, providing
configuration, orchestration, and integration for the MCP and Agent Army.
The enhanced version includes improved component architecture, error handling,
agent management, and communication protocols.
"""

from .config import CoreConfig
from .message import Message, CommandMessage, ResponseMessage, ErrorMessage, StatusUpdateMessage, AssistanceRequestMessage, EventType, Priority
from .experience import Experience, create_replay_buffer
from .logging import LogManager, ContextAdapter, create_log_manager, create_logger
from .hub import CoreHub
from .hub_enhanced import CoreHubEnhanced, create_core_hub_enhanced
from .agent_manager import AgentManager, create_agent_manager
from .communication import CommunicationManager, create_communication_manager
from .error_handler import (
    ErrorHandler, Error, ErrorCode, ErrorCategory, ErrorLevel, 
    create_error_handler
)

__all__ = [
    # Core Configuration
    'CoreConfig',
    
    # Core Hub (Original)
    'CoreHub',
    
    # Core Hub (Enhanced)
    'CoreHubEnhanced',
    'create_core_hub_enhanced',
    
    # Messaging System
    'Message',
    'CommandMessage',
    'ResponseMessage',
    'ErrorMessage',
    'StatusUpdateMessage',
    'AssistanceRequestMessage',
    'EventType',
    'Priority',
    
    # Experience Replay
    'Experience',
    'create_replay_buffer',
    
    # Logging System
    'LogManager',
    'ContextAdapter',
    'create_log_manager',
    'create_logger',
    
    # Agent Management
    'AgentManager',
    'create_agent_manager',
    
    # Communication
    'CommunicationManager',
    'create_communication_manager',
    
    # Error Handling
    'ErrorHandler',
    'Error',
    'ErrorCode',
    'ErrorCategory',
    'ErrorLevel',
    'create_error_handler'
]