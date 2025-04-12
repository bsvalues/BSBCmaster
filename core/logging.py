"""
Logging Module for Benton County Assessor's Office AI Platform

This module provides structured logging capabilities for the Core Hub
and agent components, including configurable file and console handlers,
log rotation, and JSON formatting for enhanced analysis.
"""

import os
import sys
import json
import logging
import logging.handlers
from typing import Dict, Any, Optional, Union, List
from datetime import datetime


class StructuredLogFormatter(logging.Formatter):
    """
    Custom log formatter that outputs structured logs in JSON format.
    """
    
    def __init__(self, include_context: bool = True):
        """
        Initialize the structured log formatter.
        
        Args:
            include_context: Whether to include context information in logs
        """
        super().__init__()
        self.include_context = include_context
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format the log record as a JSON string.
        
        Args:
            record: The log record to format
            
        Returns:
            JSON-formatted log string
        """
        # Base log structure
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "module": record.module,
            "name": record.name,
            "message": record.getMessage()
        }
        
        # Add exception info if present
        if record.exc_info:
            exc_type = record.exc_info[0]
            exc_type_name = exc_type.__name__ if exc_type else "Exception"
            log_data["exception"] = {
                "type": exc_type_name,
                "message": str(record.exc_info[1]) if record.exc_info[1] else "",
                "traceback": self.formatException(record.exc_info)
            }
        
        # Add context attributes if present and enabled
        if self.include_context:
            # Safely get context from extra dict if it exists
            context = {}
            if hasattr(record, "extra") and isinstance(record.extra, dict):
                context = record.extra.get("context", {})
            elif hasattr(record, "context") and record.context:
                context = record.context
                
            if context:
                log_data["context"] = context
        
        # Return JSON-formatted string
        return json.dumps(log_data)


class LogManager:
    """
    Log manager for the Core Hub and agent components.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the log manager.
        
        Args:
            config: Logging configuration
        """
        self.config = config
        self.root_logger = logging.getLogger("core")
        self.handlers = {}
        self.loggers = {}
        
        # Configure logging
        self._configure_logging()
    
    def _configure_logging(self) -> None:
        """Configure logging based on configuration."""
        # Get basic configuration
        log_level = self._get_log_level(self.config.get("log_level", "info"))
        log_dir = self.config.get("log_dir", "logs/core")
        
        # Ensure log directory exists
        os.makedirs(log_dir, exist_ok=True)
        
        # Set root logger level
        self.root_logger.setLevel(log_level)
        
        # Create console handler if enabled
        if self.config.get("console", {}).get("enabled", True):
            self._add_console_handler()
        
        # Create file handler if enabled
        if self.config.get("file", {}).get("enabled", True):
            self._add_file_handler(log_dir)
        
        # Prevent propagation to root logger to avoid duplicate logs
        if not self.config.get("propagate", False):
            self.root_logger.propagate = False
    
    def _get_log_level(self, level: str) -> int:
        """
        Convert string log level to logging module level.
        
        Args:
            level: String log level (debug, info, warning, error, critical)
            
        Returns:
            Logging module level
        """
        level_map = {
            "debug": logging.DEBUG,
            "info": logging.INFO,
            "warning": logging.WARNING,
            "error": logging.ERROR,
            "critical": logging.CRITICAL
        }
        
        return level_map.get(level.lower(), logging.INFO)
    
    def _add_console_handler(self) -> None:
        """Add console handler to root logger."""
        console_config = self.config.get("console", {})
        
        # Create handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(self._get_log_level(console_config.get("level", "info")))
        
        # Add formatter
        if console_config.get("structured", False):
            handler.setFormatter(StructuredLogFormatter(
                include_context=console_config.get("include_context", True)
            ))
        else:
            handler.setFormatter(logging.Formatter(
                console_config.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            ))
        
        # Add handler to root logger
        self.root_logger.addHandler(handler)
        self.handlers["console"] = handler
    
    def _add_file_handler(self, log_dir: str) -> None:
        """
        Add file handler to root logger.
        
        Args:
            log_dir: Directory for log files
        """
        file_config = self.config.get("file", {})
        
        # Determine log file path
        log_file = os.path.join(
            log_dir, 
            file_config.get("filename", "core.log")
        )
        
        # Create handler with rotation
        max_bytes = file_config.get("max_bytes", 10 * 1024 * 1024)  # 10 MB default
        backup_count = file_config.get("backup_count", 5)
        
        handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        
        handler.setLevel(self._get_log_level(file_config.get("level", "debug")))
        
        # Add formatter
        if file_config.get("structured", True):
            handler.setFormatter(StructuredLogFormatter(
                include_context=file_config.get("include_context", True)
            ))
        else:
            handler.setFormatter(logging.Formatter(
                file_config.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            ))
        
        # Add handler to root logger
        self.root_logger.addHandler(handler)
        self.handlers["file"] = handler
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        Get a logger with the specified name.
        
        Args:
            name: Logger name
            
        Returns:
            Configured logger
        """
        if name in self.loggers:
            return self.loggers[name]
        
        # Create a child logger of the root logger
        logger = logging.getLogger(f"core.{name}")
        
        # Store the logger
        self.loggers[name] = logger
        
        return logger


class ContextAdapter(logging.LoggerAdapter):
    """
    Logger adapter that adds context information to log records.
    """
    
    def __init__(self, logger: logging.Logger, extra: Optional[Dict[str, Any]] = None):
        """
        Initialize the context adapter.
        
        Args:
            logger: Base logger
            extra: Extra context information
        """
        super().__init__(logger, extra or {})
    
    def process(self, msg: str, kwargs: Any) -> tuple:
        """
        Process the log message and add context information.
        
        Args:
            msg: Log message
            kwargs: Keyword arguments
            
        Returns:
            Tuple with processed message and kwargs
        """
        # Initialize kwargs if needed
        if kwargs is None:
            kwargs = {}
        
        # Ensure kwargs is a dictionary (might be MutableMapping in base class)
        if not isinstance(kwargs, dict):
            kwargs = dict(kwargs)
            
        if "extra" not in kwargs:
            kwargs["extra"] = {}
        
        if "context" not in kwargs["extra"]:
            kwargs["extra"]["context"] = {}
        
        # Add adapter context to record context (safely)
        if self.extra:
            for key, value in self.extra.items():
                kwargs["extra"]["context"][key] = value
        
        return msg, kwargs
    
    def with_context(self, **context) -> 'ContextAdapter':
        """
        Create a new adapter with additional context.
        
        Args:
            **context: Context key-value pairs
            
        Returns:
            New context adapter with merged context
        """
        # Create a new extra dictionary, safely handling None
        new_extra = {}
        if hasattr(self, 'extra') and self.extra is not None:
            if hasattr(self.extra, 'copy'):
                new_extra = self.extra.copy()
            else:
                new_extra = dict(self.extra)
                
        # Update with new context
        if context:
            new_extra.update(context)
            
        return ContextAdapter(self.logger, new_extra)


def create_log_manager(config: Dict[str, Any]) -> LogManager:
    """
    Create a log manager with the specified configuration.
    
    Args:
        config: Logging configuration
        
    Returns:
        Configured log manager
    """
    return LogManager(config)


def create_logger(name: str, context: Optional[Dict[str, Any]] = None) -> ContextAdapter:
    """
    Create a logger with the specified name and context.
    
    Args:
        name: Logger name
        context: Initial logger context
        
    Returns:
        Configured logger adapter
    """
    logger = logging.getLogger(f"core.{name}")
    return ContextAdapter(logger, context or {})