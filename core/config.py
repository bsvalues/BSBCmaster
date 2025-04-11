"""
Core Configuration Module for Benton County Assessor's Office AI Platform

This module provides the central configuration for the Core, MCP, and Agent Army,
defining roles, communication protocols, and master prompt directives.
"""

import os
import json
import yaml
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
import datetime


# Default master prompt for all agents
MASTER_PROMPT = """
Attention all agents: As part of our integrated system, each agent is responsible for executing its domain-specific tasks while maintaining communication using our standard JSON messaging format. The Core serves as the master hub, ensuring configuration consistency and orchestrating cross-module activities. The Replit AI Agent is your real-time coordinator, while the MCP monitors overall performance and directs task assignments when issues occur.

Every action you perform must be logged in the shared replay buffer. On completion of every major task, review your performance metrics and, if performance thresholds are not met, issue a 'task_request' for assistance. Furthermore, please ensure that you adhere to our established protocols for communication and security. Report any anomalies immediately to the MCP.

This directive remains effective in both standalone and integrated modes. Adapt and execute tasks based on real-time feedback while maintaining alignment with the overall system objectives. Your collaborative efforts drive continuous improvement and system optimization. End of directive.
"""


class CoreConfig:
    """
    Core configuration for the AI platform.
    
    This class provides configuration settings for the Core, MCP, 
    and Agent Army, and handles loading and saving configuration files.
    """
    
    # Default configuration values
    DEFAULT_CONFIG = {
        # Core settings
        "core": {
            "name": "BentonCountyAssessorCore",
            "version": "3.0.0",
            "log_level": "INFO",
            "log_dir": "logs/core",
            "data_dir": "data/core",
            "master_prompt": MASTER_PROMPT,
            "master_prompt_refresh_interval": 3600  # seconds
        },
        
        # Communication settings
        "communication": {
            "protocol": "redis",  # redis, mqtt, rest
            "message_format": "json",
            "retry_attempts": 3,
            "retry_delay": 1.0,  # seconds
            "timeout": 30.0,  # seconds
            "heartbeat_interval": 60.0,  # seconds
            "redis": {
                "host": "localhost",
                "port": 6379,
                "db": 0,
                "password": None,
                "channels": {
                    "commands": "benton.commands",
                    "events": "benton.events",
                    "heartbeats": "benton.heartbeats",
                    "errors": "benton.errors",
                    "status": "benton.status"
                }
            },
            "mqtt": {
                "broker": "localhost",
                "port": 1883,
                "username": None,
                "password": None,
                "topics": {
                    "commands": "benton/commands",
                    "events": "benton/events",
                    "heartbeats": "benton/heartbeats",
                    "errors": "benton/errors",
                    "status": "benton/status"
                }
            },
            "rest": {
                "host": "localhost",
                "port": 8000,
                "base_url": "/api/v1",
                "endpoints": {
                    "commands": "/commands",
                    "events": "/events",
                    "heartbeats": "/heartbeats",
                    "errors": "/errors",
                    "status": "/status"
                }
            }
        },
        
        # MCP settings
        "mcp": {
            "name": "MasterControlProgram",
            "host": "localhost",
            "port": 8001,
            "log_level": "INFO",
            "log_dir": "logs/mcp",
            "data_dir": "data/mcp",
            "max_agents": 50,
            "performance_check_interval": 300,  # seconds
            "task_timeout": 120,  # seconds
            "max_retry_attempts": 3
        },
        
        # Agent Army settings
        "agent_army": {
            "log_dir": "logs/agents",
            "data_dir": "data/agents",
            "default_log_level": "INFO",
            "shared_replay_buffer": True,
            "agents": [
                {
                    "name": "DataQualityAgent",
                    "type": "data_quality",
                    "description": "Validates property assessment data against Washington State standards",
                    "capabilities": ["validate_data", "detect_anomalies", "enhance_data"],
                    "performance_threshold": 0.7,
                    "enabled": True
                },
                {
                    "name": "ComplianceAgent",
                    "type": "compliance",
                    "description": "Ensures compliance with Washington State assessment regulations",
                    "capabilities": ["check_compliance", "verify_exemption", "create_audit_record"],
                    "performance_threshold": 0.8,
                    "enabled": True
                },
                {
                    "name": "ValuationAgent",
                    "type": "valuation",
                    "description": "Calculates property values using advanced models",
                    "capabilities": ["estimate_value", "analyze_trends", "compare_properties"],
                    "performance_threshold": 0.75,
                    "enabled": False  # Will be enabled in Phase 3
                },
                {
                    "name": "UserInteractionAgent",
                    "type": "user_interaction",
                    "description": "Handles staff queries and interface interactions",
                    "capabilities": ["answer_query", "provide_recommendation", "explain_result"],
                    "performance_threshold": 0.8,
                    "enabled": False  # Will be enabled in Phase 3
                }
            ]
        },
        
        # Experience replay buffer settings
        "replay_buffer": {
            "type": "redis",  # redis, postgres, file
            "capacity": 100000,
            "alpha": 0.6,  # Prioritization factor
            "beta": 0.4,  # Importance sampling factor
            "beta_increment": 0.001,
            "save_dir": "data/experiences",
            "redis": {
                "host": "localhost",
                "port": 6379,
                "db": 1,
                "password": None,
                "key_prefix": "benton:experience:"
            },
            "postgres": {
                "host": "localhost",
                "port": 5432,
                "database": "benton_experiences",
                "user": "postgres",
                "password": None,
                "table_name": "experiences"
            }
        },
        
        # Training settings
        "training": {
            "enabled": True,
            "trigger_type": "size",  # size, time, manual
            "size_threshold": 1000,  # Min experiences before training
            "time_interval": 3600,  # seconds
            "batch_size": 64,
            "save_dir": "data/models",
            "log_dir": "logs/training"
        },
        
        # Monitoring settings
        "monitoring": {
            "enabled": True,
            "dashboard_type": "streamlit",  # streamlit, grafana, custom
            "port": 8501,
            "refresh_interval": 10,  # seconds
            "metrics": [
                "agent_status",
                "message_throughput",
                "task_throughput",
                "error_rate",
                "response_time",
                "replay_buffer_size",
                "training_cycles"
            ],
            "log_dir": "logs/monitoring",
            "alert_thresholds": {
                "error_rate": 0.1,
                "response_time": 5.0,  # seconds
                "agent_downtime": 300  # seconds
            }
        },
        
        # Security settings
        "security": {
            "encrypt_messages": True,
            "authentication_required": True,
            "api_key_header": "X-API-Key",
            "token_expiration": 86400  # seconds (24 hours)
        }
    }
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize core configuration.
        
        Args:
            config_path: Path to configuration file (YAML or JSON)
        """
        self.config_path = config_path
        self.config = self.DEFAULT_CONFIG.copy()
        
        # Set up logging
        self._setup_logging()
        
        # Load configuration from file if provided
        if config_path:
            self.load_config(config_path)
    
    def _setup_logging(self) -> None:
        """Set up logging for the core configuration."""
        log_dir = self.config["core"]["log_dir"]
        os.makedirs(log_dir, exist_ok=True)
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f"core_config_{timestamp}.log")
        
        logging.basicConfig(
            level=getattr(logging, self.config["core"]["log_level"]),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger("core_config")
    
    def load_config(self, config_path: str) -> bool:
        """
        Load configuration from a file.
        
        Args:
            config_path: Path to configuration file (YAML or JSON)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not os.path.exists(config_path):
                self.logger.warning(f"Configuration file not found: {config_path}")
                return False
            
            with open(config_path, 'r') as f:
                if config_path.endswith('.json'):
                    loaded_config = json.load(f)
                elif config_path.endswith(('.yaml', '.yml')):
                    loaded_config = yaml.safe_load(f)
                else:
                    self.logger.error(f"Unsupported configuration file format: {config_path}")
                    return False
            
            # Update configuration with loaded values
            self._update_config_recursive(self.config, loaded_config)
            
            self.logger.info(f"Configuration loaded from {config_path}")
            return True
        
        except Exception as e:
            self.logger.error(f"Error loading configuration from {config_path}: {e}")
            return False
    
    def _update_config_recursive(self, target: Dict, source: Dict) -> None:
        """
        Update target dictionary with values from source dictionary recursively.
        
        Args:
            target: Target dictionary to update
            source: Source dictionary with new values
        """
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._update_config_recursive(target[key], value)
            else:
                target[key] = value
    
    def save_config(self, config_path: Optional[str] = None) -> bool:
        """
        Save configuration to a file.
        
        Args:
            config_path: Path to save configuration file (YAML or JSON)
            
        Returns:
            True if successful, False otherwise
        """
        if config_path is None:
            config_path = self.config_path
        
        if config_path is None:
            self.logger.error("No configuration path specified")
            return False
        
        try:
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            
            with open(config_path, 'w') as f:
                if config_path.endswith('.json'):
                    json.dump(self.config, f, indent=2)
                elif config_path.endswith(('.yaml', '.yml')):
                    yaml.dump(self.config, f, default_flow_style=False)
                else:
                    self.logger.error(f"Unsupported configuration file format: {config_path}")
                    return False
            
            self.logger.info(f"Configuration saved to {config_path}")
            return True
        
        except Exception as e:
            self.logger.error(f"Error saving configuration to {config_path}: {e}")
            return False
    
    def get(self, section: str, key: Optional[str] = None, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            section: Configuration section
            key: Configuration key within section (None = return entire section)
            default: Default value if key is not found
            
        Returns:
            Configuration value, section, or default
        """
        if section not in self.config:
            return default
        
        if key is None:
            return self.config[section]
        
        return self.config[section].get(key, default)
    
    def set(self, section: str, key: str, value: Any) -> bool:
        """
        Set a configuration value.
        
        Args:
            section: Configuration section
            key: Configuration key within section
            value: Configuration value
            
        Returns:
            True if successful, False otherwise
        """
        if section not in self.config:
            self.logger.error(f"Configuration section not found: {section}")
            return False
        
        self.config[section][key] = value
        return True
    
    def get_master_prompt(self) -> str:
        """
        Get the master prompt for all agents.
        
        Returns:
            Master prompt string
        """
        return self.config["core"]["master_prompt"]
    
    def set_master_prompt(self, prompt: str) -> None:
        """
        Set the master prompt for all agents.
        
        Args:
            prompt: Master prompt string
        """
        self.config["core"]["master_prompt"] = prompt
    
    def get_enabled_agents(self) -> List[Dict[str, Any]]:
        """
        Get a list of enabled agents.
        
        Returns:
            List of enabled agent configurations
        """
        return [
            agent for agent in self.config["agent_army"]["agents"]
            if agent.get("enabled", True)
        ]
    
    def get_agent_config(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a specific agent.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Agent configuration or None if not found
        """
        for agent in self.config["agent_army"]["agents"]:
            if agent["name"] == agent_name:
                return agent
        
        return None
    
    def get_communication_config(self) -> Dict[str, Any]:
        """
        Get communication configuration based on selected protocol.
        
        Returns:
            Communication configuration for the selected protocol
        """
        comm_config = self.config["communication"]
        protocol = comm_config["protocol"]
        
        return {
            "protocol": protocol,
            "message_format": comm_config["message_format"],
            "retry_attempts": comm_config["retry_attempts"],
            "retry_delay": comm_config["retry_delay"],
            "timeout": comm_config["timeout"],
            "heartbeat_interval": comm_config["heartbeat_interval"],
            "settings": comm_config.get(protocol, {})
        }
    
    def get_replay_buffer_config(self) -> Dict[str, Any]:
        """
        Get replay buffer configuration based on selected type.
        
        Returns:
            Replay buffer configuration for the selected type
        """
        buffer_config = self.config["replay_buffer"]
        buffer_type = buffer_config["type"]
        
        return {
            "type": buffer_type,
            "capacity": buffer_config["capacity"],
            "alpha": buffer_config["alpha"],
            "beta": buffer_config["beta"],
            "beta_increment": buffer_config["beta_increment"],
            "save_dir": buffer_config["save_dir"],
            "settings": buffer_config.get(buffer_type, {})
        }