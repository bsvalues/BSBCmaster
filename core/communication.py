"""
Communication Module for Benton County Assessor's Office AI Platform

This module provides communication capabilities for the Core Hub,
including Redis, MQTT, and REST communication protocols.
"""

import os
import json
import time
import logging
import threading
import asyncio
from typing import Dict, Any, List, Optional, Callable, Union, Set

from .logging import create_logger
from .message import Message


class CommunicationManager:
    """
    Communication Manager for the Core Hub.
    
    This class handles communication between agents and the Core Hub
    using various protocols such as Redis, MQTT, and REST.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Communication Manager.
        
        Args:
            config: Communication configuration
        """
        self.config = config
        self.protocol = config.get("protocol", "memory")
        self.settings = config.get("settings", {})
        self.message_queue = []
        self.message_callbacks = {}
        self.topic_handlers = {}
        self.subscribed_topics = set()
        self.running = False
        self.processing_thread = None
        
        # Create logger
        self.logger = create_logger("communication", {
            "component": "CommunicationManager",
            "protocol": self.protocol
        })
        
        # Initialize communication client
        self.comm_client = None
        self._init_communication()
        
        self.logger.info(f"Communication Manager initialized with protocol {self.protocol}")
    
    def _init_communication(self) -> None:
        """Initialize communication protocol."""
        if self.protocol == "redis":
            self._init_redis()
        elif self.protocol == "mqtt":
            self._init_mqtt()
        elif self.protocol == "rest":
            self._init_rest()
        elif self.protocol == "memory":
            self._init_memory()
        else:
            self.logger.warning(f"Unsupported communication protocol: {self.protocol}")
    
    def _init_redis(self) -> None:
        """Initialize Redis communication."""
        try:
            # Try to import Redis
            import redis
            
            # Connect to Redis
            self.comm_client = redis.Redis(
                host=self.settings.get("host", "localhost"),
                port=self.settings.get("port", 6379),
                db=self.settings.get("db", 0),
                password=self.settings.get("password")
            )
            
            # Test connection
            self.comm_client.ping()
            
            # Initialize PubSub
            self.pubsub = self.comm_client.pubsub(ignore_subscribe_messages=True)
            
            # Subscribe to channels
            self.channels = self.settings.get("channels", {})
            for channel_name, channel in self.channels.items():
                self.pubsub.subscribe(channel)
                self.subscribed_topics.add(channel)
            
            self.logger.info(f"Connected to Redis at {self.settings.get('host')}:{self.settings.get('port')}")
            
        except ImportError:
            self.logger.error("Redis package is not available. Install it with 'pip install redis'.")
            self.protocol = "memory"
            self._init_memory()
            
        except Exception as e:
            self.logger.error(f"Error connecting to Redis: {e}")
            self.protocol = "memory"
            self._init_memory()
    
    def _init_mqtt(self) -> None:
        """Initialize MQTT communication."""
        try:
            # Try to import MQTT
            import paho.mqtt.client as mqtt
            
            # Create MQTT client
            client_id = f"core_hub_{int(time.time())}"
            self.comm_client = mqtt.Client(client_id)
            
            # Set username and password if provided
            username = self.settings.get("username")
            password = self.settings.get("password")
            if username and password:
                self.comm_client.username_pw_set(username, password)
            
            # Set callbacks
            self.comm_client.on_connect = self._on_mqtt_connect
            self.comm_client.on_message = self._on_mqtt_message
            self.comm_client.on_disconnect = self._on_mqtt_disconnect
            
            # Connect to broker
            broker = self.settings.get("broker", "localhost")
            port = self.settings.get("port", 1883)
            self.comm_client.connect(broker, port)
            
            # Start loop
            self.comm_client.loop_start()
            
            self.logger.info(f"Connected to MQTT broker at {broker}:{port}")
            
        except ImportError:
            self.logger.error("MQTT package is not available. Install it with 'pip install paho-mqtt'.")
            self.protocol = "memory"
            self._init_memory()
            
        except Exception as e:
            self.logger.error(f"Error connecting to MQTT broker: {e}")
            self.protocol = "memory"
            self._init_memory()
    
    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """Callback for when the client connects to the MQTT broker."""
        if rc == 0:
            self.logger.info("Connected to MQTT broker")
            
            # Subscribe to topics
            topics = self.settings.get("topics", {})
            for topic_name, topic in topics.items():
                client.subscribe(topic)
                self.subscribed_topics.add(topic)
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
            
            # Call message handlers
            if msg.topic in self.topic_handlers:
                for handler in self.topic_handlers[msg.topic]:
                    handler(message)
            
        except Exception as e:
            self.logger.error(f"Error processing MQTT message: {e}")
    
    def _on_mqtt_disconnect(self, client, userdata, rc):
        """Callback for when the client disconnects from the MQTT broker."""
        if rc != 0:
            self.logger.warning(f"Unexpected disconnection from MQTT broker: {rc}")
    
    def _init_rest(self) -> None:
        """Initialize REST communication."""
        # REST communication is handled through FastAPI/Flask, not here
        self.logger.info("REST communication initialized")
    
    def _init_memory(self) -> None:
        """Initialize in-memory communication."""
        self.comm_client = None
        self.logger.info("In-memory communication initialized")
    
    def start(self) -> None:
        """Start the Communication Manager."""
        if self.running:
            self.logger.warning("Communication Manager is already running")
            return
        
        self.running = True
        
        # Start processing thread
        self.processing_thread = threading.Thread(target=self._processing_loop)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        
        self.logger.info("Communication Manager started")
    
    def stop(self) -> None:
        """Stop the Communication Manager."""
        if not self.running:
            self.logger.warning("Communication Manager is not running")
            return
        
        self.running = False
        
        # Stop the processing thread
        if self.processing_thread:
            self.processing_thread.join(timeout=5.0)
        
        # Stop MQTT client if used
        if self.protocol == "mqtt" and self.comm_client:
            self.comm_client.loop_stop()
            self.comm_client.disconnect()
        
        self.logger.info("Communication Manager stopped")
    
    def _processing_loop(self) -> None:
        """Main processing loop for the Communication Manager."""
        while self.running:
            # Process Redis messages if using Redis
            if self.protocol == "redis" and self.comm_client:
                self._process_redis_messages()
            
            # Process messages in the queue
            self._process_messages()
            
            # Sleep for a bit
            time.sleep(0.01)
    
    def _process_redis_messages(self) -> None:
        """Process messages from Redis PubSub."""
        # Get messages from PubSub
        message = self.pubsub.get_message()
        while message:
            try:
                # Skip subscribe/unsubscribe messages
                if message["type"] in ["subscribe", "unsubscribe"]:
                    message = self.pubsub.get_message()
                    continue
                
                # Parse message
                payload_str = message["data"].decode("utf-8")
                payload = json.loads(payload_str)
                
                # Create message
                msg = Message.from_dict(payload)
                
                # Add to message queue
                self.message_queue.append(msg)
                
                # Call message handlers
                channel = message["channel"].decode("utf-8")
                if channel in self.topic_handlers:
                    for handler in self.topic_handlers[channel]:
                        handler(msg)
                
            except Exception as e:
                self.logger.error(f"Error processing Redis message: {e}")
            
            # Get next message
            message = self.pubsub.get_message()
    
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
                # Call message callback if registered
                if message.message_id in self.message_callbacks:
                    callback_info = self.message_callbacks[message.message_id]
                    callback = callback_info["callback"]
                    callback(message)
                    
                    # Remove callback if one-time
                    if callback_info.get("one_time", True):
                        del self.message_callbacks[message.message_id]
            
            except Exception as e:
                self.logger.error(f"Error processing message {message.message_id}: {e}")
    
    def send_message(self, message: Message) -> bool:
        """
        Send a message.
        
        Args:
            message: Message to send
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Serialize message
            payload = message.to_dict()
            payload_str = json.dumps(payload)
            
            # Send using appropriate protocol
            if self.protocol == "redis" and self.comm_client:
                return self._send_redis_message(message, payload_str)
            elif self.protocol == "mqtt" and self.comm_client:
                return self._send_mqtt_message(message, payload_str)
            elif self.protocol == "rest":
                return self._send_rest_message(message, payload_str)
            elif self.protocol == "memory":
                # Add directly to queue for in-memory communication
                self.message_queue.append(message)
                return True
            else:
                self.logger.warning(f"Unsupported protocol for sending message: {self.protocol}")
                return False
        
        except Exception as e:
            self.logger.error(f"Error sending message {message.message_id}: {e}")
            return False
    
    def _send_redis_message(self, message: Message, payload_str: str) -> bool:
        """
        Send a message using Redis.
        
        Args:
            message: Message to send
            payload_str: Serialized message
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Get channel for target agent
            agent_channels = self.settings.get("agent_channels", {})
            channel = agent_channels.get(message.target_agent_id)
            
            if not channel:
                # Use broadcast channel if no specific channel is defined
                channel = self.settings.get("broadcast_channel", "core_hub")
            
            # Publish message
            self.comm_client.publish(channel, payload_str)
            
            return True
        
        except Exception as e:
            self.logger.error(f"Error sending Redis message {message.message_id}: {e}")
            return False
    
    def _send_mqtt_message(self, message: Message, payload_str: str) -> bool:
        """
        Send a message using MQTT.
        
        Args:
            message: Message to send
            payload_str: Serialized message
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Get topic for target agent
            agent_topics = self.settings.get("agent_topics", {})
            topic = agent_topics.get(message.target_agent_id)
            
            if not topic:
                # Use broadcast topic if no specific topic is defined
                topic = self.settings.get("broadcast_topic", "core_hub")
            
            # Publish message
            self.comm_client.publish(topic, payload_str)
            
            return True
        
        except Exception as e:
            self.logger.error(f"Error sending MQTT message {message.message_id}: {e}")
            return False
    
    def _send_rest_message(self, message: Message, payload_str: str) -> bool:
        """
        Send a message using REST.
        
        Args:
            message: Message to send
            payload_str: Serialized message
            
        Returns:
            True if sent successfully, False otherwise
        """
        # REST communication is handled through FastAPI/Flask, not here
        self.logger.warning("REST message sending not implemented in communication manager")
        return False
    
    def broadcast_message(self, message: Message) -> bool:
        """
        Broadcast a message to all agents.
        
        Args:
            message: Message to broadcast
            
        Returns:
            True if broadcast successfully, False otherwise
        """
        try:
            # Serialize message
            payload = message.to_dict()
            payload_str = json.dumps(payload)
            
            # Broadcast using appropriate protocol
            if self.protocol == "redis" and self.comm_client:
                return self._broadcast_redis_message(message, payload_str)
            elif self.protocol == "mqtt" and self.comm_client:
                return self._broadcast_mqtt_message(message, payload_str)
            elif self.protocol == "rest":
                return self._broadcast_rest_message(message, payload_str)
            elif self.protocol == "memory":
                # Add directly to queue for in-memory communication
                self.message_queue.append(message)
                return True
            else:
                self.logger.warning(f"Unsupported protocol for broadcasting message: {self.protocol}")
                return False
        
        except Exception as e:
            self.logger.error(f"Error broadcasting message {message.message_id}: {e}")
            return False
    
    def _broadcast_redis_message(self, message: Message, payload_str: str) -> bool:
        """
        Broadcast a message using Redis.
        
        Args:
            message: Message to broadcast
            payload_str: Serialized message
            
        Returns:
            True if broadcast successfully, False otherwise
        """
        try:
            # Get broadcast channel
            channel = self.settings.get("broadcast_channel", "core_hub")
            
            # Publish message
            self.comm_client.publish(channel, payload_str)
            
            return True
        
        except Exception as e:
            self.logger.error(f"Error broadcasting Redis message {message.message_id}: {e}")
            return False
    
    def _broadcast_mqtt_message(self, message: Message, payload_str: str) -> bool:
        """
        Broadcast a message using MQTT.
        
        Args:
            message: Message to broadcast
            payload_str: Serialized message
            
        Returns:
            True if broadcast successfully, False otherwise
        """
        try:
            # Get broadcast topic
            topic = self.settings.get("broadcast_topic", "core_hub")
            
            # Publish message
            self.comm_client.publish(topic, payload_str)
            
            return True
        
        except Exception as e:
            self.logger.error(f"Error broadcasting MQTT message {message.message_id}: {e}")
            return False
    
    def _broadcast_rest_message(self, message: Message, payload_str: str) -> bool:
        """
        Broadcast a message using REST.
        
        Args:
            message: Message to broadcast
            payload_str: Serialized message
            
        Returns:
            True if broadcast successfully, False otherwise
        """
        # REST communication is handled through FastAPI/Flask, not here
        self.logger.warning("REST message broadcasting not implemented in communication manager")
        return False
    
    def register_topic_handler(self, topic: str, handler: Callable[[Message], None]) -> None:
        """
        Register a handler for a specific topic/channel.
        
        Args:
            topic: Topic or channel name
            handler: Function to call when a message is received on the topic
        """
        if topic not in self.topic_handlers:
            self.topic_handlers[topic] = []
        
        self.topic_handlers[topic].append(handler)
        
        # Subscribe to topic if using Redis or MQTT
        if self.protocol == "redis" and self.comm_client and topic not in self.subscribed_topics:
            self.pubsub.subscribe(topic)
            self.subscribed_topics.add(topic)
        elif self.protocol == "mqtt" and self.comm_client and topic not in self.subscribed_topics:
            self.comm_client.subscribe(topic)
            self.subscribed_topics.add(topic)
    
    def register_message_callback(self, message_id: str, callback: Callable[[Message], None], one_time: bool = True) -> None:
        """
        Register a callback for a specific message ID.
        
        Args:
            message_id: Message ID to wait for
            callback: Function to call when the message is received
            one_time: Whether to remove the callback after the first invocation
        """
        self.message_callbacks[message_id] = {
            "callback": callback,
            "one_time": one_time,
            "registered_at": time.time()
        }
    
    def unregister_message_callback(self, message_id: str) -> bool:
        """
        Unregister a callback for a specific message ID.
        
        Args:
            message_id: Message ID to unregister
            
        Returns:
            True if unregistered successfully, False otherwise
        """
        if message_id in self.message_callbacks:
            del self.message_callbacks[message_id]
            return True
        else:
            return False
    
    def clean_expired_callbacks(self, timeout: float = 300.0) -> int:
        """
        Clean expired message callbacks.
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            Number of callbacks removed
        """
        now = time.time()
        expired_ids = []
        
        # Find expired callbacks
        for message_id, callback_info in self.message_callbacks.items():
            if now - callback_info["registered_at"] > timeout:
                expired_ids.append(message_id)
        
        # Remove expired callbacks
        for message_id in expired_ids:
            del self.message_callbacks[message_id]
        
        if expired_ids:
            self.logger.info(f"Removed {len(expired_ids)} expired message callbacks")
        
        return len(expired_ids)


def create_communication_manager(config: Dict[str, Any]) -> CommunicationManager:
    """
    Create a Communication Manager with the specified configuration.
    
    Args:
        config: Communication configuration
        
    Returns:
        Configured Communication Manager
    """
    return CommunicationManager(config)