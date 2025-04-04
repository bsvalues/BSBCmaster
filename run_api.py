"""
This script runs the FastAPI server component of the MCP Assessor Agent API.
It should run in parallel with the Flask application.
"""

import os
import uvicorn
from app import create_app

if __name__ == "__main__":
    # Create and configure the FastAPI app
    app = create_app()
    
    # Run with uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )