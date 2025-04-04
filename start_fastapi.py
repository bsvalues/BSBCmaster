"""
This script starts the FastAPI application using uvicorn.
"""

import os
import logging
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Main function to run the FastAPI application."""
    # Check if API_KEY is set
    api_key = os.environ.get("API_KEY")
    if not api_key:
        custom_key = "b6212a0ff43102f608553e842293eba0ec013ff6926459f96fba31d0fabacd2e"
        logger.warning(f"API_KEY not set. Using custom value: {custom_key[:8]}...")
        os.environ["API_KEY"] = custom_key
    
    # Check if we have OPENAI_API_KEY
    if not os.environ.get("OPENAI_API_KEY"):
        logger.warning("OPENAI_API_KEY not set. Natural language translation will be unavailable.")
    
    # Get FastAPI port from environment variable
    port = int(os.environ.get("FASTAPI_PORT", 8000))
    
    # Start uvicorn server
    logger.info(f"Starting FastAPI application on port {port}")
    uvicorn.run(
        "asgi:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main()