#!/usr/bin/env python3
"""
Combined runner for both FastAPI and Flask applications.
"""

import subprocess
import threading
import time
import os
import signal
import sys

# Global processes
processes = []

def run_process(command, name):
    """Run a process and add it to the global processes list."""
    print(f"Starting {name}...")
    process = subprocess.Popen(command, shell=True)
    processes.append((process, name))
    return process

def start_flask():
    """Start the Flask application."""
    return run_process("gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app", "Flask")

def start_fastapi():
    """Start the FastAPI application."""
    return run_process("uvicorn app:app --host 0.0.0.0 --port 8000 --reload", "FastAPI")

def seed_database():
    """Run the database seeding script."""
    print("Seeding database...")
    try:
        result = subprocess.run(["python", "seed_database.py"], capture_output=True, text=True)
        if result.returncode == 0:
            print("Database seeded successfully!")
        else:
            print(f"Database seeding failed: {result.stderr}")
    except Exception as e:
        print(f"Error seeding database: {str(e)}")

def cleanup(signum=None, frame=None):
    """Clean up processes on exit."""
    print("\nShutting down all services...")
    for process, name in processes:
        print(f"Terminating {name}...")
        process.terminate()
    
    # Wait for processes to terminate
    time.sleep(2)
    
    # Force kill any remaining processes
    for process, name in processes:
        if process.poll() is None:
            print(f"Force killing {name}...")
            try:
                process.kill()
            except:
                pass
    
    print("All services stopped.")
    sys.exit(0)

def main():
    """Main function to run both services."""
    # Set up signal handlers
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    # Start services
    fastapi_process = start_fastapi()
    
    # Give FastAPI time to start
    time.sleep(2)
    
    # Seed the database if needed
    seed_database()
    
    # Start Flask
    flask_process = start_flask()
    
    print("\nAll services are running!")
    print("FastAPI is accessible at: http://localhost:8000")
    print("Flask is accessible at: http://localhost:5000")
    
    # Keep the script running
    try:
        while True:
            # Check if any process has died
            for i, (process, name) in enumerate(processes[:]):
                if process.poll() is not None:
                    print(f"{name} process died with exit code {process.returncode}. Restarting...")
                    if name == "Flask":
                        new_process = start_flask()
                    elif name == "FastAPI":
                        new_process = start_fastapi()
                    processes[i] = (new_process, name)
            time.sleep(5)
    except KeyboardInterrupt:
        cleanup()

if __name__ == "__main__":
    main()