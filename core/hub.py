"""
Core Hub Module for Benton County Assessor's Office AI Platform

This module implements the Core Hub that serves as the central orchestrator
for the AI platform, managing configurations, system-wide directives,
shared resources, and integration of agent responses.
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
from .message import Message, CommandMessage, ResponseMessage, ErrorMessage, StatusUpdateMessage, EventType, Priority
from .experience import Experience, create_replay_buffer
from .logging import LogManager, ContextAdapter, create_log_manager, create_logger

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False


class CoreHub:
    """
    Core Hub for the AI platform.
    
    This class serves as the central orchestrator for the AI platform,
    managing configurations, system-wide directives, shared resources,
    and integration of agent responses.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the Core Hub.
        
        Args:
            config_path: Path to configuration file
        """
        # Load configuration
        self.config = CoreConfig(config_path)
        
        # Set up logging
        log_config = self.config.get_logging_config()
        self.log_manager = create_log_manager(log_config)
        
        # Create main logger with context
        self.logger = create_logger("core_hub", {
            "component": "CoreHub",
            "version": self.config.get("core.version", "3.0.0")
        })
        
        # Message handlers by event type
        self.message_handlers = {
            EventType.COMMAND: self._handle_command,
            EventType.EVENT: self._handle_event,
            EventType.QUERY: self._handle_query,
            EventType.RESPONSE: self._handle_response,
            EventType.ERROR: self._handle_error,
            EventType.STATUS_UPDATE: self._handle_status_update,
            EventType.ASSISTANCE_REQUESTED: self._handle_assistance_request
        }
        
        # Additional message handlers by topic/channel
        self.topic_handlers = {}
        
        # Registered agents
        self.registered_agents = {}
        
        # Message queue for processing
        self.message_queue = []
        
        # Running flag
        self.running = False
        
        # Start time
        self.start_time = time.time()
        
        # Processing thread
        self.processing_thread = None
        
        # Event loop for async operations
        self.loop = None
        
        # Replay buffer
        self.replay_buffer = create_replay_buffer(self.config.get_replay_buffer_config())
        
        # Communication client
        self.comm_client = None
        
        # Initialize communication
        self._init_communication()
        
        # Last master prompt refresh time
        self.last_prompt_refresh = time.time()
        
        # Data directory for persistence
        self.data_dir = self.config.get("core.data_dir", "data/core")
        os.makedirs(self.data_dir, exist_ok=True)
        
        # State persistence file
        self.state_file = os.path.join(self.data_dir, "core_hub_state.json")
        
        # Load persisted state if available
        self._load_state()
    
    def _init_communication(self) -> None:
        """Initialize communication protocol."""
        comm_config = self.config.get_communication_config()
        protocol = comm_config.get("protocol")
        settings = comm_config.get("settings", {})
        
        if protocol == "redis":
            self._init_redis(settings)
        elif protocol == "mqtt":
            self._init_mqtt(settings)
        elif protocol == "rest":
            self._init_rest(settings)
        else:
            self.logger.warning(f"Unsupported communication protocol: {protocol}")
    
    def _init_redis(self, settings: Dict[str, Any]) -> None:
        """
        Initialize Redis communication.
        
        Args:
            settings: Redis connection settings
        """
        if not REDIS_AVAILABLE:
            self.logger.error("Redis package is not available. Install it with 'pip install redis'.")
            return
        
        try:
            # Connect to Redis
            self.comm_client = redis.Redis(
                host=settings.get("host", "localhost"),
                port=settings.get("port", 6379),
                db=settings.get("db", 0),
                password=settings.get("password")
            )
            
            # Test connection
            self.comm_client.ping()
            
            # Get channel configuration
            channels = settings.get("channels", {})
            
            # Initialize PubSub
            self.pubsub = self.comm_client.pubsub()
            
            # Subscribe to channels
            for channel_name, channel in channels.items():
                self.pubsub.subscribe(channel)
            
            self.logger.info(f"Connected to Redis at {settings.get('host')}:{settings.get('port')}")
        
        except Exception as e:
            self.logger.error(f"Error connecting to Redis: {e}")
            self.comm_client = None
    
    def _init_mqtt(self, settings: Dict[str, Any]) -> None:
        """
        Initialize MQTT communication.
        
        Args:
            settings: MQTT connection settings
        """
        if not MQTT_AVAILABLE:
            self.logger.error("MQTT package is not available. Install it with 'pip install paho-mqtt'.")
            return
        
        try:
            # Create MQTT client
            client_id = f"core_hub_{int(time.time())}"
            self.comm_client = mqtt.Client(client_id)
            
            # Set username and password if provided
            username = settings.get("username")
            password = settings.get("password")
            if username and password:
                self.comm_client.username_pw_set(username, password)
            
            # Set callbacks
            self.comm_client.on_connect = self._on_mqtt_connect
            self.comm_client.on_message = self._on_mqtt_message
            self.comm_client.on_disconnect = self._on_mqtt_disconnect
            
            # Connect to broker
            broker = settings.get("broker", "localhost")
            port = settings.get("port", 1883)
            self.comm_client.connect(broker, port)
            
            # Start loop
            self.comm_client.loop_start()
            
            self.logger.info(f"Connected to MQTT broker at {broker}:{port}")
        
        except Exception as e:
            self.logger.error(f"Error connecting to MQTT broker: {e}")
            self.comm_client = None
    
    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """Callback for when the client connects to the MQTT broker."""
        if rc == 0:
            self.logger.info("Connected to MQTT broker")
            
            # Subscribe to topics
            topics = self.config.get("communication", {}).get("mqtt", {}).get("topics", {})
            for topic_name, topic in topics.items():
                client.subscribe(topic)
                self.logger.info(f"Subscribed to topic: {topic}")
        else:
            self.logger.error(f"Failed to connect to MQTT broker: {rc}")
    
    def _on_mqtt_message(self, client, userdata, msg):
        """Callback for when a message is received from the MQTT broker."""
        try:
            # Decode message
            payload_str = msg.payload.decode("utf-8")
            
            # Parse as JSON
            payload = json.loads(payload_str)
            
            # Create message
            message = Message.from_dict(payload)
            
            # Add to message queue
            self.message_queue.append(message)
        
        except Exception as e:
            self.logger.error(f"Error processing MQTT message: {e}")
    
    def _on_mqtt_disconnect(self, client, userdata, rc):
        """Callback for when the client disconnects from the MQTT broker."""
        if rc != 0:
            self.logger.warning(f"Unexpected disconnection from MQTT broker: {rc}")
    
    def _init_rest(self, settings: Dict[str, Any]) -> None:
        """
        Initialize REST communication.
        
        Args:
            settings: REST API settings
        """
        # REST communication is handled through FastAPI/Flask, not here
        pass
    
    def start(self) -> None:
        """Start the Core Hub."""
        if self.running:
            self.logger.warning("Core Hub is already running")
            return
        
        self.running = True
        
        # Start processing thread
        self.processing_thread = threading.Thread(target=self._processing_loop)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        
        # Start event loop thread for async operations
        loop_thread = threading.Thread(target=self._start_event_loop)
        loop_thread.daemon = True
        loop_thread.start()
        
        self.logger.info("Core Hub started")
        
        # Broadcast master prompt
        self._broadcast_master_prompt()
    
    def _start_event_loop(self) -> None:
        """Start the event loop for async operations."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()
    
    def force_save_state(self) -> bool:
        """
        Force saving the Core Hub state immediately.
        
        Returns:
            True if successful, False otherwise
        """
        return self._save_state()
        
    def stop(self) -> None:
        """Stop the Core Hub."""
        if not self.running:
            self.logger.warning("Core Hub is not running")
            return
        
        # Save state before shutting down
        self._save_state()
        
        self.running = False
        
        # Stop the processing thread
        if self.processing_thread:
            self.processing_thread.join(timeout=5.0)
        
        # Stop MQTT client if used
        if self.comm_client and hasattr(self.comm_client, "loop_stop"):
            self.comm_client.loop_stop()
            self.comm_client.disconnect()
        
        # Stop event loop
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
        
        self.logger.info("Core Hub stopped")
    
    def _processing_loop(self) -> None:
        """Main processing loop for the Core Hub."""
        while self.running:
            # Process messages in the queue
            self._process_messages()
            
            # Refresh master prompt if needed
            self._check_master_prompt_refresh()
            
            # Sleep for a bit
            time.sleep(0.01)
    
    def _process_messages(self) -> None:
        """Process messages in the queue."""
        # Check if there are messages
        if not self.message_queue:
            return
        
        # Get all messages from the queue
        messages = self.message_queue
        self.message_queue = []
        
        # Process each message
        for message in messages:
            try:
                # Check if message is expired
                if hasattr(message, "is_expired") and message.is_expired():
                    self.logger.warning(f"Skipping expired message: {message.message_id}")
                    continue
                
                # Get handler for message type
                event_type = message.event_type
                handler = self.message_handlers.get(event_type)
                
                if handler:
                    # Call handler
                    handler(message)
                else:
                    self.logger.warning(f"No handler for message type: {event_type}")
            
            except Exception as e:
                self.logger.error(f"Error processing message {message.message_id}: {e}")
    
    def _handle_command(self, message: Message) -> None:
        """
        Handle a command message.
        
        Args:
            message: Command message
        """
        # Check if target agent is registered
        target_agent_id = message.target_agent_id
        if target_agent_id not in self.registered_agents:
            self.logger.warning(f"Target agent {target_agent_id} not registered")
            
            # Send error response
            self.send_message(
                ErrorMessage(
                    source_agent_id="core_hub",
                    target_agent_id=message.source_agent_id,
                    error_code="AGENT_NOT_FOUND",
                    error_message=f"Target agent {target_agent_id} not registered",
                    original_message_id=message.message_id,
                    correlation_id=message.correlation_id
                )
            )
            return
        
        # Route command to target agent
        self._route_message(message)
    
    def _handle_event(self, message: Message) -> None:
        """
        Handle an event message.
        
        Args:
            message: Event message
        """
        # Route event to interested agents
        self._route_message(message)
    
    def _handle_query(self, message: Message) -> None:
        """
        Handle a query message.
        
        Args:
            message: Query message
        """
        # Check if target agent is registered
        target_agent_id = message.target_agent_id
        if target_agent_id not in self.registered_agents:
            self.logger.warning(f"Target agent {target_agent_id} not registered")
            
            # Send error response
            self.send_message(
                ErrorMessage(
                    source_agent_id="core_hub",
                    target_agent_id=message.source_agent_id,
                    error_code="AGENT_NOT_FOUND",
                    error_message=f"Target agent {target_agent_id} not registered",
                    original_message_id=message.message_id,
                    correlation_id=message.correlation_id
                )
            )
            return
        
        # Route query to target agent
        self._route_message(message)
    
    def _handle_response(self, message: Message) -> None:
        """
        Handle a response message.
        
        Args:
            message: Response message
        """
        # Route response to target agent
        self._route_message(message)
    
    def _handle_error(self, message: Message) -> None:
        """
        Handle an error message.
        
        Args:
            message: Error message
        """
        # Log the error
        self.logger.error(f"Error from {message.source_agent_id}: {message.payload.get('error_code')} - {message.payload.get('error_message')}")
        
        # Route error to target agent
        self._route_message(message)
    
    def _handle_status_update(self, message: Message) -> None:
        """
        Handle a status update message.
        
        Args:
            message: Status update message
        """
        # Update agent status
        agent_id = message.source_agent_id
        status = message.payload.get("status")
        metrics = message.payload.get("metrics", {})
        
        if agent_id in self.registered_agents:
            self.registered_agents[agent_id]["status"] = status
            self.registered_agents[agent_id]["metrics"] = metrics
            self.registered_agents[agent_id]["last_update"] = time.time()
            
            # Save state periodically when handling status updates
            # Only save on significant status changes or every 15 status updates to avoid excessive I/O
            significant_status = status in ["terminated", "error", "restarting"]
            status_update_count = self.registered_agents[agent_id].get("status_update_count", 0) + 1
            self.registered_agents[agent_id]["status_update_count"] = status_update_count
            
            if significant_status or status_update_count % 15 == 0:
                self._save_state()
        
        # Route status update to target agent
        self._route_message(message)
    
    def _handle_assistance_request(self, message: Message) -> None:
        """
        Handle an assistance request message.
        
        Args:
            message: Assistance request message
        """
        # Log the request
        self.logger.info(f"Assistance request from {message.source_agent_id}: {message.payload.get('assistance_type')}")
        
        # Record in the replay buffer
        self._record_assistance_request(message)
        
        # Route assistance request to target agent
        self._route_message(message)
    
    def _record_assistance_request(self, message: Message) -> None:
        """
        Record an assistance request in the replay buffer.
        
        Args:
            message: Assistance request message
        """
        try:
            # Create experience
            experience = Experience(
                agent_id=message.source_agent_id,
                state={"message_type": "assistance_request"},
                action={"assistance_type": message.payload.get("assistance_type")},
                result={"status": "pending"},
                next_state={"message_type": "assistance_request_pending"},
                metadata={
                    "priority": 1.5,  # Higher priority for assistance requests
                    "message_id": message.message_id,
                    "correlation_id": message.correlation_id,
                    "timestamp": time.time()
                }
            )
            
            # Add to replay buffer
            self.replay_buffer.add(experience)
            
            # Save state after recording assistance request
            # These are important events that should be persisted
            self._save_state()
        
        except Exception as e:
            self.logger.error(f"Error recording assistance request: {e}")
            
    def record_assistance_response(self, request_message_id: str, response: Dict[str, Any], success: bool = True) -> None:
        """
        Record a response to an assistance request in the replay buffer.
        
        Args:
            request_message_id: ID of the original assistance request message
            response: Response data
            success: Whether the assistance was successful
        """
        try:
            # Find experiences in replay buffer with matching message_id
            # This would be more efficient with a database-backed replay buffer
            # For now, we'll add a new experience with a reference to the original
            
            experience = Experience(
                agent_id="core_hub",
                state={"message_type": "assistance_response"},
                action={"response_to": request_message_id},
                result={"success": success, "data": response},
                next_state={"message_type": "assistance_completed"},
                metadata={
                    "priority": 1.0,
                    "original_message_id": request_message_id,
                    "timestamp": time.time()
                }
            )
            
            # Add to replay buffer
            self.replay_buffer.add(experience)
            
            # Save state after recording assistance response
            self._save_state()
            
            self.logger.info(f"Recorded response to assistance request {request_message_id}")
        
        except Exception as e:
            self.logger.error(f"Error recording assistance response: {e}")
    
    def _route_message(self, message: Message) -> None:
        """
        Route a message to its target agent.
        
        Args:
            message: Message to route
        """
        # Check if target is "broadcast"
        if message.target_agent_id == "broadcast":
            self._broadcast_message(message)
            return
        
        # Get communication protocol
        protocol = self.config.get("communication", {}).get("protocol")
        
        if protocol == "redis":
            self._route_redis_message(message)
        elif protocol == "mqtt":
            self._route_mqtt_message(message)
        elif protocol == "rest":
            self._route_rest_message(message)
        else:
            self.logger.warning(f"Unsupported communication protocol: {protocol}")
    
    def _route_redis_message(self, message: Message) -> None:
        """
        Route a message using Redis.
        
        Args:
            message: Message to route
        """
        if not self.comm_client:
            self.logger.error("Redis client not initialized")
            return
        
        try:
            # Get target channel
            target_agent_id = message.target_agent_id
            channels = self.config.get("communication", {}).get("redis", {}).get("channels", {})
            
            # Determine channel based on message type
            channel_map = {
                EventType.COMMAND: channels.get("commands"),
                EventType.EVENT: channels.get("events"),
                EventType.QUERY: channels.get("commands"),
                EventType.RESPONSE: channels.get("events"),
                EventType.ERROR: channels.get("errors"),
                EventType.STATUS_UPDATE: channels.get("status"),
                EventType.ASSISTANCE_REQUESTED: channels.get("commands")
            }
            
            channel = channel_map.get(message.event_type)
            
            if not channel:
                self.logger.warning(f"No channel defined for message type: {message.event_type}")
                return
            
            # Publish message
            self.comm_client.publish(
                channel,
                message.to_json()
            )
        
        except Exception as e:
            self.logger.error(f"Error routing Redis message: {e}")
    
    def _route_mqtt_message(self, message: Message) -> None:
        """
        Route a message using MQTT.
        
        Args:
            message: Message to route
        """
        if not self.comm_client or not hasattr(self.comm_client, "publish"):
            self.logger.error("MQTT client not initialized")
            return
        
        try:
            # Get target topic
            target_agent_id = message.target_agent_id
            topics = self.config.get("communication", {}).get("mqtt", {}).get("topics", {})
            
            # Determine topic based on message type
            topic_map = {
                EventType.COMMAND: topics.get("commands"),
                EventType.EVENT: topics.get("events"),
                EventType.QUERY: topics.get("commands"),
                EventType.RESPONSE: topics.get("events"),
                EventType.ERROR: topics.get("errors"),
                EventType.STATUS_UPDATE: topics.get("status"),
                EventType.ASSISTANCE_REQUESTED: topics.get("commands")
            }
            
            topic = topic_map.get(message.event_type)
            
            if not topic:
                self.logger.warning(f"No topic defined for message type: {message.event_type}")
                return
            
            # Publish message
            self.comm_client.publish(
                topic,
                message.to_json()
            )
        
        except Exception as e:
            self.logger.error(f"Error routing MQTT message: {e}")
    
    def _route_rest_message(self, message: Message) -> None:
        """
        Route a message using REST.
        
        Args:
            message: Message to route
        """
        # REST routing is handled through FastAPI/Flask, not here
        pass
    
    def _broadcast_message(self, message: Message) -> None:
        """
        Broadcast a message to all agents.
        
        Args:
            message: Message to broadcast
        """
        # Get communication protocol
        protocol = self.config.get("communication", {}).get("protocol")
        
        if protocol == "redis":
            self._broadcast_redis_message(message)
        elif protocol == "mqtt":
            self._broadcast_mqtt_message(message)
        elif protocol == "rest":
            self._broadcast_rest_message(message)
        else:
            self.logger.warning(f"Unsupported communication protocol: {protocol}")
    
    def _broadcast_redis_message(self, message: Message) -> None:
        """
        Broadcast a message using Redis.
        
        Args:
            message: Message to broadcast
        """
        if not self.comm_client:
            self.logger.error("Redis client not initialized")
            return
        
        try:
            # Get channels
            channels = self.config.get("communication", {}).get("redis", {}).get("channels", {})
            
            # Determine channel based on message type
            channel_map = {
                EventType.COMMAND: channels.get("commands"),
                EventType.EVENT: channels.get("events"),
                EventType.QUERY: channels.get("commands"),
                EventType.RESPONSE: channels.get("events"),
                EventType.ERROR: channels.get("errors"),
                EventType.STATUS_UPDATE: channels.get("status"),
                EventType.ASSISTANCE_REQUESTED: channels.get("commands")
            }
            
            channel = channel_map.get(message.event_type)
            
            if not channel:
                self.logger.warning(f"No channel defined for message type: {message.event_type}")
                return
            
            # Publish message
            self.comm_client.publish(
                channel,
                message.to_json()
            )
        
        except Exception as e:
            self.logger.error(f"Error broadcasting Redis message: {e}")
    
    def _broadcast_mqtt_message(self, message: Message) -> None:
        """
        Broadcast a message using MQTT.
        
        Args:
            message: Message to broadcast
        """
        if not self.comm_client or not hasattr(self.comm_client, "publish"):
            self.logger.error("MQTT client not initialized")
            return
        
        try:
            # Get topics
            topics = self.config.get("communication", {}).get("mqtt", {}).get("topics", {})
            
            # Determine topic based on message type
            topic_map = {
                EventType.COMMAND: topics.get("commands"),
                EventType.EVENT: topics.get("events"),
                EventType.QUERY: topics.get("commands"),
                EventType.RESPONSE: topics.get("events"),
                EventType.ERROR: topics.get("errors"),
                EventType.STATUS_UPDATE: topics.get("status"),
                EventType.ASSISTANCE_REQUESTED: topics.get("commands")
            }
            
            topic = topic_map.get(message.event_type)
            
            if not topic:
                self.logger.warning(f"No topic defined for message type: {message.event_type}")
                return
            
            # Publish message
            self.comm_client.publish(
                topic,
                message.to_json()
            )
        
        except Exception as e:
            self.logger.error(f"Error broadcasting MQTT message: {e}")
    
    def _broadcast_rest_message(self, message: Message) -> None:
        """
        Broadcast a message using REST.
        
        Args:
            message: Message to broadcast
        """
        # REST broadcasting is handled through FastAPI/Flask, not here
        pass
    
    def send_message(self, message: Message) -> None:
        """
        Send a message.
        
        Args:
            message: Message to send
        """
        # Route message to target
        self._route_message(message)
    
    def _broadcast_master_prompt(self) -> None:
        """Broadcast the master prompt to all agents."""
        try:
            # Get master prompt
            master_prompt = self.config.get_master_prompt()
            
            # Create command message
            message = CommandMessage(
                source_agent_id="core_hub",
                target_agent_id="broadcast",
                command_name="update_master_prompt",
                parameters={"prompt": master_prompt}
            )
            
            # Broadcast message
            self._broadcast_message(message)
            
            # Update last refresh time
            self.last_prompt_refresh = time.time()
            
            self.logger.info("Master prompt broadcasted to all agents")
        
        except Exception as e:
            self.logger.error(f"Error broadcasting master prompt: {e}")
    
    def _check_master_prompt_refresh(self) -> None:
        """Check if master prompt needs to be refreshed."""
        # Get refresh interval
        refresh_interval = self.config.get("core", {}).get("master_prompt_refresh_interval", 3600)
        
        # Check if it's time to refresh
        if time.time() - self.last_prompt_refresh > refresh_interval:
            self._broadcast_master_prompt()
    
    def _save_state(self) -> bool:
        """
        Save the Core Hub state to a file.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create state object
            state = {
                "registered_agents": self.registered_agents,
                "last_prompt_refresh": self.last_prompt_refresh,
                "start_time": self.start_time,
                "version": self.config.get("core.version", "3.0.0"),
                "saved_at": time.time(),
                "agent_metrics": {
                    agent_id: agent.get("metrics", {})
                    for agent_id, agent in self.registered_agents.items()
                }
            }
            
            # Save to file
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
            
            self.logger.info(f"Core Hub state saved to {self.state_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving Core Hub state: {e}")
            return False
    
    def _load_state(self) -> bool:
        """
        Load the Core Hub state from a file.
        
        Returns:
            True if successful, False otherwise
        """
        if not os.path.exists(self.state_file):
            self.logger.info(f"No saved state found at {self.state_file}")
            return False
        
        try:
            # Load from file
            with open(self.state_file, 'r') as f:
                state = json.load(f)
            
            # Restore registered agents
            if "registered_agents" in state:
                self.registered_agents = state["registered_agents"]
            
            # Restore other state variables
            if "last_prompt_refresh" in state:
                self.last_prompt_refresh = state["last_prompt_refresh"]
            
            self.logger.info(f"Core Hub state loaded from {self.state_file}")
            self.logger.info(f"Restored {len(self.registered_agents)} registered agents")
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading Core Hub state: {e}")
            return False
    
    def register_agent(self, agent_id: str, agent_info: Dict[str, Any]) -> bool:
        """
        Register an agent with the Core Hub.
        
        Args:
            agent_id: Unique identifier for the agent
            agent_info: Information about the agent
            
        Returns:
            True if registration successful, False otherwise
        """
        if agent_id in self.registered_agents:
            self.logger.warning(f"Agent {agent_id} already registered")
            return False
        
        # Add agent to registry
        self.registered_agents[agent_id] = {
            **agent_info,
            "registered_at": time.time(),
            "last_update": time.time(),
            "status": "active"
        }
        
        self.logger.info(f"Agent {agent_id} registered: {agent_info.get('type', 'unknown')}")
        
        # Save state after registering a new agent
        self._save_state()
        
        # Send master prompt to the new agent
        try:
            # Get master prompt
            master_prompt = self.config.get_master_prompt()
            
            # Create command message
            message = CommandMessage(
                source_agent_id="core_hub",
                target_agent_id=agent_id,
                command_name="update_master_prompt",
                parameters={"prompt": master_prompt}
            )
            
            # Send message
            self.send_message(message)
        
        except Exception as e:
            self.logger.error(f"Error sending master prompt to new agent {agent_id}: {e}")
        
        return True
    
    def deregister_agent(self, agent_id: str) -> bool:
        """
        Deregister an agent from the Core Hub.
        
        Args:
            agent_id: Unique identifier for the agent
            
        Returns:
            True if deregistration successful, False otherwise
        """
        if agent_id not in self.registered_agents:
            self.logger.warning(f"Agent {agent_id} not registered")
            return False
        
        # Remove agent from registry
        agent_info = self.registered_agents.pop(agent_id)
        
        self.logger.info(f"Agent {agent_id} deregistered: {agent_info.get('type', 'unknown')}")
        
        # Save state after deregistering an agent
        self._save_state()
        
        return True
    
    def get_agent_info(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a registered agent.
        
        Args:
            agent_id: Unique identifier for the agent
            
        Returns:
            Agent information or None if not registered
        """
        return self.registered_agents.get(agent_id)
    
    def get_registered_agents(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all registered agents.
        
        Returns:
            Dictionary mapping agent IDs to agent information
        """
        return self.registered_agents.copy()
    
    def register_topic_handler(self, topic: str, handler: Callable[[Message], None]) -> None:
        """
        Register a handler for a specific topic/channel.
        
        Args:
            topic: Topic or channel name
            handler: Function to call when a message is received on the topic
        """
        self.topic_handlers[topic] = handler
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        Get the status of the Core Hub system.
        
        Returns:
            System status information
        """
        return {
            "core": {
                "name": self.config.get("core", {}).get("name"),
                "version": self.config.get("core", {}).get("version"),
                "uptime": time.time() - self.start_time if hasattr(self, "start_time") else 0,
                "message_queue_size": len(self.message_queue)
            },
            "agents": {
                "registered": len(self.registered_agents),
                "active": sum(1 for info in self.registered_agents.values() if info.get("status") == "active"),
                "list": [
                    {
                        "id": agent_id,
                        "type": info.get("type"),
                        "status": info.get("status"),
                        "registered_at": info.get("registered_at"),
                        "last_update": info.get("last_update")
                    }
                    for agent_id, info in self.registered_agents.items()
                ]
            },
            "replay_buffer": self.replay_buffer.get_stats()
        }