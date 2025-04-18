#!/usr/bin/env python3
"""
Run the PoRW blockchain server on port 2000.
"""

import sys
import os
import subprocess
import signal
import time
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def run_server():
    """Run the blockchain server on port 2000."""
    print("Starting PoRW blockchain server on port 2000...")

    # Set environment variable for Python path
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).parent)

    # Run the server
    server_process = subprocess.Popen(
        ["python3", "src/porw_blockchain/bin/porw-api", "--port", "2000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env
    )

    # Wait for the server to start
    time.sleep(2)

    # Check if the server is running
    if server_process.poll() is None:
        print("Server is running on port 2000")
        return server_process
    else:
        stdout, stderr = server_process.communicate()
        print(f"Server failed to start: {stderr}")
        return None

if __name__ == "__main__":
    # Run the server
    server_process = run_server()

    if server_process:
        try:
            # Keep the server running
            print("Press Ctrl+C to stop the server")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            # Stop the server
            print("\nStopping server...")
            server_process.terminate()
            server_process.wait()
            print("Server stopped")
