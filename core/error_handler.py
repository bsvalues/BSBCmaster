"""
Error Handler Module for Benton County Assessor's Office AI Platform

This module provides centralized error handling for the Core Hub,
including error reporting, classification, and recovery.
"""

import os
import json
import time
import logging
import traceback
from typing import Dict, Any, List, Optional, Callable, Union, Set, Tuple

from .logging import create_logger
from .message import Message, ErrorMessage


class ErrorLevel:
    """Error severity levels."""
    
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorCategory:
    """Error category classifications."""
    
    CONFIGURATION = "configuration"
    COMMUNICATION = "communication"
    VALIDATION = "validation"
    BUSINESS_LOGIC = "business_logic"
    PERSISTENCE = "persistence"
    RESOURCE = "resource"
    SECURITY = "security"
    UNKNOWN = "unknown"


class ErrorCode:
    """Common error codes."""
    
    # Configuration errors
    INVALID_CONFIG = "INVALID_CONFIG"
    MISSING_CONFIG = "MISSING_CONFIG"
    
    # Communication errors
    COMMUNICATION_FAILURE = "COMMUNICATION_FAILURE"
    MESSAGE_TIMEOUT = "MESSAGE_TIMEOUT"
    
    # Validation errors
    INVALID_INPUT = "INVALID_INPUT"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    
    # Business logic errors
    BUSINESS_RULE_VIOLATION = "BUSINESS_RULE_VIOLATION"
    CALCULATION_ERROR = "CALCULATION_ERROR"
    
    # Persistence errors
    STORAGE_ERROR = "STORAGE_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    
    # Resource errors
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    RESOURCE_UNAVAILABLE = "RESOURCE_UNAVAILABLE"
    
    # Security errors
    AUTHENTICATION_FAILURE = "AUTHENTICATION_FAILURE"
    AUTHORIZATION_FAILURE = "AUTHORIZATION_FAILURE"
    
    # Unknown errors
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


class Error:
    """
    Represents an error with detailed information.
    """
    
    def __init__(
        self,
        code: str,
        message: str,
        level: str = ErrorLevel.ERROR,
        category: str = ErrorCategory.UNKNOWN,
        details: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None,
        original_error: Optional[Exception] = None,
        timestamp: Optional[float] = None
    ):
        """
        Initialize the error.
        
        Args:
            code: Error code
            message: Error message
            level: Error severity level
            category: Error category
            details: Additional error details
            source: Error source
            original_error: Original exception
            timestamp: Error timestamp
        """
        self.code = code
        self.message = message
        self.level = level
        self.category = category
        self.details = details or {}
        self.source = source
        self.original_error = original_error
        self.timestamp = timestamp or time.time()
        
        # Add traceback if original error is provided
        if original_error:
            self.details["traceback"] = traceback.format_exception(
                type(original_error),
                original_error,
                original_error.__traceback__
            )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the error to a dictionary.
        
        Returns:
            Dictionary representation of the error
        """
        result = {
            "code": self.code,
            "message": self.message,
            "level": self.level,
            "category": self.category,
            "timestamp": self.timestamp
        }
        
        if self.details:
            result["details"] = self.details
        
        if self.source:
            result["source"] = self.source
        
        return result
    
    def to_message(self, source_agent_id: str, target_agent_id: str, correlation_id: Optional[str] = None) -> ErrorMessage:
        """
        Convert the error to an error message.
        
        Args:
            source_agent_id: Source agent ID
            target_agent_id: Target agent ID
            correlation_id: Correlation ID
            
        Returns:
            Error message
        """
        return ErrorMessage(
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_id,
            error_code=self.code,
            error_message=self.message,
            correlation_id=correlation_id,
            payload={
                "level": self.level,
                "category": self.category,
                "details": self.details,
                "timestamp": self.timestamp
            }
        )
    
    @classmethod
    def from_exception(
        cls,
        exception: Exception,
        code: Optional[str] = None,
        message: Optional[str] = None,
        level: str = ErrorLevel.ERROR,
        category: str = ErrorCategory.UNKNOWN,
        details: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None
    ) -> 'Error':
        """
        Create an error from an exception.
        
        Args:
            exception: Exception to convert
            code: Error code
            message: Error message
            level: Error severity level
            category: Error category
            details: Additional error details
            source: Error source
            
        Returns:
            Error object
        """
        return cls(
            code=code or ErrorCode.UNKNOWN_ERROR,
            message=message or str(exception),
            level=level,
            category=category,
            details=details or {},
            source=source,
            original_error=exception
        )


class ErrorHandler:
    """
    Error handler for the Core Hub.
    
    This class provides methods for handling, reporting, and recovering from errors.
    """
    
    def __init__(self, config: Dict[str, Any], data_dir: str):
        """
        Initialize the error handler.
        
        Args:
            config: Error handler configuration
            data_dir: Data directory for error logs
        """
        self.config = config
        self.data_dir = data_dir
        self.errors = []
        self.handlers = {}
        self.max_errors = config.get("max_errors", 1000)
        self.error_file = os.path.join(data_dir, "errors.json")
        
        # Create logger
        self.logger = create_logger("error_handler", {
            "component": "ErrorHandler"
        })
        
        # Ensure data directory exists
        os.makedirs(data_dir, exist_ok=True)
        
        # Load persisted errors if available
        self._load_errors()
        
        self.logger.info(f"Error Handler initialized with {len(self.errors)} previous errors")
    
    def handle_error(
        self,
        error: Union[Error, Exception, str],
        code: Optional[str] = None,
        level: str = ErrorLevel.ERROR,
        category: str = ErrorCategory.UNKNOWN,
        details: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None
    ) -> Error:
        """
        Handle an error.
        
        Args:
            error: Error to handle
            code: Error code
            level: Error severity level
            category: Error category
            details: Additional error details
            source: Error source
            
        Returns:
            Error object
        """
        # Convert error to Error object
        if isinstance(error, Error):
            error_obj = error
        elif isinstance(error, Exception):
            error_obj = Error.from_exception(
                error,
                code=code or ErrorCode.UNKNOWN_ERROR,
                level=level,
                category=category,
                details=details,
                source=source
            )
        else:
            error_obj = Error(
                code=code or ErrorCode.UNKNOWN_ERROR,
                message=str(error),
                level=level,
                category=category,
                details=details,
                source=source
            )
        
        # Add error to list
        self.errors.append(error_obj)
        
        # Trim errors if necessary
        if len(self.errors) > self.max_errors:
            self.errors = self.errors[-self.max_errors:]
        
        # Save errors periodically
        if len(self.errors) % 10 == 0:
            self._save_errors()
        
        # Log error
        self._log_error(error_obj)
        
        # Call error handlers
        self._call_handlers(error_obj)
        
        return error_obj
    
    def _log_error(self, error: Error) -> None:
        """
        Log an error.
        
        Args:
            error: Error to log
        """
        # Determine log level
        log_level = {
            ErrorLevel.DEBUG: logging.DEBUG,
            ErrorLevel.INFO: logging.INFO,
            ErrorLevel.WARNING: logging.WARNING,
            ErrorLevel.ERROR: logging.ERROR,
            ErrorLevel.CRITICAL: logging.CRITICAL
        }.get(error.level, logging.ERROR)
        
        # Log error with context
        extra = {
            "context": {
                "error_code": error.code,
                "error_category": error.category,
                "error_source": error.source
            }
        }
        
        # Add details if not too large
        if error.details and len(str(error.details)) < 1000:
            extra["context"]["error_details"] = error.details
        
        # Log the error
        self.logger.log(log_level, error.message, extra=extra)
    
    def _call_handlers(self, error: Error) -> None:
        """
        Call registered error handlers.
        
        Args:
            error: Error to handle
        """
        # Call handlers for specific error code
        if error.code in self.handlers:
            for handler in self.handlers[error.code]:
                try:
                    handler(error)
                except Exception as e:
                    self.logger.error(f"Error in error handler: {e}")
        
        # Call handlers for error category
        if error.category in self.handlers:
            for handler in self.handlers[error.category]:
                try:
                    handler(error)
                except Exception as e:
                    self.logger.error(f"Error in error handler: {e}")
        
        # Call handlers for error level
        if error.level in self.handlers:
            for handler in self.handlers[error.level]:
                try:
                    handler(error)
                except Exception as e:
                    self.logger.error(f"Error in error handler: {e}")
        
        # Call generic handlers
        if "all" in self.handlers:
            for handler in self.handlers["all"]:
                try:
                    handler(error)
                except Exception as e:
                    self.logger.error(f"Error in error handler: {e}")
    
    def register_handler(self, handler: Callable[[Error], None], key: str = "all") -> None:
        """
        Register an error handler.
        
        Args:
            handler: Function to call when an error occurs
            key: Error code, category, level, or 'all' for all errors
        """
        if key not in self.handlers:
            self.handlers[key] = []
        
        self.handlers[key].append(handler)
    
    def unregister_handler(self, handler: Callable[[Error], None], key: str = "all") -> bool:
        """
        Unregister an error handler.
        
        Args:
            handler: Handler to unregister
            key: Error code, category, level, or 'all'
            
        Returns:
            True if unregistered successfully, False otherwise
        """
        if key in self.handlers and handler in self.handlers[key]:
            self.handlers[key].remove(handler)
            return True
        else:
            return False
    
    def get_errors(
        self,
        code: Optional[str] = None,
        level: Optional[str] = None,
        category: Optional[str] = None,
        source: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        limit: int = 100
    ) -> List[Error]:
        """
        Get errors with optional filtering.
        
        Args:
            code: Error code filter
            level: Error level filter
            category: Error category filter
            source: Error source filter
            start_time: Start time filter
            end_time: End time filter
            limit: Maximum number of errors to return
            
        Returns:
            List of errors matching the filters
        """
        filtered_errors = []
        
        # Apply filters
        for error in reversed(self.errors):
            # Filter by code
            if code and error.code != code:
                continue
            
            # Filter by level
            if level and error.level != level:
                continue
            
            # Filter by category
            if category and error.category != category:
                continue
            
            # Filter by source
            if source and error.source != source:
                continue
            
            # Filter by start time
            if start_time and error.timestamp < start_time:
                continue
            
            # Filter by end time
            if end_time and error.timestamp > end_time:
                continue
            
            # Add error to filtered list
            filtered_errors.append(error)
            
            # Check limit
            if len(filtered_errors) >= limit:
                break
        
        return filtered_errors
    
    def get_error_summary(self) -> Dict[str, Any]:
        """
        Get a summary of errors.
        
        Returns:
            Error summary
        """
        # Count errors by code
        code_count = {}
        for error in self.errors:
            code_count[error.code] = code_count.get(error.code, 0) + 1
        
        # Count errors by level
        level_count = {}
        for error in self.errors:
            level_count[error.level] = level_count.get(error.level, 0) + 1
        
        # Count errors by category
        category_count = {}
        for error in self.errors:
            category_count[error.category] = category_count.get(error.category, 0) + 1
        
        # Count errors by source
        source_count = {}
        for error in self.errors:
            if error.source:
                source_count[error.source] = source_count.get(error.source, 0) + 1
        
        return {
            "total": len(self.errors),
            "by_code": code_count,
            "by_level": level_count,
            "by_category": category_count,
            "by_source": source_count,
            "first_timestamp": self.errors[0].timestamp if self.errors else None,
            "last_timestamp": self.errors[-1].timestamp if self.errors else None
        }
    
    def clear_errors(self) -> int:
        """
        Clear all errors.
        
        Returns:
            Number of errors cleared
        """
        count = len(self.errors)
        self.errors = []
        self._save_errors()
        return count
    
    def _save_errors(self) -> bool:
        """
        Save errors to a file.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create error data
            error_data = {
                "errors": [error.to_dict() for error in self.errors],
                "saved_at": time.time()
            }
            
            # Write to file
            with open(self.error_file, "w") as f:
                json.dump(error_data, f, indent=2)
            
            self.logger.debug(f"Saved {len(self.errors)} errors to {self.error_file}")
            
            return True
        
        except Exception as e:
            self.logger.error(f"Error saving errors: {e}")
            return False
    
    def _load_errors(self) -> bool:
        """
        Load errors from a file.
        
        Returns:
            True if successful, False otherwise
        """
        # Check if file exists
        if not os.path.exists(self.error_file):
            return False
        
        try:
            # Read from file
            with open(self.error_file, "r") as f:
                error_data = json.load(f)
            
            # Parse errors
            for error_dict in error_data.get("errors", []):
                error = Error(
                    code=error_dict.get("code"),
                    message=error_dict.get("message"),
                    level=error_dict.get("level"),
                    category=error_dict.get("category"),
                    details=error_dict.get("details"),
                    source=error_dict.get("source"),
                    timestamp=error_dict.get("timestamp")
                )
                
                self.errors.append(error)
            
            self.logger.info(f"Loaded {len(self.errors)} errors from {self.error_file}")
            
            return True
        
        except Exception as e:
            self.logger.error(f"Error loading errors: {e}")
            return False


def create_error_handler(config: Dict[str, Any], data_dir: str) -> ErrorHandler:
    """
    Create an error handler with the specified configuration.
    
    Args:
        config: Error handler configuration
        data_dir: Data directory for error logs
        
    Returns:
        Configured error handler
    """
    return ErrorHandler(config, data_dir)