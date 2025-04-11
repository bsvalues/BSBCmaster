"""
Test Configuration Module

This module provides configuration settings for the test framework,
including test data paths, test environment setup, and test parameters.
"""

import os
import json
from typing import Dict, Any, Optional, List
import logging


class TestConfig:
    """
    Configuration settings for the test framework.
    
    This class manages test configuration options, including data paths,
    environment settings, and test parameters.
    """
    
    # Default configuration values
    DEFAULT_CONFIG = {
        # Test data settings
        "test_data_path": "testing/test_data",
        "authentic_data_only": True,
        
        # Test execution settings
        "parallel_tests": False,
        "max_workers": 4,
        "test_timeout": 30,  # seconds
        
        # Logging settings
        "log_level": "INFO",
        "log_dir": "logs/testing",
        
        # Agent testing settings
        "use_agent_coordinator": True,
        "record_agent_performance": True,
        
        # Database testing settings
        "use_test_database": True,
        "preserve_test_data": False,
        
        # Test coverage settings
        "coverage_threshold": 80,  # percent
        "generate_coverage_report": True,
        
        # Washington State-specific test settings
        "wa_compliance_check": True,
        "benton_county_specific_checks": True,
        
        # Test categories and weights
        "test_categories": {
            "validation": 30,
            "compliance": 30,
            "performance": 20,
            "integration": 20
        }
    }
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize test configuration.
        
        Args:
            config_path: Path to configuration JSON file (None = use defaults)
        """
        self.config = self.DEFAULT_CONFIG.copy()
        
        # Load from file if provided
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    loaded_config = json.load(f)
                
                # Update default config with loaded values
                self.config.update(loaded_config)
                logging.info(f"Loaded test configuration from {config_path}")
            except Exception as e:
                logging.error(f"Error loading test configuration: {e}")
        
        # Set up logging
        self._setup_logging()
    
    def _setup_logging(self) -> None:
        """Configure logging based on settings."""
        log_level = getattr(logging, self.config["log_level"], logging.INFO)
        log_dir = self.config["log_dir"]
        
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, "testing.log")
            
            logging.basicConfig(
                level=log_level,
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                handlers=[
                    logging.FileHandler(log_file),
                    logging.StreamHandler()
                ]
            )
        else:
            logging.basicConfig(
                level=log_level,
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key is not found
        
        Returns:
            Value for the given key, or default if not found
        """
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value.
        
        Args:
            key: Configuration key
            value: Configuration value
        """
        self.config[key] = value
    
    def is_enabled(self, feature: str) -> bool:
        """
        Check if a feature is enabled.
        
        Args:
            feature: Feature name (e.g., 'use_agent_coordinator')
        
        Returns:
            True if the feature is enabled, False otherwise
        """
        return bool(self.config.get(feature, False))
    
    def save(self, config_path: str) -> None:
        """
        Save configuration to a file.
        
        Args:
            config_path: Path to save configuration JSON file
        """
        try:
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            logging.info(f"Saved test configuration to {config_path}")
        except Exception as e:
            logging.error(f"Error saving test configuration: {e}")
    
    def get_test_categories(self) -> Dict[str, int]:
        """
        Get test categories and their weights.
        
        Returns:
            Dictionary mapping category names to weights
        """
        return self.config.get("test_categories", {})
    
    def get_test_data_path(self, category: Optional[str] = None) -> str:
        """
        Get path to test data directory.
        
        Args:
            category: Optional subcategory of test data
        
        Returns:
            Path to test data directory
        """
        base_path = self.config.get("test_data_path", "testing/test_data")
        if category:
            return os.path.join(base_path, category)
        return base_path