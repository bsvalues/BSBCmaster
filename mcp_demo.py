"""
MCP Demo Script for Benton County Assessor's Office

This script demonstrates the Master Control Program (MCP) and AI agents
for the Benton County Assessor's Office property assessment platform.
"""

import logging
import time
import json
from typing import Dict, Any
import os

from mcp.master_control import MasterControlProgram
from mcp.agents.data_quality_agent import DataQualityAgent
from mcp.agents.compliance_agent import ComplianceAgent
from mcp.message import MessageType, MessagePriority
from mcp.task import TaskPriority

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def print_section(title):
    """Print a section title."""
    print("\n" + "=" * 80)
    print(f" {title} ".center(80, "="))
    print("=" * 80)

def print_json(data):
    """Print data as formatted JSON."""
    print(json.dumps(data, indent=2))

def main():
    """Main demo function."""
    print_section("Benton County Assessor's Office MCP Demo")
    
    # Create the MCP
    print("\nInitializing Master Control Program...")
    mcp = MasterControlProgram()
    
    # Start the MCP
    mcp.start()
    print("MCP started successfully.")
    
    # Create and register agents
    print("\nCreating and registering agents...")
    
    # Data Quality Agent
    data_quality_agent = DataQualityAgent(
        name="Property Data Quality Agent",
        description="Validates property assessment data against Washington State standards and Benton County regulations"
    )
    data_quality_agent.register_with_mcp(mcp)
    
    # Compliance Agent
    compliance_agent = ComplianceAgent(
        name="Assessment Compliance Agent",
        description="Ensures compliance with Washington State assessment regulations and Benton County policies"
    )
    compliance_agent.register_with_mcp(mcp)
    
    print("Agents registered successfully.")
    
    # View registered agents
    print("\nRegistered Agents:")
    agents = mcp.list_agents()
    for agent in agents:
        print(f"  - {agent['name']} ({agent['agent_id']}) - Type: {agent['type']}")
    
    print("\nWaiting for agents to initialize...")
    time.sleep(2)
    
    # Get system status
    print("\nMCP System Status:")
    status = mcp.get_system_status()
    print_json(status)
    
    # Demo: Data Quality Agent
    print_section("Data Quality Agent Demo")
    
    # Sample parcel data for validation
    print("\nValidating sample parcel data...")
    sample_parcel = {
        "parcel_id": "12345678-1234",
        "address": "123 Main St",
        "city": "Richland",
        "state": "WA",
        "zip_code": "99352",
        "land_value": 100000,
        "improvement_value": 200000,
        "total_value": 300000,
        "assessment_year": 2024,
        "latitude": 46.2,
        "longitude": -119.2
    }
    
    # Direct agent method call
    validation_result = data_quality_agent.validate_entity("parcel", sample_parcel)
    print("Direct validation result:")
    print_json(validation_result)
    
    # Via MCP message
    print("\nSending validation request via MCP message...")
    message_result = mcp.send_message(
        from_agent_id="mcp_demo",
        to_agent_id=data_quality_agent.agent_id,
        message_type=MessageType.VALIDATION_REQUEST,
        content={
            "entity_type": "parcel",
            "data": sample_parcel
        }
    )
    print(f"Message sent: {message_result['message_id']}")
    
    # Via MCP task
    print("\nCreating data quality task via MCP...")
    task_result = mcp.create_task(
        to_agent_id=data_quality_agent.agent_id,
        task_type="validate_entity",
        parameters={
            "entity_type": "parcel",
            "data": sample_parcel
        },
        from_agent_id="mcp_demo"
    )
    print(f"Task created: {task_result['task_id']}")
    
    # Wait for task to process
    print("\nWaiting for task processing...")
    time.sleep(2)
    
    # Get task status
    task_status = mcp.get_task_status(task_result['task_id'])
    print("Task status:")
    print_json(task_status)
    
    # Demo: Anomaly Detection
    print("\nDetecting anomalies in property data...")
    anomalous_property = {
        "property_type": "Residential",
        "year_built": 1850,  # Unusually old
        "square_footage": 15000,  # Unusually large
        "bedrooms": 8,
        "bathrooms": 10,
        "lot_size": 20000,
        "lot_size_unit": "sq ft"
    }
    
    anomaly_task = mcp.create_task(
        to_agent_id=data_quality_agent.agent_id,
        task_type="detect_anomalies",
        parameters={
            "entity_type": "property",
            "data": anomalous_property
        },
        from_agent_id="mcp_demo"
    )
    
    # Wait for task to process
    time.sleep(2)
    
    # Get anomaly detection results
    anomaly_result = mcp.get_task_status(anomaly_task['task_id'])
    print("Anomaly detection results:")
    if 'result' in anomaly_result and anomaly_result['result']:
        print_json(anomaly_result['result'])
    else:
        print("No anomaly detection results available yet.")
    
    # Demo: Compliance Agent
    print_section("Compliance Agent Demo")
    
    # Sample tax calculation data for compliance check
    print("\nChecking tax calculation compliance...")
    tax_data = {
        "city": "Richland",
        "assessed_value": 350000,
        "tax_amount": 3800,  # Slightly off from expected value
        "tax_year": 2024
    }
    
    # Direct agent method call
    compliance_result = compliance_agent.check_compliance("tax_calculation", tax_data)
    print("Direct compliance check result:")
    print_json(compliance_result)
    
    # Exemption verification
    print("\nVerifying senior exemption eligibility...")
    exemption_data = {
        "exemption_type": "Senior/Disabled",
        "applicant_data": {
            "age": 65,
            "disabled": False,
            "income": 35000,
            "primary_residence": True,
            "documents": ["Income Verification", "Age Verification", "Residence Affidavit"]
        },
        "property_data": {
            "property_type": "Residential",
            "assessed_value": 250000
        }
    }
    
    exemption_task = mcp.create_task(
        to_agent_id=compliance_agent.agent_id,
        task_type="verify_exemption",
        parameters={
            "exemption_type": exemption_data["exemption_type"],
            "applicant_data": exemption_data["applicant_data"],
            "property_data": exemption_data["property_data"]
        },
        from_agent_id="mcp_demo"
    )
    
    # Wait for task to process
    time.sleep(2)
    
    # Get exemption verification results
    exemption_result = mcp.get_task_status(exemption_task['task_id'])
    print("Exemption verification results:")
    if 'result' in exemption_result and exemption_result['result']:
        print_json(exemption_result['result'])
    else:
        print("No exemption verification results available yet.")
    
    # Create audit trail record
    print("\nCreating audit trail record...")
    audit_task = mcp.create_task(
        to_agent_id=compliance_agent.agent_id,
        task_type="create_audit_record",
        parameters={
            "entity_type": "account",
            "entity_id": "ACC-12345",
            "action": "update",
            "changes": {
                "assessed_value": {
                    "old": 300000,
                    "new": 325000
                }
            },
            "user_id": "assessor123",
            "reason_code": "ANN-REV",
            "previous_value": 300000
        },
        from_agent_id="mcp_demo"
    )
    
    # Wait for task to process
    time.sleep(2)
    
    # Get audit record creation results
    audit_result = mcp.get_task_status(audit_task['task_id'])
    print("Audit record creation results:")
    if 'result' in audit_result and audit_result['result']:
        print_json(audit_result['result'])
    else:
        print("No audit record results available yet.")
    
    # Demo: Inter-agent communication
    print_section("Inter-Agent Communication Demo")
    
    print("\nDemonstrating communication between agents...")
    
    # Data Quality agent sends message to Compliance agent
    message_content = {
        "data_validation_summary": {
            "parcels_validated": 256,
            "properties_validated": 342,
            "accounts_validated": 256,
            "validation_errors": 15,
            "warning_level": "medium"
        }
    }
    
    # Send message via MCP
    dq_to_comp_message = mcp.send_message(
        from_agent_id=data_quality_agent.agent_id,
        to_agent_id=compliance_agent.agent_id,
        message_type=MessageType.DATA_UPDATE,
        content=message_content
    )
    
    print(f"Message sent from Data Quality Agent to Compliance Agent: {dq_to_comp_message['message_id']}")
    
    # Wait a moment
    time.sleep(2)
    
    # Stop the MCP
    print_section("Shutting Down")
    print("\nStopping the MCP...")
    mcp.stop()
    print("MCP stopped successfully.")
    
    print("\nDemo completed successfully.")

if __name__ == "__main__":
    main()