#!/usr/bin/env python3
"""
Enhanced Core Hub Demo for Benton County Assessor's Office AI Platform

This script demonstrates the Enhanced Core Hub functionality, including
modular component architecture, improved error handling, enhanced agent management,
and comprehensive logging.
"""

import os
import json
import time
import uuid
import random
from typing import Dict, Any, List

from core.hub_enhanced import CoreHubEnhanced, create_core_hub_enhanced
from core.message import CommandMessage, ResponseMessage, ErrorMessage, EventType, Priority
from core.error_handler import ErrorCode, ErrorCategory, ErrorLevel


def print_header(title: str) -> None:
    """Print a formatted header."""
    print("\n" + "=" * 80)
    print(f"{title:^80}")
    print("=" * 80 + "\n")


def print_section(title: str) -> None:
    """Print a section title."""
    print(f"\n{title}...")


def create_demo_config() -> Dict[str, Any]:
    """Create a demo configuration."""
    return {
        "core": {
            "name": "BentonCountyAssessorCore",
            "version": "3.0.0",
            "data_dir": "data/core",
            "master_prompt": "You are an AI assistant for the Benton County Assessor's Office.",
            "master_prompt_refresh_interval": 3600
        },
        "logging": {
            "log_level": "debug",
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
                "max_bytes": 10485760,
                "backup_count": 5
            },
            "propagate": False
        },
        "communication": {
            "protocol": "memory",
            "settings": {}
        },
        "agent_manager": {
            "health_check_interval": 60,
            "health_check_enabled": True,
            "agent_timeout": 300
        },
        "error_handler": {
            "max_errors": 1000
        },
        "replay_buffer": {
            "type": "memory",
            "capacity": 10000,
            "alpha": 0.6,
            "beta": 0.4
        }
    }


def save_config(config: Dict[str, Any], path: str) -> None:
    """Save configuration to a file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    with open(path, "w") as f:
        json.dump(config, f, indent=2)
    
    print(f"Configuration saved to {path}")


def register_mock_agents(hub: CoreHubEnhanced) -> List[str]:
    """Register mock agents for the demo."""
    print_section("Registering mock agents")
    
    agents = [
        {
            "id": "data_quality_agent",
            "name": "Data Quality Agent",
            "type": "data_quality",
            "description": "Validates property assessment data against Washington State standards",
            "capabilities": ["validate_data", "detect_anomalies", "enhance_data"],
            "subscriptions": ["data_update", "validation_request"],
            "dependencies": []
        },
        {
            "id": "compliance_agent",
            "name": "Compliance Agent",
            "type": "compliance",
            "description": "Ensures compliance with Washington State Department of Revenue requirements",
            "capabilities": ["verify_compliance", "generate_reports", "analyze_regulations"],
            "subscriptions": ["regulation_update", "compliance_request"],
            "dependencies": ["validate_data"]
        },
        {
            "id": "valuation_agent",
            "name": "Valuation Agent",
            "type": "valuation",
            "description": "Provides property valuation services using advanced ML models",
            "capabilities": ["valuate_property", "trend_analysis", "comparative_analysis"],
            "subscriptions": ["valuation_request", "market_update"],
            "dependencies": ["validate_data", "verify_compliance"]
        }
    ]
    
    # First unregister any existing agents to avoid conflicts
    for agent in agents:
        agent_id = agent["id"]
        existing = hub.get_agent_info(agent_id)
        if existing:
            print(f"Deregistering existing agent: {agent_id}")
            hub.deregister_agent(agent_id)
    
    # Now register agents with clean state
    registered_agents = []
    for agent in agents:
        agent_id = agent.pop("id")
        print(f"Registering agent: {agent['name']}")
        success = hub.register_agent(agent_id, agent)
        
        if success:
            print(f"Agent registered successfully: {agent_id}")
            registered_agents.append(agent_id)
        else:
            print(f"Failed to register agent: {agent_id}")
    
    print(f"Registered {len(registered_agents)} agents:")
    for agent_id in registered_agents:
        agent_info = hub.get_agent_info(agent_id)
        print(f"  - {agent_id}: {agent_info['type']} ({agent_info['name']})")
    
    return registered_agents


def simulate_message_exchange(hub: CoreHubEnhanced, agent_ids: List[str]) -> None:
    """Simulate message exchange between agents."""
    print_section("Simulating message exchange")
    
    # Command message
    source_agent = random.choice(agent_ids)
    target_agent = random.choice([a for a in agent_ids if a != source_agent])
    
    command = CommandMessage(
        source_agent_id=source_agent,
        target_agent_id=target_agent,
        command_name="verify_compliance",
        parameters={
            "property_id": "12345",
            "assessment_date": "2025-01-01",
            "assessment_value": 450000
        }
    )
    
    print(f"Sending command: {command.payload.get('command_name')}")
    hub.send_message(command)
    print("Command sent successfully")
    
    # Response message
    response = ResponseMessage(
        source_agent_id=target_agent,
        target_agent_id=source_agent,
        status="success",
        result={
            "compliance_status": "compliant",
            "details": {
                "requirements_met": 5,
                "requirements_total": 5
            }
        },
        original_message_id=command.message_id,
        correlation_id=command.correlation_id
    )
    
    print(f"Sending response with status: {response.payload.get('status')}")
    hub.send_message(response)
    print("Response sent successfully")
    
    # Error message
    error = ErrorMessage(
        source_agent_id=target_agent,
        target_agent_id=source_agent,
        error_code=ErrorCode.INVALID_INPUT,
        error_message="Invalid property ID format",
        details={
            "level": ErrorLevel.WARNING,
            "category": ErrorCategory.VALIDATION,
            "property_id": "12345",
            "expected_format": "COUNTY-PARCEL-XXXX"
        },
        correlation_id=str(uuid.uuid4())
    )
    
    print(f"Sending error: {error.payload.get('error_code')}")
    hub.send_message(error)
    print("Error sent successfully")


def test_error_handling(hub: CoreHubEnhanced) -> None:
    """Test error handling functionality."""
    print_section("Testing error handling")
    
    # Create an error
    try:
        # Simulate error
        raise ValueError("Invalid property assessment value")
    except Exception as e:
        # Handle error through error handler
        error = hub.error_handler.handle_error(
            e,
            code=ErrorCode.INVALID_INPUT,
            level=ErrorLevel.ERROR,
            category=ErrorCategory.VALIDATION,
            details={
                "property_id": "BENTON-12345",
                "assessment_value": "-10000"
            },
            source="valuation_agent"
        )
        
        print(f"Error handled: {error.code} - {error.message}")
    
    # Get error summary
    summary = hub.error_handler.get_error_summary()
    print(f"Error summary: {json.dumps(summary, indent=2)}")


def main() -> None:
    """Main function to demonstrate Enhanced Core Hub functionality."""
    print_header("Benton County Assessor's Office AI Platform - Enhanced Core Hub Demo")
    
    print("Demonstrating enhanced core hub capabilities...")
    
    print_section("Creating required directories")
    os.makedirs("data/core", exist_ok=True)
    os.makedirs("logs/core", exist_ok=True)
    
    print_section("Creating demo configuration")
    config = create_demo_config()
    save_config(config, "data/core/config.json")
    
    print_section("Initializing Enhanced Core Hub")
    hub = create_core_hub_enhanced("data/core/config.json")
    print("Enhanced Core Hub initialized")
    
    print_section("Starting Enhanced Core Hub")
    hub.start()
    print("Enhanced Core Hub started successfully")
    
    # Register mock agents
    agent_ids = register_mock_agents(hub)
    
    # Simulate message exchange
    simulate_message_exchange(hub, agent_ids)
    
    # Test error handling
    test_error_handling(hub)
    
    # Get system status
    print_section("Getting system status")
    status = hub.get_system_status()
    print("System status:")
    print(json.dumps(status, indent=2))
    
    # Stop the hub
    print_section("Stopping Enhanced Core Hub")
    hub.stop()
    print("Enhanced Core Hub stopped successfully")
    
    print_header("Enhanced Core Hub Demo Completed")


if __name__ == "__main__":
    main()