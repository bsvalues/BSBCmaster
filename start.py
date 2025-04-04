#!/usr/bin/env python3
"""
MCP Assessor Agent API - Starter Script

This script provides a menu to quickly launch and manage services
for the MCP Assessor Agent API.
"""

import os
import sys
import subprocess
import time
import signal
import multiprocessing
from typing import List, Tuple

# Running processes
processes = []

# Colors for terminal output
GREEN = "\033[0;32m"
YELLOW = "\033[0;33m"
RED = "\033[0;31m"
BLUE = "\033[0;34m"
NC = "\033[0m"  # No Color


def print_header():
    """Print the application header."""
    os.system('clear' if os.name == 'posix' else 'cls')
    print(f"{GREEN}===================================={NC}")
    print(f"{GREEN}  MCP Assessor Agent API Service  {NC}")
    print(f"{GREEN}===================================={NC}")
    print()


def print_menu():
    """Print the main menu."""
    print(f"{BLUE}Choose an option:{NC}")
    print(f"  {YELLOW}1{NC}. Start Flask Documentation (port 5000)")
    print(f"  {YELLOW}2{NC}. Start FastAPI Service (port 8000)")
    print(f"  {YELLOW}3{NC}. Start Both Services")
    print(f"  {YELLOW}4{NC}. Seed Database")
    print(f"  {YELLOW}5{NC}. Test Database Connection")
    print(f"  {YELLOW}6{NC}. Environment Variables Status")
    print(f"  {YELLOW}0{NC}. Exit")
    print()


def run_process(command: str, name: str) -> subprocess.Popen:
    """Run a command as a subprocess and capture its output."""
    print(f"{BLUE}Starting {name}...{NC}")
    
    # Start the process
    process = subprocess.Popen(
        command, 
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        shell=True
    )
    
    # Add to global processes list
    processes.append((process, name))
    
    # Function to continuously read and display output
    def log_output():
        try:
            for line in process.stdout:
                print(f"{BLUE}[{name}]{NC} {line.strip()}")
            for line in process.stderr:
                print(f"{RED}[{name} ERROR]{NC} {line.strip()}")
        except Exception as e:
            print(f"{RED}Error reading output from {name}: {str(e)}{NC}")
    
    # Start a thread to handle the output asynchronously
    output_thread = multiprocessing.Process(target=log_output)
    output_thread.daemon = True
    output_thread.start()
    
    return process


def start_flask():
    """Start the Flask documentation service."""
    command = "gunicorn --bind 0.0.0.0:5000 --workers 1 --reuse-port --reload main:app"
    process = run_process(command, "Flask")
    time.sleep(1)
    
    # Check if process is running
    if process.poll() is None:
        print(f"{GREEN}Flask documentation running on http://localhost:5000{NC}")
    else:
        print(f"{RED}Flask service failed to start.{NC}")
    
    return process


def start_fastapi():
    """Start the FastAPI service."""
    command = "uvicorn app:app --host 0.0.0.0 --port 8000 --reload"
    process = run_process(command, "FastAPI")
    time.sleep(1)
    
    # Check if process is running
    if process.poll() is None:
        print(f"{GREEN}FastAPI service running on http://localhost:8000{NC}")
        print(f"{GREEN}API docs available at http://localhost:8000/api/docs{NC}")
    else:
        print(f"{RED}FastAPI service failed to start.{NC}")
    
    return process


def seed_database():
    """Run the database seeding script."""
    print(f"{YELLOW}Seeding database...{NC}")
    
    try:
        result = subprocess.run(
            ["python", "seed_database.py"], 
            capture_output=True, 
            text=True, 
            check=True
        )
        print(result.stdout)
        print(f"{GREEN}Database seeded successfully!{NC}")
    except subprocess.CalledProcessError as e:
        print(f"{RED}Error seeding database: {e}{NC}")
        print(e.stdout)
        print(e.stderr)


def test_database_connection():
    """Test the database connection."""
    print(f"{YELLOW}Testing database connection...{NC}")
    
    try:
        from app.db import test_db_connections
        results = test_db_connections()
        
        print(f"{GREEN}Database connection test results:{NC}")
        for db, status in results.items():
            status_str = f"{GREEN}Connected{NC}" if status else f"{RED}Failed{NC}"
            print(f"  - {db}: {status_str}")
    except ImportError:
        print(f"{RED}Error: Could not import database module.{NC}")
    except Exception as e:
        print(f"{RED}Error testing database connection: {str(e)}{NC}")


def check_environment():
    """Check and display environment variables status."""
    print(f"{YELLOW}Environment Variables Status:{NC}")
    
    # Define essential variables
    essential_vars = [
        ("DATABASE_URL", True),
        ("API_KEY", True),
        ("OPENAI_API_KEY", False)  # Not required, but useful
    ]
    
    all_present = True
    
    for var, required in essential_vars:
        value = os.environ.get(var)
        
        if value:
            # Mask the value for security
            if var.endswith("KEY"):
                displayed_value = value[:4] + "..." + value[-4:] if len(value) > 8 else "****"
            else:
                displayed_value = value
            
            print(f"  {GREEN}✓{NC} {var}: {displayed_value}")
        else:
            status = f"{RED}Missing{NC}" if required else f"{YELLOW}Not set{NC}"
            print(f"  {RED}✗{NC} {var}: {status}")
            
            if required:
                all_present = False
                
    if all_present:
        print(f"\n{GREEN}All required environment variables are set.{NC}")
    else:
        print(f"\n{RED}Some required environment variables are missing.{NC}")
        print(f"{YELLOW}Services may not function properly.{NC}")


def cleanup():
    """Clean up all processes on exit."""
    print(f"\n{YELLOW}Shutting down services...{NC}")
    
    for process, name in processes:
        if process.poll() is None:  # If process is still running
            print(f"{YELLOW}Terminating {name}...{NC}")
            try:
                process.terminate()
                # Give it a moment to terminate gracefully
                time.sleep(0.5)
                if process.poll() is None:
                    process.kill()
                    print(f"{RED}Had to force kill {name}{NC}")
            except Exception as e:
                print(f"{RED}Error terminating {name}: {str(e)}{NC}")
    
    print(f"{GREEN}All services stopped.{NC}")


def signal_handler(sig, frame):
    """Handle SIGINT signal (Ctrl+C)."""
    cleanup()
    sys.exit(0)


def main():
    """Main function."""
    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    while True:
        print_header()
        print_menu()
        
        try:
            choice = input(f"{YELLOW}Enter your choice: {NC}")
            
            if choice == "1":
                start_flask()
                input(f"\n{GREEN}Press Enter to return to menu...{NC}")
                cleanup()
            
            elif choice == "2":
                start_fastapi()
                input(f"\n{GREEN}Press Enter to return to menu...{NC}")
                cleanup()
            
            elif choice == "3":
                flask_process = start_flask()
                fastapi_process = start_fastapi()
                
                print(f"\n{GREEN}Both services are now running.{NC}")
                print(f"{YELLOW}Press Enter to stop services and return to menu...{NC}")
                input()
                cleanup()
            
            elif choice == "4":
                seed_database()
                input(f"\n{GREEN}Press Enter to return to menu...{NC}")
            
            elif choice == "5":
                test_database_connection()
                input(f"\n{GREEN}Press Enter to return to menu...{NC}")
            
            elif choice == "6":
                check_environment()
                input(f"\n{GREEN}Press Enter to return to menu...{NC}")
            
            elif choice == "0":
                cleanup()
                print(f"{GREEN}Exiting. Goodbye!{NC}")
                break
            
            else:
                print(f"{RED}Invalid choice. Please try again.{NC}")
                time.sleep(1)
        
        except KeyboardInterrupt:
            cleanup()
            print(f"{GREEN}Exiting. Goodbye!{NC}")
            break
        
        except Exception as e:
            print(f"{RED}Error: {str(e)}{NC}")
            time.sleep(2)


if __name__ == "__main__":
    main()