#!/usr/bin/env python3
"""
Core Hub Demo for Benton County Assessor's Office AI Platform

This script demonstrates the Core Hub functionality, including
configuration, messaging, experience replay, agent registration,
and enhanced structured logging.
"""

import time
import json
import logging
import os
from typing import Dict, Any

from core import (
    CoreConfig, CoreHub, Message, CommandMessage, ResponseMessage, 
    EventType, Experience, create_logger, ContextAdapter
)

# Configure basic logging for demo setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create a context-aware logger for the demo
logger = create_logger("core_demo", {
    "component": "Demo", 
    "version": "1.0.0",
    "purpose": "Demonstration"
})


def main():
    """Main function to demonstrate Core Hub functionality."""
    print("\n" + "=" * 80)
    print("Benton County Assessor's Office AI Platform - Core Hub Demo".center(80))
    print("=" * 80 + "\n")
    
    # Demonstrate structured logging capabilities
    print("Demonstrating structured logging capabilities...")
    
    # Log with different context levels
    logger.info("Starting Core Hub demo")
    
    # Add transaction context
    transaction_logger = logger.with_context(transaction_id="DEMO-001", source="command_line")
    transaction_logger.info("Demo transaction initiated")
    
    # Add more specific context for a task
    task_logger = transaction_logger.with_context(task="initialization", priority="high")
    task_logger.info("Creating required directories")
    
    # Create config directories
    os.makedirs("data/core", exist_ok=True)
    os.makedirs("logs/core", exist_ok=True)
    
    # Initialize Core Hub
    task_logger.info("Initializing Core Hub")
    print("Initializing Core Hub...")
    hub = CoreHub()
    
    # Create a configuration file
    config_path = "data/core/config.json"
    hub.config.save_config(config_path)
    task_logger.info(f"Configuration saved to {config_path}")
    print(f"Configuration saved to {config_path}")
    
    # Log success with different context
    logger.with_context(
        stage="setup", 
        status="complete", 
        time_taken=time.time() - time.time()
    ).info("Core Hub setup completed successfully")
    
    # Start the Core Hub
    hub.start()
    print("Core Hub started successfully.")
    
    # Register mock agents
    print("\nRegistering mock agents...")
    
    # Create logger for agent registration process
    agent_logger = logger.with_context(
        process="agent_registration",
        operation_id=f"REGISTER-{int(time.time())}"
    )
    agent_logger.info("Beginning agent registration process")
    
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
    
    # Register with contextual logging
    for agent_id, agent_info in [
        ("data_quality_agent", data_quality_agent),
        ("compliance_agent", compliance_agent),
        ("valuation_agent", valuation_agent)
    ]:
        agent_specific_logger = agent_logger.with_context(
            agent_id=agent_id,
            agent_type=agent_info["type"]
        )
        agent_specific_logger.info(f"Registering agent: {agent_info['name']}")
        hub.register_agent(agent_id, agent_info)
        agent_specific_logger.info(f"Agent registered successfully: {agent_id}")
    
    # Get registered agents
    agents = hub.get_registered_agents()
    agent_logger.with_context(
        registration_count=len(agents),
        registration_complete=True
    ).info(f"Completed agent registration process with {len(agents)} agents")
    
    print(f"Registered {len(agents)} agents:")
    for agent_id, info in agents.items():
        print(f"  - {agent_id}: {info['type']} ({info['name']})")
    
    # Simulate message sending
    print("\nSimulating message exchange...")
    
    # Create message exchange logger
    msg_logger = logger.with_context(
        process="message_exchange",
        transaction_id=f"MSG-FLOW-{int(time.time())}"
    )
    msg_logger.info("Beginning message exchange simulation")
    
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
    
    # Send the command with logging
    cmd_logger = msg_logger.with_context(
        message_id=command.message_id,
        message_type="command",
        source_agent=command.source_agent_id,
        target_agent=command.target_agent_id,
        command=command.payload.get("command_name")
    )
    cmd_logger.info(f"Sending command: {command.payload.get('command_name')}")
    print(f"Sending command: {command.payload.get('command_name')}")
    hub.send_message(command)
    cmd_logger.info("Command sent successfully")
    
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
    
    # Send the response with logging
    resp_logger = msg_logger.with_context(
        message_id=response.message_id,
        message_type="response",
        source_agent=response.source_agent_id,
        target_agent=response.target_agent_id,
        status=response.payload.get("status"),
        original_message_id=response.payload.get("original_message_id")
    )
    resp_logger.info(f"Sending response: {response.payload.get('status')}")
    print(f"Sending response: {response.payload['status']}")
    hub.send_message(response)
    resp_logger.info("Response sent successfully")
    
    # Log the completion of the message exchange
    msg_logger.with_context(
        exchange_complete=True,
        messages_sent=2
    ).info("Message exchange simulation completed successfully")
    
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
    system_status = hub.get_system_status()
    print("System status:")
    print(json.dumps(system_status, indent=2))
    
    # Demonstrate state persistence
    print("\nDemonstrating state persistence...")
    
    # Force save state
    print("Forcing state save...")
    hub.force_save_state()
    print(f"State saved to {hub.state_file}")
    
    # Simulate status updates
    print("\nSimulating agent status updates...")
    for agent_id in list(hub.get_registered_agents().keys()):
        # Create status update message for each agent
        status_message = Message(
            message_id=f"status_{agent_id}_{int(time.time())}",
            source_agent_id=agent_id,
            target_agent_id="core_hub",
            event_type=EventType.STATUS_UPDATE,
            payload={
                "status": "active",
                "metrics": {
                    "cpu_usage": 0.2 + (hash(agent_id) % 5) / 10,
                    "memory_usage": 120 + (hash(agent_id) % 10) * 10,
                    "tasks_completed": hash(agent_id) % 10,
                    "errors": 0
                }
            }
        )
        
        # Handle status update
        hub._handle_status_update(status_message)
        print(f"Updated status for {agent_id}")
    
    # Demonstrate assistance request and response tracking
    print("\nDemonstrating assistance request and response tracking...")
    
    # Create assistance logger
    assist_logger = logger.with_context(
        process="assistance_tracking",
        operation_id=f"ASSIST-{int(time.time())}"
    )
    assist_logger.info("Beginning assistance request and response tracking")
    
    # Create an assistance request
    assistance_request = Message(
        message_id=f"assist_req_{int(time.time())}",
        source_agent_id="valuation_agent",
        target_agent_id="core_hub",
        event_type=EventType.ASSISTANCE_REQUESTED,
        payload={
            "assistance_type": "model_selection",
            "property_type": "commercial",
            "location": "downtown",
            "priority": "high"
        }
    )
    
    # Record the assistance request with contextual logging
    request_logger = assist_logger.with_context(
        message_id=assistance_request.message_id,
        source_agent=assistance_request.source_agent_id,
        assistance_type=assistance_request.payload.get("assistance_type"),
        priority=assistance_request.payload.get("priority"),
        stage="request"
    )
    request_logger.info("Recording assistance request...")
    print("Recording assistance request...")
    hub._handle_assistance_request(assistance_request)
    request_logger.info("Assistance request recorded successfully")
    
    # Record a response to the assistance request with contextual logging
    response_logger = assist_logger.with_context(
        request_message_id=assistance_request.message_id,
        stage="response",
        success=True
    )
    response_logger.info("Recording assistance response...")
    print("Recording assistance response...")
    hub.record_assistance_response(
        request_message_id=assistance_request.message_id,
        response={
            "model_selected": "commercial_downtown_high_value",
            "confidence": 0.92,
            "additional_data_needed": False
        },
        success=True
    )
    response_logger.info("Assistance response recorded successfully")
    
    # Log the completion of the assistance tracking
    assist_logger.with_context(
        process_complete=True,
        total_operations=2
    ).info("Assistance request and response tracking completed successfully")
    
    # Demonstrate a second save and show replay buffer stats
    print("\nForcing another state save and checking replay buffer...")
    hub.force_save_state()
    
    # Get updated buffer statistics
    buffer_stats = hub.replay_buffer.get_stats()
    print("\nUpdated replay buffer statistics:")
    print(f"  Size: {buffer_stats['size']}/{buffer_stats['capacity']}")
    print(f"  Total added: {buffer_stats['total_added']}")
    print(f"  Agent distribution: {buffer_stats['agent_distribution']}")
    print(f"  Average reward: {buffer_stats['avg_reward']:.2f}")
    
    # Clean up with logging
    # Create shutdown logger
    shutdown_logger = logger.with_context(
        process="shutdown",
        operation_id=f"SHUTDOWN-{int(time.time())}"
    )
    shutdown_logger.info("Beginning Core Hub shutdown process")
    print("\nStopping Core Hub...")
    
    # Stop the hub
    hub.stop()
    shutdown_logger.info("Core Hub stopped successfully")
    print("Core Hub stopped successfully.")
    
    # Verify that state was saved on shutdown
    state_logger = shutdown_logger.with_context(
        state_file=hub.state_file,
        stage="state_verification"
    )
    state_logger.info("Verifying state persistence after shutdown")
    print(f"\nVerifying state file exists at {hub.state_file}...")
    
    if os.path.exists(hub.state_file):
        file_size = os.path.getsize(hub.state_file)
        state_logger.with_context(file_size=file_size).info(f"State file exists and is {file_size} bytes")
        print(f"State file exists and is {file_size} bytes")
        
        # Load and print some state data
        try:
            with open(hub.state_file, 'r') as f:
                state_data = json.load(f)
            
            agent_count = len(state_data.get('registered_agents', {}))
            saved_time = time.ctime(state_data.get('saved_at', 0))
            
            state_logger.with_context(
                agent_count=agent_count,
                saved_at=saved_time,
                state_valid=True
            ).info(f"State file contains valid data for {agent_count} agents")
            
            print(f"State contains data for {agent_count} agents")
            print(f"State was saved at: {saved_time}")
        
        except Exception as e:
            state_logger.with_context(
                error=str(e),
                state_valid=False
            ).error(f"Error reading state file: {e}")
            print(f"Error reading state file: {e}")
    else:
        state_logger.with_context(state_valid=False).warning("State file doesn't exist!")
        print("State file doesn't exist!")
    
    # Log final completion
    logger.with_context(
        demo_success=True,
        completion_time=time.time()
    ).info("Core Hub demo completed successfully")
    
    print("\nDemo completed successfully.\n")


if __name__ == "__main__":
    main()