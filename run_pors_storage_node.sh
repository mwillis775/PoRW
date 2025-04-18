#!/bin/bash
# Script to run a PoRS storage node on port 3500

# Create data directory for the PoRS node
mkdir -p ~/.porw/pors_storage_node
mkdir -p ~/.porw/pors_storage_node/storage

# Create a configuration file for the PoRS storage node
cat > ~/.porw/pors_storage_node/config.yaml << EOF
# Node identity
node_id: ""  # Will be generated

# Storage settings
storage_dir: "~/.porw/pors_storage_node/storage"
max_storage_bytes: 1073741824  # 1 GB
min_replication_factor: 1  # Failsafe mode: only require 1 copy initially
target_replication_factor: 3  # Target: 3 copies when more nodes are available

# Protocol settings
challenge_interval_seconds: 3600  # 1 hour
verification_threshold: 0.8  # 80% of challenges must be successful
max_verification_time_seconds: 300  # 5 minutes

# Network settings
storage_port: 3500
node_host: "127.0.0.1"
node_port: 3000

# Failsafe settings
single_node_mode: true
auto_replicate: true
EOF

# Run the PoRS storage node
poetry run python src/porw_blockchain/bin/porw-storage \
  --node-id "storage_node" \
  --storage-dir ~/.porw/pors_storage_node/storage \
  --max-storage 1024 \
  --min-replication 1 \
  --storage-port 3500 \
  --log-level INFO \
  --log-file ~/.porw/pors_storage_node/pors_storage_node.log \
  --node-host 127.0.0.1 \
  --node-port 3000

# Note: The config.yaml file is created but not used directly by the command line.
# In a production environment, you would use the config file instead of command line arguments.
