"""
Agent Manager Module for Benton County Assessor's Office AI Platform

This module provides centralized agent lifecycle management for the Core Hub,
including registration, deregistration, health monitoring, and capability discovery.
"""

import os
import json
import time
import logging
from typing import Dict, Any, List, Optional, Set, Tuple

from .logging import create_logger
from .message import Message, StatusUpdateMessage, CommandMessage, EventType


class AgentManager:
    """
    Agent Manager for the Core Hub.
    
    This class handles agent registration, deregistration, health monitoring,
    and capability discovery for the Core Hub.
    """
    
    def __init__(self, config: Dict[str, Any], data_dir: str):
        """
        Initialize the Agent Manager.
        
        Args:
            config: Agent manager configuration
            data_dir: Data directory for persistence
        """
        self.config = config
        self.data_dir = data_dir
        self.registered_agents = {}
        self.agent_capabilities = {}
        self.agent_subscriptions = {}
        self.agent_dependencies = {}
        self.health_check_interval = config.get("health_check_interval", 60)
        self.last_health_check = time.time()
        
        # Create logger
        self.logger = create_logger("agent_manager", {
            "component": "AgentManager",
            "version": config.get("version", "1.0.0")
        })
        
        # Ensure data directory exists
        os.makedirs(data_dir, exist_ok=True)
        
        # State persistence file
        self.state_file = os.path.join(data_dir, "agent_state.json")
        
        # Load persisted state if available
        self._load_state()
        
        self.logger.info(f"Agent Manager initialized with {len(self.registered_agents)} agents")
    
    def register_agent(self, agent_id: str, agent_info: Dict[str, Any]) -> bool:
        """
        Register an agent with the Core Hub.
        
        Args:
            agent_id: Unique identifier for the agent
            agent_info: Information about the agent
            
        Returns:
            True if registration successful, False otherwise
        """
        # Check if agent is already registered
        if agent_id in self.registered_agents:
            self.logger.warning(f"Agent {agent_id} already registered")
            return False
        
        # Add registration timestamp
        agent_info["registered_at"] = time.time()
        agent_info["last_update"] = time.time()
        agent_info["status"] = agent_info.get("status", "inactive")
        
        # Register agent
        self.registered_agents[agent_id] = agent_info
        
        # Register capabilities
        if "capabilities" in agent_info:
            for capability in agent_info["capabilities"]:
                if capability not in self.agent_capabilities:
                    self.agent_capabilities[capability] = set()
                
                self.agent_capabilities[capability].add(agent_id)
        
        # Register subscriptions
        if "subscriptions" in agent_info:
            self.agent_subscriptions[agent_id] = set(agent_info["subscriptions"])
        
        # Register dependencies
        if "dependencies" in agent_info:
            self.agent_dependencies[agent_id] = set(agent_info["dependencies"])
        
        # Persist state
        self._save_state()
        
        self.logger.info(f"Agent {agent_id} registered successfully")
        
        return True
    
    def deregister_agent(self, agent_id: str) -> bool:
        """
        Deregister an agent from the Core Hub.
        
        Args:
            agent_id: Unique identifier for the agent
            
        Returns:
            True if deregistration successful, False otherwise
        """
        # Check if agent is registered
        if agent_id not in self.registered_agents:
            self.logger.warning(f"Agent {agent_id} not registered")
            return False
        
        # Get agent info before removal
        agent_info = self.registered_agents[agent_id]
        
        # Remove agent
        del self.registered_agents[agent_id]
        
        # Remove capabilities
        if "capabilities" in agent_info:
            for capability in agent_info["capabilities"]:
                if capability in self.agent_capabilities:
                    self.agent_capabilities[capability].discard(agent_id)
                    
                    # Remove capability if no agents provide it
                    if not self.agent_capabilities[capability]:
                        del self.agent_capabilities[capability]
        
        # Remove subscriptions
        if agent_id in self.agent_subscriptions:
            del self.agent_subscriptions[agent_id]
        
        # Remove dependencies
        if agent_id in self.agent_dependencies:
            del self.agent_dependencies[agent_id]
        
        # Persist state
        self._save_state()
        
        self.logger.info(f"Agent {agent_id} deregistered successfully")
        
        return True
    
    def update_agent_status(self, agent_id: str, status: str, metrics: Optional[Dict[str, Any]] = None) -> bool:
        """
        Update an agent's status and metrics.
        
        Args:
            agent_id: Unique identifier for the agent
            status: New status (active, inactive, error, etc.)
            metrics: Performance metrics
            
        Returns:
            True if update successful, False otherwise
        """
        # Check if agent is registered
        if agent_id not in self.registered_agents:
            self.logger.warning(f"Agent {agent_id} not registered")
            return False
        
        # Update status and metrics
        self.registered_agents[agent_id]["status"] = status
        self.registered_agents[agent_id]["last_update"] = time.time()
        
        if metrics:
            self.registered_agents[agent_id]["metrics"] = metrics
        
        # Persist state
        if status in ["error", "terminated", "restarting"] or time.time() - self.registered_agents[agent_id].get("last_save", 0) > 60:
            self._save_state()
            self.registered_agents[agent_id]["last_save"] = time.time()
        
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
        return self.registered_agents
    
    def get_active_agents(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all active agents.
        
        Returns:
            Dictionary mapping agent IDs to agent information
        """
        return {
            agent_id: agent_info
            for agent_id, agent_info in self.registered_agents.items()
            if agent_info.get("status") == "active"
        }
    
    def get_agents_by_capability(self, capability: str) -> List[str]:
        """
        Get agents with a specific capability.
        
        Args:
            capability: Capability to search for
            
        Returns:
            List of agent IDs with the capability
        """
        return list(self.agent_capabilities.get(capability, set()))
    
    def get_agents_by_status(self, status: str) -> List[str]:
        """
        Get agents with a specific status.
        
        Args:
            status: Status to search for
            
        Returns:
            List of agent IDs with the status
        """
        return [
            agent_id
            for agent_id, agent_info in self.registered_agents.items()
            if agent_info.get("status") == status
        ]
    
    def get_agents_by_subscription(self, topic: str) -> List[str]:
        """
        Get agents subscribed to a specific topic.
        
        Args:
            topic: Topic to check
            
        Returns:
            List of agent IDs subscribed to the topic
        """
        return [
            agent_id
            for agent_id, subscriptions in self.agent_subscriptions.items()
            if topic in subscriptions
        ]
    
    def check_agent_health(self) -> Dict[str, List[str]]:
        """
        Check the health of all registered agents and update their status.
        
        Returns:
            Dictionary of agent IDs by health status (healthy, unhealthy, unreachable)
        """
        now = time.time()
        
        # Skip if health check was performed recently
        if now - self.last_health_check < self.health_check_interval:
            return {
                "healthy": [],
                "unhealthy": [],
                "unreachable": []
            }
        
        self.last_health_check = now
        
        health_status = {
            "healthy": [],
            "unhealthy": [],
            "unreachable": []
        }
        
        # Check health of each agent
        for agent_id, agent_info in self.registered_agents.items():
            # Skip if agent is not active
            if agent_info.get("status") != "active":
                continue
            
            # Check last update time
            last_update = agent_info.get("last_update", 0)
            if now - last_update > self.config.get("agent_timeout", 300):
                # Agent hasn't updated in a while, mark as unreachable
                self.registered_agents[agent_id]["status"] = "unreachable"
                health_status["unreachable"].append(agent_id)
            elif "metrics" in agent_info and agent_info["metrics"].get("errors", 0) > 0:
                # Agent has errors, mark as unhealthy
                health_status["unhealthy"].append(agent_id)
            else:
                # Agent is healthy
                health_status["healthy"].append(agent_id)
        
        # Save state if there are unreachable agents
        if health_status["unreachable"]:
            self._save_state()
        
        self.logger.info(f"Health check completed: {len(health_status['healthy'])} healthy, {len(health_status['unhealthy'])} unhealthy, {len(health_status['unreachable'])} unreachable")
        
        return health_status
    
    def generate_health_check_messages(self) -> List[Message]:
        """
        Generate health check messages for active agents.
        
        Returns:
            List of health check messages
        """
        messages = []
        
        # Check if health check is enabled
        if not self.config.get("health_check_enabled", True):
            return messages
        
        # Get active agents
        active_agents = self.get_active_agents()
        
        # Generate health check messages
        for agent_id in active_agents:
            messages.append(
                CommandMessage(
                    source_agent_id="core_hub",
                    target_agent_id=agent_id,
                    command="health_check",
                    parameters={},
                    priority="low"
                )
            )
        
        return messages
    
    def check_dependencies(self) -> Dict[str, List[str]]:
        """
        Check dependencies for all agents.
        
        Returns:
            Dictionary mapping agent IDs to lists of missing dependencies
        """
        dependency_status = {}
        
        # Check dependencies for each agent
        for agent_id, dependencies in self.agent_dependencies.items():
            # Skip if agent is not active
            if self.registered_agents.get(agent_id, {}).get("status") != "active":
                continue
            
            # Check dependencies
            missing_dependencies = []
            for dependency in dependencies:
                # Check if any agent provides the capability
                if dependency in self.agent_capabilities and self.agent_capabilities[dependency]:
                    # Check if any provider is active
                    providers = self.agent_capabilities[dependency]
                    active_providers = [
                        provider
                        for provider in providers
                        if self.registered_agents.get(provider, {}).get("status") == "active"
                    ]
                    
                    if not active_providers:
                        missing_dependencies.append(dependency)
                else:
                    missing_dependencies.append(dependency)
            
            # Store missing dependencies
            if missing_dependencies:
                dependency_status[agent_id] = missing_dependencies
        
        return dependency_status
    
    def _save_state(self) -> bool:
        """
        Save the Agent Manager state to a file.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create state dictionary
            state = {
                "registered_agents": self.registered_agents,
                "agent_capabilities": {
                    capability: list(agents)
                    for capability, agents in self.agent_capabilities.items()
                },
                "agent_subscriptions": {
                    agent_id: list(subscriptions)
                    for agent_id, subscriptions in self.agent_subscriptions.items()
                },
                "agent_dependencies": {
                    agent_id: list(dependencies)
                    for agent_id, dependencies in self.agent_dependencies.items()
                },
                "saved_at": time.ctime()
            }
            
            # Write state to file
            with open(self.state_file, "w") as f:
                json.dump(state, f, indent=2)
            
            self.logger.debug(f"Agent Manager state saved to {self.state_file}")
            
            return True
        
        except Exception as e:
            self.logger.error(f"Error saving Agent Manager state: {e}")
            return False
    
    def _load_state(self) -> bool:
        """
        Load the Agent Manager state from a file.
        
        Returns:
            True if successful, False otherwise
        """
        # Check if state file exists
        if not os.path.exists(self.state_file):
            self.logger.info(f"Agent Manager state file {self.state_file} does not exist")
            return False
        
        try:
            # Read state from file
            with open(self.state_file, "r") as f:
                state = json.load(f)
            
            # Restore state
            self.registered_agents = state.get("registered_agents", {})
            
            # Restore agent capabilities
            self.agent_capabilities = {}
            for capability, agents in state.get("agent_capabilities", {}).items():
                self.agent_capabilities[capability] = set(agents)
            
            # Restore agent subscriptions
            self.agent_subscriptions = {}
            for agent_id, subscriptions in state.get("agent_subscriptions", {}).items():
                self.agent_subscriptions[agent_id] = set(subscriptions)
            
            # Restore agent dependencies
            self.agent_dependencies = {}
            for agent_id, dependencies in state.get("agent_dependencies", {}).items():
                self.agent_dependencies[agent_id] = set(dependencies)
            
            self.logger.info(f"Agent Manager state loaded from {self.state_file}")
            self.logger.info(f"Restored {len(self.registered_agents)} registered agents")
            
            return True
        
        except Exception as e:
            self.logger.error(f"Error loading Agent Manager state: {e}")
            return False
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        Get the status of the agent system.
        
        Returns:
            System status information
        """
        # Count agents by status
        status_count = {}
        for agent_info in self.registered_agents.values():
            status = agent_info.get("status", "unknown")
            status_count[status] = status_count.get(status, 0) + 1
        
        return {
            "agents": {
                "total": len(self.registered_agents),
                "by_status": status_count
            },
            "capabilities": {
                "total": len(self.agent_capabilities),
                "details": {
                    capability: len(agents)
                    for capability, agents in self.agent_capabilities.items()
                }
            },
            "health_check": {
                "last_check": self.last_health_check,
                "interval": self.health_check_interval
            }
        }


def create_agent_manager(config: Dict[str, Any], data_dir: str) -> AgentManager:
    """
    Create an Agent Manager with the specified configuration.
    
    Args:
        config: Agent manager configuration
        data_dir: Data directory for persistence
        
    Returns:
        Configured Agent Manager
    """
    return AgentManager(config, data_dir)