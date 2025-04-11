"""
Configuration Module for Benton County Assessor's Office AI Platform

This module provides configuration management for the Core Hub,
including loading from files, validation, and defaults.
"""

import os
import json
import yaml
import logging
from typing import Dict, Any, List, Optional, Union


class CoreConfig:
    """
    Configuration manager for the Core Hub.
    
    This class provides methods for loading, saving, and accessing
    configuration settings for the Core Hub and related components.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the configuration manager.
        
        Args:
            config_path: Path to configuration file
        """
        # Set up logging
        self.logger = logging.getLogger("core_config")
        
        # Initialize configuration with defaults
        self.config = self._get_default_config()
        
        # Load configuration from file if provided
        if config_path:
            self.load_config(config_path)
    
    def _get_default_config(self) -> Dict[str, Any]:
        """
        Get default configuration.
        
        Returns:
            Dictionary with default configuration
        """
        return {
            "core": {
                "name": "BentonCountyAssessorCore",
                "version": "3.0.0",
                "data_dir": "data/core",
                "master_prompt_refresh_interval": 3600  # seconds
            },
            "logging": {
                "log_level": "info",
                "log_dir": "logs/core",
                "console": {
                    "enabled": True,
                    "level": "info",
                    "structured": False,
                    "include_context": True,
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                },
                "file": {
                    "enabled": True,
                    "level": "debug",
                    "structured": True,
                    "include_context": True,
                    "filename": "core.log",
                    "max_bytes": 10485760,  # 10 MB
                    "backup_count": 5
                },
                "propagate": False
            },
            "communication": {
                "protocol": "rest",  # rest, redis, mqtt
                "host": "localhost",
                "rest": {
                    "host": "0.0.0.0",
                    "port": 8000,
                    "api_prefix": "/api/v1/core"
                },
                "redis": {
                    "host": "localhost",
                    "port": 6379,
                    "db": 0,
                    "channels": {
                        "commands": "core:commands",
                        "events": "core:events",
                        "errors": "core:errors",
                        "status": "core:status"
                    }
                },
                "mqtt": {
                    "broker": "localhost",
                    "port": 1883,
                    "topics": {
                        "commands": "core/commands",
                        "events": "core/events",
                        "errors": "core/errors",
                        "status": "core/status"
                    }
                }
            },
            "agents": {
                "enabled": [
                    {
                        "id": "data_quality_agent",
                        "name": "Data Quality Agent",
                        "type": "data_quality",
                        "description": "Validates property assessment data against Washington State standards",
                        "capabilities": ["validate_data", "detect_anomalies", "enhance_data"],
                        "enabled": True
                    },
                    {
                        "id": "compliance_agent",
                        "name": "Compliance Agent",
                        "type": "compliance",
                        "description": "Ensures compliance with Washington State assessment regulations",
                        "capabilities": ["check_compliance", "verify_exemption", "create_audit_record"],
                        "enabled": True
                    },
                    {
                        "id": "valuation_agent",
                        "name": "Valuation Agent",
                        "type": "valuation",
                        "description": "Calculates property values using advanced models",
                        "capabilities": ["estimate_value", "analyze_trends", "compare_properties"],
                        "enabled": False  # Not yet implemented
                    },
                    {
                        "id": "tax_agent",
                        "name": "Tax Calculation Agent",
                        "type": "tax",
                        "description": "Calculates property taxes based on mill rates and exemptions",
                        "capabilities": ["calculate_tax", "apply_exemptions", "generate_tax_report"],
                        "enabled": False  # Not yet implemented
                    },
                    {
                        "id": "user_agent",
                        "name": "User Interaction Agent",
                        "type": "user_interaction",
                        "description": "Handles user queries and interactions",
                        "capabilities": ["process_query", "generate_response", "follow_up"],
                        "enabled": False  # Not yet implemented
                    }
                ]
            },
            "replay_buffer": {
                "type": "memory",  # memory, file, redis
                "capacity": 10000,
                "alpha": 0.6,  # prioritization factor
                "beta": 0.4,  # importance sampling factor
                "beta_increment": 0.001,
                "file": {
                    "save_dir": "data/core/replay_buffer"
                },
                "redis": {
                    "host": "localhost",
                    "port": 6379,
                    "db": 1,
                    "key_prefix": "replay:"
                }
            },
            "dashboard": {
                "enabled": True,
                "type": "streamlit",  # streamlit, flask
                "host": "0.0.0.0",
                "port": 8501,
                "update_interval": 10,  # seconds
                "metrics_history_size": 100
            },
            "master_prompt": (
                "You are an AI assistant working for the Benton County Assessor's Office. "
                "Your role is to help with property assessment, valuation, and tax calculations "
                "in accordance with Washington State law and Benton County regulations. "
                "Always be helpful, accurate, and compliant with all applicable regulations. "
                "Focus on providing factual information and follow the specific "
                "guidelines for your agent type."
            )
        }
    
    def load_config(self, config_path: str) -> bool:
        """
        Load configuration from file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not os.path.exists(config_path):
                self.logger.warning(f"Configuration file not found: {config_path}")
                return False
            
            # Determine file type based on extension
            _, ext = os.path.splitext(config_path)
            
            if ext.lower() in ['.yaml', '.yml']:
                with open(config_path, 'r') as f:
                    loaded_config = yaml.safe_load(f)
            elif ext.lower() == '.json':
                with open(config_path, 'r') as f:
                    loaded_config = json.load(f)
            else:
                self.logger.error(f"Unsupported configuration file type: {ext}")
                return False
            
            # Merge loaded config with defaults
            self._merge_config(loaded_config)
            
            self.logger.info(f"Loaded configuration from {config_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading configuration: {e}")
            return False
    
    def _merge_config(self, loaded_config: Dict[str, Any]) -> None:
        """
        Merge loaded configuration with defaults.
        
        Args:
            loaded_config: Loaded configuration
        """
        def _merge_dicts(base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
            """Merge two dictionaries recursively."""
            for key, value in overlay.items():
                if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                    _merge_dicts(base[key], value)
                else:
                    base[key] = value
            return base
        
        _merge_dicts(self.config, loaded_config)
    
    def save_config(self, config_path: str, format: str = 'json') -> bool:
        """
        Save configuration to file.
        
        Args:
            config_path: Path to configuration file
            format: Format to save in ('json' or 'yaml')
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            
            if format.lower() == 'yaml':
                with open(config_path, 'w') as f:
                    yaml.dump(self.config, f, default_flow_style=False)
            else:
                with open(config_path, 'w') as f:
                    json.dump(self.config, f, indent=2)
            
            self.logger.info(f"Saved configuration to {config_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving configuration: {e}")
            return False
    
    def get(self, key: Optional[str] = None, default: Any = None) -> Any:
        """
        Get configuration value.
        
        Args:
            key: Configuration key (dot notation for nested keys, e.g., 'core.name')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        if key is None:
            return self.config
        
        # Handle dot notation
        parts = key.split('.')
        value = self.config
        
        try:
            for part in parts:
                value = value[part]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any) -> bool:
        """
        Set configuration value.
        
        Args:
            key: Configuration key (dot notation for nested keys, e.g., 'core.name')
            value: Value to set
            
        Returns:
            True if successful, False otherwise
        """
        # Handle dot notation
        parts = key.split('.')
        config = self.config
        
        try:
            # Navigate to the parent of the target key
            for part in parts[:-1]:
                if part not in config:
                    config[part] = {}
                config = config[part]
            
            # Set the value
            config[parts[-1]] = value
            return True
            
        except Exception as e:
            self.logger.error(f"Error setting configuration: {e}")
            return False
    
    def get_master_prompt(self) -> str:
        """
        Get the master prompt.
        
        Returns:
            Master prompt string
        """
        return self.config.get("master_prompt", "")
    
    def set_master_prompt(self, prompt: str) -> bool:
        """
        Set the master prompt.
        
        Args:
            prompt: Master prompt string
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.config["master_prompt"] = prompt
            return True
        except Exception as e:
            self.logger.error(f"Error setting master prompt: {e}")
            return False
    
    def get_enabled_agents(self) -> List[Dict[str, Any]]:
        """
        Get list of enabled agents.
        
        Returns:
            List of enabled agent configurations
        """
        try:
            agents = self.config.get("agents", {}).get("enabled", [])
            return [agent for agent in agents if agent.get("enabled", False)]
        except Exception as e:
            self.logger.error(f"Error getting enabled agents: {e}")
            return []
    
    def get_agent_config(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a specific agent.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Agent configuration or None if not found
        """
        try:
            agents = self.config.get("agents", {}).get("enabled", [])
            for agent in agents:
                if agent.get("id") == agent_id:
                    return agent
            return None
        except Exception as e:
            self.logger.error(f"Error getting agent configuration: {e}")
            return None
    
    def get_communication_config(self) -> Dict[str, Any]:
        """
        Get communication configuration.
        
        Returns:
            Communication configuration
        """
        return self.config.get("communication", {})
    
    def get_replay_buffer_config(self) -> Dict[str, Any]:
        """
        Get replay buffer configuration.
        
        Returns:
            Replay buffer configuration
        """
        return self.config.get("replay_buffer", {})
    
    def get_dashboard_config(self) -> Dict[str, Any]:
        """
        Get dashboard configuration.
        
        Returns:
            Dashboard configuration
        """
        return self.config.get("dashboard", {})
        
    def get_logging_config(self) -> Dict[str, Any]:
        """
        Get logging configuration.
        
        Returns:
            Logging configuration
        """
        return self.config.get("logging", {})