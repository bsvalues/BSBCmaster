"""
Agent Coordinator Module

This module provides the central coordination system for the AI agents,
enabling task delegation, performance monitoring, and collaborative learning.
"""

import time
import threading
import logging
import json
import os
from typing import Dict, Any, List, Optional, Callable, Tuple
from datetime import datetime

from .message import CoordinationMessage, MessageType
from .replay_buffer import ReplayBuffer, Experience
from .performance import PerformanceTracker


class AgentCoordinator:
    """
    Central coordination system for AI agents.
    
    This class manages inter-agent communication, task delegation,
    performance monitoring, and collaborative learning for the AI agent system.
    It integrates with the Master Control Program (MCP) to provide a complete
    agent orchestration solution.
    """
    
    def __init__(self, mcp, config_path: Optional[str] = None, 
                 log_dir: Optional[str] = 'logs/coordination'):
        """
        Initialize the agent coordinator.
        
        Args:
            mcp: Reference to the Master Control Program
            config_path: Path to configuration file (None = use defaults)
            log_dir: Directory for logs (None = no logging)
        """
        self.mcp = mcp
        self.log_dir = log_dir
        
        # Set up logging
        self._setup_logging()
        
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Initialize replay buffer for experience sharing
        self.replay_buffer = ReplayBuffer(
            capacity=self.config.get('replay_buffer_capacity', 10000),
            alpha=self.config.get('replay_buffer_alpha', 0.6),
            beta=self.config.get('replay_buffer_beta', 0.4),
            beta_increment=self.config.get('replay_buffer_beta_increment', 0.001),
            save_dir=self.config.get('replay_buffer_save_dir', 'data/experiences')
        )
        
        # Initialize performance tracker
        self.performance_tracker = PerformanceTracker(
            performance_threshold=self.config.get('performance_threshold', 0.7),
            window_size=self.config.get('performance_window_size', 100),
            save_dir=self.config.get('performance_save_dir', 'data/performance')
        )
        
        # Message queue and thread for background processing
        self.message_queue = []
        self.running = False
        self.processing_thread = None
        
        # Registered agents and their capabilities
        self.agent_capabilities = {}
        
        # Training callbacks
        self.training_callbacks = {}
        
        self.logger.info("Agent Coordinator initialized")
    
    def _setup_logging(self) -> None:
        """Set up logging for the agent coordinator."""
        if self.log_dir:
            os.makedirs(self.log_dir, exist_ok=True)
            
            # Create logger
            self.logger = logging.getLogger('agent_coordinator')
            self.logger.setLevel(logging.INFO)
            
            # Create file handler
            log_file = os.path.join(self.log_dir, f'coordinator_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
            file_handler = logging.FileHandler(log_file)
            
            # Create formatter
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)
            
            # Add handler to logger
            self.logger.addHandler(file_handler)
        else:
            # Create a null logger if no log directory is specified
            self.logger = logging.getLogger('agent_coordinator')
            self.logger.addHandler(logging.NullHandler())
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """
        Load configuration from a JSON file or use defaults.
        
        Args:
            config_path: Path to the configuration file
            
        Returns:
            Configuration dictionary
        """
        default_config = {
            'poll_interval': 1.0,  # seconds
            'replay_buffer_capacity': 10000,
            'replay_buffer_alpha': 0.6,
            'replay_buffer_beta': 0.4,
            'replay_buffer_beta_increment': 0.001,
            'replay_buffer_save_dir': 'data/experiences',
            'performance_threshold': 0.7,
            'performance_window_size': 100,
            'performance_save_dir': 'data/performance',
            'training_threshold': 1000,  # min experiences to start training
            'training_batch_size': 32,
            'training_frequency': 50,  # train every N new experiences
        }
        
        # If no config path, use defaults
        if config_path is None:
            return default_config
        
        # Load from file if it exists
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    loaded_config = json.load(f)
                
                # Merge with defaults (loaded config takes precedence)
                config = {**default_config, **loaded_config}
                self.logger.info(f"Configuration loaded from {config_path}")
                return config
            except Exception as e:
                self.logger.error(f"Error loading configuration from {config_path}: {e}")
                return default_config
        else:
            self.logger.warning(f"Configuration file not found: {config_path}")
            return default_config
    
    def start(self) -> None:
        """Start the agent coordinator."""
        if self.running:
            self.logger.warning("Agent Coordinator is already running")
            return
        
        self.running = True
        self.processing_thread = threading.Thread(target=self._processing_loop)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        
        self.logger.info("Agent Coordinator started")
    
    def stop(self) -> None:
        """Stop the agent coordinator."""
        if not self.running:
            self.logger.warning("Agent Coordinator is not running")
            return
        
        self.running = False
        if self.processing_thread:
            self.processing_thread.join(timeout=5.0)
        
        self.logger.info("Agent Coordinator stopped")
    
    def _processing_loop(self) -> None:
        """Background thread for processing messages and training."""
        last_training_time = time.time()
        experiences_since_training = 0
        
        while self.running:
            # Process waiting messages
            self._process_messages()
            
            # Check if agents need assistance
            self._check_agent_performance()
            
            # Check if we should trigger training
            if (experiences_since_training >= self.config.get('training_frequency', 50) and
                len(self.replay_buffer) >= self.config.get('training_threshold', 1000)):
                self._trigger_training()
                experiences_since_training = 0
                last_training_time = time.time()
            
            # Sleep for a bit
            time.sleep(self.config.get('poll_interval', 1.0))
    
    def _process_messages(self) -> None:
        """Process waiting messages in the queue."""
        # Make a copy of the queue to avoid modification during iteration
        current_queue = list(self.message_queue)
        self.message_queue = []
        
        for message in current_queue:
            try:
                self._handle_message(message)
            except Exception as e:
                self.logger.error(f"Error handling message {message.message_id}: {e}")
    
    def _handle_message(self, message: CoordinationMessage) -> None:
        """
        Handle a coordination message.
        
        Args:
            message: The message to handle
        """
        self.logger.debug(f"Handling message: {message}")
        
        # Handle different message types
        if message.message_type == MessageType.HELP_REQUEST:
            self._handle_help_request(message)
        elif message.message_type == MessageType.TASK_DELEGATION:
            self._handle_task_delegation(message)
        elif message.message_type == MessageType.TRAINING_UPDATE:
            self._handle_training_update(message)
        elif message.message_type == MessageType.ACTION:
            # Record action for the replay buffer
            self._record_action(message)
        elif message.message_type == MessageType.RESULT:
            # Record result for the replay buffer
            self._record_result(message)
        elif message.message_type == MessageType.STATUS_UPDATE:
            # Update agent performance metrics
            self._update_performance_metrics(message)
        elif message.message_type == MessageType.ERROR:
            # Log error and potentially take remedial action
            self._handle_error(message)
    
    def _handle_help_request(self, message: CoordinationMessage) -> None:
        """
        Handle a help request from an agent.
        
        Args:
            message: The help request message
        """
        self.logger.info(f"Help request from {message.agent_id}: {message.payload.get('assistance_type')}")
        
        # Get the type of assistance needed
        assistance_type = message.payload.get('assistance_type')
        context = message.payload.get('context', {})
        
        if assistance_type == 'debug':
            # Delegate to MCP for debugging assistance
            self.mcp.delegate_task(
                to_agent_id="MCP",
                task_type="provide_debugging_assistance",
                parameters={
                    "target_agent_id": message.agent_id,
                    "error_context": context
                },
                from_agent_id="coordinator"
            )
        elif assistance_type == 'optimization':
            # Find a suitable agent for optimization assistance
            suitable_agent = self._find_suitable_agent_for_task("optimization")
            
            if suitable_agent:
                self.mcp.delegate_task(
                    to_agent_id=suitable_agent,
                    task_type="provide_optimization_assistance",
                    parameters={
                        "target_agent_id": message.agent_id,
                        "performance_metrics": self.performance_tracker.get_agent_stats(message.agent_id),
                        "context": context
                    },
                    from_agent_id="coordinator"
                )
            else:
                # Fall back to MCP if no suitable agent is found
                self.mcp.delegate_task(
                    to_agent_id="MCP",
                    task_type="provide_optimization_assistance",
                    parameters={
                        "target_agent_id": message.agent_id,
                        "performance_metrics": self.performance_tracker.get_agent_stats(message.agent_id),
                        "context": context
                    },
                    from_agent_id="coordinator"
                )
    
    def _handle_task_delegation(self, message: CoordinationMessage) -> None:
        """
        Handle a task delegation message.
        
        Args:
            message: The task delegation message
        """
        self.logger.info(f"Task delegation from {message.agent_id}: {message.payload.get('task_type')}")
        
        # Extract task details
        task_type = message.payload.get('task_type')
        parameters = message.payload.get('parameters', {})
        priority = message.payload.get('priority', 'normal')
        
        # Find a suitable agent for the task
        suitable_agent = self._find_suitable_agent_for_task(task_type)
        
        if suitable_agent:
            # Delegate the task to the suitable agent
            task_result = self.mcp.create_task(
                to_agent_id=suitable_agent,
                task_type=task_type,
                parameters=parameters,
                from_agent_id="coordinator"
            )
            
            # Notify the original agent of the delegation
            self.send_message(
                from_agent_id="coordinator",
                to_agent_id=message.agent_id,
                message_type=MessageType.RESULT,
                payload={
                    "original_message_id": message.message_id,
                    "delegated_to": suitable_agent,
                    "task_id": task_result.get('task_id')
                }
            )
        else:
            # Notify the agent that no suitable agent was found
            self.send_message(
                from_agent_id="coordinator",
                to_agent_id=message.agent_id,
                message_type=MessageType.ERROR,
                payload={
                    "original_message_id": message.message_id,
                    "error": "No suitable agent found for task",
                    "task_type": task_type
                }
            )
    
    def _handle_training_update(self, message: CoordinationMessage) -> None:
        """
        Handle a training update message.
        
        Args:
            message: The training update message
        """
        self.logger.info(f"Training update from {message.agent_id}")
        
        # Extract model updates
        model_updates = message.payload.get('model_updates', {})
        metrics = message.payload.get('metrics', {})
        
        # Apply updates to registered training callbacks
        for agent_id, callback in self.training_callbacks.items():
            try:
                callback(model_updates, metrics)
                
                # Notify the agent of the update
                self.send_message(
                    from_agent_id="coordinator",
                    to_agent_id=agent_id,
                    message_type=MessageType.POLICY_UPDATE,
                    payload={
                        "model_updates": model_updates,
                        "metrics": metrics,
                        "source_agent": message.agent_id
                    }
                )
            except Exception as e:
                self.logger.error(f"Error applying model updates to {agent_id}: {e}")
    
    def _record_action(self, message: CoordinationMessage) -> None:
        """
        Record an action for the replay buffer.
        
        Args:
            message: The action message
        """
        # Extract action details
        agent_id = message.agent_id
        state = message.payload.get('state', {})
        action = message.payload.get('action', {})
        action_id = message.payload.get('action_id')
        
        # Store the action in a temporary buffer until we receive the result
        # For now, we'll just log it
        self.logger.debug(f"Recorded action from {agent_id}: {action_id}")
    
    def _record_result(self, message: CoordinationMessage) -> None:
        """
        Record a result for the replay buffer.
        
        Args:
            message: The result message
        """
        # Extract result details
        agent_id = message.agent_id
        action_id = message.payload.get('action_id')
        reward = message.payload.get('reward', 0.0)
        next_state = message.payload.get('next_state', {})
        done = message.payload.get('done', False)
        
        # In a real system, we would match this with the previous action
        # For demonstration, we'll create a simple experience
        experience = Experience(
            agent_id=agent_id,
            state={"demo": "state"},  # Would be the actual state from the matched action
            action={"action_id": action_id},  # Would be the actual action from the matched action
            reward=reward,
            next_state=next_state,
            done=done
        )
        
        # Add the experience to the replay buffer
        self.replay_buffer.add(experience)
        
        self.logger.debug(f"Recorded result from {agent_id}: {action_id} with reward {reward}")
    
    def _update_performance_metrics(self, message: CoordinationMessage) -> None:
        """
        Update performance metrics for an agent.
        
        Args:
            message: The status update message
        """
        # Extract metrics
        agent_id = message.agent_id
        metrics = message.payload.get('metrics', {})
        
        # Record each metric
        for metric_name, value in metrics.items():
            self.performance_tracker.record_metric(agent_id, metric_name, value)
        
        self.logger.debug(f"Updated performance metrics for {agent_id}")
    
    def _handle_error(self, message: CoordinationMessage) -> None:
        """
        Handle an error message from an agent.
        
        Args:
            message: The error message
        """
        agent_id = message.agent_id
        error = message.payload.get('error')
        context = message.payload.get('context', {})
        
        self.logger.warning(f"Error from {agent_id}: {error}")
        
        # Check if the agent needs assistance based on errors
        if self.performance_tracker.needs_assistance(agent_id):
            self.logger.info(f"Agent {agent_id} needs assistance due to errors")
            
            # Delegate to MCP for assistance
            self.mcp.delegate_task(
                to_agent_id="MCP",
                task_type="provide_error_assistance",
                parameters={
                    "target_agent_id": agent_id,
                    "error": error,
                    "context": context,
                    "performance_metrics": self.performance_tracker.get_agent_stats(agent_id)
                },
                from_agent_id="coordinator"
            )
    
    def _check_agent_performance(self) -> None:
        """Check if any agents need assistance based on performance."""
        # Get all registered agents from MCP
        agents = self.mcp.list_agents()
        
        for agent in agents:
            agent_id = agent.get('agent_id')
            
            # Skip the MCP itself and the coordinator
            if agent_id in ['MCP', 'coordinator']:
                continue
            
            # Check if the agent needs assistance
            if self.performance_tracker.needs_assistance(agent_id):
                self.logger.info(f"Agent {agent_id} needs assistance due to poor performance")
                
                # Get agent stats
                stats = self.performance_tracker.get_agent_stats(agent_id)
                
                # Find the most problematic metric
                problematic_metric = None
                lowest_value = float('inf')
                
                for metric_name, metric_stats in stats.items():
                    if metric_name == 'overall_score':
                        continue
                    
                    if 'mean' in metric_stats:
                        # For metrics where higher is better
                        if metric_name in ['success_rate', 'accuracy']:
                            if metric_stats['mean'] < lowest_value:
                                lowest_value = metric_stats['mean']
                                problematic_metric = metric_name
                        # For metrics where lower is better
                        elif metric_name in ['error_rate', 'response_time']:
                            if 1.0 - metric_stats['mean'] < lowest_value:
                                lowest_value = 1.0 - metric_stats['mean']
                                problematic_metric = metric_name
                
                # Delegate to MCP for optimization assistance
                self.mcp.delegate_task(
                    to_agent_id="MCP",
                    task_type="provide_optimization_assistance",
                    parameters={
                        "target_agent_id": agent_id,
                        "performance_metrics": stats,
                        "problematic_metric": problematic_metric
                    },
                    from_agent_id="coordinator"
                )
    
    def _trigger_training(self) -> None:
        """Trigger a training cycle using the replay buffer."""
        self.logger.info("Triggering training cycle")
        
        # Sample from the replay buffer
        batch_size = self.config.get('training_batch_size', 32)
        experiences, indices, weights = self.replay_buffer.sample(batch_size)
        
        if not experiences:
            self.logger.warning("No experiences to train on")
            return
        
        # In a real system, we would train a model here
        # For demonstration, we'll just log the training
        self.logger.info(f"Training on {len(experiences)} experiences")
        
        # Update priorities based on some hypothetical loss
        # In a real system, this would be based on the actual training loss
        priorities = [1.0] * len(indices)  # Example: all equal priorities
        self.replay_buffer.update_priorities(indices, priorities)
        
        # Notify agents of the training update
        self.send_message(
            from_agent_id="coordinator",
            to_agent_id=None,  # Broadcast to all agents
            message_type=MessageType.POLICY_UPDATE,
            payload={
                "model_updates": {"version": time.time()},  # Example update
                "metrics": {"loss": 0.1, "accuracy": 0.9}  # Example metrics
            }
        )
    
    def _find_suitable_agent_for_task(self, task_type: str) -> Optional[str]:
        """
        Find a suitable agent for a specific task.
        
        Args:
            task_type: Type of task to find an agent for
            
        Returns:
            Agent ID of a suitable agent, or None if no suitable agent is found
        """
        # Check registered agent capabilities
        for agent_id, capabilities in self.agent_capabilities.items():
            if task_type in capabilities:
                return agent_id
        
        # If not found in registered capabilities, check MCP's agent list
        agents = self.mcp.list_agents()
        
        for agent in agents:
            agent_id = agent.get('agent_id')
            agent_type = agent.get('type')
            
            # Heuristic: check if the agent type matches the task type
            if task_type.lower() in agent_type.lower():
                return agent_id
        
        return None
    
    def register_agent_capabilities(self, agent_id: str, capabilities: List[str]) -> None:
        """
        Register an agent's capabilities.
        
        Args:
            agent_id: Identifier of the agent
            capabilities: List of capabilities the agent has
        """
        self.agent_capabilities[agent_id] = capabilities
        self.logger.info(f"Registered capabilities for {agent_id}: {capabilities}")
    
    def register_training_callback(self, agent_id: str, callback: Callable[[Dict[str, Any], Dict[str, Any]], None]) -> None:
        """
        Register a callback for policy updates.
        
        Args:
            agent_id: Identifier of the agent
            callback: Function to call with model updates
        """
        self.training_callbacks[agent_id] = callback
        self.logger.info(f"Registered training callback for {agent_id}")
    
    def send_message(self, from_agent_id: str, to_agent_id: Optional[str],
                     message_type: MessageType, payload: Dict[str, Any]) -> str:
        """
        Send a message to another agent.
        
        Args:
            from_agent_id: Identifier of the sender agent
            to_agent_id: Identifier of the recipient agent (None = broadcast)
            message_type: Type of message
            payload: Content of the message
            
        Returns:
            ID of the sent message
        """
        message = CoordinationMessage(
            agent_id=from_agent_id,
            recipient_id=to_agent_id,
            message_type=message_type,
            payload=payload
        )
        
        # If recipient is None, broadcast to all agents via MCP
        if to_agent_id is None:
            # Use MCP to broadcast
            self.mcp.broadcast_message(
                from_agent_id=from_agent_id,
                message_type=message_type.name,
                content=payload
            )
        else:
            # Send direct message via MCP
            self.mcp.send_message(
                from_agent_id=from_agent_id,
                to_agent_id=to_agent_id,
                message_type=message_type.name,
                content=payload
            )
        
        # Queue the message for our own processing
        self.message_queue.append(message)
        
        return message.message_id
    
    def record_experience(self, agent_id: str, state: Dict[str, Any],
                         action: Dict[str, Any], reward: float,
                         next_state: Dict[str, Any], done: bool) -> None:
        """
        Record an experience directly.
        
        Args:
            agent_id: Identifier of the agent
            state: State before action
            action: Action taken
            reward: Reward received
            next_state: State after action
            done: Whether the episode is done
        """
        experience = Experience(
            agent_id=agent_id,
            state=state,
            action=action,
            reward=reward,
            next_state=next_state,
            done=done
        )
        
        self.replay_buffer.add(experience)
    
    def request_help(self, agent_id: str, assistance_type: str,
                    context: Optional[Dict[str, Any]] = None) -> str:
        """
        Request help for an agent.
        
        Args:
            agent_id: Identifier of the agent requesting help
            assistance_type: Type of assistance needed
            context: Additional context for the help request
            
        Returns:
            ID of the sent message
        """
        return self.send_message(
            from_agent_id=agent_id,
            to_agent_id="coordinator",  # To self, will be processed in the message loop
            message_type=MessageType.HELP_REQUEST,
            payload={
                "assistance_type": assistance_type,
                "context": context or {}
            }
        )
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        Get the status of the coordination system.
        
        Returns:
            Dictionary with system status
        """
        return {
            "running": self.running,
            "replay_buffer": {
                "size": len(self.replay_buffer),
                "capacity": self.replay_buffer.capacity,
                "stats": self.replay_buffer.get_stats()
            },
            "performance_tracker": {
                "agent_count": len(self.performance_tracker.metrics),
                "agents_needing_assistance": [
                    agent_id for agent_id in self.performance_tracker.metrics
                    if self.performance_tracker.needs_assistance(agent_id)
                ]
            },
            "message_queue_size": len(self.message_queue),
            "registered_agents": list(self.agent_capabilities.keys()),
            "registered_callbacks": list(self.training_callbacks.keys())
        }
    
    def get_agent_performance(self, agent_id: str) -> Dict[str, Any]:
        """
        Get performance metrics for an agent.
        
        Args:
            agent_id: Identifier of the agent
            
        Returns:
            Dictionary with performance metrics
        """
        return self.performance_tracker.get_agent_stats(agent_id)
    
    def generate_performance_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive performance report.
        
        Returns:
            Dictionary with performance data for all agents
        """
        return self.performance_tracker.generate_performance_report()