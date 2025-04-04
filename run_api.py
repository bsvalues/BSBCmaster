"""
This file provides a runner for the FastAPI application.
It allows running the FastAPI application with uvicorn.
"""

import os
import uvicorn
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Define port for the FastAPI application
API_PORT = int(os.environ.get("API_PORT", 8000))

if __name__ == "__main__":
    # Run FastAPI application
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=API_PORT,
        reload=True,
        log_level="info"
    )