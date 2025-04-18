#!/bin/bash
# Script to run the PoRW blockchain web interface

# Create data directory for the web interface
mkdir -p ~/.porw/web

# Run the web interface
poetry run python -m src.porw_blockchain.web.simple_app --host 0.0.0.0 --port 8080 --data-dir ~/.porw/web
