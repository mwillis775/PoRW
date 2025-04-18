#!/bin/bash
# Script to run a PoRW node on port 2025

# Create data directory for the PoRW node
mkdir -p ~/.porw/porw_node

# Run the PoRW node
poetry run python src/porw_blockchain/bin/porw-node \
  --listen-port 3000 \
  --data-dir ~/.porw/porw_node \
  --log-level INFO \
  --log-file ~/.porw/porw_node/porw_node.log \
  --network testnet \
  --max-peers 10 \
  --min-peers 1 \
  --bootstrap-node "pors_node@127.0.0.1:3500"
