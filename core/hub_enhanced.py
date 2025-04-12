"""
Enhanced Core Hub Module for Benton County Assessor's Office AI Platform

This module implements the enhanced Core Hub that serves as the central orchestrator
for the AI platform, with improved component architecture, error handling,
agent management, and communication protocols.
"""

import os
import json
import time
import logging
import threading
import asyncio
from typing import Dict, Any, List, Optional, Callable, Union
from datetime import datetime

from .config import CoreConfig
from .logging import create_logger
from .message import Message, CommandMessage, ResponseMessage, ErrorMessage, StatusUpdateMessage, EventType, Priority
from .experience import Experience, create_replay_buffer
from .agent_manager import AgentManager, create_agent_manager
from .communication import CommunicationManager, create_communication_manager
from .error_handler import ErrorHandler, Error, ErrorCode, ErrorCategory, ErrorLevel, create_error_handler


class CoreHubEnhanced:
    """
    Enhanced Core Hub for the AI platform.
    
    This class serves as the central orchestrator for the AI platform,
    with improved component architecture, error handling, agent management,
    and communication protocols.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the Enhanced Core Hub.
        
        Args:
            config_path: Path to configuration file
        """
        # Load configuration
        self.config = CoreConfig(config_path)
        
        # Data directory for persistence
        self.data_dir = self.config.get("core.data_dir", "data/core")
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Set up logging
        log_config = self.config.get_logging_config()
        
        # Create main logger with context
        self.logger = create_logger("core_hub_enhanced", {
            "component": "CoreHubEnhanced",
            "version": self.config.get("core.version", "3.0.0")
        })
        
        # Running flag
        self.running = False
        
        # Start time
        self.start_time = time.time()
        
        # Processing thread
        self.processing_thread = None
        
        # Event loop for async operations
        self.loop = None
        
        # Initialize error handler
        error_config = self.config.get("error_handler", {})
        self.error_handler = create_error_handler(error_config, self.data_dir)
        
        # Initialize agent manager
        agent_config = self.config.get("agent_manager", {})
        self.agent_manager = create_agent_manager(agent_config, self.data_dir)
        
        # Initialize communication manager
        comm_config = self.config.get_communication_config()
        self.comm_manager = create_communication_manager(comm_config)
        
        # Register error handler for communication errors
        self.error_handler.register_handler(
            self._handle_communication_error,
            key=ErrorCategory.COMMUNICATION
        )
        
        # Initialize replay buffer
        self.replay_buffer = create_replay_buffer(self.config.get_replay_buffer_config())
        
        # Last master prompt refresh time
        self.last_prompt_refresh = time.time()
        
        # Register message handlers
        self._register_message_handlers()
        
        self.logger.info("Enhanced Core Hub initialized")
    
    def _register_message_handlers(self) -> None:
        """Register message handlers with the communication manager."""
        # Register handlers for different event types
        self.comm_manager.register_topic_handler("command", self._handle_command_message)
        self.comm_manager.register_topic_handler("event", self._handle_event_message)
        self.comm_manager.register_topic_handler("query", self._handle_query_message)
        self.comm_manager.register_topic_handler("response", self._handle_response_message)
        self.comm_manager.register_topic_handler("error", self._handle_error_message)
        self.comm_manager.register_topic_handler("status_update", self._handle_status_update_message)
        self.comm_manager.register_topic_handler("assistance_request", self._handle_assistance_request_message)
    
    def _handle_communication_error(self, error: Error) -> None:
        """
        Handle communication errors.
        
        Args:
            error: Communication error
        """
        self.logger.warning(f"Communication error: {error.message}")
        
        # Attempt recovery based on error code
        if error.code == ErrorCode.COMMUNICATION_FAILURE:
            # Restart communication manager
            self.logger.info("Attempting to restart communication manager")
            self.comm_manager.stop()
            time.sleep(1)
            self.comm_manager.start()
    
    def start(self) -> None:
        """Start the Enhanced Core Hub."""
        if self.running:
            self.logger.warning("Enhanced Core Hub is already running")
            return
        
        self.running = True
        
        # Start communication manager
        self.comm_manager.start()
        
        # Start processing thread
        self.processing_thread = threading.Thread(target=self._processing_loop)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        
        # Start event loop thread for async operations
        loop_thread = threading.Thread(target=self._start_event_loop)
        loop_thread.daemon = True
        loop_thread.start()
        
        self.logger.info("Enhanced Core Hub started")
        
        # Broadcast master prompt
        self._broadcast_master_prompt()
    
    def _start_event_loop(self) -> None:
        """Start the event loop for async operations."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()
    
    def force_save_state(self) -> bool:
        """
        Force saving the Enhanced Core Hub state immediately.
        
        Returns:
            True if successful, False otherwise
        """
        # No need to explicitly save state since component managers handle this
        return True
    
    def stop(self) -> None:
        """Stop the Enhanced Core Hub."""
        if not self.running:
            self.logger.warning("Enhanced Core Hub is not running")
            return
        
        self.running = False
        
        # Stop the processing thread
        if self.processing_thread:
            self.processing_thread.join(timeout=5.0)
        
        # Stop communication manager
        self.comm_manager.stop()
        
        # Stop event loop
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
        
        self.logger.info("Enhanced Core Hub stopped")
    
    def _processing_loop(self) -> None:
        """Main processing loop for the Enhanced Core Hub."""
        while self.running:
            # Check agent health
            self.agent_manager.check_agent_health()
            
            # Check for missing dependencies
            dependencies = self.agent_manager.check_dependencies()
            if dependencies:
                for agent_id, missing in dependencies.items():
                    self.logger.warning(f"Agent {agent_id} missing dependencies: {missing}")
            
            # Refresh master prompt if needed
            self._check_master_prompt_refresh()
            
            # Clean expired message callbacks
            self.comm_manager.clean_expired_callbacks()
            
            # Sleep for a bit
            time.sleep(0.5)
    
    def _handle_command_message(self, message: Message) -> None:
        """
        Handle a command message.
        
        Args:
            message: Command message
        """
        # Check if target agent is registered
        target_agent_id = message.target_agent_id
        agent_info = self.agent_manager.get_agent_info(target_agent_id)
        
        if not agent_info:
            self.logger.warning(f"Target agent {target_agent_id} not registered")
            
            # Send error response
            error_message = ErrorMessage(
                source_agent_id="core_hub",
                target_agent_id=message.source_agent_id,
                error_code=ErrorCode.RESOURCE_NOT_FOUND,
                error_message=f"Target agent {target_agent_id} not registered",
                original_message_id=message.message_id,
                correlation_id=message.correlation_id
            )
            
            self.send_message(error_message)
            return
        
        # Route command to target agent
        self.send_message(message)
    
    def _handle_event_message(self, message: Message) -> None:
        """
        Handle an event message.
        
        Args:
            message: Event message
        """
        # Get agents subscribed to this event
        event_type = message.event_type
        
        # Broadcast event to interested agents
        self.broadcast_message(message)
    
    def _handle_query_message(self, message: Message) -> None:
        """
        Handle a query message.
        
        Args:
            message: Query message
        """
        # Check if target agent is registered
        target_agent_id = message.target_agent_id
        agent_info = self.agent_manager.get_agent_info(target_agent_id)
        
        if not agent_info:
            self.logger.warning(f"Target agent {target_agent_id} not registered")
            
            # Send error response
            error_message = ErrorMessage(
                source_agent_id="core_hub",
                target_agent_id=message.source_agent_id,
                error_code=ErrorCode.RESOURCE_NOT_FOUND,
                error_message=f"Target agent {target_agent_id} not registered",
                original_message_id=message.message_id,
                correlation_id=message.correlation_id
            )
            
            self.send_message(error_message)
            return
        
        # Route query to target agent
        self.send_message(message)
    
    def _handle_response_message(self, message: Message) -> None:
        """
        Handle a response message.
        
        Args:
            message: Response message
        """
        # Route response to target agent
        self.send_message(message)
        
        # If it's a response to an assistance request, record it
        if message.original_message_id and message.original_message_id in self.replay_buffer.get_experience_ids():
            self.record_assistance_response(
                message.original_message_id,
                message.payload,
                True  # Assume success for now
            )
    
    def _handle_error_message(self, message: Message) -> None:
        """
        Handle an error message.
        
        Args:
            message: Error message
        """
        # Log the error
        error = Error(
            code=message.payload.get("error_code"),
            message=message.payload.get("error_message"),
            level=message.payload.get("level", ErrorLevel.ERROR),
            category=message.payload.get("category", ErrorCategory.UNKNOWN),
            details=message.payload.get("details"),
            source=message.source_agent_id,
            timestamp=message.payload.get("timestamp", time.time())
        )
        
        self.error_handler.handle_error(error)
        
        # Route error to target agent
        self.send_message(message)
    
    def _handle_status_update_message(self, message: Message) -> None:
        """
        Handle a status update message.
        
        Args:
            message: Status update message
        """
        # Update agent status
        agent_id = message.source_agent_id
        status = message.payload.get("status")
        metrics = message.payload.get("metrics", {})
        
        self.agent_manager.update_agent_status(agent_id, status, metrics)
    
    def _handle_assistance_request_message(self, message: Message) -> None:
        """
        Handle an assistance request message.
        
        Args:
            message: Assistance request message
        """
        # Record the assistance request in the replay buffer
        self._record_assistance_request(message)
        
        # Find capable agents for the request
        capability = message.payload.get("capability")
        if capability:
            capable_agents = self.agent_manager.get_agents_by_capability(capability)
            
            if capable_agents:
                # Route to the first capable agent
                message.target_agent_id = capable_agents[0]
                self.send_message(message)
            else:
                # No capable agents, send error response
                error_message = ErrorMessage(
                    source_agent_id="core_hub",
                    target_agent_id=message.source_agent_id,
                    error_code=ErrorCode.RESOURCE_UNAVAILABLE,
                    error_message=f"No agents capable of handling {capability}",
                    original_message_id=message.message_id,
                    correlation_id=message.correlation_id
                )
                
                self.send_message(error_message)
        else:
            # No capability specified, use target agent
            self.send_message(message)
    
    def _record_assistance_request(self, message: Message) -> None:
        """
        Record an assistance request in the replay buffer.
        
        Args:
            message: Assistance request message
        """
        experience = Experience(
            experience_id=message.message_id,
            agent_id=message.source_agent_id,
            timestamp=time.time(),
            request=message.payload,
            context={
                "message_id": message.message_id,
                "correlation_id": message.correlation_id,
                "target_agent_id": message.target_agent_id,
                "priority": message.priority
            },
            reward=0.5  # Initial reward, will be updated on response
        )
        
        self.replay_buffer.add_experience(experience)
    
    def record_assistance_response(self, request_message_id: str, response: Dict[str, Any], success: bool = True) -> None:
        """
        Record a response to an assistance request in the replay buffer.
        
        Args:
            request_message_id: ID of the original assistance request message
            response: Response data
            success: Whether the assistance was successful
        """
        # Get experience from replay buffer
        experience = self.replay_buffer.get_experience(request_message_id)
        
        if experience:
            # Update experience with response
            experience.response = response
            experience.response_timestamp = time.time()
            experience.reward = 1.0 if success else 0.0
            
            # Update in replay buffer
            self.replay_buffer.update_experience(experience)
            
            self.logger.info(f"Recorded assistance response for {request_message_id}")
    
    def send_message(self, message: Message) -> bool:
        """
        Send a message.
        
        Args:
            message: Message to send
            
        Returns:
            True if sent successfully, False otherwise
        """
        return self.comm_manager.send_message(message)
    
    def broadcast_message(self, message: Message) -> bool:
        """
        Broadcast a message to all agents.
        
        Args:
            message: Message to broadcast
            
        Returns:
            True if broadcast successfully, False otherwise
        """
        return self.comm_manager.broadcast_message(message)
    
    def _broadcast_master_prompt(self) -> None:
        """Broadcast the master prompt to all agents."""
        master_prompt = self.config.get_master_prompt()
        
        if not master_prompt:
            self.logger.warning("Master prompt not configured")
            return
        
        # Create message
        message = CommandMessage(
            source_agent_id="core_hub",
            target_agent_id="broadcast",
            command_name="update_master_prompt",
            parameters={
                "prompt": master_prompt
            }
        )
        
        # Broadcast message
        self.broadcast_message(message)
        
        self.logger.info("Master prompt broadcasted to all agents")
    
    def _check_master_prompt_refresh(self) -> None:
        """Check if master prompt needs to be refreshed."""
        refresh_interval = self.config.get("core.master_prompt_refresh_interval", 3600)
        
        if time.time() - self.last_prompt_refresh > refresh_interval:
            self._broadcast_master_prompt()
            self.last_prompt_refresh = time.time()
    
    def register_agent(self, agent_id: str, agent_info: Dict[str, Any]) -> bool:
        """
        Register an agent with the Enhanced Core Hub.
        
        Args:
            agent_id: Unique identifier for the agent
            agent_info: Information about the agent
            
        Returns:
            True if registration successful, False otherwise
        """
        return self.agent_manager.register_agent(agent_id, agent_info)
    
    def deregister_agent(self, agent_id: str) -> bool:
        """
        Deregister an agent from the Enhanced Core Hub.
        
        Args:
            agent_id: Unique identifier for the agent
            
        Returns:
            True if deregistration successful, False otherwise
        """
        return self.agent_manager.deregister_agent(agent_id)
    
    def get_agent_info(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a registered agent.
        
        Args:
            agent_id: Unique identifier for the agent
            
        Returns:
            Agent information or None if not registered
        """
        return self.agent_manager.get_agent_info(agent_id)
    
    def get_registered_agents(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all registered agents.
        
        Returns:
            Dictionary mapping agent IDs to agent information
        """
        return self.agent_manager.get_registered_agents()
    
    def register_topic_handler(self, topic: str, handler: Callable[[Message], None]) -> None:
        """
        Register a handler for a specific topic/channel.
        
        Args:
            topic: Topic or channel name
            handler: Function to call when a message is received on the topic
        """
        self.comm_manager.register_topic_handler(topic, handler)
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        Get the status of the Enhanced Core Hub system.
        
        Returns:
            System status information
        """
        uptime = time.time() - self.start_time
        
        return {
            "core": {
                "name": self.config.get("core.name", "BentonCountyAssessorCore"),
                "version": self.config.get("core.version", "3.0.0"),
                "uptime": uptime,
                "running": self.running
            },
            "agents": self.agent_manager.get_system_status(),
            "errors": self.error_handler.get_error_summary(),
            "replay_buffer": {
                "size": len(self.replay_buffer),
                "capacity": self.replay_buffer.capacity,
                "average_reward": 0.0  # Placeholder until we implement get_average_reward
            }
        }


def create_core_hub_enhanced(config_path: Optional[str] = None) -> CoreHubEnhanced:
    """
    Create an Enhanced Core Hub with the specified configuration.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Configured Enhanced Core Hub
    """
    return CoreHubEnhanced(config_path)