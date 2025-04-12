"""
Integration module for connecting the agent-assisted development framework 
with the Benton County Assessor's Office AI Platform.

This module provides functions to initialize and integrate the agent-assisted
development system with the existing MCP platform.
"""

import os
import sys
import json
import logging
from typing import Dict, Any, Optional, List, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("agent_coordination.integration")


def load_configuration(config_path: str) -> Dict[str, Any]:
    """
    Load configuration from a file.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        Loaded configuration
    """
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
        logger.info(f"Configuration loaded from {config_path}")
        return config
    except Exception as e:
        logger.error(f"Error loading configuration from {config_path}: {str(e)}")
        # Return default configuration
        return {
            "core": {
                "name": "BentonCountyAssessorCore",
                "version": "3.0.0",
                "data_dir": "data/core",
                "log_level": "info"
            },
            "agent_coordinator": {
                "data_dir": "data/agent_coordination",
                "max_agent_tasks": 3
            }
        }


def initialize_agent_coordinator(config: Dict[str, Any], hub=None) -> Union[Any, None]:
    """
    Initialize the agent coordinator.
    
    Args:
        config: Configuration
        hub: Core Hub instance, or None if not available
        
    Returns:
        Agent Coordinator instance, or None if initialization failed
    """
    try:
        # Attempt to import required modules
        try:
            from agent_coordination.coordinator import AgentCoordinator, create_agent_coordinator
            logger.info("Successfully imported AgentCoordinator")
        except ImportError:
            logger.warning("Could not import AgentCoordinator, falling back to mock implementation")
            from agent_coordination.simple_demo import MockAgent
            
            # Create a mock coordinator if the real one isn't available
            class MockCoordinator:
                def __init__(self, config):
                    self.config = config
                    self.tasks = {}
                    self.logger = logging.getLogger("mock_coordinator")
                    self.logger.info("Mock coordinator initialized")
                
                def create_task(self, task_data):
                    task_id = f"task-{len(self.tasks) + 1}"
                    self.tasks[task_id] = task_data
                    self.logger.info(f"Created mock task {task_id}")
                    return task_id
                
                def assign_task(self, task_id, agent_id=None):
                    self.logger.info(f"Assigned mock task {task_id} to agent {agent_id}")
                    return True
                
                def analyze_codebase(self):
                    self.logger.info("Analyzing codebase (mock)")
                    return {
                        "modules": [],
                        "code_quality": {"issues": []},
                        "test_coverage": {"low_coverage": []}
                    }
                
                def generate_tasks_from_analysis(self, analysis):
                    self.logger.info("Generating tasks from analysis (mock)")
                    return []
            
            # Return mock coordinator
            coordinator = MockCoordinator(config.get("agent_coordinator", {}))
            logger.info("Mock coordinator created successfully")
            return coordinator
        
        # Initialize the real coordinator if we have a hub
        if hub is not None:
            coordinator = create_agent_coordinator(hub, config.get("agent_coordinator", {}))
            logger.info("Agent coordinator created successfully")
            return coordinator
        else:
            logger.warning("No hub provided, cannot create real agent coordinator")
            # Return None to indicate that we couldn't create a real coordinator
            return None
            
    except Exception as e:
        logger.error(f"Error initializing agent coordinator: {str(e)}")
        return None


def initialize_developer_agents(config: Dict[str, Any], coordinator: Any, hub=None) -> List[Any]:
    """
    Initialize developer agents.
    
    Args:
        config: Configuration
        coordinator: Agent Coordinator instance
        hub: Core Hub instance, or None if not available
        
    Returns:
        List of created agents
    """
    agents = []
    
    try:
        # Attempt to import required modules
        try:
            from agent_coordination.developer_agent import DeveloperAgent, create_developer_agent
            from agent_coordination.data_validation_agent import DataValidationAgent, create_data_validation_agent
            logger.info("Successfully imported agent implementations")
            have_real_agents = True
        except ImportError:
            logger.warning("Could not import agent implementations, falling back to mock agents")
            from agent_coordination.simple_demo import MockAgent
            have_real_agents = False
        
        # Create developer agents
        developer_configs = config.get("developer_agents", [])
        for agent_config in developer_configs:
            agent_id = agent_config.get("id", f"developer-{len(agents) + 1}")
            logger.info(f"Creating developer agent: {agent_id}")
            
            if have_real_agents and hub is not None:
                agent = create_developer_agent(agent_id, None)
                # Connect to hub if possible
                try:
                    agent.connect_to_hub(hub)
                    logger.info(f"Connected agent {agent_id} to hub")
                except Exception as e:
                    logger.warning(f"Could not connect agent {agent_id} to hub: {str(e)}")
            else:
                # Create mock agent
                agent = MockAgent(
                    agent_id=agent_id,
                    agent_type="developer",
                    capabilities=agent_config.get("capabilities", [])
                )
                logger.info(f"Created mock developer agent: {agent_id}")
            
            agents.append(agent)
            
            # Register with hub if possible
            if hub is not None:
                try:
                    hub.register_agent(
                        agent_id=agent_id,
                        agent_info={
                            "name": f"{agent_config.get('specialization', 'General').title()} Developer",
                            "type": "developer",
                            "description": f"AI agent specialized in {agent_config.get('specialization', 'general')} development",
                            "capabilities": agent_config.get("capabilities", []),
                            "programming_languages": agent_config.get("programming_languages", []),
                            "specialization": agent_config.get("specialization", "general")
                        }
                    )
                    logger.info(f"Registered agent {agent_id} with hub")
                except Exception as e:
                    logger.warning(f"Could not register agent {agent_id} with hub: {str(e)}")
        
        # Create validator agents
        validator_configs = config.get("validator_agents", [])
        for agent_config in validator_configs:
            agent_id = agent_config.get("id", f"validator-{len(agents) + 1}")
            logger.info(f"Creating validator agent: {agent_id}")
            
            if have_real_agents and hub is not None:
                agent = create_data_validation_agent(agent_id, None)
                # Connect to hub if possible
                try:
                    agent.connect_to_hub(hub)
                    logger.info(f"Connected agent {agent_id} to hub")
                except Exception as e:
                    logger.warning(f"Could not connect agent {agent_id} to hub: {str(e)}")
            else:
                # Create mock agent
                agent = MockAgent(
                    agent_id=agent_id,
                    agent_type="validator",
                    capabilities=["data_validation", "anomaly_detection", "quality_reporting"]
                )
                logger.info(f"Created mock validator agent: {agent_id}")
            
            agents.append(agent)
            
            # Register with hub if possible
            if hub is not None:
                try:
                    hub.register_agent(
                        agent_id=agent_id,
                        agent_info={
                            "name": "Data Validation Agent",
                            "type": "validator",
                            "description": "AI agent specialized in data validation and quality assessment",
                            "capabilities": ["data_validation", "anomaly_detection", "quality_reporting"],
                            "specialization": "data_quality"
                        }
                    )
                    logger.info(f"Registered agent {agent_id} with hub")
                except Exception as e:
                    logger.warning(f"Could not register agent {agent_id} with hub: {str(e)}")
                    
    except Exception as e:
        logger.error(f"Error initializing developer agents: {str(e)}")
    
    return agents


def initialize_agent_development_system(config_path: Optional[str] = None, hub=None):
    """
    Initialize the agent-assisted development system.
    
    Args:
        config_path: Path to the configuration file, or None to use default
        hub: Core Hub instance, or None if not available
        
    Returns:
        Tuple of (coordinator, agents)
    """
    # Use default config path if none provided
    if config_path is None:
        config_path = "data/core/config.json"
    
    # Load configuration
    config = load_configuration(config_path)
    
    # Initialize agent coordinator
    coordinator = initialize_agent_coordinator(config, hub)
    
    # Initialize developer agents if coordinator was created
    agents = []
    if coordinator is not None:
        agents = initialize_developer_agents(config, coordinator, hub)
    
    return coordinator, agents


def analyze_and_create_tasks(coordinator):
    """
    Analyze the codebase and create development tasks.
    
    Args:
        coordinator: Agent Coordinator
        
    Returns:
        List of created task IDs
    """
    try:
        # Analyze codebase
        logger.info("Analyzing codebase...")
        analysis = coordinator.analyze_codebase()
        
        # Log analysis results
        code_issues = len(analysis.get("code_quality", {}).get("issues", []))
        low_coverage_modules = len(analysis.get("test_coverage", {}).get("low_coverage", []))
        total_modules = len(analysis.get("modules", []))
        
        logger.info(f"Code analysis completed: {total_modules} modules analyzed, {code_issues} issues found, {low_coverage_modules} modules with low test coverage")
        
        # Generate tasks from analysis
        logger.info("Generating tasks from analysis...")
        task_ids = coordinator.generate_tasks_from_analysis(analysis)
        
        logger.info(f"Generated {len(task_ids)} tasks from analysis")
        
        return task_ids
    except Exception as e:
        logger.error(f"Error analyzing and creating tasks: {str(e)}")
        return []


if __name__ == "__main__":
    print("Benton County Assessor's Office - Agent-Assisted Development Integration")
    print("-------------------------------------------------------------------")
    print("This module provides integration for agent-assisted development.")
    print("Import this module from your main application to use it.")
    
    # Simple test of functionality
    coordinator, agents = initialize_agent_development_system()
    
    if coordinator is not None:
        print(f"Successfully initialized agent coordinator")
        if agents:
            print(f"Successfully initialized {len(agents)} agents")
        else:
            print("No agents were initialized")
    else:
        print("Failed to initialize agent coordinator")