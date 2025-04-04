"""
MCP Assessor Agent API - Starter Script

This script can be used to quickly start the integrated services 
(FastAPI and Flask) for the MCP Assessor Agent API.
"""

import sys
import os
import subprocess
import time

def print_header():
    """Print the application header."""
    print("\n" + "="*60)
    print("  MCP Assessor Agent API - Integrated Services Starter")
    print("="*60)
    print("This script will start both the Flask documentation interface")
    print("(port 5000) and the FastAPI service (port 8000).")
    print("="*60 + "\n")

def main():
    """Main function to run the services."""
    print_header()
    
    print("Starting integrated services...")
    try:
        # Run the integrated services runner
        subprocess.run(["python", "run_dual_app.py"], check=True)
    except KeyboardInterrupt:
        print("\nReceived keyboard interrupt. Shutting down...")
    except subprocess.CalledProcessError as e:
        print(f"\nError running services: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()