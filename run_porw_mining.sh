#!/bin/bash
# Script to run a PoRW mining node

# Create data directory for the PoRW mining node
mkdir -p ~/.porw/porw_mining
mkdir -p ~/.porw/porw_mining/protein_data

# Run the PoRW mining node
poetry run python src/porw_blockchain/bin/porw-miner \
  --enable-mining \
  --mining-threads 4 \
  --enable-gpu \
  --protein-data-dir ~/.porw/porw_mining/protein_data \
  --node-host 127.0.0.1 \
  --node-port 3000 \
  --log-level INFO \
  --log-file ~/.porw/porw_mining/porw_mining.log
