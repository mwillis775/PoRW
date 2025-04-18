#!/bin/bash
# Script to run a PoRS node on port 2525

# Create data directory for the PoRS node
mkdir -p ~/.porw/pors_node
mkdir -p ~/.porw/pors_node/storage

# Run the PoRS node
poetry run python src/porw_blockchain/bin/porw-node \
  --listen-port 3500 \
  --data-dir ~/.porw/pors_node \
  --log-level INFO \
  --log-file ~/.porw/pors_node/pors_node.log \
  --network testnet \
  --max-peers 10 \
  --min-peers 1
