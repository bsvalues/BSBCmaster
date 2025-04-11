# Valuation Agent

## Overview

The Valuation Agent is a key component of the Benton County Assessor's Office AI Platform. It is responsible for estimating property values using various valuation methodologies, including:

1. **Cost Approach**: Estimates property value based on the cost to replace or reproduce the property, less depreciation.
2. **Market Comparison Approach**: Estimates property value by comparing the subject property to similar properties that have recently sold.
3. **Income Approach**: Estimates property value based on the income the property generates, primarily used for commercial properties.

The Valuation Agent also provides trend analysis and comparative property analysis capabilities.

## Architecture

The Valuation Agent is built on the agent framework of the Master Control Program (MCP) and integrates with the Core Hub for inter-agent communication. Key components include:

- `agent.py`: The main Valuation Agent implementation with valuation methodologies
- `factory.py`: Factory functions for creating and registering Valuation Agents
- `__init__.py`: Package initialization and exports

## Features

### Property Valuation

The Valuation Agent can calculate property values using three different methodologies:

#### Cost Approach

1. Calculates replacement cost based on property type, quality, and size
2. Applies depreciation based on age of the property
3. Adds land value and applies location adjustment factors
4. Returns detailed breakdown of the valuation calculations

#### Market Comparison Approach

1. Finds comparable properties with similar characteristics
2. Applies adjustments for differences in size, bedrooms, bathrooms, etc.
3. Calculates adjusted values for each comparable
4. Returns a weighted average of comparable property values

#### Income Approach

1. Estimates rental income based on property type and location
2. Applies vacancy and collection loss rates
3. Subtracts operating expenses
4. Applies capitalization rate to calculate property value
5. Returns detailed breakdown of income-based valuation

### Trend Analysis

The Valuation Agent can analyze property value trends:

1. Projects property values into the past and future
2. Uses location-specific growth rates based on historical data
3. Returns year-by-year trend data with growth rates

### Comparative Analysis

The Valuation Agent can perform comparative analyses between properties:

1. Compares a subject property with multiple comparable properties
2. Calculates value metrics including average values, percentile ranks, etc.
3. Returns detailed comparison metrics for reporting

## Message Types

The Valuation Agent responds to the following message types:

- `VALUATION_REQUEST`: Request for property valuation
- `TREND_ANALYSIS_REQUEST`: Request for property value trend analysis
- `COMPARATIVE_ANALYSIS_REQUEST`: Request for comparative property analysis

## Usage Examples

### Property Valuation Request

```python
# Example valuation request
mcp.send_message(
    Message(
        from_agent_id="client",
        to_agent_id="valuation_agent",
        message_type=MessageType.VALUATION_REQUEST,
        content={
            "property_id": 1,
            "methodology": "all"  # Or "cost", "market", "income"
        }
    )
)
```

### Trend Analysis Request

```python
# Example trend analysis request
mcp.send_message(
    Message(
        from_agent_id="client",
        to_agent_id="valuation_agent",
        message_type=MessageType.TREND_ANALYSIS_REQUEST,
        content={
            "property_id": 1,
            "years": 5  # Number of years to analyze
        }
    )
)
```

### Comparative Analysis Request

```python
# Example comparative analysis request
mcp.send_message(
    Message(
        from_agent_id="client",
        to_agent_id="valuation_agent",
        message_type=MessageType.COMPARATIVE_ANALYSIS_REQUEST,
        content={
            "property_id": 1,
            "comparison_property_ids": [2, 3, 4]  # Optional: If not provided, similar properties will be found
        }
    )
)
```

## Running Tests

To run the Valuation Agent tests:

```bash
python run_valuation_tests.py
```

This will run both unit tests and integration tests for the Valuation Agent.

## Integration with Core Hub

The Valuation Agent integrates with the Core Hub system of the platform:

```python
from core import CoreHub
from mcp.agents.valuation.factory import register_valuation_agent

# Create Core Hub
hub = CoreHub()

# Register Valuation Agent
agent = register_valuation_agent(hub)

# Start the hub
hub.start()
```

## Dependencies

- SQLAlchemy for database access
- NumPy for numerical calculations
- The Master Control Program (MCP) agent framework
- Core Hub communication system