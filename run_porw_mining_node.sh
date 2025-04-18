#!/bin/bash
# Script to run a PoRW mining node on port 3000

# Create data directory for the PoRW node
mkdir -p ~/.porw/porw_mining_node
mkdir -p ~/.porw/porw_mining_node/protein_data

# Create a configuration file for the PoRW mining node
cat > ~/.porw/porw_mining_node/config.yaml << EOF
# Node identity
node_id: ""  # Will be generated
listen_ip: "0.0.0.0"
listen_port: 3000

# Network settings
network: "testnet"
max_peers: 10
min_peers: 1

# API settings
enable_api: true
api_host: "127.0.0.1"
api_port: 8080

# Mining settings
enable_mining: true
mining_threads: 4
enable_gpu: true
protein_data_dir: "~/.porw/porw_mining_node/protein_data"

# Storage settings
enable_storage: false

# Data directory
data_dir: "~/.porw/porw_mining_node"

# Logging
log_level: "info"
log_file: "~/.porw/porw_mining_node/porw_mining_node.log"

# Failsafe settings
single_node_mode: true
auto_replicate: true
EOF

# Run the PoRW node with mining enabled
poetry run python src/porw_blockchain/bin/porw-node \
  --listen-port 3000 \
  --data-dir ~/.porw/porw_mining_node \
  --log-level INFO \
  --log-file ~/.porw/porw_mining_node/porw_mining_node.log \
  --network testnet \
  --max-peers 10 \
  --min-peers 1 \
  --bootstrap-node "storage_node@127.0.0.1:3500"

# Note: The config.yaml file is created but not used directly by the command line.
# In a production environment, you would use the config file instead of command line arguments.
