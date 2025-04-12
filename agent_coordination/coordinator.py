"""
Agent Coordination System for Benton County Assessor's Office AI Platform

This module implements a coordination system that enables AI agents to
actively contribute to building and improving the application codebase.
"""

import os
import sys
import json
import uuid
import inspect
import importlib
import pkgutil
from typing import Dict, Any, List, Optional, Callable, Tuple, Set, Union
from dataclasses import dataclass, field
from datetime import datetime
import logging

from core.message import Message, CommandMessage, ResponseMessage, ErrorMessage
from core.hub_enhanced import CoreHubEnhanced


@dataclass
class DevelopmentTask:
    """
    Represents a development task that can be assigned to an agent.
    
    Attributes:
        task_id: Unique identifier for this task
        title: Short description of the task
        description: Detailed description of the task
        task_type: Type of development task (code_generation, code_review, testing, documentation)
        priority: Task priority (high, medium, low)
        status: Current status of the task
        agent_id: ID of the agent assigned to this task
        related_files: List of files related to this task
        dependencies: List of tasks that must be completed before this task
        created_at: When the task was created
        updated_at: When the task was last updated
        completion_criteria: Criteria to determine if the task is complete
        result: Result produced by the agent (code, review, test results, etc.)
    """
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    task_type: str = ""  # code_generation, code_review, testing, documentation
    priority: str = "medium"  # high, medium, low
    status: str = "pending"  # pending, assigned, in_progress, completed, failed
    agent_id: Optional[str] = None
    related_files: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completion_criteria: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None


class AgentCoordinator:
    """
    Coordinates AI agents to contribute to building and improving the application.
    
    This class manages the workflow for assigning development tasks to agents,
    reviewing their contributions, and integrating their work into the codebase.
    """
    
    def __init__(self, core_hub: CoreHubEnhanced, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Agent Coordinator.
        
        Args:
            core_hub: Enhanced Core Hub instance
            config: Configuration options
        """
        self.core_hub = core_hub
        self.config = config or {}
        self.logger = logging.getLogger("agent_coordinator")
        self.tasks: Dict[str, DevelopmentTask] = {}
        self.agent_capabilities: Dict[str, List[str]] = {}
        
        # Register message handlers
        self.core_hub.register_topic_handler("development_task", self._handle_development_task)
        self.core_hub.register_topic_handler("task_update", self._handle_task_update)
        self.core_hub.register_topic_handler("code_contribution", self._handle_code_contribution)
        
        # Initialize task database
        self._load_tasks()
    
    def create_task(self, task_data: Dict[str, Any]) -> str:
        """
        Create a new development task.
        
        Args:
            task_data: Task details
            
        Returns:
            Task ID
        """
        task = DevelopmentTask(
            title=task_data.get("title", ""),
            description=task_data.get("description", ""),
            task_type=task_data.get("task_type", ""),
            priority=task_data.get("priority", "medium"),
            related_files=task_data.get("related_files", []),
            dependencies=task_data.get("dependencies", []),
            completion_criteria=task_data.get("completion_criteria", {})
        )
        
        self.tasks[task.task_id] = task
        self._save_tasks()
        
        self.logger.info(f"Created task {task.task_id}: {task.title}")
        return task.task_id
    
    def assign_task(self, task_id: str, agent_id: Optional[str] = None) -> bool:
        """
        Assign a task to an agent.
        
        Args:
            task_id: Task to assign
            agent_id: Agent to assign the task to, or None to auto-assign
            
        Returns:
            True if successful, False otherwise
        """
        if task_id not in self.tasks:
            self.logger.error(f"Task {task_id} not found")
            return False
        
        task = self.tasks[task_id]
        
        # Check dependencies
        for dep_id in task.dependencies:
            if dep_id in self.tasks and self.tasks[dep_id].status != "completed":
                self.logger.warning(f"Task {task_id} has incomplete dependency {dep_id}")
                return False
        
        # Auto-assign if no agent specified
        if agent_id is None:
            agent_id = self._find_best_agent_for_task(task)
            if agent_id is None:
                self.logger.error(f"No suitable agent found for task {task_id}")
                return False
        
        # Update task
        task.agent_id = agent_id
        task.status = "assigned"
        task.updated_at = datetime.now().isoformat()
        self._save_tasks()
        
        # Send task assignment message
        self._send_task_assignment(task)
        
        self.logger.info(f"Assigned task {task_id} to agent {agent_id}")
        return True
    
    def update_task_status(self, task_id: str, status: str, result: Optional[Dict[str, Any]] = None) -> bool:
        """
        Update the status of a task.
        
        Args:
            task_id: Task to update
            status: New status
            result: Task result
            
        Returns:
            True if successful, False otherwise
        """
        if task_id not in self.tasks:
            self.logger.error(f"Task {task_id} not found")
            return False
        
        task = self.tasks[task_id]
        task.status = status
        task.updated_at = datetime.now().isoformat()
        
        if result is not None:
            task.result = result
        
        self._save_tasks()
        
        self.logger.info(f"Updated task {task_id} status to {status}")
        return True
    
    def get_task(self, task_id: str) -> Optional[DevelopmentTask]:
        """
        Get a task by ID.
        
        Args:
            task_id: Task ID
            
        Returns:
            Task, or None if not found
        """
        return self.tasks.get(task_id)
    
    def get_tasks_by_status(self, status: str) -> List[DevelopmentTask]:
        """
        Get all tasks with a specific status.
        
        Args:
            status: Status to filter by
            
        Returns:
            List of tasks
        """
        return [task for task in self.tasks.values() if task.status == status]
    
    def get_tasks_by_agent(self, agent_id: str) -> List[DevelopmentTask]:
        """
        Get all tasks assigned to a specific agent.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            List of tasks
        """
        return [task for task in self.tasks.values() if task.agent_id == agent_id]
    
    def analyze_codebase(self) -> Dict[str, Any]:
        """
        Analyze the codebase to identify areas for improvement.
        
        Returns:
            Analysis results
        """
        # Implement codebase analysis logic here
        analysis_results = {
            "modules": self._discover_modules(),
            "code_quality": self._analyze_code_quality(),
            "test_coverage": self._analyze_test_coverage()
        }
        
        return analysis_results
    
    def generate_tasks_from_analysis(self, analysis: Dict[str, Any]) -> List[str]:
        """
        Generate development tasks based on codebase analysis.
        
        Args:
            analysis: Analysis results
            
        Returns:
            List of created task IDs
        """
        task_ids = []
        
        # Generate code improvement tasks
        if "code_quality" in analysis and "issues" in analysis["code_quality"]:
            for issue in analysis["code_quality"]["issues"]:
                task_data = {
                    "title": f"Fix code quality issue: {issue['type']}",
                    "description": f"Address {issue['type']} issue in {issue['file']}:{issue['line']}:\n{issue['description']}",
                    "task_type": "code_improvement",
                    "priority": issue.get("severity", "medium"),
                    "related_files": [issue["file"]]
                }
                task_id = self.create_task(task_data)
                task_ids.append(task_id)
        
        # Generate test coverage tasks
        if "test_coverage" in analysis and "low_coverage" in analysis["test_coverage"]:
            for module in analysis["test_coverage"]["low_coverage"]:
                task_data = {
                    "title": f"Improve test coverage for {module['name']}",
                    "description": f"Create tests to improve coverage for {module['name']} (current: {module['coverage']}%)",
                    "task_type": "testing",
                    "priority": "medium",
                    "related_files": module.get("files", [])
                }
                task_id = self.create_task(task_data)
                task_ids.append(task_id)
        
        return task_ids
    
    def _find_best_agent_for_task(self, task: DevelopmentTask) -> Optional[str]:
        """
        Find the best agent to handle a specific task.
        
        Args:
            task: Task to assign
            
        Returns:
            Agent ID, or None if no suitable agent found
        """
        # Get all registered agents
        agent_infos = self._get_all_agent_infos()
        
        # Match task type to agent capabilities
        best_match = None
        best_score = 0
        
        for agent_id, agent_info in agent_infos.items():
            # Skip agents that are busy with too many tasks
            assigned_tasks = self.get_tasks_by_agent(agent_id)
            active_tasks = [t for t in assigned_tasks if t.status in ["assigned", "in_progress"]]
            if len(active_tasks) >= self.config.get("max_agent_tasks", 3):
                continue
                
            # Calculate capability match score
            score = 0
            capabilities = agent_info.get("capabilities", [])
            
            if task.task_type == "code_generation" and "code_generation" in capabilities:
                score += 5
            elif task.task_type == "code_review" and "code_review" in capabilities:
                score += 5
            elif task.task_type == "testing" and "testing" in capabilities:
                score += 5
            elif task.task_type == "documentation" and "documentation" in capabilities:
                score += 5
                
            # Check for file type expertise
            for file in task.related_files:
                ext = os.path.splitext(file)[1].lower()
                if ext == ".py" and "python" in capabilities:
                    score += 2
                elif ext == ".js" and "javascript" in capabilities:
                    score += 2
                elif ext == ".html" and "web" in capabilities:
                    score += 2
                elif ext == ".css" and "web" in capabilities:
                    score += 2
            
            if score > best_score:
                best_score = score
                best_match = agent_id
        
        return best_match
    
    def _save_tasks(self) -> None:
        """Save tasks to the database."""
        tasks_dir = os.path.join(self.config.get("data_dir", "data"), "tasks")
        os.makedirs(tasks_dir, exist_ok=True)
        
        tasks_file = os.path.join(tasks_dir, "tasks.json")
        with open(tasks_file, "w") as f:
            task_dict = {task_id: self._task_to_dict(task) for task_id, task in self.tasks.items()}
            json.dump(task_dict, f, indent=2)
    
    def _load_tasks(self) -> None:
        """Load tasks from the database."""
        tasks_dir = os.path.join(self.config.get("data_dir", "data"), "tasks")
        os.makedirs(tasks_dir, exist_ok=True)
        
        tasks_file = os.path.join(tasks_dir, "tasks.json")
        if os.path.exists(tasks_file):
            try:
                with open(tasks_file, "r") as f:
                    task_dict = json.load(f)
                    self.tasks = {task_id: self._dict_to_task(task_data) for task_id, task_data in task_dict.items()}
                self.logger.info(f"Loaded {len(self.tasks)} tasks from database")
            except Exception as e:
                self.logger.error(f"Error loading tasks: {str(e)}")
    
    def _task_to_dict(self, task: DevelopmentTask) -> Dict[str, Any]:
        """Convert a task to a dictionary for serialization."""
        return {
            "task_id": task.task_id,
            "title": task.title,
            "description": task.description,
            "task_type": task.task_type,
            "priority": task.priority,
            "status": task.status,
            "agent_id": task.agent_id,
            "related_files": task.related_files,
            "dependencies": task.dependencies,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
            "completion_criteria": task.completion_criteria,
            "result": task.result
        }
    
    def _dict_to_task(self, data: Dict[str, Any]) -> DevelopmentTask:
        """Convert a dictionary to a task."""
        return DevelopmentTask(
            task_id=data.get("task_id", str(uuid.uuid4())),
            title=data.get("title", ""),
            description=data.get("description", ""),
            task_type=data.get("task_type", ""),
            priority=data.get("priority", "medium"),
            status=data.get("status", "pending"),
            agent_id=data.get("agent_id"),
            related_files=data.get("related_files", []),
            dependencies=data.get("dependencies", []),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
            completion_criteria=data.get("completion_criteria", {}),
            result=data.get("result")
        )
    
    def _get_all_agent_infos(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all registered agents."""
        agents = {}
        agent_manager = self.core_hub.agent_manager
        agent_ids = agent_manager.get_all_agent_ids()
        
        for agent_id in agent_ids:
            agent_info = agent_manager.get_agent_info(agent_id)
            if agent_info:
                agents[agent_id] = agent_info
        
        return agents
    
    def _send_task_assignment(self, task: DevelopmentTask) -> None:
        """
        Send a task assignment message to an agent.
        
        Args:
            task: Task to assign
        """
        if not task.agent_id:
            self.logger.error(f"Cannot send task assignment for task {task.task_id}: no agent assigned")
            return
        
        command = CommandMessage(
            source_agent_id="agent_coordinator",
            target_agent_id=task.agent_id,
            command_name="execute_development_task",
            parameters={
                "task_id": task.task_id,
                "task_type": task.task_type,
                "title": task.title,
                "description": task.description,
                "related_files": task.related_files,
                "completion_criteria": task.completion_criteria
            }
        )
        
        self.core_hub.send_message(command)
        self.logger.info(f"Sent task assignment command for task {task.task_id} to agent {task.agent_id}")
    
    def _handle_development_task(self, message: Message) -> None:
        """
        Handle incoming development task messages.
        
        Args:
            message: Incoming message
        """
        if not isinstance(message, CommandMessage):
            return
        
        command_name = message.payload.get("command_name")
        
        if command_name == "create_task":
            # Handle create task command
            task_data = message.payload.get("parameters", {})
            task_id = self.create_task(task_data)
            
            # Send response
            response = ResponseMessage(
                source_agent_id="agent_coordinator",
                target_agent_id=message.source_agent_id,
                status="success",
                result={"task_id": task_id},
                original_message_id=message.message_id,
                correlation_id=message.correlation_id
            )
            self.core_hub.send_message(response)
            
        elif command_name == "assign_task":
            # Handle assign task command
            params = message.payload.get("parameters", {})
            task_id = params.get("task_id")
            agent_id = params.get("agent_id")
            
            if not task_id:
                error = ErrorMessage(
                    source_agent_id="agent_coordinator",
                    target_agent_id=message.source_agent_id,
                    error_code="MISSING_TASK_ID",
                    error_message="Task ID is required",
                    correlation_id=message.correlation_id
                )
                self.core_hub.send_message(error)
                return
            
            success = self.assign_task(task_id, agent_id)
            
            # Send response
            response = ResponseMessage(
                source_agent_id="agent_coordinator",
                target_agent_id=message.source_agent_id,
                status="success" if success else "failure",
                result={"task_id": task_id, "agent_id": agent_id if success else None},
                original_message_id=message.message_id,
                correlation_id=message.correlation_id
            )
            self.core_hub.send_message(response)
    
    def _handle_task_update(self, message: Message) -> None:
        """
        Handle task update messages from agents.
        
        Args:
            message: Incoming message
        """
        if not isinstance(message, CommandMessage):
            return
        
        command_name = message.payload.get("command_name")
        
        if command_name == "update_task_status":
            # Handle task status update
            params = message.payload.get("parameters", {})
            task_id = params.get("task_id")
            status = params.get("status")
            result = params.get("result")
            
            if not task_id or not status:
                error = ErrorMessage(
                    source_agent_id="agent_coordinator",
                    target_agent_id=message.source_agent_id,
                    error_code="INVALID_PARAMETERS",
                    error_message="Task ID and status are required",
                    correlation_id=message.correlation_id
                )
                self.core_hub.send_message(error)
                return
            
            success = self.update_task_status(task_id, status, result)
            
            # Send response
            response = ResponseMessage(
                source_agent_id="agent_coordinator",
                target_agent_id=message.source_agent_id,
                status="success" if success else "failure",
                result={"task_id": task_id, "status": status},
                original_message_id=message.message_id,
                correlation_id=message.correlation_id
            )
            self.core_hub.send_message(response)
    
    def _handle_code_contribution(self, message: Message) -> None:
        """
        Handle code contribution messages from agents.
        
        Args:
            message: Incoming message
        """
        if not isinstance(message, CommandMessage):
            return
        
        command_name = message.payload.get("command_name")
        
        if command_name == "submit_code_contribution":
            # Handle code contribution
            params = message.payload.get("parameters", {})
            task_id = params.get("task_id")
            file_path = params.get("file_path")
            code = params.get("code")
            
            if not task_id or not file_path or not code:
                error = ErrorMessage(
                    source_agent_id="agent_coordinator",
                    target_agent_id=message.source_agent_id,
                    error_code="INVALID_PARAMETERS",
                    error_message="Task ID, file path, and code are required",
                    correlation_id=message.correlation_id
                )
                self.core_hub.send_message(error)
                return
            
            # Create directory structure if needed
            directory = os.path.dirname(file_path)
            if directory:
                os.makedirs(directory, exist_ok=True)
            
            # Write code to file
            with open(file_path, "w") as f:
                f.write(code)
            
            # Update task status
            task = self.get_task(task_id)
            if task:
                self.update_task_status(
                    task_id, 
                    "completed", 
                    {
                        "file_path": file_path,
                        "code_size": len(code),
                        "timestamp": datetime.now().isoformat()
                    }
                )
            
            # Send response
            response = ResponseMessage(
                source_agent_id="agent_coordinator",
                target_agent_id=message.source_agent_id,
                status="success",
                result={"task_id": task_id, "file_path": file_path},
                original_message_id=message.message_id,
                correlation_id=message.correlation_id
            )
            self.core_hub.send_message(response)
    
    def _discover_modules(self) -> List[Dict[str, Any]]:
        """
        Discover all Python modules in the project.
        
        Returns:
            List of module information
        """
        modules = []
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        
        for root, dirs, files in os.walk(base_path):
            # Skip hidden directories and __pycache__
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]
            
            for file in files:
                if file.endswith(".py"):
                    rel_path = os.path.relpath(os.path.join(root, file), base_path)
                    module_path = rel_path.replace(os.path.sep, ".").replace(".py", "")
                    
                    modules.append({
                        "name": module_path,
                        "path": rel_path,
                        "full_path": os.path.join(root, file)
                    })
        
        return modules
    
    def _analyze_code_quality(self) -> Dict[str, Any]:
        """
        Analyze code quality of the codebase.
        
        Returns:
            Code quality analysis results
        """
        # Simple placeholder implementation
        # In a real implementation, this would use tools like pylint or flake8
        issues = []
        modules = self._discover_modules()
        
        for module_info in modules:
            file_path = module_info["full_path"]
            try:
                with open(file_path, "r") as f:
                    lines = f.readlines()
                    
                for i, line in enumerate(lines):
                    # Check line length
                    if len(line) > 100:
                        issues.append({
                            "file": module_info["path"],
                            "line": i + 1,
                            "type": "line-too-long",
                            "severity": "low",
                            "description": f"Line longer than 100 characters ({len(line)} chars)"
                        })
                    
                    # Check for TODOs
                    if "TODO" in line:
                        issues.append({
                            "file": module_info["path"],
                            "line": i + 1,
                            "type": "todo-found",
                            "severity": "low",
                            "description": f"TODO comment found: {line.strip()}"
                        })
            except Exception as e:
                self.logger.warning(f"Error analyzing {file_path}: {str(e)}")
        
        return {
            "issues": issues,
            "issue_count": len(issues)
        }
    
    def _analyze_test_coverage(self) -> Dict[str, Any]:
        """
        Analyze test coverage of the codebase.
        
        Returns:
            Test coverage analysis results
        """
        # Simple placeholder implementation
        # In a real implementation, this would use tools like coverage.py
        modules = self._discover_modules()
        test_files = [m for m in modules if "test_" in m["name"] or "tests" in m["name"]]
        
        # Find modules without corresponding test files
        low_coverage = []
        for module in modules:
            if "test_" not in module["name"] and "tests" not in module["name"]:
                has_test = False
                for test in test_files:
                    if module["name"] in test["name"]:
                        has_test = True
                        break
                
                if not has_test:
                    low_coverage.append({
                        "name": module["name"],
                        "path": module["path"],
                        "coverage": 0,
                        "files": [module["path"]]
                    })
        
        return {
            "test_files": len(test_files),
            "total_modules": len(modules),
            "low_coverage": low_coverage,
            "coverage_percentage": 100 * (1 - len(low_coverage) / max(1, len(modules) - len(test_files)))
        }


def create_agent_coordinator(core_hub: CoreHubEnhanced, config_path: Optional[str] = None) -> AgentCoordinator:
    """
    Create an Agent Coordinator with the specified configuration.
    
    Args:
        core_hub: Enhanced Core Hub instance
        config_path: Path to configuration file
        
    Returns:
        Configured Agent Coordinator
    """
    if config_path and os.path.exists(config_path):
        with open(config_path, "r") as f:
            config = json.load(f)
    else:
        config = {
            "data_dir": "data/agent_coordination",
            "max_agent_tasks": 3
        }
    
    return AgentCoordinator(core_hub, config)