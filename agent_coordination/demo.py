#!/usr/bin/env python3
"""
Agent-Assisted Development Demo for Benton County Assessor's Office AI Platform

This script demonstrates how AI agents can contribute to building and
improving the application codebase.
"""

import os
import sys
import json
import time
import logging
from typing import Dict, Any, List

from core.hub_enhanced import CoreHubEnhanced, create_core_hub_enhanced
from agent_coordination.coordinator import AgentCoordinator, create_agent_coordinator
from agent_coordination.developer_agent import DeveloperAgent, create_developer_agent


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("agent_development_demo")


def print_header(title: str) -> None:
    """Print a formatted header."""
    print("\n" + "=" * 80)
    print(f"{title:^80}")
    print("=" * 80 + "\n")


def print_section(title: str) -> None:
    """Print a section title."""
    print(f"\n{title}...")


def create_demo_config() -> Dict[str, Any]:
    """
    Create configuration for the demo.
    
    Returns:
        Demo configuration
    """
    return {
        "core": {
            "name": "BentonCountyAssessorCore",
            "version": "3.0.0",
            "data_dir": "data/core",
            "master_prompt": "You are an AI assistant for the Benton County Assessor's Office.",
            "master_prompt_refresh_interval": 3600
        },
        "agent_coordinator": {
            "data_dir": "data/agent_coordination",
            "max_agent_tasks": 3
        },
        "developer_agents": [
            {
                "id": "python_developer",
                "specialization": "backend",
                "code_generation_mode": "incremental",
                "programming_languages": ["python"],
                "capabilities": ["code_generation", "code_review", "testing", "documentation"]
            },
            {
                "id": "web_developer",
                "specialization": "frontend",
                "code_generation_mode": "incremental",
                "programming_languages": ["javascript", "html", "css"],
                "capabilities": ["code_generation", "ui_design", "documentation"]
            },
            {
                "id": "database_developer",
                "specialization": "database",
                "code_generation_mode": "incremental",
                "programming_languages": ["sql", "python"],
                "capabilities": ["data_modeling", "query_optimization", "testing"]
            }
        ]
    }


def save_config(config: Dict[str, Any], path: str) -> None:
    """
    Save configuration to a file.
    
    Args:
        config: Configuration
        path: File path
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    with open(path, "w") as f:
        json.dump(config, f, indent=2)
    
    logger.info(f"Configuration saved to {path}")


def create_agents(hub: CoreHubEnhanced, config: Dict[str, Any]) -> List[DeveloperAgent]:
    """
    Create developer agents.
    
    Args:
        hub: Enhanced Core Hub
        config: Configuration
        
    Returns:
        List of developer agents
    """
    agents = []
    
    for agent_config in config["developer_agents"]:
        agent_id = agent_config["id"]
        logger.info(f"Creating developer agent: {agent_id}")
        
        agent = create_developer_agent(agent_id, None)
        agent.connect_to_hub(hub)
        agents.append(agent)
        
        # Register agent with the hub
        hub.register_agent(
            agent_id=agent_id,
            agent_info={
                "name": f"{agent_config['specialization'].title()} Developer",
                "type": "developer",
                "description": f"AI agent specialized in {agent_config['specialization']} development",
                "capabilities": agent_config["capabilities"],
                "programming_languages": agent_config["programming_languages"],
                "specialization": agent_config["specialization"]
            }
        )
    
    return agents


def create_development_tasks(coordinator: AgentCoordinator) -> List[str]:
    """
    Create development tasks.
    
    Args:
        coordinator: Agent Coordinator
        
    Returns:
        List of task IDs
    """
    tasks = [
        {
            "title": "Implement Data Validation Agent",
            "description": "Create a new agent that specializes in data validation for property assessments. The agent should:\n\n- Validate property data against Washington State standards\n- Check for data consistency and completeness\n- Identify anomalies in assessment data\n- Generate data quality reports",
            "task_type": "code_generation",
            "priority": "high",
            "related_files": ["mcp/agent.py", "core/message.py"]
        },
        {
            "title": "Improve Error Handling in Communication Module",
            "description": "Enhance error handling in the communication module to better handle network failures and message timeouts. Implementation should:\n\n- Add exponential backoff for retries\n- Implement circuit breaker pattern\n- Improve error messages and logging\n- Add metrics collection for failures",
            "task_type": "code_improvement",
            "priority": "medium",
            "related_files": ["core/communication.py"]
        },
        {
            "title": "Create Documentation for Agent System",
            "description": "Generate comprehensive documentation for the MCP Assessor Agent API and multi-agent system. Documentation should cover:\n\n- System architecture overview\n- Agent interactions and message protocols\n- Configuration options\n- Extension points for new agents\n- Example usage scenarios",
            "task_type": "documentation",
            "priority": "medium",
            "related_files": ["core/hub_enhanced.py", "mcp/agent.py", "core/message.py"]
        }
    ]
    
    task_ids = []
    for task in tasks:
        logger.info(f"Creating task: {task['title']}")
        task_id = coordinator.create_task(task)
        task_ids.append(task_id)
    
    return task_ids


def assign_tasks(coordinator: AgentCoordinator, task_ids: List[str]) -> None:
    """
    Assign tasks to agents.
    
    Args:
        coordinator: Agent Coordinator
        task_ids: List of task IDs
    """
    for task_id in task_ids:
        task = coordinator.get_task(task_id)
        if task:
            logger.info(f"Assigning task: {task.title}")
            coordinator.assign_task(task_id)


def monitor_tasks(coordinator: AgentCoordinator, task_ids: List[str], timeout: int = 60) -> bool:
    """
    Monitor tasks until they are completed or timeout.
    
    Args:
        coordinator: Agent Coordinator
        task_ids: List of task IDs
        timeout: Timeout in seconds
        
    Returns:
        True if all tasks completed, False if timeout
    """
    start_time = time.time()
    completed_count = 0
    
    print_section(f"Monitoring {len(task_ids)} tasks")
    
    while time.time() - start_time < timeout:
        all_completed = True
        completed_count = 0
        
        for task_id in task_ids:
            task = coordinator.get_task(task_id)
            if task:
                if task.status == "completed":
                    completed_count += 1
                elif task.status == "failed":
                    logger.warning(f"Task failed: {task.title}")
                    completed_count += 1
                else:
                    all_completed = False
        
        if all_completed:
            logger.info(f"All tasks completed")
            return True
        
        print(f"Progress: {completed_count}/{len(task_ids)} tasks completed")
        time.sleep(5)
    
    logger.warning(f"Timeout waiting for tasks to complete")
    return False


def summarize_results(coordinator: AgentCoordinator, task_ids: List[str]) -> None:
    """
    Summarize task results.
    
    Args:
        coordinator: Agent Coordinator
        task_ids: List of task IDs
    """
    print_section("Task Results Summary")
    
    for task_id in task_ids:
        task = coordinator.get_task(task_id)
        if task:
            print(f"\nTask: {task.title}")
            print(f"Status: {task.status}")
            print(f"Assigned to: {task.agent_id}")
            
            if task.result:
                if "file_path" in task.result:
                    print(f"Generated file: {task.result['file_path']}")
                
                if "reviews" in task.result:
                    print(f"Reviews: {len(task.result['reviews'])} files reviewed")
                
                if "test_files" in task.result:
                    print(f"Tests: {len(task.result['test_files'])} test files created")
                
                if "doc_files" in task.result:
                    print(f"Documentation: {len(task.result['doc_files'])} files documented")
                
                if "improved_files" in task.result:
                    print(f"Improvements: {len(task.result['improved_files'])} files improved")


def create_agent_codebase_contribution_demo(hub: CoreHubEnhanced) -> None:
    """
    Create a demo of agent codebase contribution.
    
    Args:
        hub: Enhanced Core Hub
    """
    print_section("Setting up agent coordinator")
    
    # Create agent coordinator
    agent_coordinator_config = {
        "data_dir": "data/agent_coordination",
        "max_agent_tasks": 3
    }
    coordinator = create_agent_coordinator(hub, agent_coordinator_config)
    
    # Create and register agents
    agents = create_agents(hub, create_demo_config())
    logger.info(f"Created {len(agents)} developer agents")
    
    # Wait for a moment to let everything initialize
    time.sleep(2)
    
    # Create and assign tasks
    task_ids = create_development_tasks(coordinator)
    logger.info(f"Created {len(task_ids)} development tasks")
    
    # Assign tasks to agents
    assign_tasks(coordinator, task_ids)
    
    # Monitor tasks
    tasks_completed = monitor_tasks(coordinator, task_ids, timeout=120)
    
    # Summarize results
    summarize_results(coordinator, task_ids)
    
    # Analyze results
    if tasks_completed:
        run_codebase_analysis(coordinator)


def run_codebase_analysis(coordinator: AgentCoordinator) -> None:
    """
    Run codebase analysis and generate tasks from results.
    
    Args:
        coordinator: Agent Coordinator
    """
    print_section("Running codebase analysis")
    
    # Analyze codebase
    analysis = coordinator.analyze_codebase()
    
    print(f"Found {len(analysis['modules'])} modules")
    
    if "code_quality" in analysis and "issues" in analysis["code_quality"]:
        print(f"Found {len(analysis['code_quality']['issues'])} code quality issues")
    
    if "test_coverage" in analysis and "low_coverage" in analysis["test_coverage"]:
        print(f"Found {len(analysis['test_coverage']['low_coverage'])} modules with low test coverage")
    
    # Generate tasks from analysis
    print_section("Generating tasks from analysis")
    task_ids = coordinator.generate_tasks_from_analysis(analysis)
    
    print(f"Generated {len(task_ids)} tasks from analysis")
    for task_id in task_ids:
        task = coordinator.get_task(task_id)
        if task:
            print(f"- {task.title}")


def main() -> None:
    """
    Main function for the demo.
    """
    print_header("Benton County Assessor's Office AI Platform - Agent-Assisted Development Demo")
    
    print("This demo shows how AI agents can contribute to building and improving the application codebase.")
    
    # Create necessary directories
    os.makedirs("data/core", exist_ok=True)
    os.makedirs("data/agent_coordination", exist_ok=True)
    os.makedirs("logs/core", exist_ok=True)
    
    # Create and save demo configuration
    config = create_demo_config()
    save_config(config, "data/core/config.json")
    
    # Create and start the Core Hub
    print_section("Initializing Enhanced Core Hub")
    hub = create_core_hub_enhanced("data/core/config.json")
    hub.start()
    print("Enhanced Core Hub started successfully")
    
    try:
        # Run the demo
        create_agent_codebase_contribution_demo(hub)
    except Exception as e:
        logger.error(f"Error running demo: {str(e)}")
        raise
    finally:
        # Stop the hub
        print_section("Stopping Enhanced Core Hub")
        hub.stop()
        print("Enhanced Core Hub stopped successfully")
    
    print_header("Agent-Assisted Development Demo Completed")
    print("\nThe demo has shown how AI agents can contribute to building and improving the application codebase.")
    print("Agents have generated code, improved existing components, created tests, and documented the system.")
    print("This demonstrates the potential for a self-improving system where agents actively help build the application.")


if __name__ == "__main__":
    main()