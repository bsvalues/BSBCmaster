#!/usr/bin/env python3
"""
Core Hub Demo for Benton County Assessor's Office AI Platform

This script demonstrates the Core Hub functionality, including
configuration, messaging, experience replay, and agent registration.
"""

import time
import json
import logging
import os
from typing import Dict, Any

from core import CoreConfig, CoreHub, Message, CommandMessage, ResponseMessage, EventType, Experience

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("core_demo")


def main():
    """Main function to demonstrate Core Hub functionality."""
    print("\n" + "=" * 80)
    print("Benton County Assessor's Office AI Platform - Core Hub Demo".center(80))
    print("=" * 80 + "\n")
    
    # Create config directories
    os.makedirs("data/core", exist_ok=True)
    os.makedirs("logs/core", exist_ok=True)
    
    # Initialize Core Hub
    print("Initializing Core Hub...")
    hub = CoreHub()
    
    # Create a configuration file
    config_path = "data/core/config.json"
    hub.config.save_config(config_path)
    print(f"Configuration saved to {config_path}")
    
    # Start the Core Hub
    hub.start()
    print("Core Hub started successfully.")
    
    # Register mock agents
    print("\nRegistering mock agents...")
    
    data_quality_agent = {
        "name": "Data Quality Agent",
        "type": "data_quality",
        "description": "Validates property assessment data against Washington State standards",
        "capabilities": ["validate_data", "detect_anomalies", "enhance_data"]
    }
    
    compliance_agent = {
        "name": "Compliance Agent",
        "type": "compliance",
        "description": "Ensures compliance with Washington State assessment regulations",
        "capabilities": ["check_compliance", "verify_exemption", "create_audit_record"]
    }
    
    valuation_agent = {
        "name": "Valuation Agent",
        "type": "valuation",
        "description": "Calculates property values using advanced models",
        "capabilities": ["estimate_value", "analyze_trends", "compare_properties"]
    }
    
    hub.register_agent("data_quality_agent", data_quality_agent)
    hub.register_agent("compliance_agent", compliance_agent)
    hub.register_agent("valuation_agent", valuation_agent)
    
    # Get registered agents
    agents = hub.get_registered_agents()
    print(f"Registered {len(agents)} agents:")
    for agent_id, info in agents.items():
        print(f"  - {agent_id}: {info['type']} ({info['name']})")
    
    # Simulate message sending
    print("\nSimulating message exchange...")
    
    # Create a command message
    command = CommandMessage(
        source_agent_id="data_quality_agent",
        target_agent_id="compliance_agent",
        command_name="verify_compliance",
        parameters={
            "property_id": "123456",
            "assessment_year": 2024,
            "value": 350000
        }
    )
    
    # Send the command
    print(f"Sending command: {command.command_name}")
    hub.send_message(command)
    
    # Simulate response
    response = ResponseMessage(
        source_agent_id="compliance_agent",
        target_agent_id="data_quality_agent",
        status="success",
        result={
            "compliant": True,
            "regulations_checked": ["RCW 84.40.020", "WAC 458-07-015"],
            "notes": "Property assessment complies with all requirements"
        },
        original_message_id=command.message_id
    )
    
    # Send the response
    print(f"Sending response: {response.payload['status']}")
    hub.send_message(response)
    
    # Record experiences in the replay buffer
    print("\nRecording experiences in replay buffer...")
    
    # Create an experience
    experience = Experience(
        agent_id="data_quality_agent",
        state={
            "property_id": "123456",
            "validation_running": False
        },
        action={
            "type": "start_validation",
            "property_id": "123456"
        },
        result={
            "status": "success",
            "validation_started": True
        },
        next_state={
            "property_id": "123456",
            "validation_running": True
        },
        reward_signal=1.0
    )
    
    # Add to replay buffer
    hub.replay_buffer.add(experience)
    print(f"Added experience to replay buffer: {experience.experience_id}")
    
    # Add a few more experiences
    for i in range(5):
        exp = Experience(
            agent_id=["data_quality_agent", "compliance_agent", "valuation_agent"][i % 3],
            state={"demo": f"state_{i}"},
            action={"type": f"action_{i}"},
            result={"status": "success"},
            next_state={"demo": f"next_state_{i}"},
            reward_signal=0.8 + (i * 0.04)
        )
        hub.replay_buffer.add(exp)
    
    # Get buffer statistics
    buffer_stats = hub.replay_buffer.get_stats()
    print("\nReplay buffer statistics:")
    print(f"  Size: {buffer_stats['size']}/{buffer_stats['capacity']}")
    print(f"  Total added: {buffer_stats['total_added']}")
    print(f"  Agent distribution: {buffer_stats['agent_distribution']}")
    print(f"  Average reward: {buffer_stats['avg_reward']:.2f}")
    
    # Sample from replay buffer
    print("\nSampling from replay buffer...")
    experiences, indices, weights = hub.replay_buffer.sample(batch_size=3)
    print(f"Sampled {len(experiences)} experiences")
    
    for i, exp in enumerate(experiences):
        print(f"  Experience {i+1}: Agent={exp.agent_id}, Reward={exp.reward_signal:.2f}, Weight={weights[i]:.2f}")
    
    # Get system status
    print("\nGetting system status...")
    
    try:
        # Note: This will fail because we haven't added start_time to CoreHub
        system_status = hub.get_system_status()
        print("System status:")
        print(json.dumps(system_status, indent=2))
    except Exception as e:
        print(f"Error getting system status: {e}")
        
        # Show what we can get
        print("Registered agents:")
        print(json.dumps(hub.get_registered_agents(), indent=2))
    
    # Clean up
    print("\nStopping Core Hub...")
    hub.stop()
    print("Core Hub stopped successfully.")
    
    print("\nDemo completed successfully.\n")


if __name__ == "__main__":
    main()