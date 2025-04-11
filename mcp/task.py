"""
Task Module for Benton County Assessor's Office MCP

This module defines the Task class and related enumerations for the
task management system within the MCP framework.
"""

import logging
import uuid
import json
from datetime import datetime
from enum import Enum, auto
from typing import Dict, List, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    """Status options for tasks in the MCP system."""
    CREATED = "created"         # Task has been created but not assigned
    ASSIGNED = "assigned"       # Task has been assigned to an agent
    QUEUED = "queued"           # Task is in the agent's queue
    IN_PROGRESS = "in-progress" # Task is being processed
    COMPLETED = "completed"     # Task has been completed successfully
    FAILED = "failed"           # Task has failed
    CANCELLED = "cancelled"     # Task has been cancelled
    TIMEOUT = "timeout"         # Task has timed out


class TaskPriority(Enum):
    """Priority levels for tasks in the MCP system."""
    CRITICAL = "critical"   # Highest priority, process immediately
    HIGH = "high"           # High priority
    NORMAL = "normal"       # Normal priority
    LOW = "low"             # Low priority
    BACKGROUND = "background" # Lowest priority, process when idle


class Task:
    """
    Task class for agent task management in the MCP system.
    
    This class represents tasks that can be assigned to agents, providing
    a structured approach to task creation, assignment, execution, and tracking.
    """
    
    def __init__(self, to_agent_id: str, task_type: str,
                parameters: Dict[str, Any] = {},
                source_agent_id: Optional[str] = None,
                priority: TaskPriority = TaskPriority.NORMAL,
                task_id: Optional[str] = None,
                parent_task_id: Optional[str] = None,
                timeout_seconds: Optional[int] = None,
                retry_count: int = 0,
                max_retries: int = 3):
        """
        Initialize a new task with the specified parameters.
        
        Args:
            to_agent_id: ID of the agent the task is assigned to
            task_type: Type of task
            parameters: Task parameters as a dictionary
            source_agent_id: ID of the agent creating the task (optional)
            priority: Task priority
            task_id: Unique identifier for the task (generated if not provided)
            parent_task_id: ID of the parent task (for subtasks)
            timeout_seconds: Optional timeout for the task in seconds
            retry_count: Number of times this task has been retried
            max_retries: Maximum number of retries allowed
        """
        self.task_id = task_id or str(uuid.uuid4())
        self.parent_task_id = parent_task_id
        self.source_agent_id = source_agent_id
        self.to_agent_id = to_agent_id
        self.task_type = task_type
        self.parameters = parameters or {}
        self.priority = priority
        
        # Task state
        self.status = TaskStatus.CREATED
        self.created_at = datetime.utcnow()
        self.assigned_at = None
        self.started_at = None
        self.completed_at = None
        self.result = None
        
        # Task execution metadata
        self.timeout_seconds = timeout_seconds
        self.retry_count = retry_count
        self.max_retries = max_retries
        self.error_message = None
        self.retry_task_ids = []
        self.subtask_ids = []
        
        logger.debug(f"Created task {self.task_id} of type {task_type} for agent {to_agent_id}")
    
    def assign(self):
        """Mark the task as assigned to the target agent."""
        self.status = TaskStatus.ASSIGNED
        self.assigned_at = datetime.utcnow()
        logger.debug(f"Task {self.task_id} assigned to agent {self.to_agent_id}")
    
    def queue(self):
        """Mark the task as queued in the agent's task queue."""
        self.status = TaskStatus.QUEUED
        logger.debug(f"Task {self.task_id} queued in agent {self.to_agent_id}'s queue")
    
    def start(self):
        """Mark the task as started (in progress)."""
        self.status = TaskStatus.IN_PROGRESS
        self.started_at = datetime.utcnow()
        logger.debug(f"Task {self.task_id} started by agent {self.to_agent_id}")
    
    def complete(self, result: Dict[str, Any]):
        """
        Mark the task as completed with the provided result.
        
        Args:
            result: Result of the task
        """
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.result = result
        logger.debug(f"Task {self.task_id} completed by agent {self.to_agent_id}")
    
    def fail(self, error_message: str):
        """
        Mark the task as failed with the provided error message.
        
        Args:
            error_message: Error message explaining the failure
        """
        self.status = TaskStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error_message = error_message
        logger.debug(f"Task {self.task_id} failed: {error_message}")
    
    def cancel(self, reason: str = "Cancelled by system"):
        """
        Mark the task as cancelled with the provided reason.
        
        Args:
            reason: Reason for cancellation
        """
        self.status = TaskStatus.CANCELLED
        self.completed_at = datetime.utcnow()
        self.error_message = reason
        logger.debug(f"Task {self.task_id} cancelled: {reason}")
    
    def is_timed_out(self) -> bool:
        """
        Check if the task has timed out.
        
        Returns:
            bool: Whether the task has timed out
        """
        if self.timeout_seconds is None or not self.started_at:
            return False
        
        if self.status == TaskStatus.TIMEOUT:
            return True
        
        # Check if current time exceeds timeout
        elapsed_seconds = (datetime.utcnow() - self.started_at).total_seconds()
        timed_out = elapsed_seconds > self.timeout_seconds
        
        if timed_out and self.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            self.status = TaskStatus.TIMEOUT
            self.completed_at = datetime.utcnow()
            self.error_message = f"Task timed out after {elapsed_seconds} seconds"
            logger.warning(f"Task {self.task_id} timed out after {elapsed_seconds} seconds")
        
        return timed_out
    
    def can_retry(self) -> bool:
        """
        Check if the task can be retried.
        
        Returns:
            bool: Whether the task can be retried
        """
        return (self.status in [TaskStatus.FAILED, TaskStatus.TIMEOUT] and 
                self.retry_count < self.max_retries)
    
    def create_retry(self) -> 'Task':
        """
        Create a retry task based on this task.
        
        Returns:
            Task: The retry task
        """
        if not self.can_retry():
            raise ValueError(f"Task {self.task_id} cannot be retried")
        
        retry_task = Task(
            to_agent_id=self.to_agent_id,
            task_type=self.task_type,
            parameters=self.parameters,
            source_agent_id=self.source_agent_id,
            priority=self.priority,
            parent_task_id=self.task_id,
            timeout_seconds=self.timeout_seconds,
            retry_count=self.retry_count + 1,
            max_retries=self.max_retries
        )
        
        self.retry_task_ids.append(retry_task.task_id)
        logger.info(f"Created retry task {retry_task.task_id} for failed task {self.task_id}")
        
        return retry_task
    
    def create_subtask(self, task_type: str, parameters: Dict[str, Any],
                     priority: Optional[TaskPriority] = None) -> 'Task':
        """
        Create a subtask based on this task.
        
        Args:
            task_type: Type of subtask
            parameters: Subtask parameters
            priority: Subtask priority (default: same as parent task)
            
        Returns:
            Task: The subtask
        """
        subtask = Task(
            to_agent_id=self.to_agent_id,
            task_type=task_type,
            parameters=parameters,
            source_agent_id=self.source_agent_id,
            priority=priority or self.priority,
            parent_task_id=self.task_id,
            timeout_seconds=self.timeout_seconds
        )
        
        self.subtask_ids.append(subtask.task_id)
        logger.debug(f"Created subtask {subtask.task_id} for task {self.task_id}")
        
        return subtask
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert task to a dictionary representation.
        
        Returns:
            dict: Dictionary representation of the task
        """
        return {
            "task_id": self.task_id,
            "parent_task_id": self.parent_task_id,
            "source_agent_id": self.source_agent_id,
            "to_agent_id": self.to_agent_id,
            "task_type": self.task_type,
            "parameters": self.parameters,
            "priority": self.priority.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
            "timeout_seconds": self.timeout_seconds,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "error_message": self.error_message,
            "retry_task_ids": self.retry_task_ids,
            "subtask_ids": self.subtask_ids
        }
    
    def to_json(self) -> str:
        """
        Convert task to JSON string.
        
        Returns:
            str: JSON representation of the task
        """
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """
        Create a task from a dictionary representation.
        
        Args:
            data: Dictionary representation of the task
            
        Returns:
            Task: The reconstructed task
        """
        # Handle both new "source_agent_id" and legacy "from_agent_id" for backward compatibility
        source_agent = data.get("source_agent_id") or data.get("from_agent_id")
        
        task = cls(
            to_agent_id=data["to_agent_id"],
            task_type=data["task_type"],
            parameters=data["parameters"],
            source_agent_id=source_agent,
            priority=TaskPriority(data["priority"]),
            task_id=data["task_id"],
            parent_task_id=data.get("parent_task_id"),
            timeout_seconds=data.get("timeout_seconds"),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3)
        )
        
        # Set task state
        task.status = TaskStatus(data["status"])
        task.created_at = datetime.fromisoformat(data["created_at"])
        
        if data.get("assigned_at"):
            task.assigned_at = datetime.fromisoformat(data["assigned_at"])
        
        if data.get("started_at"):
            task.started_at = datetime.fromisoformat(data["started_at"])
        
        if data.get("completed_at"):
            task.completed_at = datetime.fromisoformat(data["completed_at"])
        
        task.result = data.get("result")
        task.error_message = data.get("error_message")
        task.retry_task_ids = data.get("retry_task_ids", [])
        task.subtask_ids = data.get("subtask_ids", [])
        
        return task
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Task':
        """
        Create a task from a JSON string.
        
        Args:
            json_str: JSON representation of the task
            
        Returns:
            Task: The reconstructed task
        """
        data = json.loads(json_str)
        return cls.from_dict(data)