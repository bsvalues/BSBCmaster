"""
This script starts both Flask and FastAPI services through the workflow management script.
"""

import os
import sys
import time
import threading
import subprocess

def main():
    """Main function to run the workflow manager."""
    print("Starting MCP Assessor Agent API services through workflow...")
    
    # Run start_application.sh in a separate process
    process = subprocess.Popen(
        ["bash", "start_application.sh"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )
    
    # Read and print output
    for line in iter(process.stdout.readline, ''):
        sys.stdout.write(line)
        sys.stdout.flush()
    
    # Wait for process to complete
    process.wait()
    
    return process.returncode

if __name__ == "__main__":
    sys.exit(main())