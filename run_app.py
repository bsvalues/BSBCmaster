#!/usr/bin/env python3
"""
MCP Assessor Agent API - Combined Runner

This script starts both the Flask documentation interface and the FastAPI service
simultaneously, with proper error handling and graceful shutdown.
"""

import multiprocessing
import os
import signal
import sys
import time
from subprocess import PIPE, Popen

# Add colors for terminal output
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
ENDC = "\033[0m"

# Track running processes for cleanup
processes = []


def run_process(command, name):
    """Run a process and add it to the global processes list."""
    print(f"{BLUE}Starting {name}...{ENDC}")
    process = Popen(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
    processes.append((process, name))
    
    # Start a thread to log output asynchronously
    def log_output():
        for line in process.stdout:
            print(f"{BLUE}[{name}]{ENDC} {line.strip()}")
        for line in process.stderr:
            print(f"{RED}[{name} ERROR]{ENDC} {line.strip()}")
    
    output_thread = multiprocessing.Process(target=log_output)
    output_thread.daemon = True
    output_thread.start()
    
    return process


def start_flask():
    """Start the Flask application."""
    command = "gunicorn --bind 0.0.0.0:5000 --workers 2 --reuse-port --reload main:app"
    return run_process(command, "Flask Docs")


def start_fastapi():
    """Start the FastAPI application."""
    command = "uvicorn app:api --host 0.0.0.0 --port 8000 --reload"
    return run_process(command, "FastAPI")


def seed_database():
    """Run the database seeding script."""
    print(f"{YELLOW}Seeding database if needed...{ENDC}")
    try:
        import seed_database
        seed_database.seed_database()
        print(f"{GREEN}Database seeding completed successfully.{ENDC}")
    except Exception as e:
        print(f"{RED}Error seeding database: {str(e)}{ENDC}")


def cleanup(signum=None, frame=None):
    """Clean up processes on exit."""
    if signum:
        print(f"\n{YELLOW}Received signal {signum}, shutting down...{ENDC}")
    
    for process, name in processes:
        print(f"{YELLOW}Terminating {name}...{ENDC}")
        try:
            process.terminate()
            # Give it a moment to terminate gracefully
            time.sleep(0.5)
            if process.poll() is None:
                process.kill()
                print(f"{RED}Had to force kill {name}{ENDC}")
        except Exception as e:
            print(f"{RED}Error terminating {name}: {str(e)}{ENDC}")
    
    print(f"{GREEN}All processes terminated.{ENDC}")
    sys.exit(0)


def main():
    """Main function to run both services."""
    print(f"{GREEN}===== Starting MCP Assessor Agent API Services ====={ENDC}")
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    try:
        # First seed the database if needed
        seed_database()
        
        # Start the Flask documentation service
        flask_process = start_flask()
        
        # Give Flask a moment to start
        time.sleep(2)
        
        # Start the FastAPI service
        fastapi_process = start_fastapi()
        
        print(f"\n{GREEN}All services started successfully!{ENDC}")
        print(f"{BLUE}Flask documentation available at: http://localhost:5000{ENDC}")
        print(f"{BLUE}FastAPI service available at: http://localhost:8000{ENDC}")
        print(f"{YELLOW}Press Ctrl+C to stop all services{ENDC}")
        
        # Monitor processes and restart if needed
        while True:
            if flask_process.poll() is not None:
                print(f"{RED}Flask process terminated unexpectedly, restarting...{ENDC}")
                flask_process = start_flask()
            
            if fastapi_process.poll() is not None:
                print(f"{RED}FastAPI process terminated unexpectedly, restarting...{ENDC}")
                fastapi_process = start_fastapi()
            
            time.sleep(1)
    
    except KeyboardInterrupt:
        # This shouldn't be reached due to the signal handler, but just in case
        cleanup()
    except Exception as e:
        print(f"{RED}Error in main process: {str(e)}{ENDC}")
        cleanup()


if __name__ == "__main__":
    main()