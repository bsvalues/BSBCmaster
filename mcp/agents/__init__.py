"""
Agent implementations for Benton County Assessor's Office MCP

This package contains concrete implementations of specialized agents
for the Master Control Program's AI agent framework.
"""

from .data_quality_agent import DataQualityAgent
from .compliance_agent import ComplianceAgent

__all__ = [
    'DataQualityAgent',
    'ComplianceAgent'
]