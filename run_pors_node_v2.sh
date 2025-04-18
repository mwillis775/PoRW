#!/bin/bash
# Script to run a PoRS node on port 3500

# Create data directory for the PoRS node
mkdir -p ~/.porw/pors_node
mkdir -p ~/.porw/pors_node/storage

# Run the PoRS node
poetry run python src/porw_blockchain/bin/porw-storage \
  --storage-dir ~/.porw/pors_node/storage \
  --max-storage 1024 \
  --min-replication 3 \
  --storage-port 3500 \
  --log-level INFO \
  --log-file ~/.porw/pors_node/pors_node.log \
  --no-blockchain
