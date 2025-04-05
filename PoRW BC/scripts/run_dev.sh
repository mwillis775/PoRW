#!/bin/bash

# scripts/run_dev.sh
# Runs the FastAPI development server using Uvicorn.
#
# Ensure this script has execute permissions: chmod +x scripts/run_dev.sh
#
# Uses `poetry run` to execute within the project's virtual environment.
# Runs the FastAPI 'app' instance located in 'src/porw_blockchain/rpc/main.py'.
# --reload: Enables auto-reloading when code changes are detected.
# --host:   Specifies the host address to bind to (0.0.0.0 makes it accessible on the network).
# --port:   Specifies the port to listen on.

# Default values (can be overridden by environment variables if needed later)
HOST=${APP_HOST:-"0.0.0.0"}
PORT=${APP_PORT:-8000}

echo "Starting FastAPI development server on http://${HOST}:${PORT}"
echo "(Using uvicorn with auto-reload)"

# Check if poetry is available
if ! command -v poetry &> /dev/null
then
    echo "Error: poetry command not found. Please install Poetry and ensure it's in your PATH."
    exit 1
fi

# Execute uvicorn within the poetry environment
poetry run uvicorn src.porw_blockchain.rpc.main:app --reload --host "${HOST}" --port "${PORT}"