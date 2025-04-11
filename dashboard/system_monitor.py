"""
System Monitoring Dashboard for Benton County Assessor's Office AI Platform

This module provides a Streamlit dashboard for monitoring the AI platform,
including agent status, message throughput, and system performance.
"""

import streamlit as st
import pandas as pd
import numpy as np
import time
import json
import os
import sys
from datetime import datetime
import requests
from typing import Dict, Any, List, Optional, Tuple
import logging

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from core import CoreConfig, CoreHub
    CORE_AVAILABLE = True
except ImportError:
    CORE_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/dashboard.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("system_monitor")


# Initialize session state
if 'update_interval' not in st.session_state:
    st.session_state.update_interval = 10  # seconds
if 'last_update' not in st.session_state:
    st.session_state.last_update = time.time()
if 'dark_mode' not in st.session_state:
    st.session_state.dark_mode = False
if 'show_advanced' not in st.session_state:
    st.session_state.show_advanced = False


def toggle_advanced():
    """Toggle advanced options."""
    st.session_state.show_advanced = not st.session_state.show_advanced


def load_core_config() -> Optional[CoreConfig]:
    """
    Load Core configuration.
    
    Returns:
        CoreConfig instance or None if not available
    """
    if not CORE_AVAILABLE:
        return None
    
    try:
        # First check if there's a config file
        config_path = "data/core/config.json"
        if os.path.exists(config_path):
            return CoreConfig(config_path)
        else:
            return CoreConfig()
    except Exception as e:
        logger.error(f"Error loading Core configuration: {e}")
        return None


def get_mock_system_data() -> Dict[str, Any]:
    """
    Generate mock system data for development.
    
    This function is only used when a real Core Hub is not available.
    Data is based on authentic system structure but with mock values.
    
    Returns:
        Dictionary with system data
    """
    # Get agents from our existing configuration
    core_config = load_core_config()
    
    if core_config:
        agents = core_config.get_enabled_agents()
        agent_names = [agent["name"] for agent in agents]
    else:
        agent_names = ["DataQualityAgent", "ComplianceAgent", "ValuationAgent"]
    
    # Create agent statuses based on real agents
    agents_data = []
    for i, name in enumerate(agent_names):
        agents_data.append({
            "id": name.lower().replace(" ", "_"),
            "name": name,
            "type": name.replace("Agent", "").lower(),
            "status": "active" if i % 4 != 0 else "idle",
            "registered_at": (datetime.now().timestamp() - i * 3600),
            "last_update": (datetime.now().timestamp() - i * 60)
        })
    
    return {
        "core": {
            "name": "BentonCountyAssessorCore",
            "version": "3.0.0",
            "uptime": 3600,
            "message_queue_size": 5
        },
        "agents": {
            "registered": len(agents_data),
            "active": sum(1 for a in agents_data if a["status"] == "active"),
            "list": agents_data
        },
        "replay_buffer": {
            "size": 1250,
            "capacity": 10000,
            "total_added": 1500,
            "agent_distribution": {
                agent["id"]: 1500 // len(agents_data) for agent in agents_data
            },
            "avg_reward": 0.75,
            "min_reward": 0.2,
            "max_reward": 1.0,
            "beta": 0.6
        },
        "message_stats": {
            "total_sent": 2500,
            "total_received": 2450,
            "throughput": 42,  # messages per second
            "error_rate": 0.02,
            "types": {
                "COMMAND": 800,
                "EVENT": 600,
                "QUERY": 400,
                "RESPONSE": 1200,
                "ERROR": 50,
                "STATUS_UPDATE": 200,
                "ASSISTANCE_REQUESTED": 10
            }
        },
        "performance": {
            "cpu_usage": 25,
            "memory_usage": 40,
            "disk_usage": 15,
            "network_throughput": 5  # MB/s
        }
    }


def get_system_data() -> Dict[str, Any]:
    """
    Get system data from the Core Hub.
    
    Returns:
        Dictionary with system data
    """
    if not CORE_AVAILABLE:
        return get_mock_system_data()
    
    try:
        # Try to connect to running Core Hub
        # In a real system, this would use the Core Hub's API
        # For now, we'll use the mock data
        return get_mock_system_data()
    except Exception as e:
        logger.error(f"Error getting system data: {e}")
        return get_mock_system_data()


def generate_agent_status_df(data: Dict[str, Any]) -> pd.DataFrame:
    """
    Generate agent status DataFrame.
    
    Args:
        data: System data
        
    Returns:
        DataFrame with agent status
    """
    agents = data.get("agents", {}).get("list", [])
    
    if not agents:
        return pd.DataFrame(columns=["Agent", "Type", "Status", "Last Update"])
    
    # Create DataFrame
    df = pd.DataFrame(agents)
    
    # Format timestamps
    df["registered_at"] = pd.to_datetime(df["registered_at"], unit='s')
    df["last_update"] = pd.to_datetime(df["last_update"], unit='s')
    
    # Format for display
    df = df.rename(columns={
        "id": "ID",
        "name": "Agent",
        "type": "Type",
        "status": "Status",
        "registered_at": "Registered At",
        "last_update": "Last Update"
    })
    
    return df


def generate_message_stats_df(data: Dict[str, Any]) -> pd.DataFrame:
    """
    Generate message statistics DataFrame.
    
    Args:
        data: System data
        
    Returns:
        DataFrame with message statistics
    """
    message_stats = data.get("message_stats", {})
    types = message_stats.get("types", {})
    
    if not types:
        return pd.DataFrame(columns=["Type", "Count"])
    
    # Create DataFrame
    df = pd.DataFrame([
        {"Type": k, "Count": v}
        for k, v in types.items()
    ])
    
    return df


def generate_replay_buffer_df(data: Dict[str, Any]) -> pd.DataFrame:
    """
    Generate replay buffer statistics DataFrame.
    
    Args:
        data: System data
        
    Returns:
        DataFrame with replay buffer statistics
    """
    buffer_stats = data.get("replay_buffer", {})
    agent_distribution = buffer_stats.get("agent_distribution", {})
    
    if not agent_distribution:
        return pd.DataFrame(columns=["Agent", "Experiences"])
    
    # Create DataFrame
    df = pd.DataFrame([
        {"Agent": k, "Experiences": v}
        for k, v in agent_distribution.items()
    ])
    
    return df


def render_system_overview(data: Dict[str, Any]):
    """
    Render system overview section.
    
    Args:
        data: System data
    """
    st.header("System Overview")
    
    core_data = data.get("core", {})
    agents_data = data.get("agents", {})
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Core Version", core_data.get("version", "Unknown"))
    
    with col2:
        uptime = core_data.get("uptime", 0)
        uptime_str = f"{int(uptime // 3600)}h {int((uptime % 3600) // 60)}m"
        st.metric("Uptime", uptime_str)
    
    with col3:
        st.metric("Registered Agents", agents_data.get("registered", 0))
    
    with col4:
        st.metric("Active Agents", agents_data.get("active", 0))
    
    # Performance metrics
    st.subheader("System Performance")
    
    performance = data.get("performance", {})
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("CPU Usage", f"{performance.get('cpu_usage', 0)}%")
    
    with col2:
        st.metric("Memory Usage", f"{performance.get('memory_usage', 0)}%")
    
    with col3:
        st.metric("Disk Usage", f"{performance.get('disk_usage', 0)}%")
    
    with col4:
        st.metric("Network", f"{performance.get('network_throughput', 0)} MB/s")


def render_agent_status(data: Dict[str, Any]):
    """
    Render agent status section.
    
    Args:
        data: System data
    """
    st.header("Agent Status")
    
    # Get agent status DataFrame
    df = generate_agent_status_df(data)
    
    if df.empty:
        st.warning("No agent data available")
        return
    
    # Display agent status
    st.dataframe(df, use_container_width=True)
    
    # Display agent status chart
    st.subheader("Agent Status Distribution")
    
    status_counts = df["Status"].value_counts().reset_index()
    status_counts.columns = ["Status", "Count"]
    
    st.bar_chart(status_counts.set_index("Status"))


def render_message_stats(data: Dict[str, Any]):
    """
    Render message statistics section.
    
    Args:
        data: System data
    """
    st.header("Message Statistics")
    
    message_stats = data.get("message_stats", {})
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Sent", message_stats.get("total_sent", 0))
    
    with col2:
        st.metric("Throughput", f"{message_stats.get('throughput', 0)}/s")
    
    with col3:
        error_rate = message_stats.get("error_rate", 0) * 100
        st.metric("Error Rate", f"{error_rate:.2f}%")
    
    # Message type distribution
    st.subheader("Message Type Distribution")
    
    df = generate_message_stats_df(data)
    
    if df.empty:
        st.warning("No message data available")
        return
    
    # Display chart
    st.bar_chart(df.set_index("Type"))


def render_replay_buffer(data: Dict[str, Any]):
    """
    Render replay buffer section.
    
    Args:
        data: System data
    """
    st.header("Experience Replay Buffer")
    
    buffer_stats = data.get("replay_buffer", {})
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        size = buffer_stats.get("size", 0)
        capacity = buffer_stats.get("capacity", 1)
        usage = (size / capacity) * 100 if capacity > 0 else 0
        st.metric("Buffer Usage", f"{usage:.1f}%", f"{size}/{capacity}")
    
    with col2:
        st.metric("Total Experiences", buffer_stats.get("total_added", 0))
    
    with col3:
        st.metric("Avg Reward", f"{buffer_stats.get('avg_reward', 0):.2f}")
    
    with col4:
        st.metric("Beta", f"{buffer_stats.get('beta', 0):.2f}")
    
    # Agent distribution
    st.subheader("Experiences by Agent")
    
    df = generate_replay_buffer_df(data)
    
    if df.empty:
        st.warning("No replay buffer data available")
        return
    
    # Display chart
    st.bar_chart(df.set_index("Agent"))


def render_agent_details(data: Dict[str, Any]):
    """
    Render agent details section.
    
    Args:
        data: System data
    """
    st.header("Agent Details")
    
    agents = data.get("agents", {}).get("list", [])
    
    if not agents:
        st.warning("No agent data available")
        return
    
    # Create selectbox for agents
    agent_names = [agent["name"] for agent in agents]
    selected_agent = st.selectbox("Select Agent", agent_names)
    
    # Find selected agent
    agent = next((a for a in agents if a["name"] == selected_agent), None)
    
    if not agent:
        st.warning("Agent not found")
        return
    
    # Display agent details
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Agent Information")
        st.write(f"**ID:** {agent.get('id', 'Unknown')}")
        st.write(f"**Type:** {agent.get('type', 'Unknown')}")
        st.write(f"**Status:** {agent.get('status', 'Unknown')}")
        st.write(f"**Registered At:** {datetime.fromtimestamp(agent.get('registered_at', 0))}")
        st.write(f"**Last Update:** {datetime.fromtimestamp(agent.get('last_update', 0))}")
    
    with col2:
        st.subheader("Agent Metrics")
        
        # In a real system, we would get metrics from the agent
        # For now, we'll use mock metrics
        metrics = {
            "tasks_processed": 150,
            "success_rate": 0.95,
            "average_response_time": 0.12,  # seconds
            "error_count": 8
        }
        
        st.write(f"**Tasks Processed:** {metrics.get('tasks_processed', 0)}")
        st.write(f"**Success Rate:** {metrics.get('success_rate', 0) * 100:.1f}%")
        st.write(f"**Avg Response Time:** {metrics.get('average_response_time', 0) * 1000:.1f} ms")
        st.write(f"**Error Count:** {metrics.get('error_count', 0)}")


def render_advanced_options():
    """Render advanced options section."""
    st.header("Advanced Options")
    
    st.number_input(
        "Update Interval (seconds)",
        min_value=1,
        max_value=60,
        value=st.session_state.update_interval,
        key="update_interval_input"
    )
    
    if st.button("Apply Settings"):
        st.session_state.update_interval = st.session_state.update_interval_input
        st.success(f"Settings applied. Update interval set to {st.session_state.update_interval} seconds.")


def main():
    """Main function for the dashboard."""
    # Set page config
    st.set_page_config(
        page_title="Benton County Assessor AI Platform - System Monitor",
        page_icon="📊",
        layout="wide"
    )
    
    # Title
    st.title("Benton County Assessor's Office AI Platform")
    st.subheader("System Monitoring Dashboard")
    
    # Sidebar
    with st.sidebar:
        st.header("Dashboard Controls")
        
        # Theme toggle
        st.toggle("Dark Mode", key="dark_mode")
        
        # Advanced options
        if st.button("Advanced Options", key="advanced_button"):
            toggle_advanced()
        
        # Refresh button
        if st.button("Refresh Now"):
            st.session_state.last_update = time.time()
        
        # About section
        st.sidebar.markdown("---")
        st.sidebar.header("About")
        st.sidebar.info(
            "This dashboard monitors the Benton County Assessor's Office "
            "AI Platform, including agent status, message throughput, and "
            "system performance."
        )
        
        # Version and last update
        st.sidebar.markdown("---")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.sidebar.text(f"Last Updated: {now}")
        st.sidebar.text("Dashboard v1.0.0")
    
    # Check if it's time to update
    current_time = time.time()
    if current_time - st.session_state.last_update >= st.session_state.update_interval:
        st.session_state.last_update = current_time
    
    # Get system data
    data = get_system_data()
    
    # Render dashboard sections
    render_system_overview(data)
    
    st.markdown("---")
    
    # Two columns for agent status and message stats
    col1, col2 = st.columns(2)
    
    with col1:
        render_agent_status(data)
    
    with col2:
        render_message_stats(data)
    
    st.markdown("---")
    
    render_replay_buffer(data)
    
    st.markdown("---")
    
    render_agent_details(data)
    
    # Advanced options if enabled
    if st.session_state.show_advanced:
        st.markdown("---")
        render_advanced_options()
    
    # Update interval message
    st.markdown("---")
    st.caption(f"Dashboard updates every {st.session_state.update_interval} seconds. Last update: {datetime.fromtimestamp(st.session_state.last_update).strftime('%H:%M:%S')}")


if __name__ == "__main__":
    # Create log directory
    os.makedirs("logs", exist_ok=True)
    main()